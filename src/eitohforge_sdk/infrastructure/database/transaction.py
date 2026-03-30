"""Transaction manager and unit-of-work primitives."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.orm import Session, sessionmaker


TResult = TypeVar("TResult")


@dataclass
class UnitOfWork:
    """Stateful unit-of-work wrapper over a SQLAlchemy session."""

    session: Session
    rollback_only: bool = False

    def mark_rollback(self) -> None:
        """Mark this unit-of-work to rollback at exit."""
        self.rollback_only = True


class TransactionManager:
    """Creates managed transactional scopes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def unit_of_work(self) -> Iterator[UnitOfWork]:
        """Open transactional scope and commit/rollback automatically."""
        with self._session_factory() as session:
            uow = UnitOfWork(session=session)
            try:
                yield uow
                if uow.rollback_only:
                    session.rollback()
                else:
                    session.commit()
            except Exception:
                session.rollback()
                raise

    def run_in_transaction(self, operation: Callable[[Session], TResult]) -> TResult:
        """Run operation in transaction scope and return result."""
        with self.unit_of_work() as uow:
            return operation(uow.session)

