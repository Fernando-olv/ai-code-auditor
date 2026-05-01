<#
.SYNOPSIS
  End-to-end local demo: lint, test, and replay a signed webhook against a running server.

.DESCRIPTION
  Runs ruff + pytest, then POSTs the canonical pull_request_opened fixture to
  the webhook endpoint with a valid HMAC signature. Use this to walk reviewers
  through the full ingestion path without a public tunnel.

  Prerequisites (in another terminal):
    .\.venv\Scripts\Activate.ps1
    uvicorn main:app --reload --host 127.0.0.1 --port 8000

.PARAMETER Url
  Target webhook URL. Defaults to the local uvicorn endpoint.

.PARAMETER Secret
  Webhook secret. Defaults to $env:GITHUB_WEBHOOK_SECRET.

.PARAMETER SkipChecks
  Skip the lint/test step. Use for quick re-runs of just the replay.

.EXAMPLE
  .\scripts\demo_local_analysis.ps1

.EXAMPLE
  .\scripts\demo_local_analysis.ps1 -SkipChecks -Url "http://127.0.0.1:8000/webhooks/github"
#>
param(
    [string]$Url = "http://127.0.0.1:8000/webhooks/github",
    [string]$Secret = $env:GITHUB_WEBHOOK_SECRET,
    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    if (-not $SkipChecks) {
        Write-Host "==> ruff check ." -ForegroundColor Cyan
        ruff check .
        Write-Host "==> ruff format --check ." -ForegroundColor Cyan
        ruff format --check .
        Write-Host "==> pytest -q" -ForegroundColor Cyan
        pytest -q
    }

    if (-not $Secret) {
        throw "GITHUB_WEBHOOK_SECRET is not set. Pass -Secret or set the environment variable."
    }

    Write-Host "==> ping the webhook (liveness)" -ForegroundColor Cyan
    python scripts/replay_webhook.py `
        --url $Url `
        --secret $Secret `
        --event ping `
        --fixture tests/fixtures/github_webhooks/ping.json

    Write-Host "==> replay pull_request:opened (queues background analysis)" -ForegroundColor Cyan
    python scripts/replay_webhook.py `
        --url $Url `
        --secret $Secret `
        --event pull_request `
        --fixture tests/fixtures/github_webhooks/pull_request_opened.json

    Write-Host ""
    Write-Host "Done. In the uvicorn terminal you should see, in order:" -ForegroundColor Green
    Write-Host "  github_webhook_pull_request   (action=opened, queued=True)"
    Write-Host "  pr_analysis_llm_outcome       (status=ok|skipped|fallback)"
    Write-Host "  pr_analysis_github_comment_posted   (only when GITHUB_TOKEN is set)"
}
finally {
    Pop-Location
}
