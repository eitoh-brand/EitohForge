"""Notification infrastructure template fragments."""

NOTIFICATION_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/notifications/__init__.py": """from app.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)
from app.infrastructure.notifications.gateway import InMemoryNotificationGateway, success_result_for
from app.infrastructure.notifications.template_engine import (
    NotificationTemplate,
    NotificationTemplateEngine,
    RenderedNotificationTemplate,
    TemplateRenderError,
    send_template,
)
""",
    "app/infrastructure/notifications/contracts.py": """from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

NotificationChannel = Literal["email", "sms", "push"]


@dataclass(frozen=True)
class NotificationMessage:
    channel: NotificationChannel
    recipient: str
    subject: str | None = None
    body: str = ""
    template_id: str | None = None
    template_vars: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class NotificationResult:
    status: str
    channel: NotificationChannel
    recipient: str
    provider_message_id: str | None = None
    error_message: str | None = None


NotificationSender = Callable[[NotificationMessage], Awaitable[NotificationResult] | NotificationResult]


class NotificationGateway(Protocol):
    def register_sender(self, channel: NotificationChannel, sender: NotificationSender) -> None:
        ...

    async def send(self, message: NotificationMessage) -> NotificationResult:
        ...

    async def send_many(self, messages: tuple[NotificationMessage, ...]) -> tuple[NotificationResult, ...]:
        ...
""",
    "app/infrastructure/notifications/gateway.py": """from dataclasses import dataclass, field
from inspect import isawaitable
from uuid import uuid4

from app.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


@dataclass
class InMemoryNotificationGateway(NotificationGateway):
    _senders: dict[NotificationChannel, NotificationSender] = field(default_factory=dict)
    _sent_messages: list[NotificationMessage] = field(default_factory=list)

    @property
    def sent_messages(self) -> tuple[NotificationMessage, ...]:
        return tuple(self._sent_messages)

    def register_sender(self, channel: NotificationChannel, sender: NotificationSender) -> None:
        self._senders[channel] = sender

    async def send(self, message: NotificationMessage) -> NotificationResult:
        sender = self._senders.get(message.channel)
        if sender is None:
            return NotificationResult(
                status="failed",
                channel=message.channel,
                recipient=message.recipient,
                error_message=f"No sender registered for channel: {message.channel}",
            )

        self._sent_messages.append(message)
        try:
            maybe_awaitable = sender(message)
            result = await maybe_awaitable if isawaitable(maybe_awaitable) else maybe_awaitable
            return result
        except Exception as exc:
            return NotificationResult(
                status="failed",
                channel=message.channel,
                recipient=message.recipient,
                error_message=str(exc),
            )

    async def send_many(self, messages: tuple[NotificationMessage, ...]) -> tuple[NotificationResult, ...]:
        results: list[NotificationResult] = []
        for message in messages:
            results.append(await self.send(message))
        return tuple(results)


def success_result_for(message: NotificationMessage) -> NotificationResult:
    return NotificationResult(
        status="sent",
        channel=message.channel,
        recipient=message.recipient,
        provider_message_id=str(uuid4()),
    )
""",
    "app/infrastructure/notifications/template_engine.py": """from dataclasses import dataclass
from string import Formatter

from app.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
)


class TemplateRenderError(ValueError):
    pass


@dataclass(frozen=True)
class NotificationTemplate:
    template_id: str
    locale: str
    channel: NotificationChannel
    body_template: str
    subject_template: str | None = None


@dataclass(frozen=True)
class RenderedNotificationTemplate:
    channel: NotificationChannel
    subject: str | None
    body: str


class NotificationTemplateEngine:
    def __init__(self, *, default_locale: str = "en") -> None:
        self._default_locale = default_locale
        self._templates: dict[tuple[str, str], NotificationTemplate] = {}

    def register(self, template: NotificationTemplate) -> None:
        key = (template.template_id, template.locale)
        self._templates[key] = template

    def render(
        self,
        *,
        template_id: str,
        locale: str,
        variables: dict[str, object] | None = None,
    ) -> RenderedNotificationTemplate:
        template = self._resolve_template(template_id=template_id, locale=locale)
        payload = variables or {}
        subject = _render_optional_template(template.subject_template, payload)
        body = _render_required_template(template.body_template, payload)
        return RenderedNotificationTemplate(channel=template.channel, subject=subject, body=body)

    def _resolve_template(self, *, template_id: str, locale: str) -> NotificationTemplate:
        for key in ((template_id, locale), (template_id, self._default_locale)):
            if key in self._templates:
                return self._templates[key]
        raise TemplateRenderError(
            f"Notification template not found for template_id='{template_id}', locale='{locale}'."
        )


async def send_template(
    gateway: NotificationGateway,
    engine: NotificationTemplateEngine,
    *,
    template_id: str,
    locale: str,
    recipient: str,
    variables: dict[str, object] | None = None,
    metadata: dict[str, str] | None = None,
) -> NotificationResult:
    rendered = engine.render(template_id=template_id, locale=locale, variables=variables)
    return await gateway.send(
        NotificationMessage(
            channel=rendered.channel,
            recipient=recipient,
            subject=rendered.subject,
            body=rendered.body,
            template_id=template_id,
            template_vars=variables or {},
            metadata=metadata or {},
        )
    )


def _render_required_template(template_text: str, variables: dict[str, object]) -> str:
    missing = _missing_fields(template_text, variables)
    if missing:
        fields = ", ".join(sorted(missing))
        raise TemplateRenderError(f"Missing template variables: {fields}")
    return template_text.format_map(variables)


def _render_optional_template(template_text: str | None, variables: dict[str, object]) -> str | None:
    if template_text is None:
        return None
    return _render_required_template(template_text, variables)


def _missing_fields(template_text: str, variables: dict[str, object]) -> set[str]:
    formatter = Formatter()
    missing: set[str] = set()
    for _, field_name, _, _ in formatter.parse(template_text):
        if field_name and field_name not in variables:
            missing.add(field_name)
    return missing
""",
}

