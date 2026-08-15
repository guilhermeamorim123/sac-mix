"""Tuning knobs for the radar. Pure data — no logic, no sibling imports.

This is the file to edit weekly: a term that returns nothing comes out, a new
funnel platform goes in. Everything here is covered by test_config.py, which
protects the invariants that silently break a run.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

# Confirmed by hand in Task 1. Bump when Meta deprecates it — the client
# surfaces the supported list in its error message.
API_VERSION = "v23.0"

# "KEYWORD_EXACT_PHRASE" or None. Unordered (the API default) inflates volume
# with false positives on two-word terms. Set to None if Task 1 found the
# parameter rejected.
SEARCH_TYPE = "KEYWORD_EXACT_PHRASE"

# EU 27 + UK. THE API RETURNS COMMERCIAL ADS ONLY FOR THESE. Any other country
# silently degrades the response to political ads only.
COUNTRIES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE", "GB",
]

# Every field a downstream module reads. Dropping one here breaks that module
# silently, with an empty column rather than an error — test_config guards it.
FIELDS = [
    "id", "page_id", "page_name",
    "ad_creative_bodies", "ad_creative_link_captions",
    "ad_creative_link_titles", "ad_creative_link_descriptions",
    "ad_delivery_start_time", "ad_delivery_stop_time",
    "ad_snapshot_url", "languages", "publisher_platforms",
    "eu_total_reach", "total_reach_by_location", "target_locations",
]

PAGE_SIZE = 100

# --------------------------------------------------------------------------
# What to look for
# --------------------------------------------------------------------------

# English only in v1: it covers the UK, Ireland and most European digital
# marketing. Each extra language multiplies the quota consumed.
SEARCH_TERMS = [
    "masterclass",
    "free training",
    "free webinar",
    "online course",
    "digital course",
    "coaching program",
    "mentorship",
    "bootcamp",
    "cohort",
    "certification",
    "join the challenge",
    "free guide",
    "playbook",
    "templates",
    "private community",
    "side hustle",
]

# Landing on one of these is near-proof of an infoproduct.
# Boundary cases kept deliberately: gumroad, whop and stan.store also host
# plain digital goods, but their volume is overwhelmingly info — course,
# template, ebook, community. Treated as funnel on purpose.
FUNNEL_DOMAINS = frozenset({
    "kajabi", "clickfunnels", "teachable", "thinkific", "learnworlds",
    "systeme.io", "kartra", "whop", "skool", "thrivecart", "samcart",
    "podia", "circle.so", "mightynetworks", "gumroad", "stan.store",
    "everwebinar", "webinarjam", "demio", "msgsndr",
})

# Landing on one of these means it is a store, not an infoproduct.
# General website builders (squarespace, wix) are deliberately NOT here: a solo
# coach running a whole funnel on one is exactly who this radar is looking for,
# and listing them would exclude that person outright. They fall through to the
# copy-based rule instead, which is the correct, weaker claim.
ECOMMERCE_DOMAINS = frozenset({
    "shopify", "myshopify", "amazon", "etsy", "ebay", "woocommerce",
    "bigcartel", "shopee", "aliexpress",
})

# Brazilian infoproduct platforms — excluded by owner decision.
BR_DOMAINS = frozenset({
    "hotmart", "eduzz", "kiwify", "braip", "monetizze", "ticto",
    "perfectpay", "cakto", "greenn", "herospark",
})

BR_LANGUAGES = frozenset({"pt", "pt_BR", "pt-BR"})
BR_COUNTRY = "BR"

# --------------------------------------------------------------------------
# Score
# --------------------------------------------------------------------------

# Longevity leads because it is the only one of the three that is hard to
# fake: nobody burns media budget for months at a loss. Reach and creative
# count confirm the size of the operation, they do not prove it works.
WEIGHT_LONGEVITY = 0.5
WEIGHT_CREATIVES = 0.3
WEIGHT_REACH = 0.2

# Caps: past these, more stops meaning more. Note the two kinds differ —
# LONGEVITY_CAP_DAYS is a hard linear clamp (min(days, cap) / cap), while
# CREATIVES_CAP and REACH_CAP are log10 denominators in offers._log_ratio.
# Doubling a log cap moves the score far less than doubling the linear one.
LONGEVITY_CAP_DAYS = 180
CREATIVES_CAP = 50
REACH_CAP = 1_000_000

# Below this, an offer may still be a test that dies next week.
MATURITY_GATE_DAYS = 21

# How many ranked offers get a full profile (copy, reach, snapshot links) in
# the run note. Past ~20 the note stops being readable in one sitting.
TOP_N_PROFILES = 20
