"""
Fleet Control Panel -- FastAPI app. Serves both the /api/machines/checkin
endpoint (called by onboard.py) and the dashboard pages (server-rendered,
Jinja2). See docs/superpowers/specs/2026-07-02-fleet-panel-design.md.

Run locally: uvicorn main:app --reload
"""
import hmac
import logging
import os
import threading

from fastapi import Depends, FastAPI, Request, Form, Header, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, Response
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

import email_sender
import whatsapp_sender
from auth import verify_login
from db import get_engine, get_session_factory
from models import (
    add_machine_manual,
    approve_machine_by_token,
    block_machine,
    checkin_machine,
    get_latest_release,
    get_machine_by_token,
    get_machine_status,
    list_machines,
    list_registered_machines,
    register_machine,
    rename_machine,
    report_cut,
    set_cut_balance,
    unblock_machine,
)

_HERE = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)

SESSION_SECRET = os.environ["SESSION_SECRET"]

app = FastAPI()
# https_only=True is required for the `Secure` cookie flag -- Starlette's
# SessionMiddleware does not set it by default even though this app is only
# ever served over HTTPS on Render. Without it, the session cookie could in
# principle be sent over a plaintext connection.
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, https_only=True)
app.mount("/static", StaticFiles(directory=os.path.join(_HERE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(_HERE, "templates"))

engine = get_engine()
SessionLocal = get_session_factory(engine)


def get_db():
    """Yield-based DB session dependency: opens a session per request and
    guarantees it's closed afterward, regardless of route outcome."""
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


class NotLoggedIn(Exception):
    """Raised by require_login when there's no active session. Converted
    into a redirect to /login by the exception handler below, so routes
    that depend on require_login don't need to handle it themselves."""


def require_login(request: Request):
    if not request.session.get("logged_in"):
        raise NotLoggedIn()


@app.exception_handler(NotLoggedIn)
def not_logged_in_handler(request: Request, exc: NotLoggedIn):
    return RedirectResponse("/login", status_code=303)


# Design spec (docs/superpowers/specs/2026-07-02-fleet-panel-design.md,
# "Error handling"): if the panel's own database is unreachable, dashboard
# pages must show a clear message instead of a raw stack trace/500. This
# catches SQLAlchemyError -- the base class covering connection failures
# and most other DB-layer errors -- wherever it's raised from a route.
# `/api/*` is a JSON API, not a dashboard page, so it gets a clean JSON
# error instead of the HTML page.
DB_ERROR_MESSAGE = "não consegui carregar os dados agora, tente de novo"


@app.exception_handler(SQLAlchemyError)
def db_error_handler(request: Request, exc: SQLAlchemyError):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": DB_ERROR_MESSAGE}, status_code=503)
    return HTMLResponse(
        f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Erro</title></head>"
        f"<body><p>{DB_ERROR_MESSAGE}</p></body></html>",
        status_code=503,
    )


@app.get("/")
def root():
    # No real content lives at the bare root -- this exists so a bare GET /
    # (which is what Render's own health check, and anyone who visits the
    # domain without a path, sends) gets a clean redirect instead of a 404.
    # A 404 here was making Render's health check consider the service
    # unhealthy and repeatedly cycle the instance.
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    if verify_login(password):
        request.session["logged_in"] = True
        return RedirectResponse("/machines", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"error": "Senha incorreta."}, status_code=401
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/machines", response_class=HTMLResponse)
def machines_list(
    request: Request,
    db_session: Session = Depends(get_db),
    _: None = Depends(require_login),
):
    machines = list_machines(db_session)
    return templates.TemplateResponse(request, "machines.html", {"machines": machines})


@app.post("/machines/rename")
def machines_rename(
    serial: str = Form(...),
    name: str = Form(...),
    db_session: Session = Depends(get_db),
    _: None = Depends(require_login),
):
    # rename_machine returns None if serial doesn't exist -- a harmless
    # no-op by design, since this form always submits a serial that was
    # just rendered from a real row on the dashboard.
    rename_machine(db_session, serial, name)
    return RedirectResponse("/machines", status_code=303)


@app.post("/machines/set-balance")
def machines_set_balance(
    serial: str = Form(...),
    balance: int = Form(..., ge=0),
    db_session: Session = Depends(get_db),
    _: None = Depends(require_login),
):
    # set_cut_balance returns None if serial doesn't exist -- a harmless
    # no-op by design, same reasoning as machines_rename's handling above.
    # balance's ge=0 constraint rejects negative values with a 422 before
    # this function body even runs.
    set_cut_balance(db_session, serial, balance)
    return RedirectResponse("/machines/em-uso", status_code=303)


@app.post("/machines/{machine_id}/block")
def machines_block(machine_id: int, db_session: Session = Depends(get_db), _: None = Depends(require_login)):
    # block_machine returns None for an unknown id -- harmless no-op, same
    # reasoning as rename_machine's None-return handling above.
    block_machine(db_session, machine_id)
    return RedirectResponse("/machines", status_code=303)


@app.post("/machines/{machine_id}/unblock")
def machines_unblock(machine_id: int, db_session: Session = Depends(get_db), _: None = Depends(require_login)):
    unblock_machine(db_session, machine_id)
    return RedirectResponse("/machines", status_code=303)


@app.get("/machines/em-uso", response_class=HTMLResponse)
def machines_em_uso(request: Request, db_session: Session = Depends(get_db), _: None = Depends(require_login)):
    machines = list_registered_machines(db_session)
    return templates.TemplateResponse(request, "machines_em_uso.html", {"machines": machines})


@app.get("/machines/add", response_class=HTMLResponse)
def add_machine_form(request: Request, _: None = Depends(require_login)):
    return templates.TemplateResponse(request, "add_machine.html", {})


@app.post("/machines/add")
def add_machine_submit(
    serial: str = Form(...),
    name: str = Form(None),
    db_session: Session = Depends(get_db),
    _: None = Depends(require_login),
):
    # Strip stray whitespace (e.g. from copy-pasting a serial out of a
    # terminal) before it can ever reach the DB -- a future real device
    # check-in matches on an exact `filter_by(serial=serial)`, so an
    # untrimmed serial here would silently create an orphaned duplicate
    # row that never receives that device's future updates.
    serial = serial.strip()
    name = name.strip() if name else name
    if not serial:
        # Whitespace-only (or otherwise empty-after-strip) serial is a
        # clearly-invalid submission from the single operator who uses
        # this form -- silently decline rather than adding a full
        # error-display system for a one-user internal tool.
        return RedirectResponse("/machines/add", status_code=303)

    # If this serial already exists and `name` is submitted blank, this
    # intentionally clears the existing name (latest submission wins) --
    # this form is a manual, deliberate operator action, not an automated
    # process, so overwriting on resubmission is acceptable/expected. We
    # pass None (not "") so the DB stores a real NULL, matching the
    # column's nullable=True intent.
    add_machine_manual(db_session, serial, name or None)
    return RedirectResponse("/machines", status_code=303)


class CheckinPayload(BaseModel):
    serial: str
    dragx_version: str | None = None


@app.post("/api/machines/checkin")
def api_checkin(payload: CheckinPayload, db_session: Session = Depends(get_db), x_api_key: str = Header(None)):
    expected_key = os.environ.get("CHECKIN_API_KEY")
    if not expected_key or not hmac.compare_digest(x_api_key or "", expected_key):
        raise HTTPException(status_code=401, detail="chave de API inválida ou ausente")
    # Pydantic's `serial: str` (no default) already rejects a request
    # where 'serial' is missing entirely (422, before we get here) -- but
    # it does NOT reject an empty string, since "" is a valid str. Keep
    # this check for that case, matching the pre-Pydantic behavior.
    if not payload.serial:
        raise HTTPException(status_code=400, detail="'serial' é obrigatório")
    checkin_machine(db_session, payload.serial, payload.dragx_version)
    return {"ok": True}


class RegisterPayload(BaseModel):
    serial: str
    phone: str
    company_name: str
    email: str
    contact_name: str


@app.post("/api/machines/register")
def api_register(payload: RegisterPayload, request: Request, db_session: Session = Depends(get_db), x_api_key: str = Header(None)):
    expected_key = os.environ.get("CHECKIN_API_KEY")
    if not expected_key or not hmac.compare_digest(x_api_key or "", expected_key):
        raise HTTPException(status_code=401, detail="chave de API inválida ou ausente")
    machine = register_machine(
        db_session,
        serial=payload.serial,
        phone=payload.phone,
        company_name=payload.company_name,
        email=payload.email,
        contact_name=payload.contact_name,
    )
    customer_fields = {
        "phone": payload.phone,
        "company_name": payload.company_name,
        "email": payload.email,
        "contact_name": payload.contact_name,
    }
    panel_base_url = str(request.base_url).rstrip("/")

    owner_email = os.environ.get("OWNER_EMAIL")
    if owner_email:
        def _send_email_in_background(serial, customer_fields, approval_token, panel_base_url):
            # Runs on a daemon thread, fully detached from this request.
            # A bounded socket timeout (see email_sender.send_raw_email)
            # only protects against a *slow* SMTP server -- it does nothing
            # for a network that silently drops the connection at a lower
            # layer than Python's socket timeout can observe (seen in
            # production: registration requests hung past 30s and came
            # back as a bare 502 from the platform's own edge proxy, with
            # this call still blocking the request the whole time). Moving
            # the send off the request thread entirely is what actually
            # satisfies the design doc's "never blocks the registration
            # itself succeeding" requirement -- a hang here now only ever
            # delays the notification email, never the API response.
            try:
                email_sender.send_approval_email(
                    to_address=owner_email,
                    machine_serial=serial,
                    customer_fields=customer_fields,
                    approval_token=approval_token,
                    panel_base_url=panel_base_url,
                )
            except Exception:
                logger.exception("failed to send registration approval email for %s", serial)

        threading.Thread(
            target=_send_email_in_background,
            args=(machine.serial, customer_fields, machine.approval_token, panel_base_url),
            daemon=True,
        ).start()

    owner_whatsapp_to = os.environ.get("OWNER_WHATSAPP_TO")
    twilio_configured = bool(
        owner_whatsapp_to
        and os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("TWILIO_WHATSAPP_FROM")
    )
    if twilio_configured:
        def _send_whatsapp_in_background(to_number, serial, customer_fields, approval_token, panel_base_url):
            # Same rationale as _send_email_in_background above: runs on
            # its own detached daemon thread so a slow or unreachable
            # Twilio API call can never block or delay the registration
            # response. This thread is independent from the email one --
            # one channel hanging or failing never affects the other.
            try:
                whatsapp_sender.send_registration_whatsapp(
                    to_number=to_number,
                    machine_serial=serial,
                    customer_fields=customer_fields,
                    approval_token=approval_token,
                    panel_base_url=panel_base_url,
                )
            except Exception:
                logger.exception("failed to send registration whatsapp notification for %s", serial)

        threading.Thread(
            target=_send_whatsapp_in_background,
            args=(owner_whatsapp_to, machine.serial, customer_fields, machine.approval_token, panel_base_url),
            daemon=True,
        ).start()

    return {"ok": True}


@app.get("/api/machines/{serial}/status")
def api_machine_status(serial: str, db_session: Session = Depends(get_db), x_api_key: str = Header(None)):
    expected_key = os.environ.get("CHECKIN_API_KEY")
    if not expected_key or not hmac.compare_digest(x_api_key or "", expected_key):
        raise HTTPException(status_code=401, detail="chave de API inválida ou ausente")
    status = get_machine_status(db_session, serial)
    if status is None:
        raise HTTPException(status_code=404, detail="máquina não encontrada")
    return {"status": status}


@app.get("/approve/{approval_token}", response_class=HTMLResponse)
def approve_machine_confirm(approval_token: str, request: Request, db_session: Session = Depends(get_db)):
    # Deliberately read-only: messaging apps (WhatsApp, email clients) often
    # fetch links automatically to build a preview, and a GET that mutated
    # state here would let that automated fetch silently approve the
    # machine before a human ever saw the message. The actual approval only
    # happens in the POST handler below, triggered by a real button click.
    machine = get_machine_by_token(db_session, approval_token)
    if machine is None:
        return templates.TemplateResponse(request, "approve.html", {"result": "not_found", "serial": None})
    if machine.status == "approved":
        return templates.TemplateResponse(request, "approve.html", {"result": "already_approved", "serial": machine.serial})
    return templates.TemplateResponse(
        request,
        "approve.html",
        {
            "result": "confirm",
            "serial": machine.serial,
            "company_name": machine.company_name,
            "contact_name": machine.contact_name,
            "approval_token": approval_token,
        },
    )


@app.post("/approve/{approval_token}", response_class=HTMLResponse)
def approve_machine(approval_token: str, request: Request, db_session: Session = Depends(get_db)):
    result = approve_machine_by_token(db_session, approval_token)
    if result is None:
        return templates.TemplateResponse(request, "approve.html", {"result": "not_found", "serial": None})
    machine, was_already_approved = result
    return templates.TemplateResponse(
        request,
        "approve.html",
        {"result": "already_approved" if was_already_approved else "approved", "serial": machine.serial},
    )


@app.post("/api/machines/{serial}/cut")
def api_report_cut(serial: str, request: Request, db_session: Session = Depends(get_db), x_api_key: str = Header(None)):
    expected_key = os.environ.get("CHECKIN_API_KEY")
    if not expected_key or not hmac.compare_digest(x_api_key or "", expected_key):
        raise HTTPException(status_code=401, detail="chave de API inválida ou ausente")
    machine, was_replenished = report_cut(db_session, serial)
    if was_replenished:
        owner_whatsapp_to = os.environ.get("OWNER_WHATSAPP_TO")
        twilio_configured = bool(
            owner_whatsapp_to
            and os.environ.get("TWILIO_ACCOUNT_SID")
            and os.environ.get("TWILIO_AUTH_TOKEN")
            and os.environ.get("TWILIO_WHATSAPP_FROM")
        )
        if twilio_configured:
            def _send_replenish_whatsapp_in_background(to_number, serial):
                # Same rationale as the registration/WhatsApp background
                # threads elsewhere in this file: runs detached so a slow
                # or unreachable Twilio API call can never delay this
                # endpoint's response to the machine.
                try:
                    whatsapp_sender.send_balance_replenished_whatsapp(
                        to_number=to_number,
                        machine_serial=serial,
                    )
                except Exception:
                    logger.exception("failed to send balance-replenished whatsapp notification for %s", serial)

            threading.Thread(
                target=_send_replenish_whatsapp_in_background,
                args=(owner_whatsapp_to, machine.serial),
                daemon=True,
            ).start()
    return {"ok": True}


@app.post("/v1/api/ver01/app_upgrade")
def dragx_app_upgrade(appVersion: str = Form("0"), db_session: Session = Depends(get_db)):
    # Malformed/missing appVersion is treated as 0 -- always "no update",
    # never accidentally treated as "everyone should update" (see design
    # doc's Error handling section).
    try:
        installed_version = int(appVersion)
    except ValueError:
        installed_version = 0

    release = get_latest_release(db_session)
    if release is None or release.version_code <= installed_version:
        # Matches the exact shape captured from a real request against the
        # live vendor server on 2026-07-07 -- no "bussData" key at all.
        return {"code": 200, "status": "success", "data": {"sysDt": 0, "resultCode": 200}}

    return {
        "code": 200,
        "status": "success",
        "data": {
            "bussData": [
                {
                    "appVersion": release.version_code,
                    "appVersionName": release.version_name,
                    "appFilePath": release.download_url,
                    "appFileMd5": release.file_md5,
                    "appFileName": "dragx.apk",
                    "appContent": "",
                    "binVersion": "",
                    "binFilePath": "",
                    "binFileMd5": "",
                    "binFileName": "",
                    "binContent": "",
                    "title": "",
                    "type": "",
                }
            ],
            "errMsg": None,
            "resultCode": 200,
            "sysDt": 0,
        },
    }


VENDOR_BASE_URL = "http://cutter.skycut.cn/v1"


def make_upstream_request(method, url, **kwargs):
    """Thin wrapper around httpx so tests can monkeypatch it (same pattern
    as _post_json in onboard.py and run_adb in dragx-web-deployer/server.py
    being monkeypatched in their respective selfchecks), instead of making a
    real network call to the vendor's server in every test run."""
    return httpx.request(method, url, **kwargs)


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def dragx_vendor_proxy(path: str, request: Request):
    # Transparent passthrough for every /v1/ path except app_upgrade (which
    # has its own route registered above and never reaches this catch-all).
    # This exists purely so find_all_data/user_themes keep working once the
    # app's .b() client is redirected here -- see design doc.
    upstream_url = f"{VENDOR_BASE_URL}/{path}"
    body = await request.body()
    upstream_response = make_upstream_request(
        request.method,
        upstream_url,
        params=request.query_params,
        content=body,
        headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")},
    )
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers={"content-type": upstream_response.headers.get("content-type", "application/octet-stream")},
    )
