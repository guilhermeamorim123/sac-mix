# Fleet Control Panel

Hosted dashboard listing every CUTTER_E326 machine onboarded via
`onboard.py`. See `docs/superpowers/specs/2026-07-02-fleet-panel-design.md`
for the full design.

## Live deployment — read this before changing anything

- **Live URL:** https://dragx-fleet-panel.onrender.com
- **Deployed from:** https://github.com/guilhermeamorim123/dragx-fleet-panel (private)

**This folder and that GitHub repo are NOT git-linked** — no submodule, no
shared remote, no shared history. They're two separate git repositories
that happen to contain the same panel code, kept in sync manually (copy
files, commit, push) whenever a change needs to reach production.

Why: this vault (where this folder lives) also contains unrelated
sensitive personal/business content that must never be pushed to GitHub.
A separate, isolated repo containing *only* the panel code
(`dragx-fleet-panel`) was created so the panel could be deployed to
Render/GitHub without exposing anything else in the vault.

**If you change `main.py` (or any other file here) and need it live**:
copy the changed file(s) into a checkout of the `dragx-fleet-panel` repo,
commit, and `git push` there. Render auto-deploys on push to that repo's
default branch. A commit here, in the vault, does **not** reach
production by itself.

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
| `OWNER_EMAIL` | Where registration-approval notifications are sent | Your own email address |
| `SMTP_HOST` | SMTP server hostname | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` (STARTTLS) |
| `SMTP_USER` | SMTP login username | Your sending account's address |
| `SMTP_PASSWORD` | SMTP login password | A Gmail **app password**, not your real password -- generate one at myaccount.google.com/apppasswords |
| `SMTP_FROM` | `From:` header value | Usually the same as `SMTP_USER` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | From the Twilio console dashboard |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | From the Twilio console dashboard |
| `TWILIO_WHATSAPP_FROM` | Sending WhatsApp number | `whatsapp:+14155238886` (Twilio's shared sandbox number) during the sandbox phase; a dedicated number once approved for production |
| `OWNER_WHATSAPP_TO` | Where WhatsApp registration-approval notifications are sent | Your own WhatsApp number, `whatsapp:+<countrycode><number>` format, e.g. `whatsapp:+5511999998888` |

## WhatsApp sandbox setup (one-time, per receiving phone number)

Twilio's WhatsApp sandbox requires the receiving phone to "join" once before it will accept messages:

1. In the Twilio console, open the WhatsApp sandbox page — it shows a phone number and a join keyword (e.g. "join `some-word`").
2. From the phone set as `OWNER_WHATSAPP_TO`, send that exact join message to that number on WhatsApp.
3. The sandbox session persists but can expire after a period of inactivity per Twilio's own rules — if notifications stop arriving, re-send the join message.

This is a manual, per-phone step outside this codebase — it cannot be automated from `main.py`. It only applies during the sandbox phase; a production WhatsApp sender number (after Twilio/Meta business verification) does not require this.

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
