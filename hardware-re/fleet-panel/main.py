"""
Fleet Control Panel -- FastAPI app. Serves both the /api/machines/checkin
endpoint (called by onboard.py) and the dashboard pages (server-rendered,
Jinja2). See docs/superpowers/specs/2026-07-02-fleet-panel-design.md.

Run locally: uvicorn main:app --reload
"""
import os

from fastapi import Depends, FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from auth import verify_login
from db import get_engine, get_session_factory
from models import list_machines, rename_machine

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
