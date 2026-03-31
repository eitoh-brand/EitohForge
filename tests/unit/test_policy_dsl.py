from __future__ import annotations

import pytest

from eitohforge_sdk.core.abac import PolicyContext
from eitohforge_sdk.core.policy_dsl import (
    ExpressionAccessPolicy,
    PolicyEvaluationError,
    PolicySyntaxError,
    eval_expr,
    expression_policy,
    parse_expr,
)
from eitohforge_sdk.core.security import SecurityPrincipal


def test_parse_compound_and() -> None:
    from eitohforge_sdk.core.policy_dsl import And

    expr = parse_expr(
        "principal.actor_id != null and attributes.resource_tenant_id == principal.tenant_id"
    )
    assert isinstance(expr, And)


def test_expr_tenant_match_equivalent_to_tenant_policy() -> None:
    expr = parse_expr('attributes.resource_tenant_id == principal.tenant_id')
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=(), tenant_id="t1"),
        attributes={"resource_tenant_id": "t1"},
    )
    assert eval_expr(expr, ctx) is True
    ctx2 = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=(), tenant_id="t1"),
        attributes={"resource_tenant_id": "t2"},
    )
    assert eval_expr(expr, ctx2) is False


def test_expression_access_policy() -> None:
    pol = ExpressionAccessPolicy.from_source(name="tenant_match", source="attributes.x == principal.tenant_id")
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=(), tenant_id="t1"),
        attributes={"x": "t1"},
    )
    assert pol.evaluate(ctx) is True


def test_expression_policy_factory() -> None:
    pol = expression_policy("p", "principal.actor_id != null")
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="u1", roles=(), tenant_id=None),
        attributes={},
    )
    assert pol.evaluate(ctx) is True


def test_roles_in_membership() -> None:
    expr = parse_expr('"admin" in principal.roles')
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=("user", "admin"), tenant_id=None),
        attributes={},
    )
    assert eval_expr(expr, ctx) is True
    ctx2 = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=("user",), tenant_id=None),
        attributes={},
    )
    assert eval_expr(expr, ctx2) is False


def test_not_in() -> None:
    expr = parse_expr('"banned" not in principal.roles')
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=("user",), tenant_id=None),
        attributes={},
    )
    assert eval_expr(expr, ctx) is True


def test_or_short_circuit() -> None:
    expr = parse_expr('principal.actor_id != null or attributes.missing == true')
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="a", roles=(), tenant_id=None),
        attributes={},
    )
    assert eval_expr(expr, ctx) is True


def test_not_unary() -> None:
    expr = parse_expr('not (principal.actor_id == null)')
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id="x", roles=(), tenant_id=None),
        attributes={},
    )
    assert eval_expr(expr, ctx) is True


def test_syntax_errors() -> None:
    with pytest.raises(PolicySyntaxError):
        parse_expr("")
    with pytest.raises(PolicySyntaxError):
        parse_expr("(")
    with pytest.raises(PolicySyntaxError):
        parse_expr("principal.")


def test_unknown_ref_root() -> None:
    expr = parse_expr("unknown.x == 1")
    ctx = PolicyContext(
        principal=SecurityPrincipal(actor_id=None, roles=(), tenant_id=None),
        attributes={},
    )
    with pytest.raises(PolicyEvaluationError, match="Unknown reference root"):
        eval_expr(expr, ctx)


def test_numeric_compare() -> None:
    expr = parse_expr("attributes.n >= 10")
    assert (
        eval_expr(
            expr,
            PolicyContext(principal=SecurityPrincipal(None, ()), attributes={"n": 5}),
        )
        is False
    )
    assert (
        eval_expr(
            expr,
            PolicyContext(principal=SecurityPrincipal(None, ()), attributes={"n": 10}),
        )
        is True
    )
