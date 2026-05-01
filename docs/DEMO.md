# Demo in 5 minutes

A self-contained walkthrough of the AI Dev Auditor that needs **no GitHub tunnel and no PAT**. Useful for code reviews, talks, and screen recordings. Setup is in [README.md](../README.md); the boundaries the demo exercises are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Prerequisites

- Python 3.11+, repo installed in a virtualenv (`pip install -e ".[dev]"`).
- `GITHUB_WEBHOOK_SECRET` set to any non-empty string in your shell.
- Optional: `OPENAI_API_KEY` or `GEMINI_API_KEY` to see a real LLM second opinion (without one, the runner logs `llm_status=skipped` and posts a rules-only review — both are valid demo states).
- Optional: `GITHUB_TOKEN` and a real PR if you want the comment to actually be posted on GitHub. The replay path below stops just before that step, which is exactly what you want for a local demo.

## 1. Start the server

```powershell
.\.venv\Scripts\Activate.ps1
$env:GITHUB_WEBHOOK_SECRET = "demo_local_secret"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Confirm liveness in another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Browse [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger UI.

## 2. Replay a signed webhook

The repo ships [`scripts/replay_webhook.py`](../scripts/replay_webhook.py): it reads a fixture, computes a valid `X-Hub-Signature-256`, and POSTs to `/webhooks/github`. No tunnel, no GitHub round-trip.

```powershell
$env:GITHUB_WEBHOOK_SECRET = "demo_local_secret"

# liveness through the signed path
python scripts/replay_webhook.py --event ping `
    --fixture tests/fixtures/github_webhooks/ping.json

# canonical demo: opens a PR and enqueues background analysis
python scripts/replay_webhook.py --event pull_request `
    --fixture tests/fixtures/github_webhooks/pull_request_opened.json
```

Expected responses:

| Call | HTTP | Body |
| --- | --- | --- |
| `ping` | `200` | `{"status":"ok"}` |
| `pull_request:opened` | `202` | `{"accepted":true,"queued":true}` |
| `pull_request:labeled` (different fixture) | `202` | `{"accepted":true,"queued":false}` |

## 3. Read the structured logs

Tail the uvicorn terminal — the runner emits one log line per stage so the demo narrates itself:

```
github_webhook_pull_request   action=opened pr_number=42 head_sha=abc1234... queued=true
pr_analysis_llm_outcome       llm_status=ok|skipped|fallback llm_findings=N
pr_analysis_persistence_skipped_not_configured   (when GOOGLE_CLOUD_PROJECT is empty)
pr_analysis_github_comment_posted                (only when GITHUB_TOKEN is set and the PR exists)
```

Without a `GITHUB_TOKEN` you instead see `pr_analysis_skipped_missing_github_token`. That is the correct local-demo state: the receive path, signature verification, event parsing, and background dispatch are all proven, no real GitHub call required.

## 4. One-command variant

For walkthroughs, two thin wrappers run lint + tests + both replays:

```powershell
.\scripts\demo_local_analysis.ps1
```

```bash
./scripts/demo_local_analysis.sh
```

Use `-SkipChecks` (PowerShell) or `SKIP_CHECKS=1` (bash) to re-run only the replay portion.

## 5. Optional: full end-to-end on a real PR

When you want to see the actual comment land on a PR:

1. Set `GITHUB_TOKEN` (classic PAT, `repo` scope) on the same terminal as uvicorn.
2. Expose `127.0.0.1:8000` with `cloudflared` or `ngrok`.
3. Configure a GitHub webhook for a test repository pointing at `<tunnel>/webhooks/github` with the same secret.
4. Open or push to a PR; the comment appears within a few seconds.

Re-pushing the same branch updates the conversation rather than spamming new comments — the hidden head-SHA marker handles idempotency. See [ARCHITECTURE.md](ARCHITECTURE.md#idempotency).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `error: GITHUB_WEBHOOK_SECRET is not set` | Replay script missing the secret | `--secret <value>` or `$env:GITHUB_WEBHOOK_SECRET` |
| `<- 401 {"detail":"Invalid signature"}` | Server and replay use different secrets | Use the same value in both shells |
| `<- 401 {"detail":"Webhook secret not configured"}` | Server has no secret at startup | Set `GITHUB_WEBHOOK_SECRET` before starting uvicorn |
| `pr_analysis_skipped_missing_github_token` | No `GITHUB_TOKEN` | Expected for local demos; set the token to attempt the real PR fetch |
| `pr_analysis_failed` with `404` from GitHub API | Fixture references `octo-org/octo-repo` which does not exist | Edit the fixture to point at a real PR you can read with your token, or stop at step 3 |
