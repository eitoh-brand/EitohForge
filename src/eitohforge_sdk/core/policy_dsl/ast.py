"""AST nodes for the policy expression DSL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass(frozen=True)
class Literal:
    """Literal value (string, number, bool, or None)."""

    value: Any


@dataclass(frozen=True)
class Ref:
    """Dotted reference into evaluation roots (`principal.*`, `attributes.*`)."""

    parts: tuple[str, ...]


@dataclass(frozen=True)
class Unary:
    """Unary operator (only `not` in surface syntax)."""

    op: str
    operand: "Expr"


@dataclass(frozen=True)
class Binary:
    """Binary comparison or membership."""

    left: "Expr"
    op: str
    right: "Expr"


@dataclass(frozen=True)
class And:
    """Logical and (short-circuit)."""

    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Or:
    """Logical or (short-circuit)."""

    left: "Expr"
    right: "Expr"


Expr = Union[Literal, Ref, Unary, Binary, And, Or]
