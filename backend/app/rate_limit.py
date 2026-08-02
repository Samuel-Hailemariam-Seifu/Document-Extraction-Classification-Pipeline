"""In-memory snapshot of the latest Groq rate-limit headers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Mapping, Optional


@dataclass
class RateLimitSnapshot:
    limit_requests: Optional[int] = None
    remaining_requests: Optional[int] = None
    reset_requests: Optional[str] = None
    limit_tokens: Optional[int] = None
    remaining_tokens: Optional[int] = None
    reset_tokens: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_lock = Lock()
_snapshot = RateLimitSnapshot()


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def update_from_headers(headers: Mapping[str, str]) -> RateLimitSnapshot:
    """Capture Groq x-ratelimit-* headers (case-insensitive mapping)."""
    # httpx Headers are case-insensitive; normalize via .get
    get = headers.get
    snap = RateLimitSnapshot(
        limit_requests=_parse_int(get("x-ratelimit-limit-requests")),
        remaining_requests=_parse_int(get("x-ratelimit-remaining-requests")),
        reset_requests=get("x-ratelimit-reset-requests") or get("x-ratelimit-reset"),
        limit_tokens=_parse_int(get("x-ratelimit-limit-tokens")),
        remaining_tokens=_parse_int(get("x-ratelimit-remaining-tokens")),
        reset_tokens=get("x-ratelimit-reset-tokens"),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    with _lock:
        global _snapshot
        # Keep previous values if a response omits a header
        _snapshot = RateLimitSnapshot(
            limit_requests=snap.limit_requests
            if snap.limit_requests is not None
            else _snapshot.limit_requests,
            remaining_requests=snap.remaining_requests
            if snap.remaining_requests is not None
            else _snapshot.remaining_requests,
            reset_requests=snap.reset_requests or _snapshot.reset_requests,
            limit_tokens=snap.limit_tokens
            if snap.limit_tokens is not None
            else _snapshot.limit_tokens,
            remaining_tokens=snap.remaining_tokens
            if snap.remaining_tokens is not None
            else _snapshot.remaining_tokens,
            reset_tokens=snap.reset_tokens or _snapshot.reset_tokens,
            updated_at=snap.updated_at,
        )
        return RateLimitSnapshot(**asdict(_snapshot))


def get_snapshot() -> RateLimitSnapshot:
    with _lock:
        return RateLimitSnapshot(**asdict(_snapshot))
