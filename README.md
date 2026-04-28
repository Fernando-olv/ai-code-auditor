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

Optional: copy [`.env.example`](.env.example) to `.env` and adjust variables.

Environment variables:

- `GITHUB_WEBHOOK_SECRET` — validates incoming GitHub webhooks (`X-Hub-Signature-256`).
- `GITHUB_TOKEN` — bearer token for GitHub REST API (PR context retrieval and later milestones). Not used for webhook signatures.
- `GITHUB_API_BASE_URL` — optional; defaults to `https://api.github.com` (useful for GitHub Enterprise).
- `OPENAI_API_KEY` — OpenAI-compatible API key for the LLM reviewer (Milestone 4). If unset, LLM review is skipped.
- `OPENAI_BASE_URL` — optional; defaults to `https://api.openai.com/v1`.
- `LLM_MODEL` — optional; defaults to `gpt-4o-mini` in settings.
- `AI_REPO_ROOT` or `AI_PROMPTS_DIR` — optional path to the repository root that contains the [`ai/`](ai/) prompts folder when not running from a normal checkout.
- `GOOGLE_CLOUD_PROJECT` — GCP project id for Firestore (`google-cloud-firestore`). Recommended on Cloud Run so the client target is explicit. When `FIRESTORE_EMULATOR_HOST` is set locally and this is empty, the app uses a demo project id for the emulator.
- `FIRESTORE_DATABASE_ID` — optional; omit or `(default)` for the default Firestore database. Otherwise set your named database id.
- `FIRESTORE_EMULATOR_HOST` — **local only** (e.g. `127.0.0.1:8080`). The Firestore client library routes to the emulator; unset in production.

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

Integration tests (Firestore emulator): install the [Firestore emulator](https://cloud.google.com/firestore/docs/emulator), start it, export `FIRESTORE_EMULATOR_HOST` (and optionally `GOOGLE_CLOUD_PROJECT`), then run `pytest -m integration`.

## Lint / format

```powershell
ruff check .
ruff format .
```

Check formatting without writing files: `ruff format --check .`

## Validate (like CI)

```powershell
ruff check .
ruff format --check .
pytest
```

## Deploy to GCP Cloud Run (Docker)

This repo includes a `Dockerfile` suitable for Cloud Run.

### Build and run locally

```powershell
docker build -t ai-code-auditor .
docker run -p 8080:8080 -e PORT=8080 -e GITHUB_WEBHOOK_SECRET="dev-secret" ai-code-auditor
```

Then verify:
- `GET http://127.0.0.1:8080/health`
- `POST http://127.0.0.1:8080/webhooks/github` (must be signed; see webhook docs/milestones)

### Firestore (Native mode)

1. In the same GCP region you use for Cloud Run (e.g. `us-central1`), create or use a **Firestore Native** database (default `(default)` is fine).
2. Enable the API: `gcloud services enable firestore.googleapis.com --project=YOUR_PROJECT_ID`.
3. Grant the **Cloud Run runtime service account** a role that can read/write application data, e.g. **`roles/datastore.user`** (validate against your org’s IAM constraints). Prefer the metadata server (ADC) — do not mount JSON keys on Cloud Run for Firestore.
4. Set **`GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID`** on the Cloud Run service. Do **not** set `FIRESTORE_EMULATOR_HOST` in Cloud Run.

After deploy, operators can verify connectivity with Application Default Credentials:

```powershell
gcloud auth application-default login
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
python scripts/verify_gcp_firestore.py
```

The script writes and deletes a small canary document under the `ops_smoke` collection.

### Deploy to Cloud Run with Secret Manager

Create the secret and add a value:

```powershell
gcloud secrets create github-webhook-secret --replication-policy="automatic"
echo "your-webhook-secret" | gcloud secrets versions add github-webhook-secret --data-file=-
```

Deploy and map the secret to `GITHUB_WEBHOOK_SECRET`:

```powershell
gcloud run deploy ai-code-auditor ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID ^
  --set-secrets GITHUB_WEBHOOK_SECRET=github-webhook-secret:latest
```

Replace `YOUR_PROJECT_ID` with the project that hosts Firestore (see **Firestore** above). Add more `--set-secrets` / `--set-env-vars` entries as needed (for example `GITHUB_TOKEN`, `OPENAI_API_KEY`).

Cloud Run will route requests to the container on `$PORT` automatically.
