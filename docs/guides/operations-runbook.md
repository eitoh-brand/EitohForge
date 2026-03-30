# EitohForge Operations Runbook

Operational baseline for deployment, rollback, and reliability governance.

## 1) Deployment Workflow

- CI quality gates must pass (`ruff`, `mypy`, `pytest`, migration policy).
- Package build must pass reproducibility and metadata checks.
- Security/compliance gates must pass (`pip-audit`, SBOM, license policy).
- Publish to internal registry first (`publish-internal.yml`).
- Promote to production release through environment approvals.

## 2) Release Environments

- `dev`: automatic deploy after merge to protected branch.
- `staging`: deploy candidate from internal registry and run smoke suite.
- `prod`: manual approval required; use release artifact already validated in staging.

## 3) Rollback Procedure

1. Identify target previous version from internal registry.
2. Trigger rollback deployment with previous version pin.
3. Confirm `/ready` and `/status` endpoints report healthy.
4. Validate core API smoke suite and critical business paths.
5. Open post-incident record with root cause and corrective action.

## 4) Incident Severity and Response

- `SEV-1`: full outage or data integrity risk, page immediately.
- `SEV-2`: degraded service with customer impact.
- `SEV-3`: minor degradation or non-critical feature issue.

Escalation path:

- On-call engineer -> platform owner -> engineering lead.

## 5) SLO and Error Budget Baseline

- Availability SLO: `99.9%` monthly for API endpoints.
- p95 latency SLO: `< 300ms` for core read/write paths.
- Error rate SLO: `< 0.5%` 5xx over rolling 30 minutes.

Error budget:

- Monthly downtime budget for 99.9%: ~43.8 minutes.
- If budget burn exceeds 50% mid-cycle, freeze non-critical releases.

## 6) Monitoring and Alerting

- Use telemetry from observability middleware and health endpoints:
  - `/health`
  - `/ready`
  - `/status`
- Alert on:
  - sustained 5xx elevation
  - SLO burn-rate threshold breach
  - readiness check failures

## 7) Change Management Policy

- No direct production deploy from untagged commits.
- Every production release must map to immutable artifacts.
- Schema migrations must be backward-compatible for rolling deployments.

## 8) Operational Checklists

### Pre-Deploy Checklist

- [ ] Release artifact built in CI with reproducibility checks
- [ ] Vulnerability and license checks green
- [ ] Migration plan reviewed
- [ ] Rollback candidate confirmed

### Post-Deploy Checklist

- [ ] Readiness/health green
- [ ] No elevated error budget burn
- [ ] Key user journeys validated
- [ ] Incident channel quiet for 30 minutes

## 9) Network and Deployment References

- `docs/guides/tls-and-cert-rotation-runbook.md`
- `docs/guides/mtls-trust-model.md`
- `docs/guides/load-balancing-and-health-routing.md`
- `docs/guides/deployment-strategies-and-rollback-controls.md`
