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

## Milestone 4 — LLM reviewer

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-28 | `feat(ai): add review prompt and memory stubs` | [`ai/prompts/review_prompt.md`](ai/prompts/review_prompt.md), [`ai/memory/patterns.md`](ai/memory/patterns.md), [`ai/memory/anti_patterns.md`](ai/memory/anti_patterns.md), [`app/services/prompt_loader.py`](app/services/prompt_loader.py) | `pytest` (imports resolve `ai/` from repo root) |
| 2026-04-28 | `feat(schemas): add LLM reviewer JSON models` | [`app/schemas/llm_review.py`](app/schemas/llm_review.py) | `pytest tests/unit/test_llm_schema.py` |
| 2026-04-28 | `feat(config): add OpenAI-compatible LLM settings` | [`app/core/config.py`](app/core/config.py), [`.env.example`](.env.example), [README](README.md) | Configure keys; `get_settings()` |
| 2026-04-28 | `feat(services): add LLM client and reviewer` | [`app/services/llm_client.py`](app/services/llm_client.py), [`app/services/llm_reviewer.py`](app/services/llm_reviewer.py), [`app/services/analysis_merge.py`](app/services/analysis_merge.py) | `pytest tests/unit/test_llm_reviewer.py` |
| 2026-04-28 | `chore(docker): bundle ai prompts in image` | [`Dockerfile`](Dockerfile) `COPY ai ./ai` | `docker build` |
| 2026-04-28 | `test: add LLM schema and reviewer unit tests` | `tests/unit/test_llm_schema.py`, `test_llm_reviewer.py`, [`tests/fixtures/llm_outputs/valid_reviewer.json`](tests/fixtures/llm_outputs/valid_reviewer.json) | `pytest` |

**Status:** Milestone 4 definition of done met (prompt + strict schema + adapter + safe fallback; `source=llm` findings; coexist via `concat_findings`; webhook unchanged).

## Milestone 5 — Deterministic PR scoring

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-28 | `feat(domain): add deterministic scoring models and engine` | [`app/domain/scoring.py`](app/domain/scoring.py): `ScoreDimension`, `Subscores`, `ScoringConfig`, `PrScoreResult`, `compute_pr_score` (routing, penalties, weights, partial/truncation degradation, order-invariant) | `pytest tests/unit/test_scoring.py` |
| 2026-04-28 | `feat(services): add scoring service wrapper` | [`app/services/scoring_service.py`](app/services/scoring_service.py): `default_scoring_config`, `score_pr` | `pytest tests/unit/test_scoring.py` |
| 2026-04-28 | `test: add scoring unit tests` | [`tests/unit/test_scoring.py`](tests/unit/test_scoring.py) | `pytest` |

**Status:** Milestone 5 definition of done met (deterministic `final_score` 0–100, five subscores, explanations; tests cover baselines, routing, partial context, order invariance).

## Milestone 6 — Firestore persistence + GCP verification

| Date       | Commit / area | What changed | How to validate |
|------------|---------------|--------------|-----------------|
| 2026-04-27 | `feat(deps): add google-cloud-firestore` | [`pyproject.toml`](pyproject.toml): `google-cloud-firestore`; [`app/core/config.py`](app/core/config.py): `google_cloud_project`, `firestore_database_id`; [`.env.example`](.env.example) + [README](README.md) emulator / Cloud Run / IAM | `pip install -e ".[dev]"` |
| 2026-04-27 | `feat(infra): Firestore client factory` | [`app/infra/firestore_client.py`](app/infra/firestore_client.py): emulator host + project + optional database id | Import `create_firestore_client` |
| 2026-04-27 | `feat(domain): analysis run Firestore mappers` | [`app/domain/analysis_run.py`](app/domain/analysis_run.py): `finding_to_firestore_dict`, `build_analysis_run_document`, partial/summary helpers | `pytest tests/unit/test_analysis_run.py` |
| 2026-04-27 | `feat(repositories): AnalysisRepository` | [`app/repositories/analysis_repository.py`](app/repositories/analysis_repository.py): batch persist, get run, list findings; `asyncio.to_thread` | `pytest tests/unit/test_analysis_repository.py` |
| 2026-04-27 | `feat(services): analysis persistence orchestration` | [`app/services/analysis_persistence.py`](app/services/analysis_persistence.py): `persist_analysis_run` | `pytest tests/unit/test_analysis_persistence.py` |
| 2026-04-27 | `test: Firestore integration marker` | [`tests/unit/test_firestore_integration.py`](tests/unit/test_firestore_integration.py) (`@pytest.mark.integration`), [`pyproject.toml`](pyproject.toml) marker registration | `FIRESTORE_EMULATOR_HOST=... pytest -m integration` |
| 2026-04-27 | `chore(scripts): GCP Firestore smoke` | [`scripts/verify_gcp_firestore.py`](scripts/verify_gcp_firestore.py) | `GOOGLE_CLOUD_PROJECT=... python scripts/verify_gcp_firestore.py` |

**Status:** Milestone 6 definition of done met (repository + mapper + orchestration + unit tests + optional emulator round-trip + GCP smoke script and deploy docs).

## Next

- Milestone 7 — Wire persistence into the analyzer / webhook path (background or queued), idempotency, and hardening.
