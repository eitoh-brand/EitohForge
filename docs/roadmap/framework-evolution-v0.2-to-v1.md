# EitohForge platform framework evolution (v0.2 → v1.0)

This checklist tracks the **framework evolution roadmap** (database-agnostic repositories, provider expansion, adoption). It complements the time-based [master-implementation-roadmap.md](./master-implementation-roadmap.md).

**Legend:** `[x]` done · `[~]` partial · `[ ]` not started

---

## Phase 1 — Pre v0.2 (stabilization)

| Item | Status | Notes |
|------|--------|--------|
| Generic repository: `BaseRepository`, `QuerySpec`, `Filter` / `Sort` / `Page`, `Specification`, `coalesce_query_spec` | [x] | SDK + SQLAlchemy; **CLI templates** (`domain_repository_templates`, `contracts`, `sqlalchemy_repository`) aligned |
| SQL adapter | [x] | `SQLAlchemyRepository` / `SQLRepository` |
| Mongo / Elastic / Redis repository adapters | [x] | `InMemoryRepository`; **`RedisJsonRepository`** (stdlib `redis`); **`MongoJsonRepository`** (optional `pymongo` / `eitohforge[mongo]`). Elasticsearch document CRUD is not a generic repo adapter — use **`SearchProvider`** (OpenSearch / Meilisearch) for search indices. |
| Storage: presigned upload/download + public URL | [x] | S3 + MinIO (same adapter) + **Azure Blob** + **GCS** + presign/public URL patterns; optional extras `azure-storage`, `gcs` |
| Notification providers (SES, SendGrid, SMTP, Twilio, SNS, WhatsApp, push) | [x] | + `build_firebase_push_sender` (optional extra `firebase`) |
| Feature flag rollout engine (%, cohort, tenant, environment) | [x] | `FeatureFlagService` + actor/tenant allowlists + **environment** + **cohort** gates + rollout bucket + `enabled()` / `evaluate_for_user()` / `targeting_context_from_user`; headers `x-environment`, `x-cohort-id` |
| Quickstart / README | [x] | Gist + Hello World in root README; optional extras documented in `pyproject` |

---

## Phase 2 — Toward v0.5 (platform core)

| Item | Status |
|------|--------|
| Policy DSL (expression AST) | [x] | `policy_dsl`: parse → AST → `eval_expr`; `ExpressionAccessPolicy` / `expression_policy`; roots `principal.*`, `attributes.*` |
| Multi-database routing registry | [x] | `DatabaseRegistry` + **`RepositoryBindingMap`** + `build_database_registry`; see `docs/guides/multi-database-routing.md` |
| Secret provider expansion (Vault, AWS, Azure, GCP) | [x] | `VaultSecretProvider`, `AwsSecretsManagerSecretProvider`, `AzureKeyVaultSecretProvider`, **`GcpSecretManagerSecretProvider`** (`EITOHFORGE_SECRET_PROVIDER=gcp`, `EITOHFORGE_SECRET_GCP_PROJECT_ID`); optional extra `eitohforge[gcp-secrets]` |
| Realtime presence (`PresenceManager`, rooms) | [x] | `PresenceManager` + `PresenceStatus` / snapshots; hub gains `connection_rooms` / `principal_for_connection`; events `presence:join|leave|update` |

---

## Phase 3 — Toward v1.0 (ecosystem)

| Item | Status |
|------|--------|
| CLI generators (`create module`, `provider`, `plugin`, …) | [x] | `eitohforge create module|provider|plugin` + `generator_templates` (Jinja) |
| Plugin hook types (`RoutePlugin`, …) | [x] | `core/plugin_contracts`: `RoutePlugin`, `ProviderPlugin`, `EventsPlugin` |
| Background job providers (Celery, Dramatiq, …) | [x] | `JobPublisher` + `CeleryJobPublisher` / `DramatiqJobPublisher` (extras `jobs-celery`, `jobs-dramatiq`) |
| Search providers (Elastic, Meili, …) | [x] | OpenSearch/ES + **Meilisearch** (`provider=meilisearch`, `api_key`, stdlib HTTP) |

---

## Phase 4 — Adoption

| Item | Status |
|------|--------|
| Architecture diagrams in docs | [x] | `docs/architecture/platform-overview.md` (Mermaid: layers, request path, plugins, realtime, policy) |
| PLUGIN / PROVIDER / POLICY guides | [x] | `docs/guides/plugins.md`, `providers.md`, `policy.md` |

---

## Phase 5 — Enterprise (optional)

| Item | Status |
|------|--------|
| Saga manager | [x] | `SagaOrchestrator` + `SagaManager` + `on_compensation_failure` callback; `InMemorySagaStateStore` |
| Domain event bus | [x] | `InMemoryEventBus` / Redis bridge + `DomainEvent` / `DomainEventPublisher` |
| API contract enforcement middleware | [x] | `register_api_contract_middleware`; `EITOHFORGE_API_CONTRACT_ENFORCE_JSON_ENVELOPE`; validates `success` + `error` shape |

---

## Release mapping (suggested)

| Version | Target contents |
|---------|-----------------|
| **v0.2** | Repository ergonomics + CLI parity, presign/public URL baseline, notification facade + core providers, feature targeting (env/cohort) |
| **v0.3** | Policy DSL, multi-DB routing, search/job/plugin expansions |
| **v0.5** | CLI generators, presence, event bus, API response envelope middleware |
| **v1.0** | Saga hardening, full ecosystem docs, marketplace readiness |

_Last updated: framework checklist maintained alongside code changes._
