from collections.abc import Generator
import ssl

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def build_mysql_ssl_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def build_connect_args() -> dict:
    connect_args = {
        "connect_timeout": settings.db_connect_timeout,
        "read_timeout": settings.db_read_timeout,
        "write_timeout": settings.db_write_timeout,
    }
    if settings.db_ssl:
        connect_args["ssl"] = build_mysql_ssl_context()
    return connect_args


engine = create_engine(
    url=settings.database_url,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=settings.db_pool_recycle,
    connect_args=build_connect_args(),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
