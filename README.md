# AI Dev Auditor

Demo-ready MVP: GitHub PR webhooks, deterministic rules + LLM review, scoring, Firestore persistence.

See [docs/EXECUTION_PLAN.md](docs/EXECUTION_PLAN.md) for milestones and [docs/PROGRESS.md](docs/PROGRESS.md) for what is implemented.

## Setup

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Interactive API docs: `http://127.0.0.1:8000/docs`

Health check: `GET http://127.0.0.1:8000/health`

## Test

```powershell
pytest
```

## Lint / format

```powershell
ruff check .
ruff format .
```
