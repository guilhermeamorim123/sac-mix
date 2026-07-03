"""
Fleet Control Panel -- FastAPI app. Serves both the /api/machines/checkin
endpoint (called by onboard.py) and the dashboard pages (server-rendered,
Jinja2). See docs/superpowers/specs/2026-07-02-fleet-panel-design.md.

Run locally: uvicorn main:app --reload
"""
import os

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
def machines_list(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db_session = SessionLocal()
    try:
        machines = list_machines(db_session)
    finally:
        db_session.close()
    return templates.TemplateResponse(request, "machines.html", {"machines": machines})


@app.post("/machines/rename")
def machines_rename(request: Request, serial: str = Form(...), name: str = Form(...)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    db_session = SessionLocal()
    try:
        # rename_machine returns None if serial doesn't exist -- a harmless
        # no-op by design, since this form always submits a serial that was
        # just rendered from a real row on the dashboard.
        rename_machine(db_session, serial, name)
    finally:
        db_session.close()
    return RedirectResponse("/machines", status_code=303)
