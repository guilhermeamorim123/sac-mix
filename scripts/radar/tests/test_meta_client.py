import pytest

from radar import config, meta_client


def test_build_params_serializes_countries_as_json_array():
    params = meta_client.build_params("tok", "masterclass", ["DE", "GB"])
    assert params["ad_reached_countries"] == '["DE", "GB"]'
    assert params["search_terms"] == "masterclass"
    assert params["ad_type"] == "ALL"
    assert params["access_token"] == "tok"


def test_build_params_joins_fields_with_commas():
    params = meta_client.build_params("tok", "masterclass", ["DE"])
    assert "ad_creative_link_captions" in params["fields"].split(",")
    assert "eu_total_reach" in params["fields"].split(",")


def test_build_params_omits_search_type_when_disabled():
    params = meta_client.build_params("tok", "masterclass", ["DE"],
                                      search_type=None)
    assert "search_type" not in params


def test_guard_rejects_a_non_eu_country():
    with pytest.raises(SystemExit) as exc:
        meta_client.assert_countries_supported(["DE", "US"])
    assert "US" in str(exc.value)


def test_guard_accepts_eu_and_uk():
    meta_client.assert_countries_supported(["DE", "GB", "ES"])


def test_guard_fires_on_the_real_config_path(monkeypatch):
    # The guard's whole job is to catch a bad edit to config.COUNTRIES, and
    # main() calls it with exactly that list. An earlier version derived
    # SUPPORTED from config.COUNTRIES, so the check compared the config
    # against itself and could never fail — while the literal-input tests
    # above kept passing. This test exercises the production path.
    monkeypatch.setattr(config, "COUNTRIES", ["DE", "GB", "US"])
    with pytest.raises(SystemExit) as exc:
        meta_client.assert_countries_supported(config.COUNTRIES)
    assert "US" in str(exc.value)


def test_supported_is_not_derived_from_the_config():
    # Belt and braces on the same defect: the constant must be independent.
    assert meta_client.SUPPORTED is not config.COUNTRIES
    assert "US" not in meta_client.SUPPORTED
    assert len(meta_client.SUPPORTED) == 28


def test_next_page_url_is_read_from_paging_cursor():
    payload = {"data": [], "paging": {"next": "https://graph.facebook.com/next"}}
    assert meta_client.next_page(payload) == "https://graph.facebook.com/next"


def test_next_page_returns_none_at_the_end():
    assert meta_client.next_page({"data": []}) is None
    assert meta_client.next_page({"data": [], "paging": {}}) is None
