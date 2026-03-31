"""Evaluate policy AST against :class:`~eitohforge_sdk.core.abac.PolicyContext`."""

from __future__ import annotations

from collections.abc import Mapping

from eitohforge_sdk.core.abac import PolicyContext

from .ast import And, Binary, Expr, Literal, Or, Ref, Unary


class PolicyEvaluationError(RuntimeError):
    """Raised when evaluation cannot complete (unknown ref root, bad types)."""


def _resolve_ref(parts: tuple[str, ...], ctx: PolicyContext) -> object:
    if not parts:
        raise PolicyEvaluationError("Empty reference path.")
    root = parts[0]
    if root == "principal":
        obj: object = ctx.principal
        rest = parts[1:]
    elif root == "attributes":
        obj = ctx.attributes
        rest = parts[1:]
    else:
        raise PolicyEvaluationError(
            f"Unknown reference root {root!r}; expected 'principal' or 'attributes'."
        )
    for part in rest:
        if isinstance(obj, Mapping):
            obj = obj.get(part)
        else:
            obj = getattr(obj, part, None)
    return obj


def eval_expr(expr: Expr, ctx: PolicyContext) -> object:
    """Evaluate expression to a Python value (truthiness used for policy decisions)."""
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Ref):
        return _resolve_ref(expr.parts, ctx)
    if isinstance(expr, Unary):
        if expr.op != "not":
            raise PolicyEvaluationError(f"Unsupported unary operator {expr.op!r}.")
        return not _truthy(eval_expr(expr.operand, ctx))
    if isinstance(expr, And):
        if not _truthy(eval_expr(expr.left, ctx)):
            return False
        return eval_expr(expr.right, ctx)
    if isinstance(expr, Or):
        if _truthy(eval_expr(expr.left, ctx)):
            return True
        return eval_expr(expr.right, ctx)
    if isinstance(expr, Binary):
        return _eval_binary(expr, ctx)
    raise PolicyEvaluationError(f"Unsupported expression node: {type(expr)!r}.")


def _truthy(value: object) -> bool:
    return bool(value)


def _eval_binary(expr: Binary, ctx: PolicyContext) -> object:
    op = expr.op
    left = eval_expr(expr.left, ctx)
    right = eval_expr(expr.right, ctx)
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "<":
        return left < right  # type: ignore[operator]
    if op == "<=":
        return left <= right  # type: ignore[operator]
    if op == ">":
        return left > right  # type: ignore[operator]
    if op == ">=":
        return left >= right  # type: ignore[operator]
    if op == "in":
        return left in right  # type: ignore[operator]
    if op == "not_in":
        return left not in right  # type: ignore[operator]
    raise PolicyEvaluationError(f"Unsupported binary operator {op!r}.")
