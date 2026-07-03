"""
Database engine/session setup for the fleet panel. Defaults to a local
SQLite file for development; reads DATABASE_URL (a Neon Postgres
connection string) in production, set as a Render environment variable.

In-memory SQLite (used by selfcheck.py) needs special handling: SQLAlchemy
normally hands out a fresh, separate, empty in-memory database per
connection, which would make writes from one request invisible to the
next. StaticPool keeps a single connection alive for the lifetime of the
engine so all reads/writes in a test run share the same in-memory data.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base


def get_engine(db_url=None):
    db_url = db_url or os.environ.get("DATABASE_URL", "sqlite:///./fleet_panel.db")
    if db_url == "sqlite:///:memory:":
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


def get_session_factory(engine):
    return sessionmaker(bind=engine)
