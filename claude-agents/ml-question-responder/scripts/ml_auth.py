"""
Mercado Livre OAuth2 authentication handler.

Env vars per account (N = 1, 2, 3...):
  ML_CLIENT_ID_N       App ID from ML Developers
  ML_CLIENT_SECRET_N   Secret Key from ML Developers
  ML_ACCESS_TOKEN_N    Current access token
  ML_REFRESH_TOKEN_N   Refresh token

Usage:
  python ml_auth.py --setup --account 1   # First-time OAuth flow
  python ml_auth.py --refresh --account 1  # Refresh expired token
  python ml_auth.py --list                  # List configured accounts
"""

import os
import sys
import json
import argparse
import webbrowser
from urllib.parse import urlencode
import requests

ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
REDIRECT_URI = "https://www.example.com/ml-callback"


def get_account_env(n: int) -> dict | None:
    token = os.environ.get(f"ML_ACCESS_TOKEN_{n}")
    if not token:
        return None
    return {
        "index": n,
        "client_id": os.environ.get(f"ML_CLIENT_ID_{n}", ""),
        "client_secret": os.environ.get(f"ML_CLIENT_SECRET_{n}", ""),
        "access_token": token,
        "refresh_token": os.environ.get(f"ML_REFRESH_TOKEN_{n}", ""),
    }


def get_all_accounts() -> list[dict]:
    accounts = []
    n = 1
    while True:
        acc = get_account_env(n)
        if not acc:
            break
        accounts.append(acc)
        n += 1
    return accounts


def refresh_token(account: dict) -> str:
    resp = requests.post(ML_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": account["client_id"],
        "client_secret": account["client_secret"],
        "refresh_token": account["refresh_token"],
    })
    resp.raise_for_status()
    data = resp.json()
    new_token = data["access_token"]
    new_refresh = data.get("refresh_token", account["refresh_token"])
    print(f"REFRESHED account_{account['index']}")
    print(f"SET ML_ACCESS_TOKEN_{account['index']}={new_token}")
    print(f"SET ML_REFRESH_TOKEN_{account['index']}={new_refresh}")
    return new_token


def setup_flow(account_n: int, client_id: str):
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
    }
    url = f"{ML_AUTH_URL}?{urlencode(params)}"
    print(f"\nAbrindo browser para autorizar conta {account_n}...")
    print(f"URL: {url}\n")
    webbrowser.open(url)
    code = input("Cole o 'code' recebido no redirect URL: ").strip()

    client_secret = input(f"ML_CLIENT_SECRET_{account_n}: ").strip()
    resp = requests.post(ML_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    })
    resp.raise_for_status()
    data = resp.json()
    print(f"\nTokens para conta {account_n}:")
    print(f"ML_CLIENT_ID_{account_n}={client_id}")
    print(f"ML_CLIENT_SECRET_{account_n}={client_secret}")
    print(f"ML_ACCESS_TOKEN_{account_n}={data['access_token']}")
    print(f"ML_REFRESH_TOKEN_{account_n}={data.get('refresh_token', '')}")
    print("\nSalve essas variáveis de ambiente antes de usar o agente.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--account", type=int, default=1)
    parser.add_argument("--client-id", type=str, default="")
    args = parser.parse_args()

    if args.list:
        accounts = get_all_accounts()
        if not accounts:
            print("Nenhuma conta configurada.")
        for acc in accounts:
            print(f"Conta {acc['index']}: token ...{acc['access_token'][-6:]}")
        return

    if args.setup:
        client_id = args.client_id or os.environ.get(f"ML_CLIENT_ID_{args.account}", "")
        if not client_id:
            client_id = input(f"ML_CLIENT_ID_{args.account}: ").strip()
        setup_flow(args.account, client_id)
        return

    if args.refresh:
        acc = get_account_env(args.account)
        if not acc:
            print(f"Conta {args.account} não configurada.", file=sys.stderr)
            sys.exit(1)
        refresh_token(acc)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
