"""Validation contracts and registry abstractions."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from eitohforge_sdk.core.validation.context import ValidationContext
from eitohforge_sdk.core.validation.errors import ValidationIssue


TPayload = TypeVar("TPayload", contravariant=True)


class ValidationRule(Protocol, Generic[TPayload]):
    """Validation rule contract."""

    name: str

    async def validate(
        self, payload: TPayload, context: ValidationContext
    ) -> tuple[ValidationIssue, ...]:
        """Return validation issues for payload."""

