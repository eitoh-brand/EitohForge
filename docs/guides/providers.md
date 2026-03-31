# Infrastructure providers guide

In EitohForge, **providers** are **infrastructure adapters**: concrete implementations of SDK contracts (search, object storage, cache, notifications, background jobs, and similar). They are selected through **settings** and built with small **factory** functions.

## Configuration model

- Global settings live in `eitohforge_sdk.core.config.AppSettings` (loaded from `EITOHFORGE_*` environment variables and `.env` files).
- Each subsystem typically has a nested settings class (for example `SearchSettings`, storage settings) with its own env prefix documented on the class.

## Common provider families

| Area | Contract / entry | Typical factory | Env prefix (examples) |
|------|-------------------|-----------------|------------------------|
| Search | `SearchProvider` | `build_search_provider` | `EITOHFORGE_SEARCH_*` |
| Object storage | `StorageProvider` | `build_storage_provider` | Storage-related `EITOHFORGE_*` (see `AppSettings`) |
| Cache | `CacheProvider` | `build_cache_provider` | Cache settings in config |
| Notifications | `NotificationSender` / gateway | `build_*_sender` helpers | Channel-specific |
| Jobs | `BackgroundJobQueue` / `JobPublisher` | App wiring | Optional Celery/Dramatiq extras |

Install **optional extras** when you need a specific backend (for example `pip install eitohforge[aws]` for S3, `eitohforge[gcs]` for GCS, `eitohforge[jobs-celery]` for Celery publishers). See `pyproject.toml` `[project.optional-dependencies]`.

## Search example

Set `EITOHFORGE_SEARCH_PROVIDER` to `memory`, `opensearch`, `elasticsearch`, or `meilisearch`, and provide hosts (and credentials) as required by that provider. The factory returns a single `SearchProvider` instance.

## Storage example

Providers include local disk, S3-compatible endpoints (including MinIO), Azure Blob, and GCS. Policies such as `PolicyEnforcedStorageProvider` wrap a base provider to enforce `StorageAccessPolicy` rules per operation.

## Application-level provider stubs

For **your own** integrations (payment, CRM, custom HTTP APIs), scaffold a typed stub:

```bash
eitohforge create provider <name> --path /path/to/your/project
```

This generates `app/infrastructure/providers/<name>.py` with a `Protocol`, an in-memory implementation, and a `build_<name>_provider` function you can wire from `AppSettings` as you add real credentials.

## Design rules

- Keep **domain and application layers** free of vendor SDK imports; call only your ports or thin facades.
- Prefer **factories** that take `AppSettings` (or a slice) so tests can inject fakes.
- Use **optional dependencies** so minimal installs stay lean.

## Related

- Repository and DTO boundaries: `docs/guides/repository-contracts-and-dto-boundaries.md`.
- Non-SQL `RepositoryContract` adapters: `InMemoryRepository`, `RedisJsonRepository` (stdlib `redis`), `MongoJsonRepository` (optional `eitohforge[mongo]`); multi-DB role wiring: `docs/guides/multi-database-routing.md`.
- Query and persistence: `docs/guides/query-spec-reference.md`.
- Architecture overview: `docs/architecture/platform-overview.md`.
