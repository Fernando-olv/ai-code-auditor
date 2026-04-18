# AI Dev Auditor — Agents Specification

## Overview

This system uses specialized AI agents to analyze Pull Requests.

Each agent has:
- a clear responsibility
- structured inputs
- structured outputs
- evaluation criteria

Agents **must not** overlap responsibilities.

The goal is to make the AI layer:
- reproducible
- testable
- auditable
- evolvable

---

## Core Principles

1. Deterministic logic comes before probabilistic logic.
2. All agent outputs must be structured JSON.
3. No hallucinated facts about code.
4. Every finding must be grounded in the diff or retrieved PR context.
5. Suggestions must be specific, actionable, and minimal.
6. Agents provide signals; the platform owns final scoring and persistence.
7. AI behavior must be versionable through prompts, schemas, and rule packs.

---

## System Role of Agents

Agents are part of the analysis layer.

They do **not**:
- own transport concerns
- own persistence logic
- compute final platform metrics directly
- bypass schema validation

Agents do:
- interpret code changes
- produce structured findings/signals
- assist refactor suggestions
- support evaluation workflows

---

## Agent 1 — Reviewer Agent

### Responsibility
Analyze a Pull Request diff and generate review findings.

### Focus Areas
- code smells
- readability
- maintainability
- architecture concerns
- security risks
- testing gaps
- suspicious implementation choices

### Inputs
- PR metadata
- normalized diff
- selected file context
- active rule pack version
- memory context (`patterns.md`, `anti_patterns.md`)

### Output Requirements
Must return strict JSON matching the findings schema.

### Output Shape
```json
{
  "summary": "string",
  "findings": [
    {
      "rule_id": "string",
      "severity": "low|medium|high",
      "category": "string",
      "file_path": "string",
      "line_start": 1,
      "line_end": 1,
      "title": "string",
      "description": "string",
      "suggestion": "string",
      "confidence": 0.0
    }
  ]
}
```

### Reviewer Rules
- only analyze changed code unless extra context is explicitly provided
- do not invent missing files or hidden logic
- prefer fewer high-confidence findings over many weak ones
- avoid style nitpicks unless they affect maintainability or correctness
- mention uncertainty through confidence, not through vague wording

### Reviewer Failure Conditions
The reviewer fails if it:
- fabricates issues not grounded in the diff
- outputs invalid JSON
- gives generic advice with no file relevance
- duplicates findings for the same issue

---

## Agent 2 — Scorer Agent

### Responsibility
Convert findings into structured scoring signals.

### Important Constraint
This agent does **not** decide the final PR score.
That remains deterministic Python logic in the platform.

### Focus Areas
- maintainability signal
- correctness confidence signal
- testing adequacy signal
- security signal
- readability signal

### Inputs
- normalized findings
- severity distribution
- rule categories
- optional repository policy profile

### Output Requirements
Strict JSON only.

### Output Shape
```json
{
  "signals": {
    "maintainability": 0,
    "correctness_confidence": 0,
    "testing": 0,
    "security": 0,
    "readability": 0
  },
  "reasoning": [
    {
      "dimension": "maintainability",
      "reason": "string"
    }
  ]
}
```

### Scorer Rules
- map findings to dimensions consistently
- do not invent metrics outside defined dimensions
- do not compute the final weighted score
- do not override platform scoring policy

### Scorer Failure Conditions
The scorer fails if it:
- returns a final score directly
- introduces dimensions not in schema
- conflicts with obvious severity distribution

---

## Agent 3 — Refactor Agent

### Responsibility
Suggest a minimal improvement to problematic code.

### Focus Areas
- clarity improvement
- safer implementation
- smaller/more composable functions
- async correctness
- dependency separation

### Inputs
- targeted finding
- relevant code snippet
- project constraints if available

### Output Requirements
Strict structured output.

### Output Shape
```json
{
  "refactor": {
    "title": "string",
    "intent": "string",
    "changes": [
      "string"
    ],
    "candidate_code": "string"
  }
}
```

### Refactor Rules
- preserve behavior unless explicitly stated otherwise
- keep changes minimal
- do not introduce unrelated abstractions
- prefer readability over cleverness
- only propose code that matches project language/context

### Refactor Failure Conditions
The refactor agent fails if it:
- rewrites too much code unnecessarily
- changes behavior without stating it
- ignores the original finding

---

## Shared Agent Guardrails

All agents must:
- return machine-parseable output
- be deterministic-friendly in wording and structure
- avoid chain-of-thought style verbosity
- ground every claim in provided context
- degrade gracefully when context is incomplete

If context is insufficient, the agent should:
- lower confidence
- emit fewer findings
- avoid speculation

---

## Anti-Patterns

Agents must not:
- invent business intent not shown in the code
- recommend full rewrites for local issues
- over-penalize stylistic preferences
- confuse missing context with actual defects
- create duplicate or overlapping findings unnecessarily
- hide uncertainty behind authoritative wording

---

## Success Criteria

An agent is successful when:
- findings are accurate
- suggestions are actionable
- false positives are minimized
- outputs validate against schema
- behavior remains stable across similar inputs

---

## Evaluation Expectations

Each agent must be testable through eval datasets.

Minimum eval expectations:
- golden PR fixtures
- expected finding IDs
- false-positive checks
- schema validation checks
- regression tests for prompt/rule updates

Suggested metrics:
- precision
- recall
- false positive rate
- schema validity rate
- duplicate finding rate

---

## Versioning

Agents are versioned indirectly through:
- prompt files
- output schemas
- rule packs
- evaluation datasets
- memory files

Every analysis run should record:
- prompt version
- rule pack version
- schema version
- model identifier if applicable

---

## Integration Notes

The recommended runtime flow is:
1. deterministic rules run first
2. reviewer agent adds contextual findings
3. scorer agent emits dimension signals
4. platform computes final score deterministically
5. optional refactor agent generates targeted improvement suggestions

This keeps the platform stable while still benefiting from AI.

---

## Minimal Operating Contract

For MVP, the platform may initially use:
- one Reviewer Agent
- deterministic Python scoring
- optional Refactor Agent for high-confidence findings

The full multi-agent model can evolve later.

That means this file should be treated as the **target contract**, not necessarily the full day-one runtime implementation.
