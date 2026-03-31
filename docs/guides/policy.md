# Policy guide (RBAC, ABAC, DSL, storage)

EitohForge combines **role-based** checks (`SecurityPrincipal` + roles) with **attribute-based** policies (`PolicyContext`) and an optional **expression Policy DSL**. Object storage can apply a separate **storage policy** stack per operation.

## Security principal and roles

- `eitohforge_sdk.core.security.SecurityPrincipal` carries `actor_id`, `tenant_id`, and `roles`.
- `require_roles` enforces that at least one required role is present (FastAPI dependency).
- Use RBAC for coarse gates (“must be admin”).

## ABAC (`AccessPolicy`)

- **Context**: `PolicyContext(principal=..., attributes=...)` where `attributes` usually come from path, query, and headers (`attributes_from_request`).
- **Policies**: objects implementing `AccessPolicy` with `name` and `evaluate(context) -> bool`.
- **Engine**: `PolicyEngine.evaluate` / `assert_allowed` returns denied policy names or raises `PolicyDeniedError`.
- **FastAPI**: `require_policies(*policies)` builds a dependency that enforces policies before the handler runs.
- **Functions**: `abac_required` decorator for callables that accept `principal` and `attributes` kwargs.

Built-in examples include `ActorPresentPolicy` and `TenantMatchPolicy`.

## Policy DSL (expressions)

For composable rules without deploying new Python classes for every check, use the **policy expression DSL**:

- Parse: `eitohforge_sdk.core.policy_dsl.parse_expr(source)`
- Evaluate: `eval_expr(expr, policy_context)`
- Or wrap as policy: `ExpressionAccessPolicy.from_source("my_rule", 'principal.actor_id != null')` or `expression_policy("my_rule", "...")`

**Allowed roots** in expressions:

- `principal.*` — fields on `SecurityPrincipal` (for example `actor_id`, `tenant_id`, `roles`).
- `attributes.*` — keys from the ABAC attribute mapping (often including `resource_tenant_id` when using headers).

Supported operators include comparisons, `and` / `or` / `not`, `in` / `not in`, and literals (`null`, `true`, `false`, strings, numbers).

**Named registry**: `PolicyRegistry` can store policies by string name for documentation and composition.

## Storage policies

Object storage uses a different request shape (actions, object keys, caller roles):

- **Types**: `StorageAccessPolicy`, `StorageAccessRequest`, `StorageAction` (read, write, delete, presign, and so on).
- **Engine**: `StoragePolicyEngine` aggregates denials similar to `PolicyEngine`.
- **Wrapper**: `PolicyEnforcedStorageProvider` delegates to an inner `StorageProvider` after `assert_allowed`.

Typical policies include `AuthenticatedActorPolicy`, `TenantPrefixPolicy`, and `RoleStorageAccessPolicy`.

## Choosing an approach

| Need | Use |
|------|-----|
| Simple role gate | `require_roles` / `assert_roles` |
| Request + resource attributes | `AccessPolicy` + `require_policies` |
| Config-driven or many similar rules | Policy DSL + `ExpressionAccessPolicy` |
| Blob access control | `StorageAccessPolicy` on the storage provider |

## Related

- Architecture diagram (policy flow): `docs/architecture/platform-overview.md`.
- Plugins (orthogonal to policy, but often combined): `docs/guides/plugins.md`.
- Framework checklist: `docs/roadmap/framework-evolution-v0.2-to-v1.md`.
