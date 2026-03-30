"""Contact-related value objects."""

from __future__ import annotations

from dataclasses import dataclass
import re

from eitohforge_sdk.domain.value_objects.errors import DomainInvariantError


_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise DomainInvariantError("EmailAddress must be a valid email format.")
        object.__setattr__(self, "value", normalized)

