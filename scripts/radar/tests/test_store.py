import json

from radar import store


def offer(key, score=50.0, days_live=90):
    return {"key": key, "page_id": key.split("|")[0], "page_name": f"Page {key}",
            "domain": key.split("|")[1], "days_live": days_live,
            "active_creatives": 5, "total_creatives": 6, "reach": 1000,
            "earliest_ad_start": "2026-05-01", "score": score,
            "sample_copy": [], "snapshot_urls": []}


def test_load_returns_empty_history_when_file_absent(tmp_path):
    history = store.load(tmp_path / "history.json")
    assert history["offers"] == {}
    assert history["schema_version"] == 1


def test_first_run_marks_everything_as_new(tmp_path):
    history = store.load(tmp_path / "history.json")
    diff = store.merge(history, [offer("1|a.com"), offer("2|b.com")],
                       run_date="2026-08-14")
    assert set(diff["new"]) == {"1|a.com", "2|b.com"}
    assert diff["survived"] == []
    assert diff["died"] == []


def test_second_run_separates_new_survived_and_died(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com"), offer("2|b.com")],
                run_date="2026-08-14")
    diff = store.merge(history, [offer("2|b.com"), offer("3|c.com")],
                       run_date="2026-08-21")
    assert diff["new"] == ["3|c.com"]
    assert diff["survived"] == ["2|b.com"]
    assert diff["died"] == ["1|a.com"]


def test_merge_appends_one_run_entry_per_offer(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com", score=40.0)], run_date="2026-08-14")
    store.merge(history, [offer("1|a.com", score=60.0)], run_date="2026-08-21")
    runs = history["offers"]["1|a.com"]["runs"]
    assert [r["date"] for r in runs] == ["2026-08-14", "2026-08-21"]
    assert [r["score"] for r in runs] == [40.0, 60.0]


def test_merge_is_idempotent_for_the_same_run_date(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com", score=40.0)], run_date="2026-08-14")
    store.merge(history, [offer("1|a.com", score=44.0)], run_date="2026-08-14")
    runs = history["offers"]["1|a.com"]["runs"]
    assert len(runs) == 1
    assert runs[0]["score"] == 44.0  # re-running the same day overwrites


def test_first_seen_is_preserved_across_runs(tmp_path):
    history = store.load(tmp_path / "history.json")
    store.merge(history, [offer("1|a.com")], run_date="2026-08-14")
    store.merge(history, [offer("1|a.com")], run_date="2026-08-21")
    entry = history["offers"]["1|a.com"]
    assert entry["first_seen_run"] == "2026-08-14"
    assert entry["last_seen_run"] == "2026-08-21"


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "history.json"
    history = store.load(path)
    store.merge(history, [offer("1|a.com")], run_date="2026-08-14")
    store.save(history, path)
    assert json.loads(path.read_text(encoding="utf-8")) == history
