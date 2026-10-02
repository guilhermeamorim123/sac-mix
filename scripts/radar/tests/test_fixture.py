import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"


def test_fixture_loads():
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(ads) == 8


def test_fixture_covers_every_classification_case():
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    captions = {ad["ad_creative_link_captions"][0] for ad in ads}
    assert "exemplo.kajabi.com" in captions      # funnel platform
    assert "lojalegal.myshopify.com" in captions  # e-commerce
    assert "pay.hotmart.com" in captions          # BR platform
    assert "solocoach.co.uk" in captions          # own domain + offer term
    assert "consultoria.example.com" in captions  # own domain, no offer term
    assert any("pt" in ad.get("languages", []) for ad in ads)
    assert any("ad_delivery_stop_time" in ad for ad in ads)


def test_fixture_has_one_ad_missing_reach_by_location():
    # Ad 1003 deliberately omits total_reach_by_location, so the country
    # aggregation in Task 8 is forced to tolerate the field being absent —
    # which it will be, for any ad the API has not filled in.
    ads = json.loads(FIXTURE.read_text(encoding="utf-8"))
    academy = [ad for ad in ads if ad["page_id"] == "500"]
    assert any("total_reach_by_location" not in ad for ad in academy)
    assert any("total_reach_by_location" in ad for ad in academy)
