#!/usr/bin/env bash
# End-to-end local demo: lint, test, and replay a signed webhook against a running server.
#
# Prerequisites (in another terminal):
#   source .venv/bin/activate
#   uvicorn main:app --reload --host 127.0.0.1 --port 8000
#
# Usage:
#   ./scripts/demo_local_analysis.sh                        # full demo
#   SKIP_CHECKS=1 ./scripts/demo_local_analysis.sh          # replay only
#   URL=https://my.run.app/webhooks/github ./scripts/demo_local_analysis.sh

set -euo pipefail

URL="${URL:-http://127.0.0.1:8000/webhooks/github}"
SECRET="${GITHUB_WEBHOOK_SECRET:-}"
SKIP_CHECKS="${SKIP_CHECKS:-0}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

if [[ "$SKIP_CHECKS" != "1" ]]; then
  echo "==> ruff check ."
  ruff check .
  echo "==> ruff format --check ."
  ruff format --check .
  echo "==> pytest -q"
  pytest -q
fi

if [[ -z "$SECRET" ]]; then
  echo "error: GITHUB_WEBHOOK_SECRET is not set" >&2
  exit 2
fi

echo "==> ping the webhook (liveness)"
python scripts/replay_webhook.py \
  --url "$URL" \
  --secret "$SECRET" \
  --event ping \
  --fixture tests/fixtures/github_webhooks/ping.json

echo "==> replay pull_request:opened (queues background analysis)"
python scripts/replay_webhook.py \
  --url "$URL" \
  --secret "$SECRET" \
  --event pull_request \
  --fixture tests/fixtures/github_webhooks/pull_request_opened.json

cat <<'EOF'

Done. In the uvicorn terminal you should see, in order:
  github_webhook_pull_request   (action=opened, queued=True)
  pr_analysis_llm_outcome       (status=ok|skipped|fallback)
  pr_analysis_github_comment_posted   (only when GITHUB_TOKEN is set)
EOF
