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

# main.py requires SESSION_SECRET to be set (no insecure default) -- must
# be set before main.py is imported anywhere in this file.
os.environ["SESSION_SECRET"] = "test-secret-for-selfcheck-only"

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


# --- add_machine_manual ---
m3 = models.add_machine_manual(session, serial="XYZ789", name="Loja 2")
check("add_machine_manual creates a new machine", m3.serial, "XYZ789")
check("add_machine_manual sets name", m3.name, "Loja 2")

m3_again = models.add_machine_manual(session, serial="XYZ789", name="Loja 2 Renomeada")
check("add_machine_manual updates name on repeat call (upsert, not duplicate)", m3_again.name, "Loja 2 Renomeada")
xyz_rows = session.query(models.Machine).filter_by(serial="XYZ789").all()
check("add_machine_manual never creates a duplicate row", len(xyz_rows), 1)

# --- rename_machine ---
renamed = models.rename_machine(session, serial="ABC123", new_name="Loja 1")
check("rename_machine updates name", renamed.name, "Loja 1")
check("rename_machine does not touch dragx_version", renamed.dragx_version, "V7.0.4.000")

missing = models.rename_machine(session, serial="DOES-NOT-EXIST", new_name="whatever")
check("rename_machine returns None for unknown serial", missing, None)

# --- list_machines ---
all_now = models.list_machines(session)
check("list_machines returns every machine", len(all_now), 2)
check_true("list_machines most-recently-seen first", all_now[0].last_seen_at >= all_now[1].last_seen_at)


# --- auth.py: hash_password / verify_password / verify_login ---
import auth  # noqa: E402

stored = auth.hash_password("correct horse battery staple")
check_true("hash_password produces a 'salt$hash' string", "$" in stored)
check_true("verify_password accepts the correct password", auth.verify_password("correct horse battery staple", stored))
check("verify_password rejects a wrong password", auth.verify_password("wrong password", stored), False)
check("verify_password rejects a malformed stored hash", auth.verify_password("anything", "not-a-valid-hash"), False)

os.environ["PANEL_PASSWORD_HASH"] = stored
check_true("verify_login accepts the correct password when PANEL_PASSWORD_HASH is set", auth.verify_login("correct horse battery staple"))
check("verify_login rejects a wrong password", auth.verify_login("wrong password"), False)

del os.environ["PANEL_PASSWORD_HASH"]
check("verify_login fails closed when PANEL_PASSWORD_HASH is unset", auth.verify_login("anything"), False)


# --- main.py: FastAPI app, login/logout ---
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)

resp = client.get("/login")
check("GET /login returns 200", resp.status_code, 200)

os.environ["PANEL_PASSWORD_HASH"] = auth.hash_password("test-password-123")

resp = client.post("/login", data={"password": "wrong-password"})
check("POST /login with wrong password returns 401", resp.status_code, 401)

resp = client.post("/login", data={"password": "test-password-123"})
check_true("POST /login with correct password redirects", resp.history and resp.history[0].status_code == 303)
check("POST /login with correct password ends up at /machines", str(resp.url).endswith("/machines"), True)

resp = client.get("/logout")
check("GET /logout redirects to /login", str(resp.url).endswith("/login"), True)


# --- main.py: /machines dashboard + rename ---
anon_client = TestClient(main.app)
resp = anon_client.get("/machines")
check("GET /machines without login redirects to /login", str(resp.url).endswith("/login"), True)

# `client` was logged out by the "GET /logout redirects to /login" check
# above -- log back in so the following requests carry a valid session.
client.post("/login", data={"password": "test-password-123"})

resp = client.get("/machines")
check("GET /machines with login returns 200", resp.status_code, 200)
check_true("GET /machines lists a known machine's serial", "ABC123" in resp.text)
check_true("GET /machines lists a known machine's name", "Loja 1" in resp.text)

resp = client.post("/machines/rename", data={"serial": "XYZ789", "name": "Loja 2 Final"})
check("POST /machines/rename redirects to /machines", str(resp.url).endswith("/machines"), True)
resp = client.get("/machines")
check_true("renamed machine's new name shows up on the dashboard", "Loja 2 Final" in resp.text)

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
