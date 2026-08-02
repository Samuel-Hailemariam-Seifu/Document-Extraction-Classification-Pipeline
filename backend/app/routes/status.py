from __future__ import annotations

from fastapi import APIRouter

from app.rate_limit import get_snapshot

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("/rate-limit")
async def rate_limit_status() -> dict:
    """Latest Groq rate-limit headers captured from extraction calls."""
    return get_snapshot().to_dict()
