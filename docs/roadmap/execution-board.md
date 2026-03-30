# EitohForge Execution Board

Use this board as the implementation source of truth.  
State values: `todo`, `in-progress`, `blocked`, `done`.

## Milestones

- M1: CLI + project scaffold + config
- M2: DB + migrations + repository core
- M3: validation + error contract + auth/session
- M4: CRUD generator + platform baseline release
- M5: integration and scale layer (storage/cache/events/webhooks)
- M6: enterprise layer (SSO/multi-tenant/plugins/feature flags)
- M7: packaging, publishing, and operations readiness
- M8: enterprise deployment and documentation closure

## Immediate Tracker (First 12 Tasks)

| Order | Task ID | Focus | Suggested Day | State |
|---|---|---|---|---|
| 1 | P0-01 | ADR: ORM + migration strategy | Day 1 | done |
| 2 | P0-02 | ADR: typing/lint stack | Day 1 | done |
| 3 | P0-04 | ADR: package and publish strategy | Day 1 | done |
| 4 | P0-03 | CI skeleton | Day 1 | done |
| 5 | P1-01 | CLI root command | Day 2 | done |
| 6 | P1-02 | `create project` command | Day 2 | done |
| 7 | P1-03 | project templates | Day 2-3 | done |
| 8 | P1-04 | generated-app smoke tests | Day 3 | done |
| 9 | P2-01 | `AppSettings` modules | Day 3-4 | done |
| 10 | P2-02 | env precedence + `.env.example` | Day 4 | done |
| 11 | P2-03 | startup fail-fast validation | Day 4 | done |
| 12 | P3-01 | Postgres provider baseline | Day 5 | done |

## Phase Task Table (Full A-Z Coverage)

| ID | Phase | Task | Estimate | Depends On | State | Done Criteria |
|---|---|---|---|---|---|---|
| P0-01 | 0 | Approve ADR: ORM + migration strategy | 0.5d | - | done | ADR merged |
| P0-02 | 0 | Approve ADR: typing and lint stack | 0.5d | - | done | ADR merged |
| P0-03 | 0 | Setup CI skeleton (lint/type/test jobs) | 0.5d | P0-01,P0-02 | done | CI runs successfully |
| P0-04 | 0 | Approve ADR: packaging and publish strategy (internal registry/PyPI) | 0.5d | - | done | ADR merged |
| P1-01 | 1 | Implement CLI root with Typer | 0.5d | P0-03 | done | `eitohforge --help` works |
| P1-02 | 1 | Add `create project` command | 1.0d | P1-01 | done | project scaffold generated |
| P1-03 | 1 | Create project templates for layered architecture | 1.0d | P1-02 | done | generated app boots |
| P1-04 | 1 | Add smoke tests for generated project | 0.5d | P1-03 | done | tests pass in CI |
| P2-01 | 2 | Implement `AppSettings` and module settings | 1.0d | P1-03 | done | typed settings load correctly |
| P2-02 | 2 | Add env resolution order and `.env.example` template | 0.5d | P2-01 | done | config precedence tested |
| P2-03 | 2 | Add startup validation and clear errors | 0.5d | P2-01 | done | invalid config fails startup |
| P2-04 | 2 | Secret provider abstraction (env/vault/cloud) | 1.0d | P2-03 | done | `secret.get()` contract available |
| P3-01 | 3 | Add DB provider interface + Postgres adapter | 1.0d | P2-03 | done | DB connection reusable |
| P3-02 | 3 | Integrate migration toolchain | 1.0d | P3-01 | done | migration init works |
| P3-03 | 3 | Add CLI: db init/migrate/upgrade/downgrade/current | 1.0d | P3-02 | done | all DB CLI commands work |
| P3-04 | 3 | Add migration drift and safety checks in CI | 0.5d | P3-03 | done | CI blocks drift |
| P3-05 | 3 | Multi-DB registry scaffolding (primary/analytics/search) | 1.0d | P3-01 | done | `db_registry.get()` works |
| P4-01 | 4 | Define repository contracts and DTO boundaries | 0.5d | P3-03 | done | contracts documented |
| P4-02 | 4 | Implement SQL repository core CRUD | 1.0d | P4-01 | done | CRUD integration tests pass |
| P4-03 | 4 | Implement filter/sort/specification operators | 1.0d | P4-02 | done | query ops tested |
| P4-04 | 4 | Implement pagination and transaction manager | 1.0d | P4-02 | done | pagination + UoW tested |
| P4-05 | 4 | Add cursor/keyset pagination modes | 1.0d | P4-04 | done | cursor/keyset tested |
| P4-06 | 4 | Distributed transaction pattern (saga scaffold) | 1.0d | P4-04 | done | saga orchestration baseline works |
| P5-01 | 5 | Create validation package architecture | 0.5d | P4-01 | done | package ready |
| P5-02 | 5 | Add request/schema and cross-field validators | 1.0d | P5-01 | done | validation tests pass |
| P5-03 | 5 | Add domain typed value objects | 1.0d | P5-01 | done | invalid domain state blocked |
| P5-04 | 5 | Add business/security validation hooks | 1.0d | P5-02,P5-03 | done | rules enforced in service layer |
| P6-01 | 5 | Implement unified `ApiResponse` and pagination models | 0.5d | P5-02 | done | response contract fixed |
| P6-02 | 5 | Implement error registry and middleware mapping | 1.0d | P6-01,P5-04 | done | errors standardized |
| P6-03 | 5 | Add API versioning router strategy (`/v1`, `/v2`) | 1.0d | P6-01 | done | versioned endpoints functional |
| P7-01 | 6 | Implement JWT manager and refresh rotation | 1.0d | P6-02 | done | auth flows tested |
| P7-02 | 6 | Implement session manager (Redis first) | 1.0d | P7-01 | done | revoke/revoke-all tested |
| P7-03 | 6 | Add RBAC decorators and route integration | 1.0d | P7-01 | done | permission checks pass |
| P7-04 | 6 | Add ABAC policy engine and decorators | 1.0d | P7-03 | done | policy checks pass |
| P7-05 | 6 | Add unified `SecurityContext` object | 0.5d | P7-02,P7-03 | done | context available in request lifecycle |
| P8-01 | 7 | Build CRUD generator command | 1.0d | P4-04,P6-02 | done | command generates module |
| P8-02 | 7 | Add CRUD templates with validation + response standards | 1.0d | P8-01 | done | generated module compiles |
| P8-03 | 7 | Add generated tests and golden template checks | 1.0d | P8-02 | done | generated tests pass |
| P9-01 | 8 | Add storage abstraction and local adapter | 1.0d | P6-02 | done | local storage works |
| P9-02 | 8 | Add S3 adapter and presigned URLs | 1.0d | P9-01 | done | presigned flow tested |
| P9-03 | 8 | Add storage access policy engine | 1.0d | P9-02 | done | policy checks enforced |
| P9-04 | 8 | Add CDN URL rewriting integration layer | 0.5d | P9-02 | done | public URL generation supports CDN |
| P10-01 | 9 | Add cache abstraction and Redis adapter | 1.0d | P6-02 | done | cache get/set tested |
| P10-02 | 9 | Add advanced cache invalidation (tag/prefix/write-through) | 1.0d | P10-01 | done | invalidation semantics tested |
| P10-03 | 9 | Add rate limiter middleware | 1.0d | P7-03 | done | policy limits enforced |
| P10-04 | 9 | Add idempotency middleware for writes | 1.0d | P6-02,P10-01 | done | duplicates deduped |
| P10-05 | 9 | Add request signing middleware (timestamp/nonce/signature) | 1.0d | P7-01 | done | replay/tamper checks pass |
| P10-06 | 9 | Add capability endpoint (`/sdk/capabilities`) | 0.5d | P10-05 | done | mobile SDK can fetch capability profile |
| P11-01 | 10 | Add internal event bus contract and dispatcher | 1.0d | P6-02 | done | handlers triggered |
| P11-02 | 10 | Add background job adapter and retry policy | 1.0d | P11-01 | done | retries verified |
| P11-03 | 10 | Add webhook framework with signature and DLQ | 1.0d | P11-02,P10-05 | done | webhook events routed/retried |
| P11-04 | 10 | Add notification gateway (email/SMS/push baseline) | 1.0d | P11-02 | done | notification send path tested |
| P11-05 | 10 | Add template messaging engine (localized templates) | 1.0d | P11-04 | done | `send_template()` works |
| P11-06 | 10 | Add external API client framework (retry/circuit breaker) | 1.0d | P6-02 | done | external client baseline tested |
| P12-01 | 11 | Add metrics/logging/tracing integration points | 1.0d | P6-02 | done | telemetry exported |
| P12-02 | 11 | Add health/readiness/status endpoints | 0.5d | P3-01,P10-01 | done | subsystem checks report correctly |
| P12-03 | 11 | Add audit logging engine | 1.0d | P7-02,P8-03 | done | auth + CRUD events audited |
| P12-04 | 11 | Add search integration abstraction (Elastic/OpenSearch) | 1.0d | P3-05 | done | search provider contract works |
| P12-05 | 11 | Add socket infrastructure with JWT + rooms | 1.0d | P7-01 | done | auth rooms/presence works |
| P13-01 | 12 | Implement SSO broker and provider contracts | 1.0d | P7-01 | done | external login -> internal JWT works |
| P13-02 | 12 | Add OIDC/SAML adapters baseline | 1.0d | P13-01 | done | OIDC and SAML smoke tests pass |
| P13-03 | 12 | Add tenant context and isolation boundaries | 1.0d | P3-05,P7-05 | done | tenant isolation tested |
| P13-04 | 12 | Add plugin registry for routes/providers/events | 1.0d | P8-03 | done | plugin module can self-register |
| P13-05 | 12 | Add feature flag service and staged rollout API | 1.0d | P6-03 | done | feature switches evaluated at runtime |
| P14-01 | 13 | Security hardening review and remediation | 1.0d | P10-06,P13-02 | done | no critical findings open |
| P14-02 | 13 | Performance baseline and regression checks | 1.0d | P11-02,P12-05 | done | baseline report published |
| P14-03 | 13 | Final docs, cookbook, and release candidate prep | 1.0d | P14-01,P14-02 | done | `v0.1.0-rc` tagged |
| P15-01 | 14 | Create `pyproject.toml` packaging layout and console entrypoint | 1.0d | P0-04,P14-03 | todo | build metadata validated |
| P15-02 | 14 | Configure reproducible `wheel` + `sdist` build pipeline | 1.0d | P15-01 | todo | artifacts generated in CI |
| P15-03 | 14 | Add internal registry publishing workflow and provenance metadata | 1.0d | P15-02 | todo | artifact publish verified |
| P15-04 | 14 | Add optional PyPI release lane with guarded approvals | 0.5d | P15-03 | todo | dry-run release passes |
| P15-05 | 14 | Add dependency audit, SBOM generation, and license checks | 1.0d | P15-02 | todo | security/compliance gates green |
| P15-06 | 14 | Create operations runbook (deploy, rollback, SLO/error budget) | 1.0d | P14-03 | todo | runbook approved for prod use |
| P16-01 | 15 | Define TLS strategy (ingress termination + cert rotation policy) | 1.0d | P15-06 | todo | TLS runbook approved |
| P16-02 | 15 | Define optional mTLS for internal traffic and trust model | 1.0d | P16-01 | todo | mTLS design validated |
| P16-03 | 15 | Define load balancing architecture and health-check routing | 1.0d | P15-06 | todo | LB policy documented and tested |
| P16-04 | 15 | Define deployment strategy (rolling/blue-green/canary) and rollback controls | 1.0d | P15-06 | todo | deployment playbook approved |
| P16-05 | 15 | Implement test closure suite (contract/e2e/migration/perf/security) | 1.0d | P14-02 | todo | all test classes active in CI |
| P16-06 | 15 | Enforce test coverage threshold and flaky-test governance | 0.5d | P16-05 | todo | quality gates block regressions |
| P16-07 | 15 | Build `example-minimal` reference application | 1.0d | P8-03 | todo | minimal example smoke tests pass |
| P16-08 | 15 | Build `example-enterprise` full-feature application | 1.0d | P13-05,P12-05 | todo | enterprise example smoke tests pass |
| P16-09 | 15 | Publish full usage docs (install/config/migrations/auth/plugins/deploy/troubleshooting) | 1.0d | P16-07,P16-08 | todo | docs complete and reviewed |
| P16-10 | 15 | Documentation QA pass with onboarding simulation | 0.5d | P16-09 | todo | new-user success path validated |

## Critical Path

`P0-01 -> P0-03 -> P1-02 -> P2-03 -> P3-03 -> P4-04 -> P5-04 -> P6-02 -> P7-02 -> P8-03 -> P10-04 -> P14-03 -> P15-03 -> P16-09`

## Weekly Reporting Template

- Completed task IDs:
- In-progress task IDs:
- Blocked task IDs + reason:
- Next 7-day plan:
- Scope changes (if any):
