from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    pass


_engine = None


def _get_dsn() -> str:
    return (
        settings.postgres_dsn
    )  # e.g. postgresql+psycopg2://postgres:postgres@localhost:5432/metrics


def get_engine():
    global _engine
    dsn = _get_dsn()
    if _engine is None or str(_engine.url) != dsn:
        _engine = create_engine(
            dsn,
            future=True,
            pool_pre_ping=True,  # avoids stale connections
        )
    return _engine


def SessionLocal():
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def init_db():
    # 1) ensure models are imported so metadata is populated
    from src.database.pull_request import PullRequest
    from src.database.snapshot import Snapshot
    from src.database.task import Task

    # sanity: they all use THIS Base
    assert Task.__table__.metadata is Base.metadata
    assert PullRequest.__table__.metadata is Base.metadata
    assert Snapshot.__table__.metadata is Base.metadata

    engine = get_engine()

    # 2) actually create tables (inside a transaction)
    try:
        with engine.begin() as conn:
            Base.metadata.create_all(bind=conn, checkfirst=True)
    except SQLAlchemyError as e:
        print("[DB] create_all failed:", e)
        raise
