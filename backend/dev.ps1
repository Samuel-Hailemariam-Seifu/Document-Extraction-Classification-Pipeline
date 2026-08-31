# Start FastAPI with reload scoped to app/ only.
# Do NOT use --reload-exclude uploads/* on Windows — the shell expands the glob
# into every file under uploads/ and uvicorn treats them as extra args.
Set-Location $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --reload-dir app --port 8000
