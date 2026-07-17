"""
Data model for the fleet panel: one table, `machines`, tracking every
machine onboard.py has registered a check-in for. See
docs/superpowers/specs/2026-07-02-fleet-panel-design.md for the full
design rationale. This file has no FastAPI/HTTP code -- every function
here takes a SQLAlchemy session and plain arguments, so it's testable
with direct function calls (see selfcheck.py).
"""
import datetime
import secrets

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
    # Registration & remote approval (see
    # docs/superpowers/specs/2026-07-06-customer-registration-design.md).
    # All four nullable -- existing machines and the manual-add path don't
    # collect these. status defaults to "approved" for rows created by the
    # two existing upsert paths (checkin_machine, add_machine_manual) so
    # today's already-trusted machines aren't retroactively blocked by this
    # column existing -- only register_machine (the new app-facing
    # registration flow) ever creates a row with status="pending".
    phone = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="approved")
    approval_token = Column(String, unique=True, nullable=True)


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
            status="approved",
        )
        session.add(machine)
    else:
        # Deliberately does NOT touch status -- a routine check-in from an
        # already-registered machine must never silently re-approve a
        # blocked machine, or overwrite a pending one mid-review.
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
            status="approved",
        )
        session.add(machine)
    else:
        # Deliberately does NOT touch status -- see checkin_machine's
        # comment above, same reasoning applies here.
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


def register_machine(session, serial, phone, company_name, email, contact_name):
    """Upserts a machine's registration/contact fields, always setting
    status="pending" and generating a FRESH approval_token (even on
    re-registration -- an old, possibly-already-emailed token must not
    silently keep working once new contact details are submitted).
    Returns the Machine row."""
    now = datetime.datetime.now(datetime.timezone.utc)
    machine = session.query(Machine).filter_by(serial=serial).one_or_none()
    token = secrets.token_urlsafe(32)
    if machine is None:
        machine = Machine(
            serial=serial,
            phone=phone,
            company_name=company_name,
            email=email,
            contact_name=contact_name,
            status="pending",
            approval_token=token,
            first_onboarded_at=now,
            last_seen_at=now,
        )
        session.add(machine)
    else:
        machine.phone = phone
        machine.company_name = company_name
        machine.email = email
        machine.contact_name = contact_name
        machine.status = "pending"
        machine.approval_token = token
        machine.last_seen_at = now
    session.commit()
    return machine


def get_machine_status(session, serial):
    """Returns the machine's current status string, or None if no machine
    with this serial exists."""
    machine = session.query(Machine).filter_by(serial=serial).one_or_none()
    return machine.status if machine else None


def get_machine_by_token(session, approval_token):
    """Read-only lookup of a machine by its approval_token -- does NOT
    change status. Used to render the approval confirmation page without
    side effects, since a plain GET must be safe to fetch automatically
    (e.g. WhatsApp/email link-preview crawlers) without approving
    anything on its own."""
    return session.query(Machine).filter_by(approval_token=approval_token).one_or_none()


def approve_machine_by_token(session, approval_token):
    """Looks up a machine by its approval_token and sets status="approved".
    Returns (machine, was_already_approved) on success, or None if no
    machine has this token. Idempotent -- approving an already-approved
    machine again is not an error, matching the design's "visiting an
    old/already-used link is harmless" requirement."""
    machine = session.query(Machine).filter_by(approval_token=approval_token).one_or_none()
    if machine is None:
        return None
    was_already_approved = machine.status == "approved"
    machine.status = "approved"
    session.commit()
    return machine, was_already_approved


def block_machine(session, machine_id):
    """Sets status="blocked" for the machine with this primary key. Returns
    the Machine row, or None if no machine with this id exists."""
    machine = session.query(Machine).filter_by(id=machine_id).one_or_none()
    if machine is None:
        return None
    machine.status = "blocked"
    session.commit()
    return machine


def unblock_machine(session, machine_id):
    """Sets status="approved" for the machine with this primary key.
    Returns the Machine row, or None if no machine with this id exists."""
    machine = session.query(Machine).filter_by(id=machine_id).one_or_none()
    if machine is None:
        return None
    machine.status = "approved"
    session.commit()
    return machine


def list_registered_machines(session):
    """Returns every machine that has gone through the registration flow
    (i.e. has a company_name on file), most-recently-seen first. Excludes
    machines that only ever reached checkin_machine/add_machine_manual
    without ever registering -- those have no customer contact details to
    show."""
    return (
        session.query(Machine)
        .filter(Machine.company_name.isnot(None))
        .order_by(Machine.last_seen_at.desc())
        .all()
    )
