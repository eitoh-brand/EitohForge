# Contributing to EitohForge

## Requirements

- Python 3.12+
- Install dev dependencies from `pyproject.toml`.

## Local Workflow

1. Run lint checks.
2. Run type checks.
3. Run tests.
4. Update docs when behavior or APIs change.

## Quality Gates

- Lint must pass.
- Type checks must pass.
- Tests must pass.
- Migration and config-impacting changes must include docs updates.
- Migration policy check must pass (`python scripts/check_migration_policy.py`).

## Migration Safety Rules

- Destructive migrations (drop/truncate) are blocked unless explicitly approved.
- To approve a destructive migration, include this marker in the migration file:
  - `MIGRATION_APPROVED_DESTRUCTIVE`

## Coding Rules

- Keep domain logic framework-agnostic where possible.
- Prefer typed contracts over raw dictionaries.
- Avoid breaking public APIs without explicit versioning and release notes.
