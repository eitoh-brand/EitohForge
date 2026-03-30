# ADR 0002: Typing and Linting Strategy

## Status

Accepted

## Context

The SDK is intended for enterprise-grade adoption and requires strict static guarantees and consistent code quality.

## Decision

- Type checker: `mypy` in strict mode.
- Linter/formatter baseline: `ruff`.
- All public SDK APIs must be explicitly typed.
- CI blocks merge when lint or type checks fail.

## Consequences

- Higher initial development discipline.
- Lower runtime defect rate from type mismatches.
- More maintainable generated code for downstream teams.
