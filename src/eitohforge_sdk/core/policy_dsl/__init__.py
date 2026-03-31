"""Policy expression DSL: AST, parser, and :class:`AccessPolicy` bridge."""

from __future__ import annotations

from dataclasses import dataclass

from eitohforge_sdk.core.abac import AccessPolicy, PolicyContext

from .ast import And, Binary, Expr, Literal, Or, Ref, Unary
from .evaluate import PolicyEvaluationError, eval_expr
from .parse import PolicySyntaxError, parse_expr


@dataclass(frozen=True)
class ExpressionAccessPolicy:
    """ABAC policy backed by a parsed expression (see :func:`parse_expr`)."""

    name: str
    expression: Expr

    def evaluate(self, context: PolicyContext) -> bool:
        return bool(eval_expr(self.expression, context))

    @classmethod
    def from_source(cls, name: str, source: str) -> ExpressionAccessPolicy:
        return cls(name=name, expression=parse_expr(source))


def expression_policy(name: str, source: str) -> AccessPolicy:
    """Build an :class:`AccessPolicy` from a DSL string (registered name + source)."""
    return ExpressionAccessPolicy.from_source(name, source)


__all__ = [
    "And",
    "Binary",
    "ExpressionAccessPolicy",
    "Expr",
    "Literal",
    "Or",
    "PolicyEvaluationError",
    "PolicySyntaxError",
    "Ref",
    "Unary",
    "eval_expr",
    "expression_policy",
    "parse_expr",
]
