"""Turn ads into offers, then score them.

The API hands back ads; the unit worth analysing is the offer. One product
runs dozens of creatives, so `(page_id, domain)` is the identity key: a page
can sell more than one offer, and a domain can be run by more than one page.
"""

from __future__ import annotations

import math
from datetime import date

from radar import classify, config


def offer_key(ad: dict) -> str:
    return f"{ad.get('page_id')}|{classify.extract_domain(ad)}"


def _parse_day(value: str | None) -> date | None:
    """Accept both "2026-03-02" and "2026-03-02T10:33:00+0000"."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_int(value: object) -> int:
    """Reach arrives as int, as a numeric string, or missing."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _countries(ads: list[dict]) -> list[str]:
    """Where the offer actually reached people, from total_reach_by_location.

    Shape-tolerant on purpose: the API has shipped this as a list of dicts and
    as a list of bare strings, the dict key has been seen as `region` and as
    `name`, and the field is simply absent on ads the archive has not filled
    in. Task 1 confirms which shape is live; until then, handle all of them.
    """
    found: set[str] = set()
    for ad in ads:
        for entry in ad.get("total_reach_by_location") or []:
            if isinstance(entry, dict):
                label = entry.get("region") or entry.get("name") or entry.get("key")
            else:
                label = entry
            if label:
                found.add(str(label))
    return sorted(found)


def group(ads: list[dict], *, today: date) -> list[dict]:
    """Collapse ads into offers, aggregating the fields the score needs."""
    buckets: dict[str, list[dict]] = {}
    for ad in ads:
        buckets.setdefault(offer_key(ad), []).append(ad)

    out: list[dict] = []
    for key, group_ads in buckets.items():
        starts = [d for d in (_parse_day(a.get("ad_delivery_start_time"))
                              for a in group_ads) if d]
        earliest = min(starts) if starts else today
        active = [a for a in group_ads if not a.get("ad_delivery_stop_time")]
        bodies = sorted(
            (b for a in group_ads for b in (a.get("ad_creative_bodies") or [])),
            key=len, reverse=True,
        )
        # Newest first. Bucket order is whatever the API happened to return,
        # term by term — it carries no recency guarantee, so the note would
        # otherwise link creatives from years ago that may already be stopped
        # instead of the one actually spending money today.
        recent = sorted(
            (a for a in group_ads if a.get("ad_snapshot_url")),
            key=lambda a: _parse_day(a.get("ad_delivery_start_time")) or date.min,
            reverse=True,
        )
        out.append({
            "key": key,
            "page_id": str(group_ads[0].get("page_id")),
            # Taken from the first ad in the bucket. `domain` is safe this way
            # because it is half the bucket key; `page_name` is not, so a page
            # renamed mid-flight resolves arbitrarily. Harmless in practice.
            "page_name": group_ads[0].get("page_name") or "(sem nome)",
            "domain": classify.extract_domain(group_ads[0]) or "",
            "earliest_ad_start": earliest.isoformat(),
            "days_live": (today - earliest).days,
            "active_creatives": len(active),
            "total_creatives": len(group_ads),
            "reach": sum(_as_int(a.get("eu_total_reach")) for a in group_ads),
            "countries": _countries(group_ads),
            "lusofono": any(classify.is_lusophone(a) for a in group_ads),
            "sample_copy": bodies[:3],
            "snapshot_urls": [a["ad_snapshot_url"] for a in recent[:5]],
        })
    return out


def _log_ratio(value: int, cap: int) -> float:
    """Log-normalize into 0..1. Creatives and reach both have fat tails —
    without the log, one giant offer flattens the whole ranking."""
    if value <= 0:
        return 0.0
    return min(1.0, math.log10(1 + value) / math.log10(1 + cap))


def score(offer: dict) -> float:
    """0..100. Longevity leads because it is the hardest signal to fake."""
    longevity = min(offer["days_live"], config.LONGEVITY_CAP_DAYS) / \
        config.LONGEVITY_CAP_DAYS
    longevity = max(0.0, min(1.0, longevity))
    creatives = _log_ratio(offer["active_creatives"], config.CREATIVES_CAP)
    reach = _log_ratio(offer["reach"], config.REACH_CAP)
    return round(100 * (
        config.WEIGHT_LONGEVITY * longevity
        + config.WEIGHT_CREATIVES * creatives
        + config.WEIGHT_REACH * reach
    ), 2)


def partition(all_offers: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split into (mature, emerging), scoring and sorting the mature ones.

    An offer younger than the gate may still be a test that dies next week —
    ranking it next to a 6-month survivor would be a lie.
    """
    mature: list[dict] = []
    emerging: list[dict] = []
    for offer in all_offers:
        enriched = dict(offer, score=score(offer))
        if enriched["days_live"] >= config.MATURITY_GATE_DAYS:
            mature.append(enriched)
        else:
            emerging.append(enriched)
    mature.sort(key=lambda o: o["score"], reverse=True)
    emerging.sort(key=lambda o: o["days_live"], reverse=True)
    return mature, emerging
