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

## CI/CD Workflows

- `ci.yml`
  - quality gates: lint, typing, tests, migration policy
  - packaging metadata validation
  - reproducible build verification (`wheel` + `sdist`)
  - compliance gates: `pip-audit`, SBOM, license policy
- `publish-internal.yml`
  - workflow-dispatch controlled internal registry release
  - dry-run mode for validation-only runs
  - provenance attestation for `dist/*`
- `publish-pypi.yml`
  - optional guarded PyPI release lane
  - default dry-run mode
  - intended for environment approval gates

## Secrets and Environment Requirements

For internal publish workflow:

- `INTERNAL_PYPI_REPOSITORY_URL`
- `INTERNAL_PYPI_USERNAME`
- `INTERNAL_PYPI_PASSWORD`

For guarded PyPI workflow:

- use trusted publishing or the configured `pypi-release` environment secret policy.

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

## Local Validation Commands

- `python scripts/validate_packaging_metadata.py`
- `python -m build --sdist --wheel`
- `python scripts/verify_reproducible_build.py dist-pass-a dist-pass-b`
- `pip-audit --strict`
- `cyclonedx-py environment --output-file compliance/sbom.cdx.json --of JSON`
- `pip-licenses --format=json --output-file=./compliance/licenses.json`
- `python scripts/check_license_policy.py`
