# Blueprint completion waves (post-baseline)

This roadmap closes the gap between **`secure_backend_sdk_architecture.md`** (§1–§44) and **implementation depth** in `eitohforge_sdk` / CLI / examples. Baseline features from Phases 0–16 are largely present; this document defines **what “done” means** and **in what order** to finish remaining breadth.

**Related:**

- Specification: repository root `secure_backend_sdk_architecture.md` (see **Appendix — EitohForge implementation map**).
- Task IDs: `docs/roadmap/execution-board.md` — **Phase 17** (`P17-*`).
- Traceability: `docs/roadmap/architecture-coverage-matrix.md`.

---

## 1) Definition of done (depth levels)

Each architecture item (or appendix row) should be classified as one of:

| Level | Name | Meaning |
|-------|------|--------|
| **L1** | Contract | Protocols / settings / public API documented; one reference implementation; unit tests for the contract surface. |
| **L2** | Product | Wired for real services: env flags or `AppSettings`, CLI or `build_forge_app` where applicable; example or generated path demonstrates usage. |
| **L3** | Enterprise | Multi-instance, HA, or security posture appropriate for production (e.g. Redis-backed realtime hub, Vault secret backend, exportable OTEL metrics) with runbook notes. |

**Rule:** Do not mark an item “complete” against the blueprint at **L1** if the spec promises **multi-node or operator-grade** behavior; target **L2** first, then **L3** where the blueprint explicitly requires it.

After each wave ships, update:

1. The appendix table in `secure_backend_sdk_architecture.md` (status + notes).
2. Optionally add a **Depth** column (`L1` / `L2` / `L3`) to `architecture-coverage-matrix.md` for rows that moved.

---

## 2) Wave A — Data plane and query (foundation)

**Goal:** Match **§4 Polyglot database layer** and **§6 Query specification engine** more closely to the blueprint.

| Target | Blueprint § | Outcomes |
|--------|-------------|----------|
| Extra SQL providers | §4 | **SQLite** + **MySQL** in factory (`P17-02`, `P17-03`); `pymysql` dependency; templates aligned. Next extra engines only as needed (e.g. SQL Server), with DSN + migration docs each time. |
| Query parity | §6 | **Done:** `docs/guides/query-spec-reference.md`, `validate_query_filters_against_columns`, empty-`in` / empty-`not_in` semantics, blueprint operator matrix tests in `test_sqlalchemy_repository.py`. |
| Multi-DB | §28 | Validate **primary / analytics / search** registry with new drivers where applicable. |

**Execution tasks:** `P17-01`–`P17-04` (see execution board).

**Exit criteria:** CI runs at least one job using SQLite (or documented matrix entry); query tests cover the supported operator set declared in docs.

---

## 3) Wave B — CRUD generator and versioned HTTP API

**Goal:** **§7 CRUD auto generator** and **§42 Versioned API engine** reach **L2** with examples.

| Target | Blueprint § | Outcomes |
|--------|-------------|----------|
| CRUD breadth | §7 | **Done (P17-05):** optional `description`, `quantity`, `is_active`, `due_at`, **`parent_resource_id`** stub; golden snapshots updated; generated test exercises fields. |
| Versioned API | §42 | **Done (P17-06):** `EITOHFORGE_API_VERSION_*`, middleware on **`build_forge_app`**, cookbook for mounted OpenAPI + deprecation headers. |

**Execution tasks:** `P17-05`, `P17-06` (complete).

**Exit criteria:** Met via goldens + unit tests + cookbook; optional dedicated example mount left to products.

---

## 4) Wave C — Event bus productization

**Goal:** **§27 Event bus architecture** beyond in-process dispatcher.

| Target | Blueprint § | Outcomes |
|--------|-------------|----------|
| Bus abstraction | §27 | **Existing:** `EventBus` protocol + `InMemoryEventBus`. |
| Optional broker | §27 | **Done (P17-07):** **`RedisPublishingEventBus`** + factory; JSON **`PUBLISH`**; unit test with mock Redis; cookbook notes for **SUBSCRIBE** workers. |

**Execution tasks:** `P17-07` (complete).

**Exit criteria:** Cross-process delivery documented; runtime subscriber not embedded in web process by design.

---

## 5) Wave D — Realtime (scale and semantics)

**Goal:** **§41 Socket infrastructure** toward **L2/L3** where the blueprint implies scale and richer messaging.

| Target | Blueprint § | Outcomes |
|--------|-------------|----------|
| Multi-worker hub | §41 | **Done (P17-08):** Redis **broadcast** fan-out (`EITOHFORGE_REALTIME_REDIS_URL`); join/presence remain **per worker** (documented). |
| Private / directed messaging | §41 | **Done (P17-09):** `type: "direct"` + `send_direct_to_actor` (Redis fan-out when enabled); **`realtime-websocket.md`** documents non-goals, room naming, and app-owned auth. |

**Execution tasks:** `P17-08`, `P17-09` (complete).

**Exit criteria:** Load or soak note (even manual) for N connections; security note for anonymous vs JWT-required modes.

---

## 6) Wave E — Operations and observability

**Goal:** **§39 Secret management** and **§37 Metrics & observability** at **L2+**.

| Target | Blueprint § | Outcomes |
|--------|-------------|----------|
| Secret backends | §39 | **Done (P17-10):** `VaultSecretProvider` implements the existing `SecretProvider` contract; each `get()` fetches from Vault (no local cache) so rotation is picked up by re-fetching. Unit tests validate KV v2 JSON parsing via mocked `urllib`. |
| Telemetry export | §37 | **Done (P17-11):** Prometheus `/metrics` via `PrometheusMetricsSink` (per-app registry) when `EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS=true`, plus OTEL trace spans and `x-trace-id` headers when `EITOHFORGE_OBSERVABILITY_OTEL_ENABLED=true`. |

**Execution tasks:** `P17-11` (complete).

**Exit criteria:** Example env block in `forge-profiles` or usage doc; no secrets in logs (audit in review).

---

## 7) Wave F — Governance and matrix hygiene

**Goal:** Keep planning artifacts honest as waves land.

| Actions | Outcomes |
|---------|----------|
| Appendix refresh | Update **implementation map** rows from Partial → Implemented with caveats. |
| Coverage matrix | Add **Depth (L1/L2/L3)** where useful; keep **Task IDs** in sync with `P17-*`. |
| Standards | If new env vars or toggles appear, update `docs/standards/engineering-standards.md` and `.env.example` templates. |

**Execution task:** `P17-12` (done).

---

## 8) Sequencing and parallelism

Recommended **critical path:**

`P17-01` → `P17-02` → `P17-04` → `P17-05` → `P17-07` → `P17-08` → `P17-10`

Parallel when staffing allows:

- `P17-03` after `P17-02` pattern exists.
- `P17-06` alongside `P17-05` (different files).
- `P17-09` after `P17-08` if Redis hub changes connection semantics.
- `P17-11` alongside `P17-10`.
- `P17-12` at the end of **each** merged wave (not only the last).

---

## 9) Non-goals (explicit)

- Replacing the blueprint with a smaller scope document — the spec stays the north star; this roadmap **narrows execution**, not vision.
- Implementing every database listed in §4 in one release — add providers **incrementally** with L1→L2 promotion.
- Promising automatic backward compatibility for all future API changes — §42 is **tooling + discipline**, not magic.

---

## 10) Weekly reporting

Extend the template in `execution-board.md`:

- Completed **wave** (A–F) and **task IDs** (`P17-*`).
- **L-level** promoted this week (per § or row).
- Appendix / matrix updated: yes/no.

---

## 11) Appendix row update template (P17-01)

Use this when closing a **Phase 17** task so the specification appendix stays honest.

1. Open **`secure_backend_sdk_architecture.md`** → **Appendix — EitohForge implementation map**.
2. Edit the row for the affected **§** number: adjust **Status** (`Implemented` / `Partial` / `Planned / gap`) and **Notes** (what shipped, what remains, optional **L1/L2/L3**).
3. Optionally add a **Depth** column to **`architecture-coverage-matrix.md`** for that row.
4. If new env vars or user-facing behavior changed, update **`docs/guides/usage-complete.md`** (and `.env.example` templates if applicable).

**Copy-paste row skeleton** (replace placeholders):

```markdown
| N | Short title from blueprint | Partial | **Before:** … **After:** … (P17-xx). |
```
