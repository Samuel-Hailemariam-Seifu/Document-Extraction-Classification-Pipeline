from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.config import get_settings
from app.extraction import ExtractionError, extract_invoice
from app.images import UnreadableDocumentError, assert_file_looks_valid, render_preview_png
from app.schemas import (
    DocumentRecord,
    DocumentSummary,
    DocumentUpdate,
    ErrorResponse,
    FieldIssue,
)
from app.store import store
from app.validation import add_issues, validate_extraction

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


def _uploads_dir() -> Path:
    settings = get_settings()
    path = Path(__file__).resolve().parents[2] / settings.upload_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post(
    "/upload",
    response_model=DocumentRecord,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_document(file: UploadFile = File(...)) -> DocumentRecord:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    content_type = (file.content_type or mimetypes.guess_type(file.filename)[0] or "").lower()

    if suffix not in ALLOWED_EXTENSIONS and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This file couldn't be read, please check the format and try again",
                "code": "unreadable_file",
            },
        )

    stored_name = f"{uuid4().hex}{suffix}"
    dest = _uploads_dir() / stored_name

    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc
    finally:
        await file.close()

    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This file couldn't be read, please check the format and try again",
                "code": "unreadable_file",
            },
        )

    try:
        assert_file_looks_valid(dest, content_type or "application/octet-stream")
    except UnreadableDocumentError:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This file couldn't be read, please check the format and try again",
                "code": "unreadable_file",
            },
        ) from None

    try:
        result = await extract_invoice(dest, content_type or "application/octet-stream")
    except ExtractionError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.to_detail()) from exc
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={
                "message": "The extraction service is temporarily unavailable, please try again",
                "code": "service_unavailable",
            },
        ) from None

    validation = validate_extraction(result.extracted)
    if result.warnings:
        validation = add_issues(
            validation,
            [
                FieldIssue(field="document", message=msg, severity="warning")
                for msg in result.warnings
            ],
        )
    return store.create(
        filename=file.filename,
        content_type=content_type or "application/octet-stream",
        file_url=f"/uploads/{stored_name}",
        extracted=result.extracted,
        validation=validation,
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents() -> list[DocumentSummary]:
    return store.list()


def _resolve_stored_file(doc: DocumentRecord) -> Path:
    path = _uploads_dir() / Path(doc.file_url).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Original file not found on disk")
    return path


@router.get(
    "/{document_id}/file",
    responses={404: {"model": ErrorResponse}},
)
async def get_document_file(document_id: UUID) -> FileResponse:
    """Stream the original upload for download / new-tab viewing."""
    doc = store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    path = _resolve_stored_file(doc)
    media = doc.content_type or mimetypes.guess_type(doc.filename)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media,
        filename=doc.filename,
        content_disposition_type="inline",
    )


@router.get(
    "/{document_id}/preview",
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def get_document_preview(document_id: UUID) -> Response:
    """PNG raster of the first page — reliable in-browser preview (no PDF iframe)."""
    doc = store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    path = _resolve_stored_file(doc)
    try:
        png = render_preview_png(path, doc.content_type)
    except UnreadableDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


@router.get(
    "/{document_id}",
    response_model=DocumentRecord,
    responses={404: {"model": ErrorResponse}},
)
async def get_document(document_id: UUID) -> DocumentRecord:
    doc = store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch(
    "/{document_id}",
    response_model=DocumentRecord,
    responses={404: {"model": ErrorResponse}},
)
async def update_document(document_id: UUID, payload: DocumentUpdate) -> DocumentRecord:
    doc = store.update(document_id, payload)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
