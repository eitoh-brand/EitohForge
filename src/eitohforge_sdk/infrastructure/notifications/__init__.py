"""Notification infrastructure primitives."""

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)
from eitohforge_sdk.infrastructure.notifications.gateway import (
    InMemoryNotificationGateway,
    success_result_for,
)
from eitohforge_sdk.infrastructure.notifications.sendgrid import build_sendgrid_email_sender
from eitohforge_sdk.infrastructure.notifications.template_engine import (
    NotificationTemplate,
    NotificationTemplateEngine,
    RenderedNotificationTemplate,
    TemplateRenderError,
    send_template,
)

__all__ = [
    "NotificationChannel",
    "NotificationGateway",
    "NotificationMessage",
    "NotificationResult",
    "NotificationSender",
    "InMemoryNotificationGateway",
    "build_sendgrid_email_sender",
    "success_result_for",
    "NotificationTemplate",
    "RenderedNotificationTemplate",
    "NotificationTemplateEngine",
    "TemplateRenderError",
    "send_template",
]

