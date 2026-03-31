"""Composable query specifications that compile to repository filter tuples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from eitohforge_sdk.application.dto.repository import FilterCondition


@runtime_checkable
class Specification(Protocol):
    """Maps to one or more ``FilterCondition`` rows (AND-composed by repositories)."""

    def to_query_filters(self) -> tuple[FilterCondition, ...]:
        """Return filters merged with sibling criteria in document order."""
        ...


@dataclass(frozen=True)
class AndSpecification:
    """AND-composition of specifications (flattened to a single filter tuple)."""

    parts: tuple[Specification, ...]

    def to_query_filters(self) -> tuple[FilterCondition, ...]:
        return tuple(cond for part in self.parts for cond in part.to_query_filters())
