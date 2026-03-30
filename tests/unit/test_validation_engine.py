from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from eitohforge_sdk.core.validation import (
    ValidationContext,
    ValidationEngine,
    ValidationFailedError,
    ValidationIssue,
    ValidationSeverity,
    ValidationStage,
)


@dataclass
class Payload:
    username: str
    password: str


class UsernameRule:
    name = "username-rule"

    async def validate(self, payload: Payload, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = context
        if len(payload.username) < 3:
            return (
                ValidationIssue(
                    code="USERNAME_TOO_SHORT",
                    message="Username must be at least 3 characters.",
                    field="username",
                ),
            )
        return ()


class PasswordRule:
    name = "password-rule"

    async def validate(self, payload: Payload, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = context
        if len(payload.password) < 8:
            return (
                ValidationIssue(
                    code="PASSWORD_WEAK",
                    message="Password must be at least 8 characters.",
                    field="password",
                ),
            )
        return ()


class AdvisoryRule:
    name = "advisory-rule"

    async def validate(self, payload: Payload, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = (payload, context)
        return (
            ValidationIssue(
                code="ADVISORY",
                message="Advisory note.",
                severity=ValidationSeverity.WARNING,
            ),
        )


def test_validation_engine_collects_issues() -> None:
    engine = ValidationEngine()
    engine.register_many((UsernameRule(), PasswordRule(), AdvisoryRule()))
    result = asyncio.run(
        engine.validate(Payload(username="ab", password="123"), ValidationContext(stage=ValidationStage.REQUEST))
    )
    assert len(result.issues) == 3
    assert result.is_valid is False


def test_validation_engine_validate_or_raise() -> None:
    engine = ValidationEngine()
    engine.register(UsernameRule())
    with pytest.raises(ValidationFailedError):
        asyncio.run(
            engine.validate_or_raise(
                Payload(username="ab", password="valid-password"),
                ValidationContext(stage=ValidationStage.DOMAIN),
            )
        )


def test_validation_engine_stop_on_first_error() -> None:
    engine = ValidationEngine()
    engine.register_many((UsernameRule(), PasswordRule()))
    result = asyncio.run(
        engine.validate(
            Payload(username="ab", password="123"),
            ValidationContext(stage=ValidationStage.REQUEST),
            stop_on_first_error=True,
        )
    )
    assert len(result.issues) == 1

