# Onboarding QA Simulation (New Team Member)

Use this checklist to validate that a new engineer can adopt EitohForge without ad hoc support. Complete in order; record pass/fail and notes.

## Environment

- [ ] Clean Python 3.12+ virtual environment.
- [ ] Repository cloned and on `main` (or release tag).
- [ ] `uv pip install -e ".[dev]"` (or `pip install -e ".[dev]"`) succeeds.

## CLI

- [ ] `eitohforge --help` shows `create` and `db` command groups.
- [ ] `eitohforge create project qa_tmp` succeeds in a temp directory.
- [ ] `eitohforge create project qa_tmp2 --mode standalone` succeeds.
- [ ] `cd qa_tmp && eitohforge create crud items --path .` succeeds.

## Generated project

- [ ] `pytest` passes inside `qa_tmp` (or documented test command from template README).
- [ ] `python -c "from app.main import app"` succeeds (SDK mode).
- [ ] `GET /health` returns 200 via `TestClient` or HTTP client.

## Examples (repository)

- [ ] `pip install -e "examples/example-minimal[dev]"` after root install.
- [ ] `pytest examples/example-minimal/tests -q` passes.
- [ ] `pip install -e "examples/example-enterprise[dev]"` passes.
- [ ] `pytest examples/example-enterprise/tests -q` passes.

## Documentation

- [ ] `docs/guides/usage-complete.md` answers: install, config, migrations, auth, deploy, troubleshooting.
- [ ] `docs/guides/cookbook.md` covers tenant, plugins, flags, hardening.
- [ ] Execution board in `docs/roadmap/execution-board.md` reflects completed phases relevant to release.

## Quality gates (optional local mirror of CI)

- [ ] `ruff check .` passes at repo root.
- [ ] `mypy src` passes.
- [ ] `pytest` at repo root passes (includes coverage gate per `pyproject.toml`).

## Sign-off

- Reviewer name:
- Date:
- Release or branch tested:
- Failures / follow-ups:
