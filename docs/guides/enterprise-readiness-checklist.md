# Enterprise Readiness Checklist

Use this checklist before calling the platform production-ready.

## 1) Configuration and Secrets

- [ ] Typed settings load from env with fail-fast startup validation.
- [ ] Secret providers support environment and managed secret backends.
- [ ] Production config matrix exists for all environments.

## 2) Data and Migration Safety

- [ ] Schema changes always accompanied by migrations.
- [ ] Upgrade and downgrade paths tested in CI.
- [ ] Migration drift checks enforced.
- [ ] Backup and rollback procedure documented.

## 3) Type and Validation Guarantees

- [ ] Strict type checks enabled in CI.
- [ ] Domain value objects enforce critical datatype constraints.
- [ ] Request, business, and security validations share a unified error contract.

## 4) Security Baseline

- [ ] JWT + refresh rotation + session revocation implemented.
- [ ] RBAC and ABAC checks enforced on protected routes.
- [ ] Rate limiting and idempotency enabled for write operations.
- [ ] Request signing and nonce checks available for high-security clients.

## 5) Platform Capabilities

- [ ] CRUD generator outputs production-valid modules.
- [ ] Storage/cache/event/webhook modules pass integration tests.
- [ ] Capability endpoint advertises active security requirements.
- [ ] API versioning strategy implemented and documented.

## 6) Observability and Operations

- [ ] Structured logs and metrics emitted by default.
- [ ] Health/readiness/status endpoints monitor dependencies.
- [ ] SLO targets and error budgets defined.
- [ ] On-call and incident runbooks available.

## 6a) Networking and Deployment Reliability

- [ ] TLS termination and certificate rotation strategy approved.
- [ ] Load-balancer health-check routing validated.
- [ ] Deployment strategy (rolling/blue-green/canary) selected and tested.
- [ ] Rollback and disaster recovery playbooks tested.

## 7) Packaging and Release

- [ ] Package builds produce wheel and sdist artifacts.
- [ ] Internal registry publish pipeline works end-to-end.
- [ ] Artifact provenance, checksums, and SBOM are generated.
- [ ] Release can be installed and smoke-tested via package manager.

## 7a) Test and Example Completeness

- [ ] Unit/integration/contract/e2e/migration/performance/security suites are active.
- [ ] Coverage thresholds and flaky-test policy are enforced.
- [ ] `example-minimal` and `example-enterprise` projects pass smoke tests.

## 8) Governance and Maintainability

- [ ] Public SDK APIs have backward compatibility policy.
- [ ] Plugin/provider interfaces are versioned and documented.
- [ ] Architecture coverage matrix maps planned vs delivered modules.
- [ ] Security/compliance gates are mandatory in CI.

## Comparison Target

A release is considered enterprise-comparable when the above baseline is met consistently, with repeatable build and runtime operations similar to mature framework ecosystems (for example, Spring Boot-based delivery workflows).
