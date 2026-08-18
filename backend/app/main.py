from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes.documents import router as documents_router, _uploads_dir
from app.routes.status import router as status_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Clear cached settings so .env edits apply on reload
    get_settings.cache_clear()
    yield


settings = get_settings()

app = FastAPI(
    title="Document Extraction & Classification Pipeline",
    description="Upload invoices/receipts → structured, validated extraction.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads = _uploads_dir()
app.mount("/uploads", StaticFiles(directory=str(uploads)), name="uploads")

app.include_router(documents_router)
app.include_router(status_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    s = get_settings()
    return {
        "status": "ok",
        "extraction": "groq",
        "model": s.groq_model,
    }
