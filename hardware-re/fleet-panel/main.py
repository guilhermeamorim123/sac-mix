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

_HERE = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-only-secret-change-me"))
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
