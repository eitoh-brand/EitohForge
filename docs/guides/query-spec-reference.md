# Query spec reference (`QuerySpec` / `SQLAlchemyRepository`)

This document is the **contract** for `eitohforge_sdk.application.dto.repository.QuerySpec` as applied by `eitohforge_sdk.infrastructure.repositories.sqlalchemy_repository.SQLAlchemyRepository`. It aligns with blueprint **§6 Query specification engine** for the SQL path.

## Filter operators

| Operator | Value shape | SQLAlchemy behavior |
|----------|-------------|---------------------|
| `eq` | scalar | `column == value` |
| `ne` | scalar | `column != value` |
| `gt`, `gte`, `lt`, `lte` | scalar | Comparison on the mapped column |
| `contains` | string (typical) | `column.contains(value)` |
| `startswith` | string | `column.startswith(value)` |
| `endswith` | string | `column.endswith(value)` |
| `between` | sequence of **exactly two** elements | `column.between(lo, hi)`; invalid length → filter skipped |
| `in` | non-string **sequence** | `column IN (...)`; **empty sequence** → matches **no rows** (`false()`) |
| `not_in` | non-string sequence | `column NOT IN (...)`; **empty sequence** → **no filter** (all rows pass this predicate) |
| `exists` | boolean | `True` → `IS NOT NULL`, `False` → `IS NULL` on the column (not a SQL `EXISTS` subquery) |

**Strings** are not valid `in` / `not_in` values (use a one-element tuple or list). **Unknown field names** are **silently ignored** (no row filter applied for that condition). To fail fast, call `validate_query_filters_against_columns` from `eitohforge_sdk.application.query_spec_support`.

## Sorting

`SortSpec`: `field` must exist on the model; unknown fields are skipped. Multiple sorts apply in order.

## Pagination

| Mode | Behavior |
|------|----------|
| `offset` | `OFFSET` + `LIMIT` from `pagination.offset` and `page_size`. |
| `cursor` | If `cursor` is numeric, used as **offset**; else falls back to `offset`. |
| `keyset` | Uses first applicable `sort` (or `id` ascending); `cursor` is compared to the sort column (`>` / `<` for asc/desc). |

## Code

```python
from eitohforge_sdk.application import validate_query_filters_against_columns
from eitohforge_sdk.application.dto.repository import FilterCondition, FilterOperator, QuerySpec

validate_query_filters_against_columns(
    query,
    valid_columns={"id", "name", "email", "tenant_id", "score"},
)
```

## Related

- DTO definitions: `src/eitohforge_sdk/application/dto/repository.py`
- Implementation: `src/eitohforge_sdk/infrastructure/repositories/sqlalchemy_repository.py`
- Tests: `tests/unit/test_sqlalchemy_repository.py`, `tests/unit/test_query_spec_support.py`
