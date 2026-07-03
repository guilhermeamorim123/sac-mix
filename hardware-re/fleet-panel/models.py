"""
Data model for the fleet panel: one table, `machines`, tracking every
machine onboard.py has registered a check-in for. See
docs/superpowers/specs/2026-07-02-fleet-panel-design.md for the full
design rationale. This file has no FastAPI/HTTP code -- every function
here takes a SQLAlchemy session and plain arguments, so it's testable
with direct function calls (see selfcheck.py).
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True)
    serial = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    dragx_version = Column(String, nullable=True)
    first_onboarded_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    notes = Column(String, nullable=True)
