"""Repository contracts and aliases for clean architecture."""

from eitohforge_sdk.domain.repositories.contracts import PageResult, RepositoryContract
from eitohforge_sdk.domain.repositories.query_coalesce import (
    coalesce_query_spec,
    expand_filter_items,
)
from eitohforge_sdk.domain.repositories.specification import AndSpecification, Specification

# Concrete implementations (e.g. ``SQLAlchemyRepository``) satisfy this protocol.
BaseRepository = RepositoryContract

__all__ = [
    "AndSpecification",
    "BaseRepository",
    "PageResult",
    "RepositoryContract",
    "Specification",
    "coalesce_query_spec",
    "expand_filter_items",
]
