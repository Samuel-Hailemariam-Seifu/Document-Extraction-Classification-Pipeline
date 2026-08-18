# Document Extraction & Classification Pipeline

Portfolio-grade invoice/receipt extraction with a confidence & validation layer.

## Stack

- **Backend:** FastAPI (Python)
- **LLM:** Groq via OpenAI-compatible SDK (`qwen/qwen3.6-27b` vision; Llama 4 Scout decommissioned on free/developer tier 2026-07-17)
- **Frontend:** Next.js App Router, TypeScript, Tailwind
- **DB:** PostgreSQL (wired in a later step; scaffold uses in-memory store)

## Quick start

1. Copy env and set your Groq key:

```bash
copy .env.example backend\.env
# Edit backend\.env — set GROQ_API_KEY from https://console.groq.com/keys
```

2. Backend:

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt

# Prefer the baked-in start script (watches only app/, not uploads/):
npm run dev
# or: .\dev.ps1
# or: uvicorn app.main:app --reload --reload-dir app --port 8000
```

Do **not** run bare `uvicorn ... --reload` from `backend/` without `--reload-dir app`:
writing to `uploads/` would restart the worker and kill in-flight uploads (`ECONNRESET`).
On Windows, avoid `--reload-exclude uploads/*` — the shell expands that glob into
file paths and uvicorn fails with "unexpected extra arguments".

3. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Build status

| Step | Status |
|------|--------|
| 1. FastAPI + Pydantic schema + stub extraction | Done |
| 2. Next.js upload / review / history UI | Done |
| 3. Real Groq extraction (`qwen/qwen3.6-27b`) | Done |
| 4. Validation layer | Done |
| 5. PostgreSQL persistence | Pending (in-memory for now) |
| 6. Confirm/edit polish | Scaffolded (PATCH works) |
