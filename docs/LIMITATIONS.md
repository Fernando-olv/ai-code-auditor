# Known limitations

The auditor is an MVP. The list below is what we deliberately do **not** do today, with enough context to decide whether each item matters for your use case. Pairs with [ARCHITECTURE.md](ARCHITECTURE.md) and [agents.md](agents.md).

## Security and trust

- **Webhook secret only.** Authentication on `/webhooks/github` is HMAC-SHA256 against `GITHUB_WEBHOOK_SECRET`. There is no GitHub App, no OAuth, no per-repository allowlist; any PR event from any repo whose webhook is configured with the right secret will be analyzed.
- **PAT, not a GitHub App.** `GITHUB_TOKEN` is a classic Personal Access Token. That means the comment author is the PAT owner, rate limits are user-scoped (5,000 req/h), and fine-grained tokens are explicitly **not** supported for cross-owner repos (they return `403`). See [README.md → GitHub setup](../README.md#github-setup).
- **No request authn beyond the signature.** Cloud Run is configured with `--allow-unauthenticated`. Defense-in-depth (Cloud Armor, IP allowlists) is not part of the MVP.
- **No secret scanning of the comment body.** The deterministic rules detect common secret patterns in the diff, but the rendered comment itself is not re-scanned before posting. Don't put credentials in PR descriptions.

## Analysis depth

- **Diff-only context.** The reviewer agent sees changed files (with patches) and PR metadata. It does **not** load the full repository tree, run the project's tests, or build the project. Findings about "missing" code or hidden helpers will be wrong.
- **Patch line filtering.** Findings are emitted only against added lines in the unified diff (see [`app/domain/patch_utils.py`](../app/domain/patch_utils.py)). Issues entirely in unchanged context are out of scope by design.
- **Single LLM pass.** One reviewer call per PR. No multi-agent debate, no self-critique loop, no retry on low-confidence output. Fallback parsing is best-effort: malformed JSON degrades to `status="fallback"` with empty findings rather than a hard failure.
- **No language-specific rule packs.** The shipped pack `v0_1_0` is language-agnostic (size, secrets, denylisted paths, missing-test heuristic). Per-language deep checks (e.g. Go, JS-specific patterns) are listed under roadmap in the README.

## PR handling

- **Head-SHA mismatch produces a `partial_context` flag,** not a re-fetch. If the PR is updated mid-analysis, the run completes against the older snapshot and the score is degraded; the next push triggers a fresh analysis.
- **Large PRs are filtered, not summarized.** [`filter_pull_files`](../app/domain/pr_context.py) caps file count and per-file size before the LLM. Excluded files do not appear in findings.
- **One comment per head SHA.** Re-pushing replaces the conversation by adding a new comment for the new SHA. We do **not** edit prior comments, do not collapse them, and do not maintain a single rolling thread.
- **No re-analysis on label/edit/assign events.** Only `opened/synchronize/reopened` enqueue work. This is intentional to avoid noisy runs and quota burn.

## LLM behavior

- **Output is non-deterministic.** Same diff can produce slightly different findings between runs. The deterministic rules and scoring exist precisely because the LLM cannot be the source of truth.
- **No grounding beyond the prompt.** The reviewer cannot read external links, fetch issue history, or query Firestore. Memory is two static files: [`ai/memory/patterns.md`](../ai/memory/patterns.md), [`ai/memory/anti_patterns.md`](../ai/memory/anti_patterns.md).
- **Token budget is fixed.** `LLM_MAX_OUTPUT_TOKENS` (default 2048) and `LLM_MAX_USER_PAYLOAD_CHARS` (default 120k) cap the request. Very long PRs lose tail context first.
- **Costs are unmetered.** No per-PR or per-repo budget enforcement; an attacker who controls a webhook secret can exhaust your LLM key. Mitigate with per-secret rate limits at the proxy layer if exposed.

## Persistence

- **Firestore is optional.** With `GOOGLE_CLOUD_PROJECT` empty, runs and findings are not stored anywhere; the comment is the only artifact. This is fine for "post a review on every PR"; it is **not** fine for "show me trend dashboards."
- **No retention policy.** When persistence is on, documents accumulate forever. Add a TTL policy in GCP if that matters for you.
- **No cross-run dedup.** Each run writes a new document; the same finding on two consecutive pushes appears twice in `analysis_runs/*/findings`.

## Operations

- **No retries on GitHub or LLM 5xx.** A transient failure in the background task is logged via `pr_analysis_failed` and dropped. The next push will re-run the analysis from scratch.
- **No metrics endpoint.** Observability is entirely structured logs. Use Cloud Logging filters (examples in the README deploy section) to build alerts.
- **Single region, single instance assumptions.** No leader election; if you scale horizontally, two instances can race on the same PR. The duplicate-comment guard makes this safe in practice (one wins, the other logs `skip_duplicate`), but it is not formally serializable.

## Roadmap pointers

The README "Roadmap" section lists the items most likely to land next: per-language rule packs, incremental review on `synchronize`, and a dashboard over the Firestore data. None of those are required for the current single-comment use case to be useful.
