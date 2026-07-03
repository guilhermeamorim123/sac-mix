"""
Simple single-password auth for the fleet panel. The panel password is
never stored in plaintext -- PANEL_PASSWORD_HASH (a salted PBKDF2 hash,
generated once via generate_password_hash.py) is set as a Render
environment variable. No user accounts, no multi-tenancy -- this is a
single-operator tool.
"""
import hashlib
import hmac
import os
import secrets

PBKDF2_ITERATIONS = 600_000


def hash_password(password, salt=None):
    """Returns 'salt$hash' (both hex-encoded). Generates a fresh salt if
    none is given -- used once, offline, to generate PANEL_PASSWORD_HASH."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored_hash):
    """Returns True if password matches stored_hash ('salt$hash' format).
    Uses constant-time comparison to avoid timing attacks. Returns False
    (not an error) for a malformed stored_hash."""
    try:
        salt, expected_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected_hex)


def verify_login(password):
    """Checks password against the PANEL_PASSWORD_HASH environment
    variable. Returns False (not an error) if the env var isn't set --
    fails closed rather than accepting any password when misconfigured."""
    stored_hash = os.environ.get("PANEL_PASSWORD_HASH")
    if not stored_hash:
        return False
    return verify_password(password, stored_hash)
