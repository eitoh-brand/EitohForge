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
- Coverage threshold enforced per package.
- Flaky tests must be quarantined with owner and remediation SLA.

## Reference Example Projects

- `example-minimal`:
  - fast bootstrap
  - single module
  - migrations and auth basics
- `example-enterprise`:
  - multi-tenant aware
  - auth/session/RBAC
  - background jobs + notifications
  - observability + health + security middleware

## Documentation Expectations for Examples

- each example has setup, run, and test instructions
- each example has architecture notes and extension hints
- each example includes smoke test automation

## Definition of “Test Complete”

- all mandatory test classes pass in CI
- examples pass smoke tests
- no unresolved critical defects in release branch
