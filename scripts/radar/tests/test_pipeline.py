import json
from datetime import date
from pathlib import Path

from radar import classify, offers, render, store

FIXTURE = Path(__file__).parent / "fixtures" / "ads_sample.json"


def test_full_pipeline_from_raw_ads_to_note(tmp_path):
    """The whole chain, wired exactly as the CLI wires it, with no network."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    kept, stats = classify.keep_infoproducts(raw, with_stats=True)
    grouped = offers.group(kept, today=date(2026, 8, 14))
    mature, emerging = offers.partition(grouped)

    history_path = tmp_path / "history.json"
    history = store.load(history_path)
    diff = store.merge(history, mature + emerging, run_date="2026-08-14")
    store.save(history, history_path)

    note_path = render.write_note(mature, emerging, diff, stats,
                                  run_date="2026-08-14", runs_dir=tmp_path)

    note = note_path.read_text(encoding="utf-8")
    assert "Exemplo Academy" in note        # kajabi offer ranked
    assert "Solo Coach" in note             # own-domain offer ranked
    assert "Nova Oferta" in note            # skool offer, emerging (9 days)
    assert "Curso BR" in note               # hotmart offer, kept and marked PT
    assert "Loja Legal" not in note         # e-commerce filtered out
    assert "Consultoria Qualquer" not in note  # no offer term
    assert history_path.is_file()


def test_pipeline_marks_the_lusophone_offer_without_dropping_it(tmp_path):
    """The reversal of the original Brazil exclusion, pinned end to end."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    kept, stats = classify.keep_infoproducts(raw, with_stats=True)
    grouped = offers.group(kept, today=date(2026, 8, 14))
    mature, emerging = offers.partition(grouped)

    note = render.build_note(mature, emerging, {"new": [], "survived": [],
                                                "died": []},
                             stats, run_date="2026-08-14")
    assert stats["lusophone"] == 1
    assert "Curso BR" in note
    assert "| PT |" in note
