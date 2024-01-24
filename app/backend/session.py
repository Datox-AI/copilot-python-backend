from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.backend.config import config

# create session factory to generate new database sessions
MainDbSessionFactory = sessionmaker(
    bind=create_engine(config.database.main_dsn),
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# create session factory to generate new database sessions
AdminDbSessionFactory = sessionmaker(
    bind=create_engine(config.database.admin_dsn),
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def create_maindb_session() -> Iterator[Session]:
    """Create new main database session.

    Yields:
        Database session.
    """

    session = MainDbSessionFactory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def open_maindb_session() -> Iterator[Session]:
    """Create new database session with context manager.

    Yields:
        Database session.
    """

    return create_maindb_session()


def create_admindb_session() -> Iterator[Session]:
    """Create new admin database session.

    Yields:
        Database session.
    """

    session = AdminDbSessionFactory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def open_admindb_session() -> Iterator[Session]:
    """Create new database session with context manager.

    Yields:
        Database session.
    """

    return create_admindb_session()
