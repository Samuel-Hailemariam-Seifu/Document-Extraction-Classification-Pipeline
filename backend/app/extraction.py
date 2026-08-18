"""Invoice extraction via Groq vision (OpenAI-compatible client)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.config import get_settings
from app.images import UnreadableDocumentError, assert_file_looks_valid, file_to_image_data_urls
from app.rate_limit import update_from_headers
from app.schemas import ExtractedInvoice

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 1.5


@dataclass(frozen=True)
class ExtractionResult:
    extracted: ExtractedInvoice
    warnings: list[str] = field(default_factory=list)

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "vendor_name": {
            "type": ["string", "null"],
            "description": "Merchant or vendor name as printed on the document",
        },
        "vendor_address": {
            "type": ["string", "null"],
            "description": "Vendor address as printed; null if absent",
        },
        "invoice_number": {
            "type": ["string", "number", "null"],
            "description": (
                "Invoice or receipt number as a string when possible; "
                "numeric IDs are accepted and coerced to string server-side"
            ),
        },
        "document_date": {
            "type": ["string", "null"],
            "description": "Issue date in YYYY-MM-DD (not the due date)",
        },
        "due_date": {
            "type": ["string", "null"],
            "description": "Payment due date in YYYY-MM-DD; null if absent",
        },
        "payment_terms": {
            "type": ["string", "null"],
            "description": "Payment terms as printed, e.g. Net 30; null if absent",
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "line_total": {"type": ["number", "null"]},
                    "item_tax": {
                        "type": ["number", "null"],
                        "description": "Tax on this line only if broken out per line",
                    },
                    "item_discount": {
                        "type": ["number", "null"],
                        "description": "Discount on this line only if broken out per line",
                    },
                },
                "required": [
                    "description",
                    "quantity",
                    "unit_price",
                    "line_total",
                    "item_tax",
                    "item_discount",
                ],
            },
        },
        "subtotal": {"type": ["number", "null"]},
        "tax": {
            "type": ["number", "null"],
            "description": "Total tax (sole amount, or sum of tax_lines)",
        },
        "tax_rate": {
            "type": ["number", "null"],
            "description": "Tax rate as fraction when stated, e.g. 0.085 for 8.5%",
        },
        "tax_lines": {
            "type": "array",
            "description": "Multiple tax components when listed separately",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["label", "amount"],
            },
        },
        "shipping": {"type": ["number", "null"]},
        "discount": {"type": ["number", "null"]},
        "total": {"type": ["number", "null"]},
        "currency": {
            "type": ["string", "null"],
            "description": "Currency code like USD, EUR, GBP when explicitly stated or clearly implied",
        },
    },
    "required": [
        "vendor_name",
        "vendor_address",
        "invoice_number",
        "document_date",
        "due_date",
        "payment_terms",
        "line_items",
        "subtotal",
        "tax",
        "tax_rate",
        "tax_lines",
        "shipping",
        "discount",
        "total",
        "currency",
    ],
}

SYSTEM_PROMPT = """You are an expert invoice and receipt data extraction engine.
Extract fields from the provided document image(s) into JSON matching the schema.
Rules:
- Use null for any field you cannot read confidently. Do not invent values.
- Extract invoice_number, due_date, tax_rate, vendor_address, and payment_terms if present; use null when absent. Do not guess.
- document_date is the issue date. due_date is the payment due date. Never conflate them; if only one date appears and it is clearly an issue/invoice date, put it in document_date and leave due_date null (and vice versa if it is clearly a due date only).
- Dates must be YYYY-MM-DD or null.
- Prefer printed totals over recomputed ones when both appear.
- If currency is not explicitly stated or clearly implied by an explicit symbol (e.g. $, €, £), return null rather than guessing.
- If the document shows multiple tax line items (e.g. state tax, local tax) rather than one tax total, populate tax_lines with each labeled amount and set top-level tax to their sum. If there is only a single tax amount, set tax and leave tax_lines empty.
- tax_rate: when a rate is printed (e.g. 8.5% or 0.085), store it as a fraction (0.085). Null if not shown.
- If any line item has its own tax or discount broken out separately from document-level totals, populate item_tax / item_discount on that line item. Do not fold those into top-level tax or discount.
- shipping and discount: document-level amounts only when printed as such; null if absent.
- Include every visible line item; skip decorative headers/footers.
- Numbers must be plain JSON numbers (no currency symbols or thousands separators).
Return JSON only."""


class ExtractionError(Exception):
    """User-facing extraction failure with a stable machine-readable code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "extraction_failed",
        http_status: int = 422,
        reset_hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status
        self.reset_hint = reset_hint

    def to_detail(self) -> dict[str, Any]:
        body: dict[str, Any] = {"message": self.message, "code": self.code}
        if self.reset_hint:
            body["reset_hint"] = self.reset_hint
        return body


MSG_RATE_LIMITED = "Rate limit reached, please wait a moment and try again"
MSG_MODEL_LIMITATION = "This document couldn't be processed due to a model limitation"
MSG_SERVICE_UNAVAILABLE = "The extraction service is temporarily unavailable, please try again"
MSG_UNREADABLE = "This file couldn't be read, please check the format and try again"
MSG_UNSTRUCTURED = "Extraction couldn't produce structured data for this document"


async def extract_invoice(file_path: Path, content_type: str) -> ExtractionResult:
    settings = get_settings()
    if not settings.groq_api_key or settings.groq_api_key.startswith("gsk_your"):
        raise ExtractionError(
            "GROQ_API_KEY is not configured. Copy .env.example to backend/.env "
            "and set your key from https://console.groq.com/keys",
            code="config_error",
            http_status=503,
        )

    warnings: list[str] = []
    try:
        assert_file_looks_valid(file_path, content_type)
        prepared = file_to_image_data_urls(file_path, content_type)
    except UnreadableDocumentError as exc:
        raise ExtractionError(MSG_UNREADABLE, code="unreadable_file", http_status=400) from exc

    if prepared.truncated:
        msg = (
            f"Only first {prepared.pages_sent} of {prepared.pages_total} pages "
            "were processed"
        )
        warnings.append(msg)
        logger.warning("%s (%s)", msg, file_path.name)

    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )

    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Extract the invoice/receipt fields from this document into JSON. "
                "Follow the schema exactly."
            ),
        }
    ]
    for url in prepared.data_urls:
        user_content.append({"type": "image_url", "image_url": {"url": url}})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        raw = await _call_groq_for_json(
            client, settings.groq_model, messages, image_metas=prepared.metas
        )
        extracted = _parse_extracted(raw)
    except ExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected extraction failure")
        raise ExtractionError(
            MSG_SERVICE_UNAVAILABLE, code="service_unavailable", http_status=503
        ) from exc

    return ExtractionResult(extracted=extracted, warnings=warnings)


class _StrategyRejected(Exception):
    """Current structured-output mode isn't supported; try the next one."""


def _messages_have_images(messages: list[dict[str, Any]]) -> bool:
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


async def _call_groq_for_json(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, Any]],
    image_metas: list[dict[str, Any]] | None = None,
) -> str:
    """Vision: tool_call then json_object. Text-only: json_schema cascade."""
    image_metas = image_metas or []
    if _messages_have_images(messages):
        strategies = (_via_tool_call, _via_json_object)
    else:
        strategies = (_via_json_schema, _via_json_object, _via_tool_call)

    last_error: Exception | None = None

    for strategy in strategies:
        try:

            async def _run(s=strategy) -> str:
                logger.debug(
                    "Groq API call: model=%s strategy=%s images=%s",
                    model,
                    s.__name__,
                    image_metas,
                )
                return await s(client, model, messages)

            result = await _with_transient_retries(_run)
            logger.info(
                "Extraction strategy succeeded: %s (model=%s)",
                strategy.__name__,
                model,
            )
            return result
        except _StrategyRejected as exc:
            logger.warning("Extraction strategy %s rejected: %s", strategy.__name__, exc)
            last_error = exc
            continue
        except ExtractionError:
            raise

    logger.warning("All extraction strategies failed: %s", last_error)
    if isinstance(last_error, _StrategyRejected):
        raise ExtractionError(MSG_MODEL_LIMITATION, code="model_limitation", http_status=400)
    raise ExtractionError(MSG_UNSTRUCTURED, code="unstructured", http_status=422)


async def _with_transient_retries(fn) -> str:
    """Retry only rate limits, 5xx, and timeouts — never permanent 400s."""
    delay = INITIAL_BACKOFF_SEC
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await fn()
        except _StrategyRejected:
            raise
        except ExtractionError as exc:
            if exc.code in {"rate_limited", "service_unavailable"} and attempt < MAX_RETRIES:
                last_exc = exc
                logger.warning(
                    "Transient extraction error (attempt %s/%s): %s",
                    attempt,
                    MAX_RETRIES,
                    exc.message,
                )
            else:
                raise
        except RateLimitError as exc:
            last_exc = exc
            _capture_rate_limit_from_exc(exc)
            if attempt >= MAX_RETRIES:
                raise _rate_limit_error(exc) from exc
            logger.warning("Groq rate limited (attempt %s/%s)", attempt, MAX_RETRIES)
        except APITimeoutError as exc:
            last_exc = exc
            if attempt >= MAX_RETRIES:
                raise ExtractionError(
                    MSG_SERVICE_UNAVAILABLE, code="service_unavailable", http_status=503
                ) from exc
            logger.warning("Groq timeout (attempt %s/%s)", attempt, MAX_RETRIES)
        except APIConnectionError as exc:
            last_exc = exc
            if attempt >= MAX_RETRIES:
                raise ExtractionError(
                    MSG_SERVICE_UNAVAILABLE, code="service_unavailable", http_status=503
                ) from exc
            logger.warning("Groq connection error (attempt %s/%s)", attempt, MAX_RETRIES)
        except APIStatusError as exc:
            _capture_rate_limit_from_exc(exc)
            if exc.status_code == 429:
                last_exc = exc
                if attempt >= MAX_RETRIES:
                    raise _rate_limit_error(exc) from exc
                logger.warning("Groq 429 (attempt %s/%s)", attempt, MAX_RETRIES)
            elif exc.status_code in {400, 413, 422}:
                raise _StrategyRejected(MSG_MODEL_LIMITATION) from exc
            elif exc.status_code >= 500:
                last_exc = exc
                if attempt >= MAX_RETRIES:
                    raise ExtractionError(
                        MSG_SERVICE_UNAVAILABLE,
                        code="service_unavailable",
                        http_status=503,
                    ) from exc
                logger.warning("Groq %s (attempt %s/%s)", exc.status_code, attempt, MAX_RETRIES)
            elif exc.status_code == 401:
                raise ExtractionError(
                    "Invalid GROQ_API_KEY. Check your key at console.groq.com/keys",
                    code="config_error",
                    http_status=503,
                ) from exc
            else:
                raise ExtractionError(
                    MSG_SERVICE_UNAVAILABLE, code="service_unavailable", http_status=503
                ) from exc

        await asyncio.sleep(delay)
        delay *= 2

    raise ExtractionError(
        MSG_SERVICE_UNAVAILABLE, code="service_unavailable", http_status=503
    ) from last_exc


def _capture_rate_limit_from_exc(exc: Exception) -> None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        update_from_headers(headers)


def _rate_limit_error(exc: Exception) -> ExtractionError:
    reset_hint = None
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        snap = update_from_headers(headers)
        reset_hint = snap.reset_requests
    message = MSG_RATE_LIMITED
    if reset_hint:
        message = f"{MSG_RATE_LIMITED} (resets in {reset_hint})"
    return ExtractionError(
        message, code="rate_limited", http_status=429, reset_hint=reset_hint
    )


async def _create_completion(client: AsyncOpenAI, **kwargs: Any) -> Any:
    """Call chat.completions with raw response so rate-limit headers are captured."""
    raw = await client.chat.completions.with_raw_response.create(**kwargs)
    try:
        update_from_headers(raw.headers)
    except Exception:  # noqa: BLE001
        logger.debug("Could not parse rate-limit headers", exc_info=True)
    return raw.parse()


async def _via_json_schema(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, Any]],
) -> str:
    completion = await _create_completion(
        client,
        model=model,
        messages=messages,
        temperature=0,
        max_completion_tokens=4096,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "extracted_invoice",
                "schema": EXTRACTION_SCHEMA,
            },
        },
        **_qwen_kwargs(model),
    )
    return _content_or_raise(completion)


async def _via_json_object(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, Any]],
) -> str:
    completion = await _create_completion(
        client,
        model=model,
        messages=messages,
        temperature=0,
        max_completion_tokens=4096,
        response_format={"type": "json_object"},
        **_qwen_kwargs(model),
    )
    return _content_or_raise(completion)


async def _via_tool_call(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, Any]],
) -> str:
    completion = await _create_completion(
        client,
        model=model,
        messages=messages,
        temperature=0,
        max_completion_tokens=4096,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "save_invoice_extraction",
                    "description": "Save structured invoice/receipt fields extracted from the document",
                    "parameters": EXTRACTION_SCHEMA,
                },
            }
        ],
        tool_choice={
            "type": "function",
            "function": {"name": "save_invoice_extraction"},
        },
        **_qwen_kwargs(model),
    )
    message = completion.choices[0].message
    if not message.tool_calls:
        raise ExtractionError(MSG_UNSTRUCTURED, code="unstructured", http_status=422)
    args = message.tool_calls[0].function.arguments
    if not args:
        raise ExtractionError(MSG_UNSTRUCTURED, code="unstructured", http_status=422)
    return args


def _qwen_kwargs(model: str) -> dict[str, Any]:
    """Disable thinking on Qwen models so JSON mode stays reliable."""
    if "qwen" not in model.lower():
        return {}
    return {
        "extra_body": {
            "reasoning_effort": "none",
            "reasoning_format": "hidden",
        },
    }


def _content_or_raise(completion: Any) -> str:
    content = completion.choices[0].message.content
    if not content or not str(content).strip():
        raise ExtractionError(MSG_UNSTRUCTURED, code="unstructured", http_status=422)
    return str(content)


def _parse_extracted(raw: str) -> ExtractedInvoice:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            try:
                payload = json.loads(cleaned)
            except json.JSONDecodeError:
                raise ExtractionError(
                    MSG_UNSTRUCTURED, code="unstructured", http_status=422
                ) from exc
        else:
            raise ExtractionError(
                MSG_UNSTRUCTURED, code="unstructured", http_status=422
            ) from exc

    if not isinstance(payload, dict):
        raise ExtractionError(MSG_UNSTRUCTURED, code="unstructured", http_status=422)

    for key in (
        "vendor_name",
        "vendor_address",
        "invoice_number",
        "document_date",
        "due_date",
        "payment_terms",
        "currency",
    ):
        if key in payload and isinstance(payload[key], str) and not payload[key].strip():
            payload[key] = None

    if "tax_lines" not in payload or payload["tax_lines"] is None:
        payload["tax_lines"] = []
    if "line_items" not in payload or payload["line_items"] is None:
        payload["line_items"] = []

    try:
        return ExtractedInvoice.model_validate(payload)
    except ValidationError as exc:
        raise ExtractionError(MSG_UNSTRUCTURED, code="unstructured", http_status=422) from exc
