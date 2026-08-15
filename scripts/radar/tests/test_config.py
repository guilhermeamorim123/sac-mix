from radar import config

# The API returns commercial ads ONLY for EU + UK. A stray country silently
# degrades the whole run into political-ads-only, so the list is load-bearing.
EU_PLUS_UK = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE", "GB",
}


def test_countries_are_eu_or_uk_only():
    assert set(config.COUNTRIES) <= EU_PLUS_UK


def test_countries_has_no_duplicates():
    assert len(config.COUNTRIES) == len(set(config.COUNTRIES))


def test_brazil_is_excluded_from_countries():
    assert "BR" not in config.COUNTRIES


def test_score_weights_sum_to_one():
    total = config.WEIGHT_LONGEVITY + config.WEIGHT_CREATIVES + config.WEIGHT_REACH
    assert abs(total - 1.0) < 1e-9


def test_domain_lists_do_not_overlap():
    assert not (config.FUNNEL_DOMAINS & config.ECOMMERCE_DOMAINS)
    assert not (config.FUNNEL_DOMAINS & config.BR_DOMAINS)
    assert not (config.ECOMMERCE_DOMAINS & config.BR_DOMAINS)


def test_search_terms_are_lowercase_and_unique():
    assert all(term == term.lower() for term in config.SEARCH_TERMS)
    assert len(config.SEARCH_TERMS) == len(set(config.SEARCH_TERMS))
