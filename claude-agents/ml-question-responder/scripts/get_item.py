"""
Fetch product details for a Mercado Livre item.
Returns title, attributes, available quantity, price, sale price, and description.

Usage:
  python get_item.py --item-id MLB123456789 --account 1

Output (JSON to stdout):
  {
    "id": "MLB123456789",
    "title": "Produto X",
    "price": 199.90,
    "sale_price": null,
    "available_quantity": 15,
    "condition": "new",
    "attributes": [
      {"id": "BRAND", "name": "Marca", "value_name": "XYZ"},
      ...
    ],
    "description": "Texto completo da descrição..."
  }
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


def fetch_item(item_id: str, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(f"{ML_BASE}/items/{item_id}", headers=headers)
    if resp.status_code == 401:
        print("Token expirado. Execute: python ml_auth.py --refresh --account N", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    item = resp.json()

    # Fetch full description separately
    desc_resp = requests.get(f"{ML_BASE}/items/{item_id}/description", headers=headers)
    description = ""
    if desc_resp.status_code == 200:
        description = desc_resp.json().get("plain_text", "")

    # Extract sale price if available
    sale_price = None
    if item.get("sale_price"):
        sale_price = item["sale_price"].get("amount")

    return {
        "id": item["id"],
        "title": item.get("title", ""),
        "price": item.get("price"),
        "sale_price": sale_price,
        "available_quantity": item.get("available_quantity", 0),
        "condition": item.get("condition", ""),
        "attributes": [
            {
                "id": attr.get("id"),
                "name": attr.get("name"),
                "value_name": attr.get("value_name"),
            }
            for attr in item.get("attributes", [])
            if attr.get("value_name")
        ],
        "description": description,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--account", type=int, default=1)
    args = parser.parse_args()

    token = get_token(args.account)
    item = fetch_item(args.item_id, token)
    print(json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
