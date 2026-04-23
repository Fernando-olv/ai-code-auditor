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

## Milestone 1 — Webhook ingestion

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-22 | `feat(api): add GitHub webhook ingestion endpoint` | `POST /webhooks/github` in `app/api/webhook.py` with strict `X-Hub-Signature-256` validation, supports `ping` + `pull_request`, minimal logging; router wired in `app/factory.py` | Set `GITHUB_WEBHOOK_SECRET`, run `pytest`, and send a signed request (or use GitHub “Test delivery”) |
| 2026-04-22 | `test: add webhook signature + endpoint fixtures` | Signature verification tests (`tests/unit/test_github_signature.py`), endpoint tests (`tests/unit/test_webhook_endpoint.py`), PR event parsing tests (`tests/unit/test_pull_request_parser.py`), fixtures under `tests/fixtures/github_webhooks/` | `pytest` |

**Status:** Milestone 1 definition of done met (signature accepted/rejected; fixture payload parsed).

## Next

- Milestone 2 — PR context retrieval (GitHub client + diff retrieval + normalization).
