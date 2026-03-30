# Python Packaging and Publishing Guide

This guide defines how EitohForge will be packaged and distributed for production use.

## Packaging Model

- Primary package: `eitohforge` (SDK + CLI together for simpler adoption).
- Future split option (if needed): `eitohforge-sdk` and `eitohforge-cli`.
- Build system: `pyproject.toml` with a modern PEP 517 backend.

## Required Artifacts

- `wheel` for normal installation.
- `sdist` for source distribution and reproducibility checks.

## Required Entry Points

- CLI command: `eitohforge`
- Package import: `eitohforge_sdk`

## Release Channels

1. Internal registry (default and recommended).
2. Public PyPI (optional, approval-gated).

## Build and Publish Flow

1. Validate branch with lint, type checks, and tests.
2. Generate changelog entries and version bump.
3. Build `wheel` and `sdist`.
4. Run artifact integrity and installation smoke test.
5. Generate SBOM and run dependency/license scans.
6. Publish to internal registry.
7. Optionally publish to PyPI after approval.

## Versioning Policy

- Use semantic versioning.
- Breaking changes require major bump and migration notes.
- Generated template changes must be versioned and documented.

## Minimum Release Checklist

- [ ] Version tag exists and matches package metadata.
- [ ] Build artifacts are reproducible from tag.
- [ ] CLI install and `eitohforge --help` smoke test passes.
- [ ] Changelog and migration notes are complete.
- [ ] Vulnerability and license checks pass.
- [ ] SBOM attached to release record.
