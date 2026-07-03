"""
Self-check for the fleet panel's pure-logic modules (models.py, auth.py)
and, later in this file, main.py's HTTP routes via FastAPI's TestClient
(no pytest needed -- TestClient is a plain Python class).

Run directly: python selfcheck.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# In-memory DB for every test in this file -- must be set before main.py
# (or db.py) is imported anywhere, since db.get_engine() reads this env
# var at call time.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import inspect  # noqa: E402

import db  # noqa: E402

failures = 0


def check(name, actual, expected):
    global failures
    if actual == expected:
        print(f"PASS: {name}")
    else:
        failures += 1
        print(f"FAIL: {name} -- expected {expected!r}, got {actual!r}")


def check_true(name, actual):
    check(name, bool(actual), True)


# --- schema creation ---
engine = db.get_engine()
table_names = inspect(engine).get_table_names()
check("machines table exists after get_engine()", "machines" in table_names, True)

# --- checkin_machine ---
import datetime  # noqa: E402
import models  # noqa: E402

SessionLocal = db.get_session_factory(engine)
session = SessionLocal()

m1 = models.checkin_machine(session, serial="ABC123", dragx_version="V7.0.3.005")
check("checkin_machine creates a new machine", m1.serial, "ABC123")
check("checkin_machine sets dragx_version", m1.dragx_version, "V7.0.3.005")
check_true("checkin_machine sets first_onboarded_at", isinstance(m1.first_onboarded_at, datetime.datetime))
check("checkin_machine first_onboarded_at equals last_seen_at on creation", m1.first_onboarded_at, m1.last_seen_at)

first_seen = m1.first_onboarded_at
m2 = models.checkin_machine(session, serial="ABC123", dragx_version="V7.0.4.000")
check("checkin_machine updates dragx_version on repeat call", m2.dragx_version, "V7.0.4.000")
check("checkin_machine does not change first_onboarded_at on repeat call", m2.first_onboarded_at, first_seen)
check_true("checkin_machine updates last_seen_at on repeat call", m2.last_seen_at >= first_seen)

all_machines = session.query(models.Machine).filter_by(serial="ABC123").all()
check("checkin_machine never creates a duplicate row for the same serial", len(all_machines), 1)

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
