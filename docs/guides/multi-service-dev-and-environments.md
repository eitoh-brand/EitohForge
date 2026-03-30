# Multi-service dev, environments, and the SDK app wrapper

## Environments

`EITOHFORGE_APP_ENV` is one of `local`, `dev`, `staging`, `prod`. The SDK maps this via `resolve_environment_behavior()` to hints such as `expose_detailed_errors`, `recommend_strict_cors`, and `is_production_like`. The same profile is exposed on `/sdk/capabilities` under `deployment`.

Runtime HTTP settings use the `EITOHFORGE_RUNTIME_*` prefix (CORS, public URL, default bind host/port). In `prod`, wildcard CORS (`EITOHFORGE_RUNTIME_CORS_ALLOW_ORIGINS=*`) is rejected at settings validation time.

## `build_forge_app`

`build_forge_app(build=ForgeAppBuildConfig(...))` applies the same middleware ordering as the full generated `register_middleware` helper: hardening, audit, observability, request signing, idempotency, rate limit, tenant, security context, error handlers, then health and capabilities. Feature-flag routes are registered when `EITOHFORGE_FEATURE_FLAGS_ENABLED=true`. Starlette `CORSMiddleware` is attached when `EITOHFORGE_RUNTIME_CORS_ALLOW_ORIGINS` lists one or more origins.

## Multi-port local development

1. Add a `forge.dev.json` at the project root (generated projects include a starter file).
2. List each ASGI app under `services` with `module` in the form `package.module:app`, optional `port`, `host`, `working_directory`, and string `env` overrides.
3. Run:

```bash
eitohforge dev --path .
# or validate only:
eitohforge dev validate --path .
```

Each service is started with `python -m uvicorn …`. Install `uvicorn` in the environment used to run the CLI (generated apps already depend on it).

## Feature catalog

`list_feature_catalog()` and the `sdk_feature_catalog` / `sdk_feature_catalog_meta` fields on `/sdk/capabilities` enumerate SDK surface areas for completeness checks and client tooling.
