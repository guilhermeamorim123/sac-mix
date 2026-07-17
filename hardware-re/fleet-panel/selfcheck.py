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
import email_sender  # noqa: E402
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


# --- models.py: registration/approval fields and helpers ---
machine = models.checkin_machine(session, "REG-TEST-001", "V9.9.9.999")
check("a machine created via checkin_machine defaults to status=approved", machine.status, "approved")

machine = models.add_machine_manual(session, "REG-TEST-002", "Test Machine")
check("a machine created via add_machine_manual defaults to status=approved", machine.status, "approved")

registered = models.register_machine(
    session, serial="REG-TEST-003",
    phone="+55 11 99999-0000", company_name="Acme Corp",
    email="owner@acme.example", contact_name="Jane Doe",
)
check("register_machine sets status=pending", registered.status, "pending")
check("register_machine stores the phone", registered.phone, "+55 11 99999-0000")
check("register_machine stores the company_name", registered.company_name, "Acme Corp")
check("register_machine stores the email", registered.email, "owner@acme.example")
check("register_machine stores the contact_name", registered.contact_name, "Jane Doe")
check_true("register_machine generates a non-empty approval_token", bool(registered.approval_token))

# Captured into a plain variable (not read off `registered` after the fact)
# because SQLAlchemy's identity map returns the SAME Python object for both
# register_machine calls below (same session, same serial) -- `registered`
# and `reregistered` end up being the identical object, so comparing
# `reregistered.approval_token != registered.approval_token` after the
# second call would always be False regardless of whether a fresh token
# was actually generated.
original_token = registered.approval_token

reregistered = models.register_machine(
    session, serial="REG-TEST-003",
    phone="+55 11 88888-0000", company_name="Acme Corp v2",
    email="owner2@acme.example", contact_name="Jane Doe v2",
)
check("re-registering the same serial updates the row, not creates a second one",
      session.query(models.Machine).filter_by(serial="REG-TEST-003").count(), 1)
check("re-registering updates the phone", reregistered.phone, "+55 11 88888-0000")
check_true("re-registering generates a fresh approval_token",
           reregistered.approval_token != original_token)

status = models.get_machine_status(session, "REG-TEST-003")
check("get_machine_status returns the current status", status, "pending")

missing_status = models.get_machine_status(session, "REG-TEST-DOES-NOT-EXIST")
check("get_machine_status returns None for an unknown serial", missing_status, None)

# checkin_machine on an ALREADY-registered machine must not touch status
models.checkin_machine(session, "REG-TEST-003", "V9.9.9.999")
after_checkin = session.query(models.Machine).filter_by(serial="REG-TEST-003").one()
check("checkin_machine does not reset status back to approved on an existing pending machine",
      after_checkin.status, "pending")

approved_machine, was_already_approved = models.approve_machine_by_token(session, reregistered.approval_token)
check("approve_machine_by_token approves the right machine", approved_machine.serial, "REG-TEST-003")
check("approve_machine_by_token reports it was not already approved", was_already_approved, False)

approved_again, was_already_approved_2 = models.approve_machine_by_token(session, reregistered.approval_token)
check("approving an already-approved machine again is idempotent", approved_again.status, "approved")
check("approving an already-approved machine reports was_already_approved=True", was_already_approved_2, True)

bad_token_result = models.approve_machine_by_token(session, "this-token-does-not-exist")
check("approve_machine_by_token returns None for an unknown token", bad_token_result, None)

blocked = models.block_machine(session, approved_machine.id)
check("block_machine sets status=blocked", blocked.status, "blocked")

unblocked = models.unblock_machine(session, approved_machine.id)
check("unblock_machine sets status=approved", unblocked.status, "approved")

check("block_machine returns None for an unknown id", models.block_machine(session, 999999), None)
check("unblock_machine returns None for an unknown id", models.unblock_machine(session, 999999), None)


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


# --- main.py: catch-all proxy for everything else under /v1/ ---
# Uses a fake upstream (monkeypatched httpx call) instead of the real vendor
# host, so this test is hermetic and doesn't depend on network access or on
# cutter.skycut.cn being reachable during a test run.
class FakeUpstreamResponse:
    status_code = 200
    headers = {"content-type": "application/json"}
    content = b'{"fake": "upstream response"}'


def fake_proxy_request(method, url, **kwargs):
    fake_proxy_request.last_call = (method, url, kwargs)
    return FakeUpstreamResponse()


real_proxy_request = main.make_upstream_request
main.make_upstream_request = fake_proxy_request

resp = client.post("/v1/api/ver01/find_all_data", data={"type": "0"})
check("proxy forwards an unrelated /v1/ path and returns the upstream body", resp.json(), {"fake": "upstream response"})
check(
    "proxy calls the real vendor host with the same path",
    fake_proxy_request.last_call[1],
    "http://cutter.skycut.cn/v1/api/ver01/find_all_data",
)
check("proxy forwards the original HTTP method", fake_proxy_request.last_call[0], "POST")

main.make_upstream_request = real_proxy_request


# --- main.py: POST /api/machines/register ---
resp = client.post(
    "/api/machines/register",
    json={
        "serial": "REG-API-TEST-001",
        "phone": "+55 11 90000-0001",
        "company_name": "Acme API Corp",
        "email": "api-owner@acme.example",
        "contact_name": "API Jane",
    },
    headers={"X-Api-Key": os.environ["CHECKIN_API_KEY"]},
)
check("register endpoint returns 200", resp.status_code, 200)
check("register endpoint response is {'ok': True}", resp.json(), {"ok": True})

registered_row = session.query(models.Machine).filter_by(serial="REG-API-TEST-001").one()
check("register endpoint created a pending machine", registered_row.status, "pending")
check("register endpoint stored the email", registered_row.email, "api-owner@acme.example")

resp = client.post(
    "/api/machines/register",
    json={
        "serial": "REG-API-TEST-002",
        "phone": "+55 11 90000-0002",
        "company_name": "No Key Corp",
        "email": "nokey@acme.example",
        "contact_name": "No Key",
    },
    headers={"X-Api-Key": "wrong-key"},
)
check("register endpoint rejects a wrong API key", resp.status_code, 401)

resp = client.post(
    "/api/machines/register",
    json={"serial": "REG-API-TEST-003"},
    headers={"X-Api-Key": os.environ["CHECKIN_API_KEY"]},
)
check("register endpoint requires all four contact fields (422 on missing ones)", resp.status_code, 422)


# --- main.py: GET /api/machines/{serial}/status ---
resp = client.get(
    "/api/machines/REG-API-TEST-001/status",
    headers={"X-Api-Key": os.environ["CHECKIN_API_KEY"]},
)
check("status endpoint returns 200 for a registered machine", resp.status_code, 200)
check("status endpoint reports pending for a freshly-registered machine", resp.json(), {"status": "pending"})

resp = client.get(
    "/api/machines/REG-API-TEST-001/status",
    headers={"X-Api-Key": "wrong-key"},
)
check("status endpoint rejects a wrong API key", resp.status_code, 401)

resp = client.get(
    "/api/machines/DOES-NOT-EXIST-AT-ALL/status",
    headers={"X-Api-Key": os.environ["CHECKIN_API_KEY"]},
)
check("status endpoint returns 404 for an unknown serial", resp.status_code, 404)


# --- main.py: GET /approve/{approval_token} ---
pending_row = session.query(models.Machine).filter_by(serial="REG-API-TEST-001").one()
token = pending_row.approval_token

resp = client.get(f"/approve/{token}")
check("approve link returns 200 for a valid pending token", resp.status_code, 200)
check_true("approve link response mentions the machine is now released", "liberada" in resp.text.lower())

session.refresh(pending_row)
check("approve link actually sets status to approved", pending_row.status, "approved")

resp = client.get(f"/approve/{token}")
check("revisiting an already-used approve link still returns 200", resp.status_code, 200)
check_true("revisiting an already-used approve link says already approved, not an error",
           "já" in resp.text.lower() or "already" in resp.text.lower())

resp = client.get("/approve/this-token-does-not-exist-at-all")
check("an unknown approve token returns 200 with an informational page, not a 500", resp.status_code, 200)
check_true("an unknown approve token's page does not look like a raw error", "traceback" not in resp.text.lower())


os.environ["OWNER_EMAIL"] = "test-owner@example.com"

# --- email_sender.py: send_approval_email ---
sent_calls = []


def fake_send_email(to_address, subject, body):
    sent_calls.append((to_address, subject, body))


real_send_email = email_sender.send_raw_email
email_sender.send_raw_email = fake_send_email

email_sender.send_approval_email(
    to_address="notify-owner@acme.example",
    machine_serial="REG-EMAIL-TEST-001",
    customer_fields={
        "phone": "+55 11 90000-9999", "company_name": "Acme Email Corp",
        "email": "customer@acme.example", "contact_name": "Email Jane",
    },
    approval_token="fake-token-abc123",
    panel_base_url="https://dragx-fleet-panel.onrender.com",
)
check("send_approval_email sends exactly one email", len(sent_calls), 1)
check("send_approval_email sends to the right address", sent_calls[0][0], "notify-owner@acme.example")
check_true("send_approval_email's subject mentions the machine serial", "REG-EMAIL-TEST-001" in sent_calls[0][1])
check_true("send_approval_email's body includes the approval link",
           "https://dragx-fleet-panel.onrender.com/approve/fake-token-abc123" in sent_calls[0][2])
check_true("send_approval_email's body includes the company name", "Acme Email Corp" in sent_calls[0][2])

email_sender.send_raw_email = real_send_email

# --- main.py: register endpoint triggers the email, and survives failures ---
sent_calls.clear()
email_sender.send_raw_email = fake_send_email

resp = client.post(
    "/api/machines/register",
    json={
        "serial": "REG-EMAIL-TEST-002",
        "phone": "+55 11 90000-8888",
        "company_name": "Acme Email Corp 2",
        "email": "customer2@acme.example",
        "contact_name": "Email Jane 2",
    },
    headers={"X-Api-Key": os.environ["CHECKIN_API_KEY"]},
)
check("register endpoint still returns 200 when email succeeds", resp.status_code, 200)
check("register endpoint triggers exactly one email send", len(sent_calls), 1)

email_sender.send_raw_email = real_send_email


def broken_send_email(to_address, subject, body):
    raise RuntimeError("SMTP is down for this test")


email_sender.send_raw_email = broken_send_email

resp = client.post(
    "/api/machines/register",
    json={
        "serial": "REG-EMAIL-TEST-003",
        "phone": "+55 11 90000-7777",
        "company_name": "Acme Email Corp 3",
        "email": "customer3@acme.example",
        "contact_name": "Email Jane 3",
    },
    headers={"X-Api-Key": os.environ["CHECKIN_API_KEY"]},
)
check("register endpoint returns 200 even when the email send raises", resp.status_code, 200)
broken_row = session.query(models.Machine).filter_by(serial="REG-EMAIL-TEST-003").one()
check("the machine is still created as pending even when the email send fails", broken_row.status, "pending")

email_sender.send_raw_email = real_send_email


# --- main.py: POST /machines/{id}/block and /machines/{id}/unblock ---
# REG-EMAIL-TEST-002 was created above via POST /api/machines/register,
# which (per models.register_machine) always sets status="pending", never
# "approved" -- so it is NOT yet approved at this point. Approve it first
# via the same helper the /approve/{token} route uses, giving us a
# genuinely-approved machine to exercise block/unblock against.
email_test_002 = session.query(models.Machine).filter_by(serial="REG-EMAIL-TEST-002").one()
models.approve_machine_by_token(session, email_test_002.approval_token)

approved_row = session.query(models.Machine).filter_by(serial="REG-EMAIL-TEST-002").one()
check("machine starts approved before the block/unblock test", approved_row.status, "approved")

resp = client.post(f"/machines/{approved_row.id}/block", follow_redirects=False)
check("block redirects back to /machines", resp.status_code, 303)
session.refresh(approved_row)
check("block sets status to blocked", approved_row.status, "blocked")

resp = client.post(f"/machines/{approved_row.id}/unblock", follow_redirects=False)
check("unblock redirects back to /machines", resp.status_code, 303)
session.refresh(approved_row)
check("unblock sets status back to approved", approved_row.status, "approved")

resp = client.post("/machines/999999/block", follow_redirects=False)
check("blocking an unknown machine id still redirects harmlessly", resp.status_code, 303)

resp = client.get("/machines")
check_true("the machines dashboard renders the current status", "approved" in resp.text or "blocked" in resp.text)


# --- models.py: list_registered_machines ---
never_registered = models.checkin_machine(session, "EMUSO-TEST-NOREG", "V9.9.9.999")
registered_pending = models.register_machine(
    session, serial="EMUSO-TEST-001",
    phone="+55 11 90000-1111", company_name="Em Uso Corp",
    email="emuso@acme.example", contact_name="Em Uso Jane",
)

registered_list = models.list_registered_machines(session)
registered_serials = [m.serial for m in registered_list]
check_true("list_registered_machines includes a machine that went through registration",
           "EMUSO-TEST-001" in registered_serials)
check_true("list_registered_machines excludes a machine that only ever checked in normally",
           "EMUSO-TEST-NOREG" not in registered_serials)

# --- main.py: GET /machines/em-uso shows registered customer details ---
resp = anon_client.get("/machines/em-uso")
check("GET /machines/em-uso without login still redirects to /login", str(resp.url).endswith("/login"), True)

resp = client.get("/machines/em-uso")
check("GET /machines/em-uso with login returns 200", resp.status_code, 200)
check_true("machines_em_uso lists a registered machine's serial", "EMUSO-TEST-001" in resp.text)
check_true("machines_em_uso lists a registered machine's company name", "Em Uso Corp" in resp.text)
check_true("machines_em_uso lists a registered machine's contact name", "Em Uso Jane" in resp.text)
check_true("machines_em_uso lists a registered machine's status", "pending" in resp.text)
check_true("machines_em_uso does not list a machine that never registered", "EMUSO-TEST-NOREG" not in resp.text)


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
