"""Localized notification template engine."""

from __future__ import annotations

from dataclasses import dataclass
from string import Formatter

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
)


class TemplateRenderError(ValueError):
    """Raised when a notification template cannot be resolved/rendered."""


@dataclass(frozen=True)
class NotificationTemplate:
    """Localized notification template payload."""

    template_id: str
    locale: str
    channel: NotificationChannel
    body_template: str
    subject_template: str | None = None


@dataclass(frozen=True)
class RenderedNotificationTemplate:
    """Rendered template output ready for gateway delivery."""

    channel: NotificationChannel
    subject: str | None
    body: str


class NotificationTemplateEngine:
    """In-memory localized template registry and renderer."""

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
    """Render and send a localized template via the notification gateway."""
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

