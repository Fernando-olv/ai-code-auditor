# Contributing

Thanks for taking a look at AI Dev Auditor. The project is an MVP, so the contribution surface is small and opinionated. This document is the minimum you need to be productive locally.

## Setup

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env   # then edit GITHUB_WEBHOOK_SECRET at minimum
```

The bash equivalent: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`.

## Run the checks CI runs

CI in [.github/workflows/ci.yml](.github/workflows/ci.yml) runs exactly these three commands. Run them locally before pushing:

```powershell
ruff check .
ruff format --check .
$env:GITHUB_WEBHOOK_SECRET = "ci_dummy_secret"
pytest -q -m "not integration"
```

`ruff format` (without `--check`) will auto-fix formatting.

## Run the integration suite (optional)

Integration tests are gated by the `integration` marker registered in [pyproject.toml](pyproject.toml). They require the Firestore emulator:

```powershell
gcloud beta emulators firestore start --host-port=127.0.0.1:8080
$env:FIRESTORE_EMULATOR_HOST = "127.0.0.1:8080"
pytest -m integration
```

## Run the local demo

Useful when changing the webhook receive path, the runner, or the markdown renderer. See [docs/DEMO.md](docs/DEMO.md) for the full script. Short version:

```powershell
.\.venv\Scripts\Activate.ps1
$env:GITHUB_WEBHOOK_SECRET = "demo_local_secret"
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# in another terminal, after setting the same secret:
.\scripts\demo_local_analysis.ps1
```

## Code style

- Type hints on public function signatures. Keep functions small and pure where possible.
- Domain types in [`app/domain/`](app/domain/) must not depend on anything in `app/services/`, `app/vendor/`, or `app/api/`.
- New external integrations go under [`app/vendor/<name>/`](app/vendor/) implementing a Protocol from [`app/ports/`](app/ports/). Wire them via the relevant factory in [`app/services/`](app/services/).
- Don't add narrating comments. Comments are for non-obvious intent or constraints. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the boundaries to respect.
- Don't widen scope. A focused diff that solves one problem is strictly better than a sweeping one.

## Commit messages

Conventional-commits style is used in the implementation log ([docs/PROGRESS.md](docs/PROGRESS.md)):

```
feat(services): one-line summary
fix(api): one-line summary
chore(deps): one-line summary
test: one-line summary
docs: one-line summary
```

Body is optional; include it when the "why" is not obvious from the diff.

## Pull requests

- Reference the milestone you are advancing (see [docs/EXECUTION_PLAN.md](docs/EXECUTION_PLAN.md)).
- Keep PRs to one vertical slice when possible.
- Update [docs/PROGRESS.md](docs/PROGRESS.md) with a row in the appropriate milestone table when your change ships behavior.
- CI must be green. The auditor will, in time, be reviewing its own PRs — try not to give it ammunition.
