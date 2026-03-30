# Testing and Example Project Strategy

This guide defines what “complete testing” means for EitohForge and how reference projects are delivered.

## Test Pyramid and Scope

- Unit tests:
  - domain logic
  - validation rules
  - provider contracts
- Integration tests:
  - database, cache, storage, queue, and search adapters
  - migration upgrade/downgrade paths
- Contract tests:
  - API response/error schema contracts
  - generated CRUD module contracts
- End-to-end tests:
  - auth/session/RBAC/ABAC paths
  - critical CRUD and workflow routes
- Security tests:
  - auth bypass attempts
  - idempotency replay checks
  - signature/nonce verification
- Performance tests:
  - baseline latency and throughput
  - regression thresholds in CI/reporting

## Quality Gates

- CI must fail if required test classes do not run.
- Coverage threshold enforced for `eitohforge_sdk` and `eitohforge_cli` (see `pyproject.toml` / CI).
- Flaky tests must be quarantined with owner and remediation SLA (`docs/standards/flaky-test-policy.md`).

## Test Closure Layout (P16)

Organized suites (markers + directories):

- `tests/contract/` — API/error JSON contracts (`@pytest.mark.contract`)
- `tests/e2e/` — CLI + HTTP journeys (`@pytest.mark.e2e`)
- `tests/migration/` — Alembic layout + migration policy (`@pytest.mark.migration`)
- `tests/performance/` — perf smoke/regression (`@pytest.mark.perf`)
- `tests/security/` — security regressions (`@pytest.mark.security`)

Integration and unit tests remain under `tests/integration/` and `tests/unit/`. Markers are strict; only registered markers may be used.

## Reference Example Projects

Committed under `examples/`:

- `examples/example-minimal` — FastAPI + capabilities + `/health`; smallest install surface.
- `examples/example-enterprise` — hardening, observability, tenant isolation, feature flags, full health family.

For a **generated** full stack (CRUD, DB, webhooks, search, sockets), use `eitohforge create project` and optional `create crud`.

## Documentation Expectations for Examples

- each example has setup, run, and test instructions
- each example has architecture notes and extension hints
- each example includes smoke test automation

## Definition of “Test Complete”

- all mandatory test classes pass in CI
- examples pass smoke tests
- no unresolved critical defects in release branch
