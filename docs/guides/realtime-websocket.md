# Realtime WebSocket (`/realtime/ws`)

Generated apps register a **first-class** WebSocket endpoint when `EITOHFORGE_REALTIME_ENABLED=true` (default).

## Handshake

- **`EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT`** (default `true`): when `false`, connections are accepted without a token (anonymous `actor_id`); optional JWT still upgrades the principal when `EITOHFORGE_AUTH_JWT_ENABLED=true`.
- When `require_access_jwt` is `true`, a **JWT access token** is required before messages are accepted (and **`EITOHFORGE_AUTH_JWT_ENABLED`** must be `true`).
- Pass the token as query `?token=<access_jwt>` and/or `Authorization: Bearer <access_jwt>` (query wins if both are set — see `extract_socket_token`).

## Hub

When **`EITOHFORGE_REALTIME_REDIS_URL`** is unset, the hub is **`InMemorySocketHub`** on `app.state.socket_hub` (single process). When set, **`build_forge_app`** uses **`RedisFanoutSocketHub`**: **broadcast** and **direct** traffic fan out across workers via Redis; **presence** / **room membership** stay per process (see cookbook).

## Private channels vs direct messages

| Mechanism | What the SDK does | What your app must do |
|-----------|-------------------|------------------------|
| **Room “privacy”** | None — any client can `join` any room name string. | Encode tenancy or secrecy in **room naming** (e.g. `tenant:{id}:orders`) and enforce policy in HTTP APIs or custom middleware before exposing room names. |
| **`type: "direct"`** | Delivers to all WebSocket connections whose **`actor_id`** matches **`target_actor_id`** (JWT subject by default). Works across workers when Redis is enabled. **Does not** encrypt payloads or prove the recipient’s tenant; **authorization** (who may message whom) is **application-owned**. | Enforce ABAC/RBAC in services or reject sensitive `target_actor_id` values server-side if you add hooks later. |

**Not supported by the SDK:** end-to-end encryption, read receipts, or guaranteed offline delivery. Use app-level queues or push for those.

## Client JSON protocol (text frames)

| `type` | Fields | Server response |
|--------|--------|-----------------|
| `ping` | — | `{ "type": "pong" }` |
| `join` | `room` (string) | `{ "type": "joined", "room", "ok" }` |
| `leave` | `room` | `{ "type": "left", "room", "ok" }` |
| `broadcast` | `room`, `event`, optional `payload` object | Others in room get `{ event, room, payload, occurred_at }`; caller gets `{ "type": "broadcast_result", "delivered" }` (sender excluded from broadcast) |
| `presence` | `room` | `{ "type": "presence_result", "connection_ids", "by_actor" }` |
| `direct` | `target_actor_id`, `event`, optional `payload` | Recipients: `{ event, room: "__direct__", payload, occurred_at, from_actor_id, target_actor_id }`. Sender: `{ "type": "direct_result", "target_actor_id", "delivered" }`. Requires non-anonymous `actor_id`. |

Malformed JSON or unknown `type` returns `{ "type": "error", "code", "message" }`.

## Capabilities

`GET /sdk/capabilities` includes `features.realtime_websocket` and a `realtime` object with `websocket_path`, `hub_kind` (`in_memory` or `redis_fanout`), and `direct_to_actor_supported`.
