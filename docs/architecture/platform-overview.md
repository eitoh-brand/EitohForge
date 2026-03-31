# EitohForge platform architecture (diagrams)

This page complements the narrative blueprint in `secure_backend_sdk_architecture.md` with **diagrams** you can render in GitHub, VS Code (Markdown preview), or any Mermaid-capable viewer.

---

## Layered composition

The SDK follows a **ports-and-adapters** style: domain and application contracts stay free of IO; infrastructure implements adapters; `build_forge_app` and app wiring connect them.

```mermaid
flowchart TB
    subgraph presentation["Presentation (FastAPI)"]
        R[Routers / WebSocket]
        MW[Middleware chain]
    end
    subgraph application["Application"]
        DTO[DTOs / QuerySpec / Envelopes]
        SVC[Application services]
    end
    subgraph domain["Domain"]
        ENT[Entities / value objects]
        REPO[Repository contracts]
    end
    subgraph infrastructure["Infrastructure"]
        SQL[(SQLAlchemy)]
        CACHE[(Cache)]
        SEARCH[(Search)]
        STORE[(Object storage)]
        BUS[(Event bus / jobs)]
    end
    R --> MW
    MW --> SVC
    SVC --> REPO
    REPO --> SQL
    SVC --> CACHE
    SVC --> SEARCH
    SVC --> STORE
    SVC --> BUS
```

---

## Typical HTTP request path

Cross-cutting behavior runs **before** route handlers: security context, tenant, optional signing, rate limits, observability, and audit (depending on toggles and settings).

```mermaid
sequenceDiagram
    participant C as Client
    participant U as Uvicorn / ASGI
    participant M as Middleware stack
    participant H as Route handler
    C->>U: HTTP request
    U->>M: dispatch
    M->>M: security / tenant / limits / trace
    M->>H: invoke
    H-->>M: response
    M-->>U: response
    U-->>C: HTTP response
```

---

## Plugin registration

Plugins are optional modules that self-register routes, provider entries, or event subscriptions through a **single registry** applied at app startup.

```mermaid
flowchart LR
    P1[Plugin A]
    P2[Plugin B]
    REG[PluginRegistry]
    APP[FastAPI app]
    PR[provider dict]
    EV[event registry]
    P1 --> REG
    P2 --> REG
    REG -->|register_routes| APP
    REG -->|register_providers| PR
    REG -->|register_events| EV
```

Implementation reference: `eitohforge_sdk.core.plugins.PluginRegistry` and `eitohforge_sdk.core.plugin_contracts` (typed `RoutePlugin`, `ProviderPlugin`, `EventsPlugin`).

---

## Realtime and Redis fan-out (multi-worker)

When `EITOHFORGE_REALTIME_REDIS_URL` is set, **broadcast** and **direct-to-actor** messages are published to Redis so all workers can deliver. Room membership and presence snapshots remain **process-local** unless you add an external store.

```mermaid
flowchart LR
    W1[Worker 1\nInMemorySocketHub]
    W2[Worker 2\nInMemorySocketHub]
    R[(Redis PUBLISH)]
    W1 -->|fan-out| R
    R --> W2
```

Details: `docs/guides/realtime-websocket.md`.

---

## Policy evaluation (ABAC + DSL)

Authorization can combine **structured policies** (`AccessPolicy`) and **expression** policies (`ExpressionAccessPolicy`) evaluated against `PolicyContext` (principal + request attributes).

```mermaid
flowchart TD
    REQ[Request]
    PC[PolicyContext]
    PE[PolicyEngine]
    AP[AccessPolicy tuple]
    REQ --> PC
    PC --> PE
    AP --> PE
    PE -->|allow / deny| OUT[Handler or 403]
```

Expression DSL reference: `docs/guides/policy.md`.

---

## Where to go next

| Topic | Document |
|--------|----------|
| Plugins (registry, CLI) | `docs/guides/plugins.md` |
| Infrastructure providers | `docs/guides/providers.md` |
| ABAC, Policy DSL, storage policies | `docs/guides/policy.md` |
| Framework checklist | `docs/roadmap/framework-evolution-v0.2-to-v1.md` |
