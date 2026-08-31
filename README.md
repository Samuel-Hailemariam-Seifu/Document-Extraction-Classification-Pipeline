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

## Deploy (Render + Vercel)

The GitHub repo is a **monorepo**: FastAPI in `backend/`, Next.js in `frontend/`.

History and uploads live **in memory / on local disk** on the API instance. On Render’s free plan the service sleeps and that data is wiped on restart. Extraction also talks to Groq, so keep `GROQ_API_KEY` only in the Render dashboard — never in git.

### 1. Backend on Render

1. Push this repo to GitHub (already: `Document-Extraction---Classification-Pipeline`).
2. In [Render](https://dashboard.render.com) → **New** → **Blueprint**, connect the repo and apply `render.yaml`, **or** create a **Web Service** manually:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3.12
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check path:** `/api/health`
3. Environment variables:

   | Key | Value |
   | --- | --- |
   | `GROQ_API_KEY` | from [Groq Console](https://console.groq.com/keys) |
   | `GROQ_MODEL` | `qwen/qwen3.6-27b` |
   | `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` |
   | `CORS_ORIGINS` | your Vercel origin, e.g. `https://your-app.vercel.app` (no trailing slash) |

   `https://*.vercel.app` preview URLs are allowed via `CORS_ORIGIN_REGEX` in `render.yaml`.
4. After the first deploy, copy the service URL. This project’s API is:

   `https://document-extraction-classification.onrender.com`

   Confirm `/api/health` returns `"status": "ok"`.

Free instances take ~30–60s to wake. Uploads that run Groq can take longer than a hobby proxy timeout, which is why the browser calls Render **directly**.

### 2. Frontend on Vercel

1. [Import the same GitHub repo](https://vercel.com/new).
2. **Root Directory:** `frontend` (Project Settings → General).
3. Environment variables (Production + Preview):

   | Key | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | `https://document-extraction-classification.onrender.com` |
   | `BACKEND_URL` | same URL (used for SSR and Next rewrites) |

4. Deploy. After Render or Vercel URLs change, update the other side’s env and **redeploy** the frontend so `NEXT_PUBLIC_*` is baked in.

If the first page load says the backend is unreachable, wait for Render to wake and refresh.

### 3. Custom domain

Add the domain to `CORS_ORIGINS` on Render (comma-separated with `https://your-app.vercel.app`).

## Build status

| Step | Status |
|------|--------|
| 1. FastAPI + Pydantic schema + stub extraction | Done |
| 2. Next.js upload / review / history UI | Done |
| 3. Real Groq extraction (`qwen/qwen3.6-27b`) | Done |
| 4. Validation layer | Done |
| 5. PostgreSQL persistence | Pending (in-memory for now) |
| 6. Confirm/edit polish | Scaffolded (PATCH works) |
