# Fleet Control Panel

Hosted dashboard listing every CUTTER_E326 machine onboarded via
`onboard.py`. See `docs/superpowers/specs/2026-07-02-fleet-panel-design.md`
for the full design.

## Running locally

```bash
pip install -r requirements.txt
python generate_password_hash.py   # prints a PANEL_PASSWORD_HASH value
export PANEL_PASSWORD_HASH="<paste the value here>"
export CHECKIN_API_KEY="any-random-string-for-local-testing"
export SESSION_SECRET="any-random-string-for-local-testing"
uvicorn main:app --reload
```

Open http://localhost:8000/login.

## Environment variables (set these in Render's dashboard for production)

| Variable | Purpose | How to generate |
|---|---|---|
| `DATABASE_URL` | Postgres connection string | From Neon.tech's dashboard, after creating a project |
| `PANEL_PASSWORD_HASH` | Login password (hashed, never plaintext) | `python generate_password_hash.py` |
| `CHECKIN_API_KEY` | Shared secret onboard.py uses to register machines | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SESSION_SECRET` | Signs the login session cookie | `python -c "import secrets; print(secrets.token_hex(32))"` |

## Deploying to Render

1. Push this repo to GitHub (or connect Render directly to it if already there).
2. In Render: New > Web Service > connect this repo, root directory `hardware-re/fleet-panel`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Set the four environment variables above under the service's "Environment" tab.
6. Deploy. Render gives you a URL like `https://<name>.onrender.com`.

## Wiring onboard.py to this panel

On the PC that runs `onboard.py`, set two more environment variables:

```bash
export PANEL_URL="https://<name>.onrender.com"
export PANEL_API_KEY="<same value as CHECKIN_API_KEY above>"
```

Every future `onboard.py` run will now register the machine automatically.
