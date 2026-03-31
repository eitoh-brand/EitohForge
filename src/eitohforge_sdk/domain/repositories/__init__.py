"""Repository contracts and aliases for clean architecture."""

from eitohforge_sdk.domain.repositories.contracts import PageResult, RepositoryContract

# Concrete implementations (e.g. ``SQLAlchemyRepository``) satisfy this protocol.
BaseRepository = RepositoryContract

__all__ = ["BaseRepository", "PageResult", "RepositoryContract"]
