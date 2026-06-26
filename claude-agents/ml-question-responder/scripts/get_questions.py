"""
Fetch unanswered buyer questions for a given seller account.

Usage:
  python get_questions.py --account 1

Output (JSON to stdout):
  [
    {
      "id": 123456,
      "item_id": "MLB123",
      "text": "Qual o tamanho?",
      "date_created": "2026-05-28T10:00:00.000Z",
      "from": {"id": 789, "answered_questions": 5}
    },
    ...
  ]

Exit codes:
  0  success (even if empty list)
  1  auth error or API failure
"""

import os
import sys
import json
import argparse
import requests

ML_BASE = "https://api.mercadolibre.com"


def get_token(account_n: int) -> str:
    token = os.environ.get(f"ML_ACCESS_TOKEN_{account_n}")
    if not token:
        print(f"ML_ACCESS_TOKEN_{account_n} not set", file=sys.stderr)
        sys.exit(1)
    return token


def get_seller_id(token: str) -> str:
    resp = requests.get(f"{ML_BASE}/users/me", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 401:
        print("Token expirado. Execute: python ml_auth.py --refresh --account N", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return str(resp.json()["id"])


def fetch_questions(token: str) -> list[dict]:
    seller_id = get_seller_id(token)
    all_questions = []
    offset = 0
    limit = 50

    while True:
        resp = requests.get(
            f"{ML_BASE}/questions/search",
            params={
                "seller_id": seller_id,
                "status": "UNANSWERED",
                "offset": offset,
                "limit": limit,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if resp.status_code == 401:
            print("Token expirado. Execute: python ml_auth.py --refresh --account N", file=sys.stderr)
            sys.exit(1)

        resp.raise_for_status()
        data = resp.json()
        questions = data.get("questions", [])
        all_questions.extend(questions)

        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break

    return all_questions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=int, required=True)
    args = parser.parse_args()

    token = get_token(args.account)
    questions = fetch_questions(token)
    print(json.dumps(questions, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
