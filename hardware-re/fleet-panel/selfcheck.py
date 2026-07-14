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


# --- DragxRelease: get_latest_release / set_latest_release ---
check("get_latest_release returns None before any publish", models.get_latest_release(session), None)

release1 = models.set_latest_release(
    session, version_code=706, version_name="V7.0.3.006",
    download_url="https://example.com/dragx-706.apk", file_md5="abc123",
)
check("set_latest_release returns the created row", release1.version_code, 706)
check("set_latest_release sets version_name", release1.version_name, "V7.0.3.006")
check("set_latest_release sets download_url", release1.download_url, "https://example.com/dragx-706.apk")
check("set_latest_release sets file_md5", release1.file_md5, "abc123")

fetched = models.get_latest_release(session)
check("get_latest_release returns the published release", fetched.version_code, 706)

release2 = models.set_latest_release(
    session, version_code=707, version_name="V7.0.3.007",
    download_url="https://example.com/dragx-707.apk", file_md5="def456",
)
check("set_latest_release on a repeat call updates version_code", release2.version_code, 707)
all_releases = session.query(models.DragxRelease).all()
check("set_latest_release never creates a second row", len(all_releases), 1)


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

# base_url must be https:// -- main.py's SessionMiddleware now sets
# https_only=True (Secure cookie flag), and httpx's cookie jar (used
# internally by TestClient) won't send a Secure-flagged cookie back on a
# plain http:// request, which would otherwise silently break every
# login-session check below.
client = TestClient(main.app, base_url="https://testserver")

resp = client.get("/")
check("GET / redirects to /login", str(resp.url).endswith("/login"), True)

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
anon_client = TestClient(main.app, base_url="https://testserver")
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


# --- main.py: /machines/em-uso placeholder ---
resp = anon_client.get("/machines/em-uso")
check("GET /machines/em-uso without login redirects to /login", str(resp.url).endswith("/login"), True)

resp = client.get("/machines/em-uso")
check("GET /machines/em-uso with login returns 200", resp.status_code, 200)
check_true("GET /machines/em-uso shows the 'em breve' message", "em breve" in resp.text.lower())


# --- main.py: /machines/add ---
resp = anon_client.get("/machines/add")
check("GET /machines/add without login redirects to /login", str(resp.url).endswith("/login"), True)

resp = client.get("/machines/add")
check("GET /machines/add with login returns 200", resp.status_code, 200)

resp = client.post("/machines/add", data={"serial": "MANUAL-001", "name": "Máquina Antiga"})
check("POST /machines/add redirects to /machines", str(resp.url).endswith("/machines"), True)
check_true("manually-added machine shows up on the dashboard", "MANUAL-001" in resp.text and "Máquina Antiga" in resp.text)

resp = client.post("/machines/add", data={"serial": "  PADDED-001  ", "name": "Loja Nova"})
check("POST /machines/add with whitespace-padded serial redirects to /machines", str(resp.url).endswith("/machines"), True)
padded_rows = session.query(models.Machine).filter_by(serial="PADDED-001").all()
check("whitespace-padded serial is normalized before storage (no surrounding whitespace)", len(padded_rows), 1)


# --- main.py: /api/machines/checkin ---
resp = client.post("/api/machines/checkin", json={"serial": "API-001", "dragx_version": "V7.0.3.005"})
check("POST /api/machines/checkin without API key returns 401", resp.status_code, 401)

os.environ["CHECKIN_API_KEY"] = "test-api-key-xyz"
resp = client.post(
    "/api/machines/checkin",
    json={"serial": "API-001", "dragx_version": "V7.0.3.005"},
    headers={"X-Api-Key": "wrong-key"},
)
check("POST /api/machines/checkin with wrong API key returns 401", resp.status_code, 401)

resp = client.post(
    "/api/machines/checkin",
    json={"serial": "API-001", "dragx_version": "V7.0.3.005"},
    headers={"X-Api-Key": "test-api-key-xyz"},
)
check("POST /api/machines/checkin with correct API key returns 200", resp.status_code, 200)
check("POST /api/machines/checkin response body", resp.json(), {"ok": True})

resp = client.get("/machines")
check_true("machine registered via checkin API shows up on the dashboard", "API-001" in resp.text)

resp = client.post(
    "/api/machines/checkin",
    json={"serial": "API-001", "dragx_version": "V7.0.4.000"},
    headers={"X-Api-Key": "test-api-key-xyz"},
)
check("repeat checkin for the same serial still returns 200", resp.status_code, 200)
resp = client.get("/machines")
check_true("repeat checkin updates dragx_version on the dashboard", "V7.0.4.000" in resp.text)

resp = client.post(
    "/api/machines/checkin",
    json={"dragx_version": "V7.0.3.005"},
    headers={"X-Api-Key": "test-api-key-xyz"},
)
check("POST /api/machines/checkin without 'serial' returns 422 (Pydantic validation)", resp.status_code, 422)


# Reset the singleton release row so app_upgrade's "no release published"
# path can be genuinely exercised here -- the earlier DragxRelease section
# left a real release (version_code=707) published, and that's a shared
# row for the whole selfcheck.py run.
session.query(models.DragxRelease).delete()
session.commit()

# --- main.py: POST /v1/api/ver01/app_upgrade ---
resp = client.post("/v1/api/ver01/app_upgrade", data={"appVersion": "1"})
check("app_upgrade with no release published returns code 200", resp.json()["code"], 200)
check_true("app_upgrade with no release published has no bussData", "bussData" not in resp.json().get("data", {}))

models.set_latest_release(
    session, version_code=706, version_name="V7.0.3.006",
    download_url="https://example.com/dragx-706.apk", file_md5="abc123",
)

resp = client.post("/v1/api/ver01/app_upgrade", data={"appVersion": "705"})
body = resp.json()
check("app_upgrade with an older installed version returns code 200", body["code"], 200)
check("app_upgrade reports the new version_code as appVersion", body["data"]["bussData"][0]["appVersion"], 706)
check("app_upgrade reports the new appVersionName", body["data"]["bussData"][0]["appVersionName"], "V7.0.3.006")
check("app_upgrade reports the download URL as appFilePath", body["data"]["bussData"][0]["appFilePath"], "https://example.com/dragx-706.apk")
check("app_upgrade reports the MD5 as appFileMd5", body["data"]["bussData"][0]["appFileMd5"], "abc123")

resp = client.post("/v1/api/ver01/app_upgrade", data={"appVersion": "706"})
check_true("app_upgrade with the current version already installed has no bussData", "bussData" not in resp.json().get("data", {}))

resp = client.post("/v1/api/ver01/app_upgrade", data={"appVersion": "999"})
check_true("app_upgrade with a NEWER-than-published version installed has no bussData", "bussData" not in resp.json().get("data", {}))

resp = client.post("/v1/api/ver01/app_upgrade", data={})
check_true("app_upgrade with a missing appVersion field does not error (treated as 0)", resp.status_code == 200)


# --- main.py: friendly error page when the DB is unreachable ---
# Design spec (docs/superpowers/specs/2026-07-02-fleet-panel-design.md,
# "Error handling"): dashboard pages must show a clear message instead of a
# raw stack trace/500 if the DB is unreachable. Simulating a real DB outage
# would mean intentionally breaking the SQLite connection this whole test
# run depends on -- instead, monkeypatch the DB-reading function each route
# calls to raise sqlalchemy.exc.SQLAlchemyError directly, which exercises
# the actual registered exception handler (main.db_error_handler) through
# FastAPI's real dispatch mechanics, not just a direct unit call.
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

real_list_machines = main.list_machines
main.list_machines = lambda db_session: (_ for _ in ()).throw(SQLAlchemyError("simulated DB outage"))
resp = client.get("/machines")
check("GET /machines returns 503 when the DB raises SQLAlchemyError", resp.status_code, 503)
check_true(
    "GET /machines shows the spec's friendly error message on DB failure",
    "não consegui carregar os dados agora, tente de novo" in resp.text,
)
main.list_machines = real_list_machines

# Confirm the dashboard is healthy again once the DB is "back" -- guards
# against the monkeypatch leaking into later checks.
resp = client.get("/machines")
check("GET /machines returns 200 again after the DB recovers", resp.status_code, 200)

real_checkin_machine = main.checkin_machine
main.checkin_machine = lambda db_session, serial, dragx_version: (_ for _ in ()).throw(
    SQLAlchemyError("simulated DB outage")
)
resp = client.post(
    "/api/machines/checkin",
    json={"serial": "API-002", "dragx_version": "V7.0.3.005"},
    headers={"X-Api-Key": "test-api-key-xyz"},
)
check("POST /api/machines/checkin returns 503 when the DB raises SQLAlchemyError", resp.status_code, 503)
check_true(
    "POST /api/machines/checkin returns JSON (not the HTML error page) on DB failure",
    resp.headers["content-type"].startswith("application/json") and "<html" not in resp.text.lower(),
)
check_true("POST /api/machines/checkin's JSON error body has a 'detail' field", bool(resp.json().get("detail")))
main.checkin_machine = real_checkin_machine

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
