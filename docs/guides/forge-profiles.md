# Forge scaffold profiles and feature toggles

## CLI profiles (`create project`)

```bash
eitohforge create project my_api --profile standard   # default
eitohforge create project my_api --profile minimal      # most platform features off in `.env.example`
```

- **standard** — typical enterprise defaults (tenant, rate limit, observability, audit, realtime WebSocket, feature flags, etc. enabled in the generated `.env.example`).
- **minimal** — the same codebase layout, but `.env.example` starts with most optional middleware **disabled**. Turn features on by setting the matching `EITOHFORGE_*_ENABLED` (or related) variables to `true` and redeploying.

Runtime behavior always follows **loaded settings** (`AppSettings`), not the profile name, after you copy `.env.example` → `.env`.

## `build_forge_app` toggles (SDK)

For SDK-only apps, use **`ForgeAppBuildConfig.toggles`** (`ForgePlatformToggles`) to override each layer without changing environment:

- Each field is `True` | `False` | `None`.
- **`None`** means “use `AppSettings`” (e.g. `rate_limit.enabled`).
- **`False`** forces that layer off even if env says on; **`True`** forces it on.

```python
from eitohforge_sdk.core import ForgeAppBuildConfig, ForgePlatformToggles, build_forge_app

app = build_forge_app(
    build=ForgeAppBuildConfig(
        toggles=ForgePlatformToggles(
            rate_limit=False,
            realtime_websocket=False,
            https_redirect=False,
        ),
    )
)
```

Other toggle keys match platform concerns: `security_hardening`, `audit`, `observability`, `request_signing`, `idempotency`, `tenant`, `security_context`, `cors`, `health`, `capabilities`, `feature_flags`, `realtime_websocket`, `https_redirect`.

`wire_realtime_websocket=False` on **`ForgeAppBuildConfig`** skips mounting `/realtime/ws` entirely (in addition to toggles).

### Uniform toggle (all layers on or off)

To force **every** `ForgePlatformToggles` field to the same value (overriding `AppSettings` for each wired layer), use:

```python
from eitohforge_sdk.core import ForgeAppBuildConfig, build_forge_app, forge_platform_toggles_uniform

app = build_forge_app(
    build=ForgeAppBuildConfig(
        toggles=forge_platform_toggles_uniform(enabled=False),
        wire_realtime_websocket=False,
    )
)
```

Use **`enabled=True`** only when you intentionally want all toggled layers on regardless of env. **`wire_*`** flags on `ForgeAppBuildConfig` are separate: set them explicitly if you need to skip router families entirely.

## Environment flags (auth, HTTPS, WebSocket)

| Concern | Variables |
|--------|-----------|
| JWT issuance/validation for HTTP and WS | `EITOHFORGE_AUTH_JWT_ENABLED` (default `true`) |
| WebSocket endpoint | `EITOHFORGE_REALTIME_ENABLED` |
| Require access JWT on `/realtime/ws` | `EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT` (if `true` and realtime on, `AUTH_JWT_ENABLED` must be `true`) |
| Redirect HTTP→HTTPS (app-level; TLS usually terminates at proxy) | `EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT` |
| CORS | `EITOHFORGE_RUNTIME_CORS_ALLOW_ORIGINS`, etc. |

`GET /sdk/capabilities` exposes `auth`, `runtime`, and `realtime` blocks for clients.
