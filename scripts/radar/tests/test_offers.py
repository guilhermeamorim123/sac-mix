import json
from datetime import date
from pathlib import Path

from radar import classify, offers

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"
TODAY = date(2026, 8, 14)


def load_kept():
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return classify.keep_infoproducts(ads)


def test_offer_key_combines_page_and_domain():
    assert offers.offer_key({"page_id": "500",
                             "ad_creative_link_captions": ["exemplo.kajabi.com"]}) \
        == "500|exemplo.kajabi.com"


def test_group_collapses_three_ads_into_one_offer():
    grouped = offers.group(load_kept(), today=TODAY)
    keys = {o["key"] for o in grouped}
    assert "500|exemplo.kajabi.com" in keys
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["total_creatives"] == 3


def test_active_creatives_excludes_stopped_ads():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["active_creatives"] == 2  # ad 1003 has a stop time


def test_days_live_uses_the_earliest_ad_start():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["earliest_ad_start"] == "2026-01-05"
    assert academy["days_live"] == (TODAY - date(2026, 1, 5)).days


def test_reach_is_summed_across_creatives():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["reach"] == 300000 + 180000 + 20000


def test_page_name_and_domain_survive_grouping():
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["page_name"] == "Exemplo Academy"
    assert academy["domain"] == "exemplo.kajabi.com"


def test_lusophone_flag_is_true_when_any_ad_in_the_group_is():
    grouped = offers.group(load_kept(), today=TODAY)
    hotmart = next(o for o in grouped if o["key"] == "700|pay.hotmart.com")
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert hotmart["lusofono"] is True
    assert academy["lusofono"] is False


def test_countries_are_unioned_and_tolerate_the_field_being_absent():
    # Ad 1003 has no total_reach_by_location at all; 1001 and 1002 carry
    # Germany and Spain. The union must be both, with no crash on the third.
    grouped = offers.group(load_kept(), today=TODAY)
    academy = next(o for o in grouped if o["key"] == "500|exemplo.kajabi.com")
    assert academy["countries"] == ["Germany", "Spain"]


def test_start_time_with_timestamp_is_parsed():
    ads = [{"id": "1", "page_id": "1", "page_name": "X",
            "ad_creative_link_captions": ["x.kajabi.com"],
            "ad_delivery_start_time": "2026-07-01T10:33:00+0000"}]
    grouped = offers.group(ads, today=TODAY)
    assert grouped[0]["earliest_ad_start"] == "2026-07-01"
