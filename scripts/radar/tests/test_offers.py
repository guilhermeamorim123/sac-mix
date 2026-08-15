import json
from datetime import date
from pathlib import Path

import pytest

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


def _dated_ad(day: str, n: int) -> dict:
    return {"id": str(n), "page_id": "1", "page_name": "X",
            "ad_creative_link_captions": ["x.kajabi.com"],
            "ad_delivery_start_time": day,
            "ad_snapshot_url": f"https://snap/{n}",
            "ad_creative_bodies": ["b" * n]}


def test_snapshot_urls_are_the_five_most_recent_not_the_first_five():
    # Bucket order is whatever the API returned, term by term — it carries no
    # recency guarantee. Feeding oldest-first proves the sort is real: without
    # it, this returns the five oldest and the owner opens dead creatives.
    ads = [_dated_ad(d, i) for i, d in enumerate(
        ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01",
         "2024-01-01", "2025-01-01", "2026-08-01"], start=1)]
    grouped = offers.group(ads, today=TODAY)
    assert grouped[0]["snapshot_urls"] == [
        "https://snap/7", "https://snap/6", "https://snap/5",
        "https://snap/4", "https://snap/3",
    ]


def test_snapshot_urls_tolerate_an_unparseable_date():
    ads = [_dated_ad("not-a-date", 1), _dated_ad("2026-01-01", 2)]
    grouped = offers.group(ads, today=TODAY)
    # The good date sorts ahead of the unparseable one; neither crashes.
    assert grouped[0]["snapshot_urls"] == ["https://snap/2", "https://snap/1"]


def test_sample_copy_takes_the_three_longest_bodies():
    ads = [_dated_ad("2026-01-01", n) for n in (5, 40, 1, 20, 30)]
    grouped = offers.group(ads, today=TODAY)
    assert grouped[0]["sample_copy"] == ["b" * 40, "b" * 30, "b" * 20]


def make_offer(days_live, active_creatives, reach):
    return {"days_live": days_live, "active_creatives": active_creatives,
            "reach": reach}


def test_score_of_an_empty_offer_is_zero():
    assert offers.score(make_offer(0, 0, 0)) == 0.0


def test_score_of_a_maxed_offer_is_one_hundred():
    assert offers.score(make_offer(180, 50, 1_000_000)) == 100.0


def test_score_caps_do_not_reward_going_past_them():
    assert offers.score(make_offer(400, 500, 50_000_000)) == 100.0


def test_longevity_outweighs_reach_and_creatives():
    # This is the whole thesis of the radar: an old, modest offer beats a
    # loud, brand-new one. If this flips, the weights are wrong.
    old_and_small = offers.score(make_offer(180, 1, 0))
    new_and_loud = offers.score(make_offer(10, 50, 1_000_000))
    assert old_and_small > new_and_loud


def test_score_is_a_known_value():
    assert offers.score(make_offer(165, 22, 480_000)) == pytest.approx(88.69, abs=0.05)


def test_maturity_gate_splits_mature_from_emerging():
    mature, emerging = offers.partition([
        {"key": "a", "days_live": 90, "active_creatives": 5, "reach": 1000},
        {"key": "b", "days_live": 5, "active_creatives": 5, "reach": 1000},
    ])
    assert [o["key"] for o in mature] == ["a"]
    assert [o["key"] for o in emerging] == ["b"]


def test_partition_sorts_mature_by_score_descending():
    mature, _ = offers.partition([
        {"key": "low", "days_live": 30, "active_creatives": 1, "reach": 100},
        {"key": "high", "days_live": 170, "active_creatives": 40, "reach": 900_000},
    ])
    assert [o["key"] for o in mature] == ["high", "low"]
    assert mature[0]["score"] > mature[1]["score"]
