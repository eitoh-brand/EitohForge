from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from eitohforge_sdk.core.validation import (
    FieldComparisonRule,
    MutuallyExclusiveFieldsRule,
    PydanticSchemaRule,
    RequiredTogetherRule,
    ValidationContext,
    ValidationEngine,
    ValidationStage,
)


class CreateUserPayload(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)


def test_pydantic_schema_rule_reports_schema_errors() -> None:
    engine = ValidationEngine()
    engine.register(PydanticSchemaRule(model_type=CreateUserPayload))
    result = asyncio.run(
        engine.validate(
            {"username": "ab", "password": "123"},
            ValidationContext(stage=ValidationStage.REQUEST),
        )
    )
    assert len(result.issues) == 2
    assert result.is_valid is False


def test_required_together_rule_flags_half_present_pair() -> None:
    engine = ValidationEngine()
    engine.register(RequiredTogetherRule(left_field="start_date", right_field="end_date"))
    result = asyncio.run(
        engine.validate(
            {"start_date": "2026-01-01"},
            ValidationContext(stage=ValidationStage.BUSINESS),
        )
    )
    assert len(result.issues) == 1
    assert result.issues[0].code == "FIELDS_REQUIRED_TOGETHER"


def test_mutually_exclusive_rule_blocks_multiple_fields() -> None:
    engine = ValidationEngine()
    engine.register(MutuallyExclusiveFieldsRule(fields=("email", "phone")))
    result = asyncio.run(
        engine.validate(
            {"email": "user@example.com", "phone": "1234567890"},
            ValidationContext(stage=ValidationStage.REQUEST),
        )
    )
    assert len(result.issues) == 1
    assert result.issues[0].code == "FIELDS_MUTUALLY_EXCLUSIVE"


def test_field_comparison_rule_enforces_cross_field_constraints() -> None:
    engine = ValidationEngine()
    engine.register(FieldComparisonRule(left_field="start", right_field="end", operator="lte"))
    result = asyncio.run(
        engine.validate(
            {"start": 10, "end": 3},
            ValidationContext(stage=ValidationStage.DOMAIN),
        )
    )
    assert len(result.issues) == 1
    assert result.issues[0].code == "FIELD_COMPARISON_FAILED"

