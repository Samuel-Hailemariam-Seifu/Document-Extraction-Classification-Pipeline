"""In-memory document store.

Replaced by PostgreSQL in a later build step. Same interface so routes stay stable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.schemas import (
    DocumentRecord,
    DocumentStatus,
    DocumentSummary,
    DocumentUpdate,
    ExtractedInvoice,
    ValidationResult,
)
from app.validation import validate_extraction


class InMemoryStore:
    def __init__(self) -> None:
        self._docs: dict[UUID, DocumentRecord] = {}

    def create(
        self,
        *,
        filename: str,
        content_type: str,
        file_url: str,
        extracted: ExtractedInvoice,
        validation: ValidationResult,
    ) -> DocumentRecord:
        now = _now_iso()
        doc = DocumentRecord(
            id=uuid4(),
            filename=filename,
            content_type=content_type,
            file_url=file_url,
            extracted=extracted,
            validation=validation,
            status=DocumentStatus.EXTRACTED,
            created_at=now,
            updated_at=now,
        )
        self._docs[doc.id] = doc
        return doc

    def list(self) -> list[DocumentSummary]:
        docs = sorted(self._docs.values(), key=lambda d: d.created_at, reverse=True)
        return [
            DocumentSummary(
                id=d.id,
                filename=d.filename,
                vendor_name=d.extracted.vendor_name,
                document_date=d.extracted.document_date,
                total=d.extracted.total,
                currency=d.extracted.currency,
                confidence_status=d.validation.status,
                status=d.status,
                created_at=d.created_at,
            )
            for d in docs
        ]

    def get(self, doc_id: UUID) -> Optional[DocumentRecord]:
        return self._docs.get(doc_id)

    def update(self, doc_id: UUID, payload: DocumentUpdate) -> Optional[DocumentRecord]:
        doc = self._docs.get(doc_id)
        if doc is None:
            return None

        data = doc.extracted.model_dump()
        updates = payload.model_dump(exclude_unset=True, exclude={"confirm"})
        for key, value in updates.items():
            if value is not None:
                data[key] = value

        extracted = ExtractedInvoice.model_validate(data)
        validation = validate_extraction(extracted)

        doc.extracted = extracted
        doc.validation = validation
        doc.updated_at = _now_iso()
        if payload.confirm:
            doc.status = DocumentStatus.CONFIRMED

        self._docs[doc_id] = doc
        return doc


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


store = InMemoryStore()
