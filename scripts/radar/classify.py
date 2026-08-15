"""Decide whether an ad is an infoproduct, and whether it is lusophone.

Pure functions over the raw ad dict the API returns. No network, no I/O.
This is the highest-leverage module in the radar: a wrong call here poisons
every downstream number.
"""

from __future__ import annotations

from typing import Any, Iterable

from radar import config


def extract_domain(ad: dict) -> str | None:
    """Registrable host from the ad's link caption, normalized.

    Captions arrive in several shapes: a bare host, an uppercase host, or a
    full URL with path and query. Everything is folded to a lowercase host
    with no scheme, no path, no port and no leading "www.".

    Takes the FIRST usable caption. An ad can carry several, but in this API
    they are the same link repeated across creative variants with cosmetic
    differences in case and format — not different destinations. If that ever
    stops holding, this is the assumption to revisit.
    """
    captions = ad.get("ad_creative_link_captions") or []
    for caption in captions:
        if not caption:
            continue
        host = caption.strip().lower()
        if "//" in host:
            host = host.split("//", 1)[1]
        host = host.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        if host:
            return host
    return None


def host_matches(host: str, needles: Iterable[str]) -> bool:
    """True when `host` belongs to one of `needles`.

    Matches on label boundaries, never on raw substring: "wix" matches
    "shop.wix.com" but not "wixyzstore.com".
    """
    labels = host.split(".")
    for needle in needles:
        if host == needle or host.endswith("." + needle) or needle in labels:
            return True
    return False


def is_lusophone(ad: dict) -> bool:
    """True when the offer speaks Portuguese — Brazilian or Portuguese.

    This is a LABEL, not a filter. Nothing is dropped for being lusophone; the
    run note marks it, because an offer the owner reads without friction is
    worth more to him than one he has to translate.

    Deliberately not called `is_brazilian`: the `pt` language tag covers
    Portugal too, and the platform list cannot tell a São Paulo seller from a
    Lisbon one.
    """
    if set(ad.get("languages") or []) & config.PT_LANGUAGES:
        return True
    host = extract_domain(ad)
    return bool(host and host_matches(host, config.PT_PLATFORM_DOMAINS))


_TEXT_FIELDS = ("ad_creative_bodies", "ad_creative_link_titles",
                "ad_creative_link_descriptions")


def ad_text(ad: dict) -> str:
    """Every piece of copy in the ad, lowercased into one searchable blob.

    Fields are joined with a pipe, not a space, so a two-word term cannot
    match by straddling the boundary between two independent copy items —
    "Join the free" + "training now" must not read as "free training". Nine
    of the sixteen search terms are multi-word, so this is not hypothetical.
    """
    parts: list[str] = []
    for field in _TEXT_FIELDS:
        parts.extend(str(v) for v in (ad.get(field) or []))
    return " | ".join(parts).lower()


def is_infoproduct(ad: dict) -> bool:
    """Two layers: platform fingerprint first, then copy on an own domain.

    Layer 1 — the domain is a known funnel platform — is near-proof and needs
    nothing else.

    Layer 2 is weaker than it looks, and the weakness is worth stating. In
    production every ad in the corpus is here BECAUSE Meta matched one of
    these same `SEARCH_TERMS` against it at collection time, so the copy check
    is nearly always satisfied by construction. What layer 2 actually rejects
    is the narrow case of an own-domain ad with no matching copy at all —
    typically an image-only creative. The real guards on this branch are
    `ECOMMERCE_DOMAINS` and the manual top-20 audit after each run, not this
    condition.

    Splitting the terms into a broad collection list and a narrow, unambiguous
    classification list would restore genuine discrimination here. That is a
    v2 change, deliberately not made now.
    """
    host = extract_domain(ad)
    if not host:
        return False
    if host_matches(host, config.FUNNEL_DOMAINS):
        return True
    if host_matches(host, config.PT_PLATFORM_DOMAINS):
        return True
    if host_matches(host, config.ECOMMERCE_DOMAINS):
        return False
    text = ad_text(ad)
    return any(term in text for term in config.SEARCH_TERMS)


def keep_infoproducts(ads: list[dict], *, with_stats: bool = False) -> Any:
    """Filter to infoproduct ads. Nothing is dropped for language.

    With `with_stats`, also returns a counter of what happened — the run
    summary uses it, and a spike in one bucket is how a broken filter
    announces itself. `lusophone` counts ads KEPT and labelled, not dropped.
    """
    kept: list[dict] = []
    stats = {"total": len(ads), "not_infoproduct": 0, "no_domain": 0,
             "lusophone": 0}
    for ad in ads:
        if not extract_domain(ad):
            stats["no_domain"] += 1
            continue
        if not is_infoproduct(ad):
            stats["not_infoproduct"] += 1
            continue
        if is_lusophone(ad):
            stats["lusophone"] += 1
        kept.append(ad)
    stats["kept"] = len(kept)
    return (kept, stats) if with_stats else kept
