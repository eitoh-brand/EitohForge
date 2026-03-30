from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from eitohforge_sdk.infrastructure.database.transaction import TransactionManager


class Base(DeclarativeBase):
    pass


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))


def _make_manager(tmp_path: Path) -> tuple[TransactionManager, sessionmaker]:
    db_file = tmp_path / "tx.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return TransactionManager(factory), factory


def test_transaction_manager_commits_on_success(tmp_path: Path) -> None:
    manager, factory = _make_manager(tmp_path)
    with manager.unit_of_work() as uow:
        uow.session.add(EventModel(name="created"))

    with factory() as session:
        names = session.scalars(select(EventModel.name)).all()
        assert names == ["created"]


def test_transaction_manager_rolls_back_on_exception(tmp_path: Path) -> None:
    manager, factory = _make_manager(tmp_path)
    with pytest.raises(RuntimeError):
        with manager.unit_of_work() as uow:
            uow.session.add(EventModel(name="created"))
            raise RuntimeError("boom")

    with factory() as session:
        names = session.scalars(select(EventModel.name)).all()
        assert names == []


def test_transaction_manager_rolls_back_when_marked(tmp_path: Path) -> None:
    manager, factory = _make_manager(tmp_path)
    with manager.unit_of_work() as uow:
        uow.session.add(EventModel(name="created"))
        uow.mark_rollback()

    with factory() as session:
        names = session.scalars(select(EventModel.name)).all()
        assert names == []

