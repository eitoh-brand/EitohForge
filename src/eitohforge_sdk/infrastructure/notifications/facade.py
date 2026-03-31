"""Typed convenience API over ``NotificationGateway`` (email/sms/whatsapp/push)."""

from __future__ import annotations

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
)


class NotificationClient:
    """Thin facade with channel-specific send methods."""

    def __init__(self, gateway: NotificationGateway) -> None:
        self._gateway = gateway

    async def send_email(
        self,
        to: str,
        body: str,
        *,
        subject: str | None = None,
        template_id: str | None = None,
        template_vars: dict[str, object] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> NotificationResult:
        return await self._gateway.send(
            NotificationMessage(
                channel="email",
                recipient=to,
                subject=subject,
                body=body,
                template_id=template_id,
                template_vars=template_vars or {},
                metadata=metadata or {},
            )
        )

    async def send_sms(self, to: str, body: str, *, metadata: dict[str, str] | None = None) -> NotificationResult:
        return await self._gateway.send(
            NotificationMessage(
                channel="sms",
                recipient=to,
                body=body,
                metadata=metadata or {},
            )
        )

    async def send_whatsapp(
        self, to: str, body: str, *, metadata: dict[str, str] | None = None
    ) -> NotificationResult:
        return await self._gateway.send(
            NotificationMessage(
                channel="whatsapp",
                recipient=to,
                body=body,
                metadata=metadata or {},
            )
        )

    async def send_push(
        self,
        to: str,
        body: str,
        *,
        subject: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> NotificationResult:
        return await self._gateway.send(
            NotificationMessage(
                channel="push",
                recipient=to,
                subject=subject,
                body=body,
                metadata=metadata or {},
            )
        )
