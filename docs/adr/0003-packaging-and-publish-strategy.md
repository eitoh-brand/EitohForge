# ADR 0003: Packaging and Publish Strategy

## Status

Accepted

## Context

EitohForge must be distributed in a reproducible, enterprise-ready way with predictable installs and release controls.

## Decision

- Package distribution: single package `eitohforge` (SDK + CLI) for initial releases.
- Build backend: hatchling via `pyproject.toml`.
- Artifact formats: `wheel` and `sdist`.
- Primary publish channel: internal package registry.
- Optional external channel: PyPI with approval gate.

## Consequences

- Simplified onboarding (`pip install eitohforge`).
- Stronger release control through internal-first distribution.
- Future split into separate `eitohforge-sdk` and `eitohforge-cli` remains possible.
