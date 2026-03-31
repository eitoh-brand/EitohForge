from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from eitohforge_sdk.infrastructure.sockets import (
    PRESENCE_EVENT_JOIN,
    PRESENCE_EVENT_LEAVE,
    PRESENCE_EVENT_UPDATE,
    InMemorySocketHub,
    PresenceManager,
    PresenceStatus,
    SocketPrincipal,
)


class FakeSocketConnection:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, payload: Mapping[str, Any]) -> None:
        self.messages.append(dict(payload))


def test_presence_manager_join_leave_and_snapshot() -> None:
    hub = InMemorySocketHub()
    a = FakeSocketConnection()
    b = FakeSocketConnection()
    ca = hub.register(a, SocketPrincipal(actor_id="alice", tenant_id="t1"))
    cb = hub.register(b, SocketPrincipal(actor_id="bob", tenant_id="t1"))
    presence = PresenceManager(hub)

    async def _run() -> None:
        assert await presence.join("room-1", ca, status=PresenceStatus.ONLINE, broadcast_event=False) is True
        assert await presence.join("room-1", cb, metadata={"client": "web"}, broadcast_event=False) is True

    asyncio.run(_run())

    snap = presence.snapshot("room-1")
    assert snap.room == "room-1"
    assert len(snap.actors) == 2
    by_id = {x.actor_id: x for x in snap.actors}
    assert by_id["alice"].status == PresenceStatus.ONLINE
    assert by_id["alice"].connection_count == 1
    assert by_id["bob"].metadata.get("client") == "web"

    async def _leave() -> None:
        assert await presence.leave("room-1", ca, broadcast_event=False) is True

    asyncio.run(_leave())
    assert len(presence.snapshot("room-1").actors) == 1


def test_presence_manager_broadcasts_join_leave_update() -> None:
    hub = InMemorySocketHub()
    a = FakeSocketConnection()
    b = FakeSocketConnection()
    ca = hub.register(a, SocketPrincipal(actor_id="alice"))
    cb = hub.register(b, SocketPrincipal(actor_id="bob"))
    presence = PresenceManager(hub)

    async def _setup() -> None:
        await presence.join("r", ca, broadcast_event=False)
        await presence.join("r", cb)

    asyncio.run(_setup())

    join_msgs = [m for m in a.messages if m.get("event") == PRESENCE_EVENT_JOIN]
    assert len(join_msgs) == 1
    assert join_msgs[0]["payload"]["actor_id"] == "bob"

    async def _upd() -> None:
        await presence.update_status(ca, PresenceStatus.BUSY, metadata={"focus": "editing"})

    asyncio.run(_upd())
    upd = [m for m in b.messages if m.get("event") == PRESENCE_EVENT_UPDATE]
    assert len(upd) == 1
    assert upd[0]["payload"]["status"] == "busy"

    async def _leave() -> None:
        await presence.leave("r", cb)

    asyncio.run(_leave())
    leave_msgs = [m for m in a.messages if m.get("event") == PRESENCE_EVENT_LEAVE]
    assert len(leave_msgs) == 1


def test_hub_connection_rooms_and_principal() -> None:
    hub = InMemorySocketHub()
    s = FakeSocketConnection()
    cid = hub.register(s, SocketPrincipal(actor_id="z", tenant_id="tz"))
    assert hub.connection_rooms(cid) == ()
    assert hub.join_room("x", cid) is True
    assert hub.connection_rooms(cid) == ("x",)
    p = hub.principal_for_connection(cid)
    assert p is not None
    assert p.actor_id == "z"
    assert hub.principal_for_connection("nope") is None


def test_presence_disconnect_clears_local_state() -> None:
    hub = InMemorySocketHub()
    s = FakeSocketConnection()
    cid = hub.register(s, SocketPrincipal(actor_id="a"))
    pm = PresenceManager(hub)

    async def _go() -> None:
        await pm.join("r", cid, broadcast_event=False)

    asyncio.run(_go())
    assert pm.disconnect(cid) is True
    assert hub.principal_for_connection(cid) is None


def test_join_fails_when_connection_unknown() -> None:
    hub = InMemorySocketHub()
    pm = PresenceManager(hub)

    async def _run() -> None:
        assert await pm.join("r", "missing", broadcast_event=False) is False

    asyncio.run(_run())


def test_leave_fails_when_not_in_room() -> None:
    hub = InMemorySocketHub()
    s = FakeSocketConnection()
    cid = hub.register(s, SocketPrincipal(actor_id="a"))
    pm = PresenceManager(hub)

    async def _run() -> None:
        assert await pm.leave("noroom", cid, broadcast_event=False) is False

    asyncio.run(_run())


def test_update_status_no_op_when_unknown_connection() -> None:
    hub = InMemorySocketHub()
    pm = PresenceManager(hub)

    async def _run() -> None:
        await pm.update_status("nope", PresenceStatus.AWAY)

    asyncio.run(_run())


def test_snapshot_merges_busy_across_connections_for_same_actor() -> None:
    hub = InMemorySocketHub()
    a = FakeSocketConnection()
    b = FakeSocketConnection()
    ca = hub.register(a, SocketPrincipal(actor_id="alice", tenant_id="t"))
    cb = hub.register(b, SocketPrincipal(actor_id="alice", tenant_id="t"))
    pm = PresenceManager(hub)

    async def _run() -> None:
        await pm.join("r", ca, status=PresenceStatus.ONLINE, broadcast_event=False)
        await pm.join("r", cb, status=PresenceStatus.BUSY, metadata={"tab": "2"}, broadcast_event=False)

    asyncio.run(_run())
    snap = pm.snapshot("r")
    assert len(snap.actors) == 1
    assert snap.actors[0].status == PresenceStatus.BUSY
    assert snap.actors[0].connection_count == 2
    assert snap.actors[0].metadata["tab"] == "2"


def test_join_with_empty_metadata_mapping_clears_stored_metadata() -> None:
    hub = InMemorySocketHub()
    b = FakeSocketConnection()
    cb = hub.register(b, SocketPrincipal(actor_id="bob"))
    pm = PresenceManager(hub)

    async def _run() -> None:
        await pm.join("r", cb, metadata={"x": 1}, broadcast_event=False)
        await pm.join("r", cb, metadata={}, broadcast_event=False)

    asyncio.run(_run())
    assert pm.snapshot("r").actors[0].metadata == {}


def test_clear_local_state_after_hub_disconnect() -> None:
    hub = InMemorySocketHub()
    s = FakeSocketConnection()
    cid = hub.register(s, SocketPrincipal(actor_id="a"))
    pm = PresenceManager(hub)

    async def _run() -> None:
        await pm.join("r", cid, metadata={"k": 1}, broadcast_event=False)

    asyncio.run(_run())
    hub.disconnect(cid)
    pm.clear_local_state(cid)
