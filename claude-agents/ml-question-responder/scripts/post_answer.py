"""
Post an answer to a buyer question on Mercado Livre.

Usage:
  python post_answer.py --question-id 123456 --text "Olá! ..." --account 1

Exit codes:
  0  answer posted successfully
  1  API error or validation failure
"""

import os
import sys
import json
import argparse
import requests

ML_BASE = "https://api.mercadolibre.com"
MAX_ANSWER_LENGTH = 2000


def get_token(account_n: int) -> str:
    token = os.environ.get(f"ML_ACCESS_TOKEN_{account_n}")
    if not token:
        print(f"ML_ACCESS_TOKEN_{account_n} not set", file=sys.stderr)
        sys.exit(1)
    return token


def post_answer(question_id: int, text: str, token: str) -> dict:
    if len(text) > MAX_ANSWER_LENGTH:
        print(f"Resposta excede {MAX_ANSWER_LENGTH} caracteres ({len(text)}). Truncando.", file=sys.stderr)
        text = text[:MAX_ANSWER_LENGTH]

    resp = requests.post(
        f"{ML_BASE}/answers",
        json={"question_id": question_id, "text": text},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    if resp.status_code == 401:
        print("Token expirado. Execute: python ml_auth.py --refresh --account N", file=sys.stderr)
        sys.exit(1)

    if resp.status_code not in (200, 201):
        print(f"Erro ao postar resposta: {resp.status_code} — {resp.text}", file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-id", type=int, required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--account", type=int, default=1)
    args = parser.parse_args()

    token = get_token(args.account)
    post_answer(args.question_id, args.text, token)
    print(f"OK question_id={args.question_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
