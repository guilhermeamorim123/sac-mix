"""Decide whether an ad is an infoproduct, and whether it is Brazilian.

Pure functions over the raw ad dict the API returns. No network, no I/O.
This is the highest-leverage module in the radar: a wrong call here poisons
every downstream number.
"""

from __future__ import annotations

from typing import Any, Iterable


def extract_domain(ad: dict) -> str | None:
    """Registrable host from the ad's link caption, normalized.

    Captions arrive in several shapes: a bare host, an uppercase host, or a
    full URL with path and query. Everything is folded to a lowercase host
    with no scheme, no path and no leading "www.".
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
