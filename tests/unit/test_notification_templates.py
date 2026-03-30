from __future__ import annotations

import asyncio

from eitohforge_sdk.infrastructure.notifications import (
    InMemoryNotificationGateway,
    NotificationTemplate,
    NotificationTemplateEngine,
    TemplateRenderError,
    send_template,
    success_result_for,
)


def test_template_engine_renders_localized_template() -> None:
    engine = NotificationTemplateEngine(default_locale="en")
    engine.register(
        NotificationTemplate(
            template_id="welcome",
            locale="en",
            channel="email",
            subject_template="Welcome {name}",
            body_template="Hello {name}, thanks for joining.",
        )
    )
    engine.register(
        NotificationTemplate(
            template_id="welcome",
            locale="es",
            channel="email",
            subject_template="Bienvenido {name}",
            body_template="Hola {name}, gracias por unirte.",
        )
    )

    rendered = engine.render(template_id="welcome", locale="es", variables={"name": "Pritam"})
    assert rendered.subject == "Bienvenido Pritam"
    assert rendered.body == "Hola Pritam, gracias por unirte."


def test_template_engine_falls_back_to_default_locale() -> None:
    engine = NotificationTemplateEngine(default_locale="en")
    engine.register(
        NotificationTemplate(
            template_id="otp",
            locale="en",
            channel="sms",
            body_template="Your OTP is {code}",
        )
    )
    rendered = engine.render(template_id="otp", locale="fr", variables={"code": 1234})
    assert rendered.channel == "sms"
    assert rendered.body == "Your OTP is 1234"


def test_template_engine_raises_on_missing_variable() -> None:
    engine = NotificationTemplateEngine()
    engine.register(
        NotificationTemplate(
            template_id="push_alert",
            locale="en",
            channel="push",
            body_template="Hi {name}",
        )
    )
    try:
        engine.render(template_id="push_alert", locale="en", variables={})
    except TemplateRenderError as exc:
        assert "Missing template variables: name" in str(exc)
    else:
        raise AssertionError("Expected TemplateRenderError for missing variable.")


def test_send_template_uses_gateway_with_rendered_content() -> None:
    gateway = InMemoryNotificationGateway()
    gateway.register_sender("email", lambda message: success_result_for(message))
    engine = NotificationTemplateEngine()
    engine.register(
        NotificationTemplate(
            template_id="invoice_paid",
            locale="en",
            channel="email",
            subject_template="Invoice {invoice_id} paid",
            body_template="Amount {amount} received",
        )
    )
    result = asyncio.run(
        send_template(
            gateway,
            engine,
            template_id="invoice_paid",
            locale="en",
            recipient="finops@acme.dev",
            variables={"invoice_id": "INV-1", "amount": "120.00"},
        )
    )
    assert result.status == "sent"
    assert len(gateway.sent_messages) == 1
    assert gateway.sent_messages[0].subject == "Invoice INV-1 paid"
    assert gateway.sent_messages[0].body == "Amount 120.00 received"

