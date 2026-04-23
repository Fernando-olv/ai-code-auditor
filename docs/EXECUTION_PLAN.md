# AI Dev Auditor — Execution Plan
_Last updated: 2026-04-18_

## Mission

Build a **demo-ready MVP** of an AI Dev Auditor that:

- receives GitHub PR webhooks
- fetches PR metadata and diff
- analyzes code with deterministic rules + one LLM reviewer
- stores analysis in Firestore
- computes a basic PR score
- posts a PR summary back to GitHub
- is testable locally
- is easy to extend into a production system later

This document is the **operating workflow** for continuous AI-assisted development inside Cursor.

---

# 1. Ground Rules for the AI

You are acting as a **senior software engineer + reviewer + implementation partner**.

## Behavior Rules

1. Do not jump straight into large implementations.
2. Work in **small vertical slices** that produce something runnable.
3. Prefer **clean architecture** and **testable code** over speed hacks.
4. Always separate:
   - API layer
   - domain logic
   - infrastructure adapters
   - AI/review logic
5. Deterministic logic must stay in Python, not in LLM prompts.
6. LLM output must always be treated as **untrusted** until validated.
7. Before changing many files, explain the intended scope briefly.
8. After each slice:
   - review the implementation
   - identify gaps
   - propose the next smallest useful step
9. If something is undefined, make a practical MVP decision and document it.
10. Optimize for **“working demo in days”**, not theoretical completeness.

## Output Style

For each implementation cycle, respond using:

### Goal
What will be built in this step.

### Files to Create/Change
List exact files.

### Implementation
Perform the work.

### Validation
Explain how to run/test it.

### Review
Critique the result like a code reviewer.

### Next Step
Propose the next smallest vertical slice.

---

# 2. MVP Scope Lock

## MUST HAVE

- FastAPI webhook endpoint
- GitHub signature validation
- PR event parsing
- GitHub PR diff retrieval
- deterministic rule engine
- one LLM review pass with structured JSON output
- findings normalization
- PR score calculation
- Firestore persistence
- local tests with webhook fixtures
- PR summary generation
- clean logs and basic observability hooks

## NICE TO HAVE

- GitHub comment posting
- compare latest analysis vs previous one
- basic repo/developer aggregates
- New Relic custom metrics
- rule pack versioning

## NOT NOW

- multi-agent orchestration at runtime
- advanced acceptance tracking
- full dashboard frontend
- multi-language support beyond MVP language set
- deep historical analytics
- autonomous code modification

---

# 3. Architecture Constraints

## System Shape

### Ingress
FastAPI receives GitHub webhook and validates signature.

### Orchestration
Webhook handler acknowledges quickly and triggers analysis flow.

### Analysis
Analyze one PR snapshot defined by:

- `repo`
- `pr_number`
- `head_sha`
- `rule_pack_version`

### Storage
Persist analysis run + findings + summary + score.

### Feedback
Generate GitHub-ready review summary.

## Non-Negotiable Design Decisions

- Heavy analysis must not live directly inside endpoint logic.
- Scoring must be deterministic and implemented in Python.
- LLM should generate **signals/findings**, not final arithmetic.
- Findings must be normalized into a stable schema.
- Large PRs must degrade gracefully.
- Rule packs must be versionable.

---

# 4. Suggested Project Structure

```text
ai-dev-auditor/
  app/
    api/
      webhook.py
      health.py
    core/
      config.py
      logging.py
      observability.py
    domain/
      models.py
      findings.py
      scoring.py
      rules.py
    services/
      github_client.py
      webhook_service.py
      analyzer.py
      llm_reviewer.py
      rule_engine.py
      feedback_service.py
    repositories/
      analysis_repository.py
    infra/
      firestore_client.py
    schemas/
      findings_schema.py
    rules/
      packs/
        v0_1_0/
          deterministic.yaml
          llm.yaml
  tests/
    unit/
    integration/
    fixtures/
      github_webhooks/
      github_diffs/
      llm_outputs/
  docs/
    architecture.md
    scoring.md
    rules.md
  ai/
    agents.md
    prompts/
      review_prompt.md
    evals/
      golden_prs.yaml
    datasets/
      golden_prs/
    memory/
      patterns.md
      anti_patterns.md
  scripts/
  main.py
```

---

# 5. Delivery Milestones

## Milestone 0 — Foundation
Goal: repo scaffolding and local run.

Deliver:
- project structure
- config loading
- FastAPI app bootstrap
- health endpoint
- test setup
- lint/format setup

Definition of done:
- app starts locally
- tests run
- health endpoint responds

---

## Milestone 1 — Webhook Ingestion
Goal: receive GitHub PR webhook safely.

Deliver:
- `/webhooks/github`
- signature validation
- pull_request event parsing
- fixture-based tests

Definition of done:
- valid signature accepted
- invalid signature rejected
- fixture payload parsed into internal model

---

## Milestone 2 — PR Context Retrieval
Goal: retrieve PR metadata and diff.

Deliver:
- GitHub client
- fetch changed files / patch / metadata
- normalization layer
- mockable tests

Definition of done:
- given repo + PR, app can build analysis context
- file filtering works

---

## Milestone 3 — Deterministic Rule Engine
Goal: get useful findings without relying on LLM first.

Initial rule candidates:
1. changed backend/service logic without test change
2. debug print/log left in code
3. very large diff warning
4. TODO/FIXME introduced
5. potential secret pattern introduced
6. async handler using blocking call heuristic
7. function too large after change heuristic
8. low test coverage signal based on changed files only
9. direct DB/API call inside controller/route heuristic
10. duplicated logic indicator heuristic

Definition of done:
- rules run on normalized PR context
- findings returned in a stable schema
- rule tests exist

---

## Milestone 4 — LLM Reviewer
Goal: add one structured AI review pass.

Deliver:
- prompt file
- strict output schema
- LLM adapter interface
- validation + fallback behavior

Definition of done:
- reviewer returns validated structured findings
- invalid AI output is rejected safely
- deterministic + LLM findings can coexist

---

## Milestone 5 — Scoring
Goal: compute one reproducible PR score.

Initial scoring dimensions:
- maintainability
- correctness confidence
- testing
- security
- readability

Definition of done:
- score is deterministic from findings/signals
- score explanation is stored
- tests cover score calculation

---

## Milestone 6 — Persistence
Goal: store analysis history in Firestore.

Collections:
- `analysis_runs`
- `analysis_runs/{id}/findings`

Definition of done:
- analysis run persisted
- findings persisted
- retrieval by analysis id works
- emulator/local test path exists

---

## Milestone 7 — Feedback
Goal: generate GitHub-ready review output.

Deliver:
- PR summary renderer
- GitHub comment/check payload generator
- Post in the PR the review

Definition of done:
- summary includes score, key findings, strengths, risks, next actions
- output is concise and readable

---

## Milestone 8 — Demo Hardening
Goal: make it presentable.

Deliver:
- seed fixtures
- sample screenshots/logs
- demo script
- architecture notes
- known limitations documented

Definition of done:
- end-to-end local demo works
- presentation narrative is clear

---

# 6. Continuous Build + Review Loop

This is the default workflow for every session.

## Loop

### Step 1 — Re-read State
First, inspect:
- current milestone
- files already created
- pending TODOs
- failing tests
- known technical debt

Then summarize the current state in 5-10 lines.

### Step 2 — Choose Smallest Vertical Slice
Pick the next smallest useful slice that:
- advances the current milestone
- is independently testable
- reduces project risk

Do not pick a huge task if a smaller one can unlock progress.

### Step 3 — Implement
Make focused changes only for that slice.

Rules:
- avoid unrelated refactors
- keep functions small
- type hint public interfaces
- add docstrings where valuable
- prefer dependency injection for adapters/clients

### Step 4 — Validate
Always run relevant checks after implementation:
- unit tests for changed logic
- integration tests if applicable
- lint/type checks if configured

If tests do not exist yet, add them before moving on.

### Step 5 — Review Like a Senior Engineer
After coding, review the work critically:
- what is good
- what is fragile
- what is overcomplicated
- what is missing
- what must be fixed now vs later

### Step 6 — Update Progress
Update:
- milestone status
- TODOs
- risks
- next action

### Step 7 — Propose Next Slice
Recommend the next smallest step.

---

# 7. Execution Mode Prompt for Cursor

Use this as the default instruction at the start of each work cycle:

> Follow `EXECUTION_PLAN.md`.
> First, inspect the current repository state and identify the active milestone.
> Then choose the next smallest vertical slice.
> Implement it with production-quality code, tests, and brief explanations.
> After implementation, perform a short code review of your own work and propose the next step.
> Do not take on multiple milestones at once.
> Do not skip validation.
> Prefer working software over broad scaffolding.

---

# 8. Review Checklist

After every meaningful change, review against this checklist.

## Architecture
- Are responsibilities separated cleanly?
- Is domain logic isolated from transport/infrastructure?
- Is this easy to test?

## Reliability
- Are edge cases handled?
- Is invalid input rejected safely?
- Is external IO abstracted?

## AI Safety / Quality
- Is LLM output schema-validated?
- Is fallback behavior defined?
- Is the prompt narrowly scoped?

## Maintainability
- Would another engineer understand this quickly?
- Are names clear?
- Is logic small and composable?

## Demo Readiness
- Does this move us closer to a presentable end-to-end story?
- Can this be shown to someone non-technical?

---

# 9. Definition of Done for Any Task

A task is only done when all of these are true:

- code compiles/runs
- tests exist and pass for changed behavior
- interfaces are typed
- no obvious dead code introduced
- behavior is documented briefly if non-obvious
- result fits current milestone
- next step is identified

---

# 10. Practical MVP Decisions

If not otherwise defined, use these defaults.

## Language Scope
Start with Python-oriented heuristics first.

## PR Analysis Unit
One run = one PR snapshot at a given `head_sha`.

## Large PR Handling
If PR is too large:
- analyze summary + selected changed files
- emit “reduced-confidence / partial-review” signal

## LLM Strategy
One reviewer pass only for MVP.

## Findings Severity
Use:
- low
- medium
- high

## Confidence
Use float `0.0 - 1.0`

## Score Scale
Use integer `0 - 100`

---

# 11. Firestore MVP Schema

## `analysis_runs`
Example fields:

- `analysis_id`
- `repo`
- `pr_number`
- `head_sha`
- `author`
- `status`
- `rule_pack_version`
- `created_at`
- `completed_at`
- `latency_ms`
- `final_score`
- `subscores`
- `summary`
- `partial_review`
- `error_message`

## `analysis_runs/{analysis_id}/findings`
Example fields:

- `finding_id`
- `rule_id`
- `source` (`deterministic` | `llm`)
- `severity`
- `category`
- `title`
- `description`
- `suggestion`
- `file_path`
- `line_start`
- `line_end`
- `confidence`

---

# 12. Initial AI Layer Files

These should exist early, even if simple.

## `ai/agents.md`
Define:
- Reviewer Agent
- Scorer Agent
- Refactor Agent

## `ai/prompts/review_prompt.md`
Strict JSON review prompt.

## `ai/evals/golden_prs.yaml`
Small eval set with expected findings.

## `ai/memory/patterns.md`
Known good patterns.

## `ai/memory/anti_patterns.md`
Known bad patterns.

Important:
These files are part of the product design, but do not block initial plumbing.

---

# 13. Risks to Watch

## Risk 1 — Too much architecture, not enough demo
Mitigation:
Prefer thin working slices.

## Risk 2 — AI output too inconsistent
Mitigation:
Strict schema validation + minimal prompt + fallback.

## Risk 3 — Overpromising scoring quality
Mitigation:
Present score as MVP signal, not definitive judgment.

## Risk 4 — Webhook logic becomes bloated
Mitigation:
Move analysis orchestration into services early.

## Risk 5 — Demo depends on too many external systems
Mitigation:
Support local/manual analysis path and mockable integrations.

---

# 14. Demo Narrative

When the MVP is working, the presentation should show:

1. GitHub PR event arrives
2. System validates and processes it
3. Deterministic + AI findings are generated
4. Score is computed
5. Analysis is stored
6. Review summary is produced

Message:
> “This is an AI-assisted PR auditor with reproducible scoring, structured findings, and versionable review logic.”

---

# 15. Session Template

At the start of each Cursor session, follow this template:

## Current State
- active milestone:
- what already works:
- what is missing:
- biggest risk right now:

## Next Slice
- objective:
- why this is the smallest useful step:
- files to change:

## After Implementation
- validation performed:
- review notes:
- follow-up step:

---

# 16. Start Here

Begin with **Milestone 0** unless the repository already has a working foundation.

If Milestone 0 is already done, begin with **Milestone 1**.

Your first action:
1. inspect the repository
2. identify the active milestone
3. propose the next smallest vertical slice
4. implement it
5. review it
6. propose the next step
