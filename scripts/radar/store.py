"""Persist offers across runs, in JSON so it travels through git.

This file is half the value of the radar. A single run shows who is
advertising today; the series shows who *survived*, and survival is the proof
of profit the whole project is after.

JSON and not SQLite on purpose: the vault moves between machines over git, and
a gitignored binary would diverge between laptop and desktop.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1

# Fields carried into the history. Copy and snapshot URLs are deliberately
# left out — they belong in the run note, and would bloat the history.
_RUN_FIELDS = ("days_live", "active_creatives", "total_creatives", "reach", "score")


def load(path: Path) -> dict:
    """Read the history, failing legibly when the file is not what we expect.

    The likeliest way this file breaks is a git merge conflict: the vault
    syncs between machines over git, and two machines running the radar in the
    same week produce competing rewrites. A raw JSONDecodeError there tells
    the owner nothing useful, so conflict markers get their own message.
    """
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "offers": {}}
    text = path.read_text(encoding="utf-8")
    if "<<<<<<<" in text or ">>>>>>>" in text:
        raise SystemExit(
            f"Erro: {path} tem marcador de conflito de merge do git.\n"
            "Duas máquinas gravaram o histórico na mesma semana. Resolva o "
            "conflito no arquivo (ou recupere uma versão com `git checkout "
            "--theirs`) e rode de novo."
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Erro: {path} não é JSON válido ({exc}).\n"
            "O histórico é versionado no git — `git log -- <arquivo>` mostra "
            "a última versão boa."
        )
    if not isinstance(data, dict):
        raise SystemExit(
            f"Erro: {path} deveria conter um objeto JSON, mas contém "
            f"{type(data).__name__}."
        )
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("offers", {})
    return data


def save(history: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False,
                               sort_keys=True) + "\n", encoding="utf-8")


def _latest_run_before(known: dict, run_date: str) -> str | None:
    """The most recent run date already recorded, ignoring this one."""
    dates = {entry["last_seen_run"] for entry in known.values()
             if entry.get("last_seen_run") and entry["last_seen_run"] < run_date}
    return max(dates) if dates else None


def merge(history: dict, current: list[dict], *, run_date: str) -> dict:
    """Fold this run into the history and report what changed.

    Re-running the same date overwrites that date's entry instead of appending
    a duplicate, so a re-render or a `--force` never corrupts the series.
    """
    known = history["offers"]
    current_keys = {o["key"] for o in current}

    # "died" means: seen in the *immediately preceding* run, absent now. Offers
    # that stopped months ago must not resurface as dying every week.
    previous_run = _latest_run_before(known, run_date)
    previous_keys = {
        key for key, entry in known.items()
        if previous_run and entry.get("last_seen_run") == previous_run
    }

    diff = {"new": [], "survived": [], "died": []}

    for offer in current:
        key = offer["key"]
        entry = known.get(key)
        run_row = {"date": run_date, **{f: offer[f] for f in _RUN_FIELDS}}
        if entry is None:
            known[key] = {
                "page_id": offer["page_id"],
                "page_name": offer["page_name"],
                "domain": offer["domain"],
                "first_seen_run": run_date,
                "last_seen_run": run_date,
                "earliest_ad_start": offer["earliest_ad_start"],
                # Offer-level attribute, like page_name — the dashboard reads
                # it to mark language across the whole series.
                "lusofono": offer.get("lusofono", False),
                "runs": [run_row],
            }
            diff["new"].append(key)
        else:
            # min/max, not plain assignment: `--date` with an older date is
            # allowed, and assigning blindly would leave first_seen AFTER
            # last_seen — an incoherent summary over a correct runs array.
            entry["first_seen_run"] = min(entry["first_seen_run"], run_date)
            entry["last_seen_run"] = max(entry["last_seen_run"], run_date)
            entry["page_name"] = offer["page_name"]
            entry["earliest_ad_start"] = offer["earliest_ad_start"]
            entry["lusofono"] = offer.get("lusofono", False)
            entry["runs"] = [r for r in entry["runs"] if r["date"] != run_date]
            entry["runs"].append(run_row)
            entry["runs"].sort(key=lambda r: r["date"])
            diff["survived"].append(key)

    for key in previous_keys - current_keys:
        diff["died"].append(key)

    for bucket in diff.values():
        bucket.sort()
    return diff
