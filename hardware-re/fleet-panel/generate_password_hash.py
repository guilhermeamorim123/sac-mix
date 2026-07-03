"""
One-off helper: run this locally to generate a PANEL_PASSWORD_HASH value
to set as a Render environment variable. Never commit the plaintext
password or this script's output anywhere -- copy the printed line
directly into Render's environment variable settings.

Usage: python generate_password_hash.py
"""
import getpass

from auth import hash_password

if __name__ == "__main__":
    password = getpass.getpass("Senha do painel: ")
    print("\nPANEL_PASSWORD_HASH=" + hash_password(password))
