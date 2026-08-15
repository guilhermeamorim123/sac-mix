"""The only module that touches the network.

Everything else in the radar is a pure function over the dicts this returns,
which is what makes the rest testable offline.
"""

from __future__ import annotations

import json
import sys
import time

import requests

from radar import config

BASE = "https://graph.facebook.com"

# EU 27 + UK — the only countries for which the API returns commercial ads.
SUPPORTED = frozenset(config.COUNTRIES)


def assert_countries_supported(countries: list[str]) -> None:
    """Fail loudly on a country the API cannot serve commercial ads for.

    This guard exists because the failure is otherwise silent: with a non-EU
    country in the list the API returns political ads only, and the run looks
    like a bad result rather than a bad config.
    """
    bad = sorted(set(countries) - SUPPORTED)
    if bad:
        sys.exit(
            f"Erro: {', '.join(bad)} não é país da UE nem o Reino Unido.\n"
            "A Ad Library só devolve anúncio comercial para UE + UK. Com outro "
            "país na lista, a API responde só anúncio político, sem avisar.\n"
            "Corrija COUNTRIES em scripts/radar/config.py."
        )


def build_params(token: str, term: str, countries: list[str], *,
                 search_type: str | None = config.SEARCH_TYPE,
                 limit: int = config.PAGE_SIZE) -> dict:
    params = {
        "access_token": token,
        "ad_type": "ALL",
        "ad_reached_countries": json.dumps(countries),
        "search_terms": term,
        "fields": ",".join(config.FIELDS),
        "limit": str(limit),
    }
    if search_type:
        params["search_type"] = search_type
    return params


def next_page(payload: dict) -> str | None:
    return (payload.get("paging") or {}).get("next")


def _get(url: str, params: dict | None, *, attempts: int = 3) -> dict:
    """GET with exponential backoff. Raises RuntimeError when out of quota."""
    delay = 5
    for attempt in range(1, attempts + 1):
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200:
            return response.json()
        if response.status_code in (429, 500, 502, 503):
            if attempt == attempts:
                raise RuntimeError(f"quota ou instabilidade: HTTP "
                                   f"{response.status_code}")
            print(f"  HTTP {response.status_code} — nova tentativa em {delay}s")
            time.sleep(delay)
            delay *= 2
            continue
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:400]}")
    raise RuntimeError("tentativas esgotadas")


def fetch_term(token: str, term: str, countries: list[str], *,
               max_pages: int = 10) -> list[dict]:
    """All ads for one search term, following pagination."""
    ads: list[dict] = []
    payload = _get(f"{BASE}/{config.API_VERSION}/ads_archive",
                   build_params(token, term, countries))
    ads.extend(payload.get("data") or [])
    pages = 1
    url = next_page(payload)
    while url and pages < max_pages:
        payload = _get(url, None)
        ads.extend(payload.get("data") or [])
        url = next_page(payload)
        pages += 1
    return ads


def fetch_all(token: str, terms: list[str],
              countries: list[str]) -> tuple[list[dict], list[str]]:
    """Every term, deduplicated by ad id.

    Returns (ads, failed_terms). A term that blows the quota does not lose the
    terms already collected — the caller caches what came back and the run
    resumes an hour later.
    """
    assert_countries_supported(countries)
    seen: set[str] = set()
    ads: list[dict] = []
    failed: list[str] = []
    for i, term in enumerate(terms, start=1):
        print(f"[{i}/{len(terms)}] '{term}'...", end=" ", flush=True)
        try:
            found = fetch_term(token, term, countries)
        except RuntimeError as exc:
            print(f"FALHOU ({exc})")
            failed.append(term)
            continue
        fresh = [ad for ad in found if ad.get("id") not in seen]
        seen.update(ad["id"] for ad in found if ad.get("id"))
        ads.extend(fresh)
        print(f"{len(found)} anúncios ({len(fresh)} novos)")
    return ads, failed
