"""
Fleet Control Panel -- FastAPI app. Serves both the /api/machines/checkin
endpoint (called by onboard.py) and the dashboard pages (server-rendered,
Jinja2). See docs/superpowers/specs/2026-07-02-fleet-panel-design.md.

Run locally: uvicorn main:app --reload
"""
import os

from fastapi import Depends, FastAPI, Request, Form, Header, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from auth import verify_login
from db import get_engine, get_session_factory
from models import add_machine_manual, checkin_machine, list_machines, rename_machine

_HERE = os.path.dirname(os.path.abspath(__file__))

SESSION_SECRET = os.environ["SESSION_SECRET"]

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
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


@app.get("/machines/em-uso", response_class=HTMLResponse)
def machines_em_uso(request: Request, _: None = Depends(require_login)):
    return templates.TemplateResponse(request, "machines_em_uso.html", {})


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


@app.post("/api/machines/checkin")
def api_checkin(payload: dict, db_session: Session = Depends(get_db), x_api_key: str = Header(None)):
    expected_key = os.environ.get("CHECKIN_API_KEY")
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="chave de API inválida ou ausente")
    serial = payload.get("serial")
    dragx_version = payload.get("dragx_version")
    if not serial:
        raise HTTPException(status_code=400, detail="'serial' é obrigatório")
    checkin_machine(db_session, serial, dragx_version)
    return {"ok": True}
