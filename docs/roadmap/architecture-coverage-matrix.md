# Architecture Coverage Matrix (A-Z)

This matrix traces the 44 architecture items from `secure_backend_sdk_architecture.md` to execution tasks.

## Status Key

- `covered`: explicitly represented in execution board tasks
- `partial`: represented as scaffold or baseline adapter in first release

## Coverage Table

| # | Architecture Item | Coverage | Depth | Task IDs |
|---|---|---|---|---|
| 1 | Core architecture philosophy | covered |  | P1-03 |
| 2 | Auto-generated folder structure | covered |  | P1-02,P1-03 |
| 3 | Central configuration engine | covered |  | P2-01,P2-02,P2-03 |
| 4 | Polyglot database layer | partial |  | P3-01,P3-05 |
| 5 | Generic repository abstraction | covered |  | P4-01,P4-02 |
| 6 | Query specification engine | covered |  | P4-03 |
| 7 | CRUD auto generator | covered | L2 | P8-01,P8-02,P8-03,P17-05 |
| 8 | Request/response model system | covered |  | P5-02,P6-01,P6-02 |
| 9 | Pagination engine | covered |  | P4-04,P4-05,P6-01 |
| 10 | Authentication system | covered |  | P7-01 |
| 11 | Session management engine | covered |  | P7-02 |
| 12 | RBAC | covered |  | P7-03 |
| 13 | ABAC | covered |  | P7-04 |
| 14 | Identity federation and SSO | covered |  | P13-01,P13-02 |
| 15 | Session + JWT unified identity | covered |  | P7-01,P7-02,P7-05 |
| 16 | Storage abstraction layer | covered |  | P9-01,P9-02 |
| 17 | Presigned URL engine | covered |  | P9-02 |
| 18 | Storage access policies | covered |  | P9-03 |
| 19 | CDN integration layer | covered |  | P9-04 |
| 20 | Distributed cache layer | covered |  | P10-01,P10-02 |
| 21 | Rate limiting engine | covered |  | P10-03 |
| 22 | Notification gateway layer | covered |  | P11-04 |
| 23 | Template messaging engine | covered |  | P11-05 |
| 24 | Background job engine | covered |  | P11-02 |
| 25 | External API client framework | covered |  | P11-06 |
| 26 | Webhook framework | covered |  | P11-03 |
| 27 | Event bus architecture | covered | L2 | P11-01,P17-07 |
| 28 | Multi-database support | covered |  | P3-05 |
| 29 | Distributed transaction support | covered |  | P4-06 |
| 30 | Search engine integration | covered |  | P12-04 |
| 31 | Audit logging engine | covered |  | P12-03 |
| 32 | Security middleware stack | covered |  | P10-05,P10-03 |
| 33 | Request signing engine | covered |  | P10-05 |
| 34 | Capability negotiation endpoint | covered |  | P10-06 |
| 35 | Multi-tenant architecture | covered | L2 | P13-03,P18-01,P18-02,P18-03,P18-04,P18-05,P18-06 |
| 36 | Plugin system | covered |  | P13-04 |
| 37 | Metrics and observability | covered | L2 | P12-01,P17-11 |
| 38 | Health monitoring endpoints | covered | L2 | P12-02,P17-11 |
| 39 | Secret management layer | covered | L2 | P2-04,P17-10 |
| 40 | Unified security context | covered |  | P7-05 |
| 41 | Socket infrastructure | covered | L2 | P12-05,P17-08,P17-09 |
| 42 | Versioned API engine | covered | L2 | P6-03,P17-06 |
| 43 | Idempotency engine | covered |  | P10-04 |
| 44 | Feature flag system | covered |  | P13-05 |

## Notes

- Polyglot providers are staged: first release ships baseline adapters, then expands.
- Coverage means planned and tracked; implementation state is controlled by task state.
- Packaging/publishing and enterprise operations are tracked separately in execution tasks `P0-04` and `P15-*`.
- **Depth completion** (L1/L2/L3 vs the blueprint): see `blueprint-completion-waves.md` and execution board **Phase 17** (`P17-*`). Optionally add a **Depth** column to this table as waves land.
- **SQLite** (`P17-02`) and **MySQL** (`P17-03`): SDK providers + scaffold; row **#4** stays **partial** until non-SQL stores (e.g. Mongo) if ever in scope.
- **Query spec** (`P17-04`): see `docs/guides/query-spec-reference.md` for §6 SQL path parity.
