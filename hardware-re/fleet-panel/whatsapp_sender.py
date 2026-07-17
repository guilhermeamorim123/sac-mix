"""
Sends the "new machine registered, approve it here" notification via
WhatsApp (Twilio's WhatsApp API) -- a second, independent channel
alongside email_sender.py, added because outbound SMTP appears to be
blocked at the network level in production (see
docs/superpowers/specs/2026-07-16-whatsapp-registration-notification-design.md).
Uses a raw HTTPS call via httpx (already a dependency of main.py)
instead of the twilio pip package, matching this project's preference
for no new dependencies (see email_sender.py's docstring).

Environment variables (set in Render's dashboard for production, same
as the other secrets documented in README.md):
    TWILIO_ACCOUNT_SID   -- Twilio account SID
    TWILIO_AUTH_TOKEN    -- Twilio auth token
    TWILIO_WHATSAPP_FROM -- sending number, "whatsapp:+14155238886" format
                            (Twilio's shared sandbox number during the
                            sandbox phase; a dedicated number in production)

OWNER_WHATSAPP_TO (who to notify) is read by main.py, not this module --
the recipient is always passed in as a parameter here, matching how
email_sender.py takes to_address as a parameter rather than reading
OWNER_EMAIL itself.
"""
import os

import httpx


def send_whatsapp_message(to, body):
    """Thin wrapper around the Twilio REST API so tests can monkeypatch
    this one function instead of needing real Twilio credentials (same
    pattern as email_sender.send_raw_email)."""
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_WHATSAPP_FROM"]

    response = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        auth=(account_sid, auth_token),
        data={"From": from_number, "To": to, "Body": body},
        timeout=10,
    )
    response.raise_for_status()


def send_registration_whatsapp(to_number, machine_serial, customer_fields, approval_token, panel_base_url):
    """Sends the owner a WhatsApp notification with a one-tap approval
    link for a newly-registered machine. customer_fields is a dict with
    phone/company_name/email/contact_name, exactly as submitted through
    the registration endpoint."""
    approval_link = f"{panel_base_url}/approve/{approval_token}"
    body = (
        f"Nova máquina aguardando aprovação: {machine_serial}\n\n"
        f"Empresa: {customer_fields['company_name']}\n"
        f"Contato: {customer_fields['contact_name']}\n"
        f"Telefone: {customer_fields['phone']}\n"
        f"Email: {customer_fields['email']}\n\n"
        f"Para liberar essa máquina, acesse:\n{approval_link}"
    )
    send_whatsapp_message(to_number, body)
