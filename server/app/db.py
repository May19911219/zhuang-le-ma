from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def reset_db() -> None:
    """关掉现有数据库连接，下次访问时按新配置重建。"""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine():
    """按当前配置创建或返回 SQLite 引擎。"""
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_db() -> Generator[Session, None, None]:
    """为每个请求提供一个数据库会话。"""
    get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表并写入预置软件。"""
    from app.models import AdminSession, Feedback, Plan, SelectionStat, Software, VersionEntry
    from app.services.seed import seed_software

    _ = (AdminSession, Feedback, Plan, SelectionStat, Software, VersionEntry)
    Base.metadata.create_all(bind=get_engine())
    db = _SessionLocal()
    try:
        seed_software(db)
    finally:
        db.close()
