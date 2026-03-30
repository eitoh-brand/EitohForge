# EitohForge Cookbook

Practical recipes for common implementation patterns.

## 1) Enable Strict Tenant Isolation

Set:

- `EITOHFORGE_TENANT_ENABLED=true`
- `EITOHFORGE_TENANT_REQUIRED_FOR_WRITE_METHODS=true`
- `EITOHFORGE_TENANT_RESOURCE_TENANT_HEADER=x-resource-tenant-id`

Behavior:

- write methods without tenant context are denied (`403`)
- cross-tenant access via mismatched resource tenant header is denied (`403`)

## 2) Add a Plugin Module

Implement a plugin object with a unique `name`, optionally:

- `register_routes(app)`
- `register_providers(registry)`
- `register_events(registry)`

Register it with `PluginRegistry.register(plugin)` and apply with `PluginRegistry.apply(...)`.

## 3) Roll Out a Feature Gradually

Use `FeatureFlagService` and register:

- `FeatureFlagDefinition(key="new-ui", rollout_percentage=10)`

Then evaluate with actor/tenant context:

- `FeatureFlagTargetingContext(actor_id="actor-1", tenant_id="tenant-a")`

Expose runtime values via `register_feature_flags_endpoint(app)`.

## 4) Harden HTTP Surface

Use `register_security_hardening_middleware` with `SecurityHardeningRule` to:

- enforce max request size
- restrict allowed hosts
- set strict response security headers

## 5) Baseline and Check Performance

Generate baseline:

- `uv run python scripts/performance_baseline.py --mode baseline`

Run regression check:

- `uv run python scripts/performance_baseline.py --mode check --threshold 25`
