"""Notification infrastructure primitives."""

from eitohforge_sdk.infrastructure.notifications.aws_ses_sns_senders import (
    build_ses_email_sender,
    build_sns_sms_sender,
)
from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)
from eitohforge_sdk.infrastructure.notifications.facade import NotificationClient
from eitohforge_sdk.infrastructure.notifications.firebase_push import build_firebase_push_sender
from eitohforge_sdk.infrastructure.notifications.gateway import (
    InMemoryNotificationGateway,
    success_result_for,
)
from eitohforge_sdk.infrastructure.notifications.sendgrid import build_sendgrid_email_sender
from eitohforge_sdk.infrastructure.notifications.smtp_sender import build_smtp_email_sender
from eitohforge_sdk.infrastructure.notifications.twilio_sender import (
    build_twilio_sms_sender,
    build_twilio_whatsapp_sender,
)
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
    "NotificationClient",
    "InMemoryNotificationGateway",
    "build_sendgrid_email_sender",
    "build_smtp_email_sender",
    "build_ses_email_sender",
    "build_sns_sms_sender",
    "build_twilio_sms_sender",
    "build_twilio_whatsapp_sender",
    "build_firebase_push_sender",
    "success_result_for",
    "NotificationTemplate",
    "RenderedNotificationTemplate",
    "NotificationTemplateEngine",
    "TemplateRenderError",
    "send_template",
]

