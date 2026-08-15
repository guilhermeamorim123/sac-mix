from radar import dashboard, store


def history_with(*entries) -> dict:
    """Build a history dict directly, the way store.save would leave it."""
    return {"schema_version": 1, "offers": {e["key"]: _entry(e) for e in entries}}


def _entry(spec: dict) -> dict:
    return {
        "page_id": spec["key"].split("|")[0],
        "page_name": spec.get("page_name", "Page " + spec["key"]),
        "domain": spec["key"].split("|")[1],
        "first_seen_run": spec["runs"][0][0],
        "last_seen_run": spec["runs"][-1][0],
        "earliest_ad_start": "2026-01-01",
        "lusofono": spec.get("lusofono", False),
        "runs": [{"date": d, "days_live": 100 + i * 7, "active_creatives": 10,
                  "total_creatives": 12, "reach": 50_000, "score": s}
                 for i, (d, s) in enumerate(spec["runs"])],
    }


def veteran():
    return {"key": "1|veterana.kajabi.com", "page_name": "Veterana",
            "runs": [("2026-06-01", 70.0), ("2026-06-08", 72.0),
                     ("2026-06-15", 75.0), ("2026-06-22", 81.0)]}


def newcomer():
    return {"key": "2|nova.skool.com", "page_name": "Nova",
            "runs": [("2026-06-22", 60.0)]}


def faller():
    return {"key": "3|caindo.hotmart.com", "page_name": "Caindo",
            "lusofono": True,
            "runs": [("2026-06-15", 90.0), ("2026-06-22", 64.0)]}


def dead():
    return {"key": "4|morta.kajabi.com", "page_name": "Morta",
            "runs": [("2026-06-01", 55.0), ("2026-06-08", 52.0)]}


def test_panel_starts_with_frontmatter():
    panel = dashboard.build_dashboard(history_with(veteran()),
                                      generated_on="2026-06-22")
    assert panel.startswith("---\n")
    assert "type: radar-panel\n" in panel
    assert "project/radar-infoproduto" in panel


def test_survivors_are_ranked_by_how_many_runs_they_lasted():
    # The whole point of the panel: persistence beats a single loud week.
    panel = dashboard.build_dashboard(
        history_with(newcomer(), veteran()), generated_on="2026-06-22")
    assert panel.index("Veterana") < panel.index("Nova")


def test_survivor_row_shows_run_count_and_score_delta():
    panel = dashboard.build_dashboard(history_with(veteran()),
                                      generated_on="2026-06-22")
    assert "| 4 |" in panel      # four runs survived
    assert "+6.00" in panel      # 81.0 - 75.0


def test_a_falling_score_is_shown_as_negative():
    panel = dashboard.build_dashboard(history_with(faller()),
                                      generated_on="2026-06-22")
    assert "-26.00" in panel


def test_first_appearance_has_no_delta():
    panel = dashboard.build_dashboard(history_with(newcomer()),
                                      generated_on="2026-06-22")
    assert "nova.skool.com" in panel
    assert "—" in panel


def test_lusophone_offers_are_marked():
    panel = dashboard.build_dashboard(history_with(faller()),
                                      generated_on="2026-06-22")
    assert "| PT |" in panel


def test_offers_absent_from_the_latest_run_go_to_the_dead_section():
    panel = dashboard.build_dashboard(
        history_with(veteran(), dead()), generated_on="2026-06-22")
    assert "## Já morreram" in panel
    dead_section = panel.split("## Já morreram")[1]
    assert "Morta" in dead_section
    assert "Veterana" not in dead_section


def test_dead_section_is_omitted_when_everything_is_alive():
    panel = dashboard.build_dashboard(history_with(veteran()),
                                      generated_on="2026-06-22")
    assert "## Já morreram" not in panel


def test_empty_history_still_produces_a_valid_panel():
    panel = dashboard.build_dashboard({"schema_version": 1, "offers": {}},
                                      generated_on="2026-06-22")
    assert panel.startswith("---\n")
    assert "Nenhuma oferta rastreada ainda" in panel


def test_summary_counts_offers_and_runs():
    panel = dashboard.build_dashboard(
        history_with(veteran(), dead(), newcomer()), generated_on="2026-06-22")
    assert "3" in panel   # offers tracked
    assert "2026-06-01" in panel  # first run in the series


def test_write_dashboard_creates_the_file(tmp_path):
    path = dashboard.write_dashboard(history_with(veteran()),
                                     tmp_path / "Painel.md",
                                     generated_on="2026-06-22")
    assert path.is_file()
    assert path.read_text(encoding="utf-8").startswith("---\n")


def test_panel_reads_what_store_actually_writes(tmp_path):
    """Guard the seam: the panel must consume store's real output shape."""
    offer = {"key": "1|a.kajabi.com", "page_id": "1", "page_name": "Real",
             "domain": "a.kajabi.com", "days_live": 90, "active_creatives": 5,
             "total_creatives": 6, "reach": 1000,
             "earliest_ad_start": "2026-05-01", "score": 50.0,
             "lusofono": True, "countries": [], "sample_copy": [],
             "snapshot_urls": []}
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer], run_date="2026-08-14")
    panel = dashboard.build_dashboard(history, generated_on="2026-08-14")
    assert "Real" in panel
    assert "| PT |" in panel
