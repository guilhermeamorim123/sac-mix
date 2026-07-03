"""
Data model for the fleet panel: one table, `machines`, tracking every
machine onboard.py has registered a check-in for. See
docs/superpowers/specs/2026-07-02-fleet-panel-design.md for the full
design rationale. This file has no FastAPI/HTTP code -- every function
here takes a SQLAlchemy session and plain arguments, so it's testable
with direct function calls (see selfcheck.py).
"""
import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True)
    serial = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    dragx_version = Column(String, nullable=True)
    # Timezone-aware, but on SQLite (local dev/selfcheck) values read back
    # from the DB come back naive (tzinfo stripped) even though tz-aware
    # values are written -- SQLite has no native tz-aware storage type.
    # Postgres (production) preserves tzinfo correctly. Don't compare a
    # freshly-created datetime.now(timezone.utc) directly against a value
    # read back from this column without normalizing tzinfo first, or a
    # naive-vs-aware TypeError may only surface against SQLite, not Postgres.
    first_onboarded_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(String, nullable=True)


def checkin_machine(session, serial, dragx_version):
    """Upserts a machine record: creates it (with first_onboarded_at = now)
    if serial is new, otherwise updates last_seen_at and dragx_version.
    Returns the Machine row."""
    now = datetime.datetime.now(datetime.timezone.utc)
    machine = session.query(Machine).filter_by(serial=serial).one_or_none()
    if machine is None:
        machine = Machine(
            serial=serial,
            dragx_version=dragx_version,
            first_onboarded_at=now,
            last_seen_at=now,
        )
        session.add(machine)
    else:
        machine.last_seen_at = now
        machine.dragx_version = dragx_version
    session.commit()
    return machine
