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
