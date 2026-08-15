import json
from pathlib import Path

from radar import classify


def test_extract_domain_from_plain_host():
    assert classify.extract_domain({"ad_creative_link_captions": ["exemplo.kajabi.com"]}) \
        == "exemplo.kajabi.com"


def test_extract_domain_strips_scheme_path_and_www():
    ad = {"ad_creative_link_captions": ["https://WWW.Exemplo.com/promo?a=1"]}
    assert classify.extract_domain(ad) == "exemplo.com"


def test_extract_domain_strips_port_and_protocol_relative_scheme():
    port = {"ad_creative_link_captions": ["example.com:8080/path"]}
    relative = {"ad_creative_link_captions": ["//example.com/x"]}
    assert classify.extract_domain(port) == "example.com"
    assert classify.extract_domain(relative) == "example.com"


def test_extract_domain_returns_none_when_caption_missing():
    assert classify.extract_domain({}) is None
    assert classify.extract_domain({"ad_creative_link_captions": []}) is None
    assert classify.extract_domain({"ad_creative_link_captions": [""]}) is None


def test_host_matches_on_label():
    assert classify.host_matches("exemplo.kajabi.com", frozenset({"kajabi"}))


def test_host_matches_on_dotted_needle():
    assert classify.host_matches("app.systeme.io", frozenset({"systeme.io"}))


def test_host_matches_rejects_a_near_miss_dotted_needle():
    # The whole reason this function is not a substring check. Both of these
    # contain "systeme.io" as a substring and neither is that company. If a
    # future simplification swaps the label logic for `needle in host`, this
    # is the test that catches it.
    assert not classify.host_matches("notsysteme.io", frozenset({"systeme.io"}))
    assert not classify.host_matches("systeme.io.evil.com",
                                     frozenset({"systeme.io"}))


def test_host_matches_rejects_substring_of_a_label():
    # "wix" must not match "wixyzstore.com" — that is a different company.
    assert not classify.host_matches("wixyzstore.com", frozenset({"wix"}))


def test_is_lusophone_by_language():
    assert classify.is_lusophone({"languages": ["pt"],
                                  "ad_creative_link_captions": ["algo.com"]})


def test_is_lusophone_by_platform_domain():
    # English copy on Hotmart is still a lusophone operation.
    assert classify.is_lusophone({"languages": ["en"],
                                  "ad_creative_link_captions": ["pay.hotmart.com"]})


def test_is_lusophone_accepts_regional_language_tags():
    for tag in ("pt_BR", "pt-BR", "pt_PT", "pt-PT"):
        assert classify.is_lusophone({"languages": [tag],
                                      "ad_creative_link_captions": ["algo.com"]})


def test_english_ad_on_a_generic_domain_is_not_lusophone():
    assert not classify.is_lusophone({"languages": ["en"],
                                      "ad_creative_link_captions": ["solocoach.co.uk"]})


FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"


def load_ads():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_funnel_platform_is_infoproduct():
    ad = {"ad_creative_link_captions": ["exemplo.kajabi.com"],
          "ad_creative_bodies": ["anything at all"]}
    assert classify.is_infoproduct(ad)


def test_lusophone_platform_is_infoproduct():
    # Hotmart is one of the largest infoproduct platforms in the world. It is
    # positive evidence, not a reason to drop the ad.
    ad = {"ad_creative_link_captions": ["pay.hotmart.com"],
          "ad_creative_bodies": ["Masterclass gratuita."]}
    assert classify.is_infoproduct(ad)


def test_ecommerce_platform_is_not_infoproduct_even_with_offer_words():
    ad = {"ad_creative_link_captions": ["lojalegal.myshopify.com"],
          "ad_creative_bodies": ["Free shipping on our templates collection."]}
    assert not classify.is_infoproduct(ad)


def test_own_domain_with_offer_term_is_infoproduct():
    ad = {"ad_creative_link_captions": ["solocoach.co.uk"],
          "ad_creative_bodies": ["My coaching program opens Monday."]}
    assert classify.is_infoproduct(ad)


def test_own_domain_without_offer_term_is_not_infoproduct():
    ad = {"ad_creative_link_captions": ["consultoria.example.com"],
          "ad_creative_bodies": ["We build custom software for logistics."]}
    assert not classify.is_infoproduct(ad)


def test_offer_term_is_matched_in_link_title_too():
    ad = {"ad_creative_link_captions": ["solocoach.co.uk"],
          "ad_creative_bodies": ["Doors open."],
          "ad_creative_link_titles": ["Free training inside"]}
    assert classify.is_infoproduct(ad)


def test_ad_without_caption_is_not_infoproduct():
    assert not classify.is_infoproduct({"ad_creative_bodies": ["masterclass"]})


def test_keep_infoproducts_filters_the_fixture():
    kept = classify.keep_infoproducts(load_ads())
    kept_ids = {ad["id"] for ad in kept}
    # kajabi x3, hotmart, own-domain coach, skool. Dropped: the shopify store
    # and the software consultancy.
    assert kept_ids == {"1001", "1002", "1003", "3001", "4001", "6001"}


def test_keep_infoproducts_reports_why_it_dropped_things():
    kept, stats = classify.keep_infoproducts(load_ads(), with_stats=True)
    assert len(kept) == 6
    assert stats["not_infoproduct"] == 2  # shopify store, software consultancy
    assert stats["no_domain"] == 0
    assert stats["lusophone"] == 1        # counted, NOT dropped


def test_keep_infoproducts_never_drops_a_lusophone_ad():
    kept = classify.keep_infoproducts(load_ads())
    assert any(ad["id"] == "3001" for ad in kept)


def test_keep_infoproducts_counts_an_ad_with_no_domain():
    # The fixture has no domainless ad, so without this test the `no_domain`
    # counter is never executed and a typo in its key would pass the suite.
    # The stats dict is described as how a broken filter announces itself —
    # the announcement channel needs its own proof.
    ads = [{"id": "x", "ad_creative_bodies": ["masterclass"]}]
    kept, stats = classify.keep_infoproducts(ads, with_stats=True)
    assert kept == []
    assert stats["no_domain"] == 1
    assert stats["total"] == stats["kept"] + stats["not_infoproduct"] \
        + stats["no_domain"]


def test_generic_copy_on_an_own_domain_is_a_known_false_positive():
    # Documents the weakness rather than pretending it is not there: the bare
    # nouns in SEARCH_TERMS ("bootcamp", "templates", "certification") match
    # ordinary business copy. A gym's 6am bootcamp passes layer 2. The guard
    # against this is the manual top-20 audit, not the classifier.
    gym = {"ad_creative_link_captions": ["academia.example.com"],
           "ad_creative_bodies": ["Join our 6am bootcamp, first week free."]}
    assert classify.is_infoproduct(gym) is True


def test_multi_word_term_does_not_match_across_two_copy_fields():
    # "free training" exists in neither field on its own. Joining the fields
    # with a space would manufacture it.
    ad = {"ad_creative_link_captions": ["algo.example.com"],
          "ad_creative_bodies": ["Join the free"],
          "ad_creative_link_titles": ["training now"]}
    assert "free training" not in classify.ad_text(ad)
    assert not classify.is_infoproduct(ad)
