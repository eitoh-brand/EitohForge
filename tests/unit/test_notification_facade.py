from __future__ import annotations

import asyncio

from eitohforge_sdk.infrastructure.notifications import (
    InMemoryNotificationGateway,
    NotificationClient,
    success_result_for,
)


def test_notification_client_routes_email_sms_whatsapp_push() -> None:
    gateway = InMemoryNotificationGateway()
    gateway.register_sender("email", lambda m: success_result_for(m))
    gateway.register_sender("sms", lambda m: success_result_for(m))
    gateway.register_sender("whatsapp", lambda m: success_result_for(m))
    gateway.register_sender("push", lambda m: success_result_for(m))

    async def _run() -> None:
        client = NotificationClient(gateway)
        e = await client.send_email("a@b.com", "hi", subject="S")
        s = await client.send_sms("+15551234567", "txt")
        w = await client.send_whatsapp("+15551234567", "wa")
        p = await client.send_push("device-token", "push body", subject="t")
        assert e.status == "sent"
        assert s.status == "sent"
        assert w.status == "sent"
        assert p.status == "sent"

    asyncio.run(_run())
    assert len(gateway.sent_messages) == 4
