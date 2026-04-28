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

## Milestone 2 — PR context retrieval

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-27 | `feat(config): add GitHub API settings and runtime httpx` | `github_token`, `github_api_base_url` in [`app/core/config.py`](app/core/config.py); [`.env.example`](.env.example) + README env docs; `httpx` in main deps; `pythonpath = ["."]` in [`pyproject.toml`](pyproject.toml) so `pytest` resolves root [`main.py`](main.py) | `pytest` |
| 2026-04-27 | `feat(github): add async REST client for PR and files` | [`app/services/github_client.py`](app/services/github_client.py): typed PR + file rows, pagination, optional `transport` for tests, `GitHubApiError` | `pytest tests/unit/test_github_client.py` |
| 2026-04-27 | `feat(domain): add normalized PR context and file filters` | [`app/domain/pr_context.py`](app/domain/pr_context.py): `NormalizedPrContext`, `NormalizedChangedFile`, `FileFilterConfig`, `split_repository_full_name`, `filter_pull_files` | `pytest tests/unit/test_pr_context_filters.py` |
| 2026-04-27 | `feat(services): add PR context builder` | [`app/services/pr_context_service.py`](app/services/pr_context_service.py): `github_client_from_settings`, `build_normalized_pr_context` (head SHA mismatch → `partial_context` + log) | `pytest tests/unit/test_pr_context_service.py` |
| 2026-04-27 | `test: add GitHub API fixtures and unit tests` | [`tests/fixtures/github_api/`](tests/fixtures/github_api/), `test_github_client.py`, `test_pr_context_service.py`, `test_pr_context_filters.py` (`httpx.MockTransport`) | `pytest` |

**Status:** Milestone 2 definition of done met (normalized context from repo + PR; filtering and caps tested; webhook path unchanged).

## Milestone 3 — Deterministic rule engine

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-28 | `feat(domain): add findings schema and rule protocol` | [`app/domain/findings.py`](app/domain/findings.py) (`Severity`, `Finding`, `RuleEngineResult`, `RuleEngineConfig`, `compute_finding_id`), [`app/domain/rule_protocol.py`](app/domain/rule_protocol.py) | `pytest tests/unit/test_findings.py` |
| 2026-04-28 | `feat(domain): add patch line iterator for unified diffs` | [`app/domain/patch_utils.py`](app/domain/patch_utils.py) (`iter_added_lines`) | `pytest tests/unit/test_patch_utils.py` |
| 2026-04-28 | `feat(services): add deterministic rule engine` | [`app/services/rule_engine.py`](app/services/rule_engine.py) (`RuleEngine`, `default_rule_engine`, pack `v0_1_0`) | `pytest tests/unit/test_rule_engine.py` |
| 2026-04-28 | `feat(rules): add MVP deterministic rules` | [`app/rules/size_rules.py`](app/rules/size_rules.py), [`app/rules/text_scan_rules.py`](app/rules/text_scan_rules.py), [`app/rules/coverage_heuristic_rules.py`](app/rules/coverage_heuristic_rules.py), [`app/rules/registry.py`](app/rules/registry.py) | `pytest tests/unit/test_deterministic_rules.py` |
| 2026-04-28 | `test: add unit tests for findings, patches, engine, rules` | `tests/unit/test_findings.py`, `test_patch_utils.py`, `test_rule_engine.py`, `test_deterministic_rules.py` | `pytest` |

**Status:** Milestone 3 definition of done met (rules run on `NormalizedPrContext`; stable `Finding` schema; rule tests; webhook unchanged).

## Next

- Milestone 4 — LLM reviewer (structured pass + validation).
