"""Time and range value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from eitohforge_sdk.domain.value_objects.errors import DomainInvariantError


@dataclass(frozen=True)
class DateTimeRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise DomainInvariantError("DateTimeRange requires start <= end.")

