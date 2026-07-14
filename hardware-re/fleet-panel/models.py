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


class DragxRelease(Base):
    __tablename__ = "dragx_release"

    # Single-row table (id is always 1) -- there is deliberately no history
    # of past releases, only "what's current right now". See
    # docs/superpowers/specs/2026-07-07-dragx-auto-update-design.md.
    id = Column(Integer, primary_key=True)
    version_code = Column(Integer, nullable=False)
    version_name = Column(String, nullable=False)
    download_url = Column(String, nullable=False)
    file_md5 = Column(String, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False)


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


def add_machine_manual(session, serial, name):
    """Adds a machine that was onboarded before this panel existed, or
    updates its name if it already exists (upsert, same as
    checkin_machine, but only ever touches `name`)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    machine = session.query(Machine).filter_by(serial=serial).one_or_none()
    if machine is None:
        machine = Machine(
            serial=serial,
            name=name,
            first_onboarded_at=now,
            last_seen_at=now,
        )
        session.add(machine)
    else:
        machine.name = name
    session.commit()
    return machine


def rename_machine(session, serial, new_name):
    """Updates only the `name` field for an existing machine. Returns the
    Machine row, or None if no machine with this serial exists."""
    machine = session.query(Machine).filter_by(serial=serial).one_or_none()
    if machine is None:
        return None
    machine.name = new_name
    session.commit()
    return machine


def list_machines(session):
    """Returns all machines, most-recently-seen first."""
    return session.query(Machine).order_by(Machine.last_seen_at.desc()).all()


def get_latest_release(session):
    """Returns the single DragxRelease row, or None if nothing has been
    published yet."""
    return session.query(DragxRelease).filter_by(id=1).one_or_none()


def set_latest_release(session, version_code, version_name, download_url, file_md5):
    """Upserts the single DragxRelease row (always id=1). Returns the row."""
    now = datetime.datetime.now(datetime.timezone.utc)
    release = session.query(DragxRelease).filter_by(id=1).one_or_none()
    if release is None:
        release = DragxRelease(
            id=1,
            version_code=version_code,
            version_name=version_name,
            download_url=download_url,
            file_md5=file_md5,
            published_at=now,
        )
        session.add(release)
    else:
        release.version_code = version_code
        release.version_name = version_name
        release.download_url = download_url
        release.file_md5 = file_md5
        release.published_at = now
    session.commit()
    return release
