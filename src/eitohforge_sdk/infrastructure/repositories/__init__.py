"""Repository adapter implementations."""

from eitohforge_sdk.infrastructure.repositories.memory_repository import InMemoryRepository
from eitohforge_sdk.infrastructure.repositories.mongo_repository import MongoJsonRepository
from eitohforge_sdk.infrastructure.repositories.redis_repository import RedisJsonRepository
from eitohforge_sdk.infrastructure.repositories.sqlalchemy_repository import SQLAlchemyRepository

SQLRepository = SQLAlchemyRepository

__all__ = [
    "InMemoryRepository",
    "MongoJsonRepository",
    "RedisJsonRepository",
    "SQLAlchemyRepository",
    "SQLRepository",
]

