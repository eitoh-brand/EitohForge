# Phase 0 and 1 Kickoff Guide

Use this guide to start implementation immediately with minimal ambiguity.

Before starting, verify `docs/roadmap/architecture-coverage-matrix.md` and `docs/roadmap/execution-board.md` are aligned.

## Goal

Reach Milestone M1:

- CLI scaffold exists
- project generation works
- baseline settings/config flow is in place

## Day 1 Checklist

- [ ] Confirm ADR decisions:
  - ORM + migration strategy
  - type checker (`mypy` or `pyright`)
  - formatter/linter stack
  - package and publish strategy (internal registry first)
- [ ] Initialize repository structure:
  - `eitohforge_cli/`
  - `eitohforge_sdk/`
  - `templates/project/`
  - `tests/`
- [ ] Add CI skeleton with lint/type/test jobs.
- [ ] Add package build job (wheel + sdist dry run).

## Day 2 Checklist

- [ ] Implement `eitohforge` CLI root command.
- [ ] Implement `create project <name>` command.
- [ ] Add template renderer (Jinja2).
- [ ] Generate FastAPI skeleton with layered folders.
- [ ] Add smoke test: generated app boots.

## Day 3 Checklist

- [ ] Implement base settings models and loader.
- [ ] Add `.env.example` generation.
- [ ] Add startup validation for required settings.
- [ ] Add tests for valid and invalid config paths.

## Suggested Initial File Targets

- `eitohforge_cli/main.py`
- `eitohforge_cli/commands/create_project.py`
- `eitohforge_cli/templates.py`
- `eitohforge_sdk/core/config.py`
- `eitohforge_sdk/core/lifecycle.py`
- `templates/project/app/main.py.j2`
- `tests/cli/test_create_project.py`
- `tests/config/test_settings_validation.py`

## Early Acceptance Tests

- `eitohforge --help` prints command tree.
- `eitohforge create project my_service` creates expected structure.
- Generated app starts with valid env.
- Generated app fails fast with missing required env.

## Common Pitfalls to Avoid

- Avoid hard-coding provider implementations in app layer.
- Avoid mixing domain logic with request schema validators.
- Avoid adding non-MVP adapters in Phase 1.
- Avoid skipping tests for generated templates.

## Definition of Done for M1

- Commands implemented and tested.
- Generated project runnable.
- Settings and env validation in place.
- CI green for lint, type checks, and tests.
- First 12 tasks in the execution board are updated with accurate state.
