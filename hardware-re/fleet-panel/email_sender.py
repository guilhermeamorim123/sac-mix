"""
Sends the "new machine registered, approve it here" notification email via
plain SMTP (smtplib, stdlib -- no new dependency), matching this project's
preference for no new paid services (see
docs/superpowers/specs/2026-07-06-customer-registration-design.md). A Gmail
account with an app password is sufficient volume for this use case.

Environment variables (set in Render's dashboard for production, same as
the other secrets documented in README.md):
    SMTP_HOST      -- e.g. smtp.gmail.com
    SMTP_PORT      -- e.g. 587 (STARTTLS)
    SMTP_USER      -- the sending account's address
    SMTP_PASSWORD  -- an app password, not the account's real login password
    SMTP_FROM      -- the From: header value (usually same as SMTP_USER)
    OWNER_EMAIL    -- where registration notifications are sent (the owner,
                      not the customer)
"""
import os
import smtplib
from email.mime.text import MIMEText


def send_raw_email(to_address, subject, body):
    """Thin wrapper around smtplib so tests can monkeypatch this one
    function instead of needing a real SMTP server (same pattern as
    make_upstream_request in main.py being monkeypatched in selfcheck.py)."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    from_address = os.environ.get("SMTP_FROM", user)

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address

    # timeout=10 is required -- without it, a slow/unresponsive SMTP server
    # (or a network hiccup between this host and the SMTP host) hangs this
    # call forever. Since api_register calls this synchronously before
    # responding, an unbounded hang here blocks the ENTIRE registration
    # request until the platform's own edge proxy gives up (observed as a
    # bare 502 in production, with the registration itself silently lost
    # even though `register_machine` had already committed) -- exactly the
    # failure this bound is meant to prevent. The existing try/except in
    # api_register only catches raised exceptions, not a hang, so the
    # timeout has to be enforced here, not just handled there.
    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_address, [to_address], message.as_string())


def send_approval_email(to_address, machine_serial, customer_fields, approval_token, panel_base_url):
    """Sends the owner a one-tap approval link for a newly-registered
    machine. customer_fields is a dict with phone/company_name/email/
    contact_name, exactly as submitted through the registration endpoint."""
    approval_link = f"{panel_base_url}/approve/{approval_token}"
    subject = f"Nova máquina aguardando aprovação: {machine_serial}"
    body = (
        f"Uma nova máquina se registrou e está aguardando sua aprovação.\n\n"
        f"Serial: {machine_serial}\n"
        f"Empresa: {customer_fields['company_name']}\n"
        f"Contato: {customer_fields['contact_name']}\n"
        f"Telefone: {customer_fields['phone']}\n"
        f"Email: {customer_fields['email']}\n\n"
        f"Para liberar essa máquina, clique no link abaixo:\n{approval_link}\n"
    )
    send_raw_email(to_address, subject, body)
