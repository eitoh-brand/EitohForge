# EitohForge Planning Docs

This folder contains the long-term planning and implementation documentation for the EitohForge backend SDK platform.

**Blueprint (repository root):** `../secure_backend_sdk_architecture.md` — full A–Z target architecture; the **Appendix — EitohForge implementation map** at the end of that file compares §1–§44 to what is implemented today.

## Documents

- `roadmap/master-implementation-roadmap.md`  
  Full end-to-end phase plan (scope, milestones, acceptance criteria).
- `roadmap/execution-board.md`  
  Task-level execution board with IDs, estimates, dependencies, and done criteria.
- `roadmap/architecture-coverage-matrix.md`  
  Traceability map from all 44 architecture items to tracked tasks.
- `roadmap/blueprint-completion-waves.md`  
  Post-baseline plan to reach L1/L2/L3 depth vs `secure_backend_sdk_architecture.md`; links to Phase 17 tasks (`P17-*`).
- `standards/engineering-standards.md`  
  Coding, validation, migration, security, testing, and release standards.
- `standards/flaky-test-policy.md`  
  Quarantine, ownership, and remediation SLA for flaky tests.
- `guides/phase-0-and-1-kickoff.md`  
  Immediate implementation checklist for getting started.
- `guides/python-packaging-and-publishing.md`  
  Package build, release channels, and publish workflow.
- `guides/usage-complete.md`  
  Full usage: install, config, migrations, auth, plugins, deploy, troubleshooting.
- `guides/onboarding-qa-simulation.md`  
  New-hire / release QA checklist for onboarding without hand-holding.
- `guides/enterprise-readiness-checklist.md`  
  Production and enterprise readiness validation checklist.
- `guides/enterprise-deployment-and-networking.md`  
  SSL/TLS, load balancing, deployment reliability, and HA guidance.
- `guides/tls-and-cert-rotation-runbook.md`  
  Ingress TLS policy, cert lifecycle, and emergency rotation procedure.
- `guides/mtls-trust-model.md`  
  Optional internal mTLS trust domains, identity mapping, and rollout modes.
- `guides/load-balancing-and-health-routing.md`  
  LB architecture, readiness routing policy, and health-check baseline.
- `guides/deployment-strategies-and-rollback-controls.md`  
  Rolling/blue-green/canary playbooks with abort and rollback controls.
- `guides/testing-and-example-project-strategy.md`  
  Test completeness model and reference example project requirements.
- `guides/repository-contracts-and-dto-boundaries.md`  
  Clean architecture repository contract and persistence DTO reference.
- `guides/query-spec-reference.md`  
  `QuerySpec` filter operators, pagination modes, and optional column validation.
- `guides/cookbook.md`  
  Implementation recipes for tenanting, plugins, flags, hardening, and perf checks.
- `guides/operations-runbook.md`  
  Deploy, rollback, SLO, error budget, and incident response baseline.
- `performance/baseline.md`  
  Latest generated baseline benchmark report.
- `releases/v0.1.0-rc.md`  
  Release candidate readiness and validation checklist.

## How to Use

1. Review `master-implementation-roadmap.md` to confirm scope and sequence.
2. Validate architecture completeness in `architecture-coverage-matrix.md`.
3. Execute tasks from `execution-board.md` in dependency order.
4. Follow `engineering-standards.md` for all PRs and generated templates.
5. Align release expectations with `python-packaging-and-publishing.md`.
6. Align deployment posture with `enterprise-deployment-and-networking.md`.
7. Align test posture with `testing-and-example-project-strategy.md`.
8. Validate launch quality with `enterprise-readiness-checklist.md`.
9. Start implementation using `phase-0-and-1-kickoff.md`.

## Update Rules

- Keep task IDs stable once assigned.
- Mark task state directly in `execution-board.md`.
- If scope changes, update both roadmap and execution board in the same change.
- Keep standards backward compatible unless versioned under a new section.
