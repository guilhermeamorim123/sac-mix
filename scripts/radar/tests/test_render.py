from radar import render


def offer(key="500|exemplo.kajabi.com", score=88.69, days_live=165):
    return {"key": key, "page_id": key.split("|")[0], "page_name": "Exemplo Academy",
            "domain": key.split("|")[1], "days_live": days_live,
            "active_creatives": 22, "total_creatives": 30, "reach": 480000,
            "earliest_ad_start": "2026-03-02", "score": score,
            "countries": ["Germany", "Spain"], "lusofono": False,
            "sample_copy": ["Join the free masterclass and learn the system."],
            "snapshot_urls": ["https://facebook.com/ads/archive/render_ad/?id=1001"]}


EMPTY_DIFF = {"new": [], "survived": [], "died": []}
STATS = {"total": 100, "kept": 40, "not_infoproduct": 55, "no_domain": 5,
         "lusophone": 8}


def test_note_starts_with_valid_frontmatter():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert note.startswith("---\n")
    assert "type: radar-run\n" in note
    assert "date: 2026-08-14\n" in note
    assert "project/radar-infoproduto" in note


def test_ranking_lists_the_mature_offer():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "Exemplo Academy" in note
    assert "exemplo.kajabi.com" in note
    assert "88.69" in note


def test_profile_includes_copy_snapshot_and_countries():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "Join the free masterclass" in note
    assert "render_ad/?id=1001" in note
    assert "Germany, Spain" in note


def test_profile_renders_a_dash_when_no_country_is_known():
    blank = dict(offer(), countries=[])
    note = render.build_note([blank], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "- Países: —" in note


def test_lusophone_offer_is_marked_in_ranking_and_profile():
    pt = dict(offer(key="700|pay.hotmart.com"), lusofono=True)
    note = render.build_note([pt], [], EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "| PT |" in note
    assert "- Idioma: lusófono" in note
    en = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                           run_date="2026-08-14")
    assert "| EN |" in en
    assert "- Idioma: inglês" in en


def test_emerging_section_appears_only_when_there_are_emerging_offers():
    without = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                                run_date="2026-08-14")
    assert "## Emergentes" not in without
    with_emerging = render.build_note(
        [offer()], [offer(key="950|novaoferta.skool.com", days_live=9)],
        EMPTY_DIFF, STATS, run_date="2026-08-14")
    assert "## Emergentes" in with_emerging
    assert "novaoferta.skool.com" in with_emerging


def test_died_section_appears_only_when_something_died():
    without = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                                run_date="2026-08-14")
    assert "## Mortas nesta rodada" not in without
    diff = {"new": [], "survived": [], "died": ["777|sumiu.kajabi.com"]}
    with_died = render.build_note([offer()], [], diff, STATS,
                                  run_date="2026-08-14")
    assert "## Mortas nesta rodada" in with_died
    assert "sumiu.kajabi.com" in with_died


def test_summary_reports_the_filter_stats():
    note = render.build_note([offer()], [], EMPTY_DIFF, STATS,
                             run_date="2026-08-14")
    assert "100" in note   # total collected
    assert "40" in note    # kept


def test_empty_run_still_produces_a_valid_note():
    note = render.build_note([], [], EMPTY_DIFF,
                             {"total": 0, "kept": 0, "not_infoproduct": 0,
                              "no_domain": 0, "lusophone": 0},
                             run_date="2026-08-14")
    assert note.startswith("---\n")
    assert "Nenhuma oferta madura" in note


def test_write_note_creates_the_file(tmp_path):
    path = render.write_note([offer()], [], EMPTY_DIFF, STATS,
                             run_date="2026-08-14", runs_dir=tmp_path)
    assert path == tmp_path / "2026-08-14.md"
    assert path.read_text(encoding="utf-8").startswith("---\n")
