from __future__ import annotations

import pytest

from eitohforge_sdk.application.dto.repository import FilterCondition, FilterOperator, QuerySpec
from eitohforge_sdk.application.query_spec_support import (
    list_unknown_query_filter_fields,
    validate_query_filters_against_columns,
)


def test_list_unknown_query_filter_fields() -> None:
    q = QuerySpec(
        filters=(
            FilterCondition(field="name", operator=FilterOperator.EQ, value="a"),
            FilterCondition(field="nope", operator=FilterOperator.EQ, value="b"),
        )
    )
    assert list_unknown_query_filter_fields(q, valid_columns={"name"}) == ("nope",)


def test_validate_query_filters_against_columns_raises() -> None:
    q = QuerySpec(filters=(FilterCondition(field="bad", operator=FilterOperator.EQ, value=1),))
    with pytest.raises(ValueError, match="unknown filter field"):
        validate_query_filters_against_columns(q, valid_columns={"id"})


def test_validate_query_filters_against_columns_ok() -> None:
    q = QuerySpec(filters=(FilterCondition(field="id", operator=FilterOperator.EQ, value="1"),))
    validate_query_filters_against_columns(q, valid_columns={"id"})
