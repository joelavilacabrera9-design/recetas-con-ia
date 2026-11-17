"""Conexión a la base de datos con SQLAlchemy 2.0."""

import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = get_settings().database_url
    if url.startswith("sqlite"):
        # SQLite en memoria se usa solo en las pruebas.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 10, delay_seconds: float = 3.0) -> None:
    """Crea las tablas. Reintenta porque MySQL puede tardar en aceptar conexiones."""
    from app import models  # noqa: F401  (registra los modelos en Base.metadata)

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == retries:
                raise
            logger.warning("Base de datos no disponible (intento %s/%s)", attempt, retries)
            time.sleep(delay_seconds)
