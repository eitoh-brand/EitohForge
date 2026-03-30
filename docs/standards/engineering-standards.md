# EitohForge Engineering Standards

This document defines mandatory standards for development, generated code, and releases.

## 1) Language and Runtime

- Python 3.12 minimum.
- FastAPI as primary HTTP framework.
- Async-first design for infrastructure operations.

## 2) Architecture Rules

- Enforce clean layering:
  - presentation
  - application
  - domain
  - infrastructure
  - core
- Domain layer must not import infrastructure.
- Application layer depends on interfaces, not concrete adapters.

## 3) Configuration and Environment

- Use `pydantic-settings` for all runtime config.
- Environment variables must be prefixed with `EITOHFORGE_`.
- Required settings validated at startup; fail fast on invalid config.
- Keep `.env.example` updated whenever settings change.

### Platform feature toggles

Choose **one primary control plane** per deployment and document it:

- **Environment (`EITOHFORGE_*`)** — default for twelve-factor apps; use `standard` vs `minimal` CLI profile only to seed `.env.example`.
- **`ForgePlatformToggles`** — per-field `True` / `False` / `None` on `ForgeAppBuildConfig`; `None` inherits from settings. Use for tests, constrained environments, or forcing behavior independent of env.
- **`forge_platform_toggles_uniform(enabled=...)`** — same as setting every toggle field to `True` or `False`; pair with `ForgeAppBuildConfig.wire_*` when you also need to omit entire route families.
- **`ForgeAppBuildConfig.wire_platform_middleware`** — when `False`, skips most middleware registration (see SDK `build_forge_app`); still applies HTTPS redirect and CORS per toggles/settings where applicable.

## 4) Type Safety

- All public SDK interfaces must have explicit type annotations.
- Use strict type checking in CI.
- Avoid untyped dictionaries in service/domain boundaries.
- Prefer typed value objects for critical fields:
  - email
  - phone
  - tenant ID
  - money

## 5) Validation Standards

- Validation must happen at four levels:
  - request/schema
  - domain/type
  - business rule
  - security input checks
- Cross-field rules must use explicit validators.
- Validation errors must map to a unified API error schema.

## 6) Database and Migration Standards

- Every schema change must ship with a migration file.
- No direct production schema edits without migration.
- Destructive migrations require explicit review and approval.
- Migration commands must be reproducible in CI and local environments.

## 7) API Contract Standards

- All endpoints return standardized envelopes:
  - `ApiResponse[T]`
  - `PaginatedResponse[T]`
  - `ErrorResponse`
- Error responses include:
  - stable `error_code`
  - human-readable message
  - trace/correlation identifier when available

## 8) Security Standards

- JWT access tokens must be short-lived.
- Refresh token rotation is mandatory.
- Session revocation support required.
- Rate limiting and idempotency required on mutable endpoints.
- Never log secrets or sensitive auth payloads.

## 9) Testing Standards

- Minimum required test classes:
  - unit tests for core contracts and validation logic
  - integration tests for DB/migration/auth flows
  - generator tests for template correctness
- Generated projects must pass tests out of the box.
- New features require tests for success and failure paths.

## 10) Observability Standards

- Use structured logs with consistent fields.
- Emit core metrics:
  - latency
  - error rate
  - cache hit rate
  - DB query duration
- Health endpoints must include dependency status checks.

## 11) Documentation Standards

- Each major module requires:
  - purpose
  - integration guide
  - configuration reference
  - examples
- Keep roadmap and execution board current with scope changes.

## 12) Release Standards

- Follow semantic versioning.
- Block release if lint/type/tests fail.
- Publish changelog and migration notes for each release.
- Keep release artifacts reproducible from tagged source.

## 13) Packaging and Distribution Standards

- Use `pyproject.toml` as the single packaging source of truth.
- Build and publish both `wheel` and `sdist` artifacts.
- Expose CLI through console scripts (command: `eitohforge`).
- Pin direct dependencies using an approved strategy and lock transitive dependencies for CI.
- Prefer internal artifact registry as primary distribution path; treat public index publishing as opt-in.
- Every published artifact must include:
  - version metadata
  - changelog entry
  - checksum
  - provenance/build metadata

## 14) Enterprise Runtime and Operations Standards

- Define baseline SLOs (availability, latency, error rate) before production launch.
- Maintain deployment and rollback runbooks for each supported environment.
- Require structured startup diagnostics (config, dependency health, migration status).
- Enforce security/compliance checks in CI:
  - dependency vulnerability scanning
  - license policy checks
  - SBOM generation
- Enforce backward compatibility policy for SDK public APIs and generated templates.

## 15) Networking, TLS, and Load Balancing Standards

- All production deployments must use TLS 1.2+ with managed certificate rotation.
- TLS termination strategy must be explicitly documented (ingress/gateway/proxy).
- Internal mTLS is recommended for service-to-service traffic in high-security environments.
- Load balancer configuration must include:
  - readiness-based routing
  - health-check path standards
  - timeout and retry settings
  - stateless defaults (sticky sessions only when justified)
- Deployment architecture must define high availability targets (multi-AZ or equivalent).

## 16) Test Completeness Standards

- CI must execute the following test classes:
  - unit
  - integration
  - contract
  - end-to-end
  - migration
  - performance baseline
  - security regression
- Coverage threshold must be enforced (project-defined target).
- Flaky-test policy is mandatory (quarantine, owner assignment, and fix SLA).
- Example projects must be included in CI smoke tests.

## 17) Documentation Completion Standards

- “Production-ready” claims require complete docs for:
  - installation and quickstart
  - configuration/environment reference
  - migration operations
  - authentication and authorization
  - plugin/provider authoring
  - deployment and rollback
  - troubleshooting and FAQ
- Every major release must include upgrade notes and breaking-change guidance.
