# Implementation log

Running record of merged vertical slices. Milestones follow [EXECUTION_PLAN.md](EXECUTION_PLAN.md).

## Milestone 0 — Foundation

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-18 | `chore: scaffold Python project and package layout` | `pyproject.toml` (FastAPI, uvicorn, pydantic-settings, pytest/ruff dev), package layout under `app/` and `tests/fixtures/`, root `main.py`, `.gitignore`, README setup/run | `pip install -e ".[dev]"`, `uvicorn main:app` |
| 2026-04-18 | `feat(api): add GET /health endpoint` | `app/api/health.py`, router wired in `app/factory.py`, README documents `/health` | `GET /health` → `{"status":"ok"}` |
| 2026-04-18 | `feat(core): add pydantic settings and logging bootstrap` | `app/core/config.py` (`get_settings`, `GITHUB_WEBHOOK_SECRET` placeholder), `app/core/logging.py`, FastAPI `lifespan`, `.env.example`, `.env` gitignored | Set `LOG_LEVEL`, run app and confirm stderr logging |
| 2026-04-18 | `test: add async health endpoint test with httpx ASGI transport` | `tests/unit/test_health.py` using `httpx.AsyncClient` + `ASGITransport` | `pytest` |
| 2026-04-18 | `chore: document ruff format check and validate recipe` | README “Validate” section; Ruff already configured in `pyproject.toml` | `ruff check .`, `ruff format --check .`, `pytest` |

**Status:** Milestone 0 definition of done met (local run, tests pass, health responds).

## Next

- Milestone 1 — Webhook ingestion (`/webhooks/github`, signature validation, fixture tests).
