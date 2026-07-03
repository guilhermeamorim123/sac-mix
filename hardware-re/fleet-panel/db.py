"""
Database engine/session setup for the fleet panel. Defaults to a local
SQLite file for development; reads DATABASE_URL (a Neon Postgres
connection string) in production, set as a Render environment variable.

In-memory SQLite (used by selfcheck.py) needs special handling: SQLAlchemy
normally hands out a fresh, separate, empty in-memory database per
connection, which would make writes from one request invisible to the
next. StaticPool keeps a single connection alive for the lifetime of the
engine so all reads/writes in a test run share the same in-memory data --
but that promise only holds within a single engine instance. selfcheck.py
calls get_engine() directly to seed test data, and separately triggers
main.py's own top-level `engine = get_engine()` call (via `import main`).
Without caching, each call would create a brand-new StaticPool/connection
-- i.e. a second, disconnected in-memory database -- so writes made
before `import main` would be invisible to routes tested afterward via
TestClient. Caching by resolved db_url ensures every caller within the
same process (selfcheck.py's setup code and main.py's app) shares the
exact same engine/connection for a given DATABASE_URL, in-memory or not.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base

_engine_cache = {}


def get_engine(db_url=None):
    db_url = db_url or os.environ.get("DATABASE_URL", "sqlite:///./fleet_panel.db")
    if db_url in _engine_cache:
        return _engine_cache[db_url]
    url = make_url(db_url)
    is_memory_sqlite = url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:")
    if is_memory_sqlite:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    _engine_cache[db_url] = engine
    return engine


def get_session_factory(engine):
    return sessionmaker(bind=engine)
