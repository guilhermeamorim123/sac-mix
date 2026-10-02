"""The cross-run panel: one note, rewritten every run, read at a glance.

The per-run note answers "what is hot this week". It cannot answer "what
survived the last three months" — and survival is the entire thesis of the
radar. The series lives in `history.json` and nothing displayed it, so this
module does.

Plain markdown on purpose: no Obsidian plugin, no JavaScript, no republishing.
It opens in any editor and it is rewritten whenever the radar runs.
"""

from __future__ import annotations

from pathlib import Path


def _fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _latest_run(history: dict) -> str | None:
    """The most recent run date anywhere in the series."""
    dates = [entry["last_seen_run"] for entry in history["offers"].values()
             if entry.get("last_seen_run")]
    return max(dates) if dates else None


def _first_run(history: dict) -> str | None:
    dates = [entry["first_seen_run"] for entry in history["offers"].values()
             if entry.get("first_seen_run")]
    return min(dates) if dates else None


def _rows(history: dict) -> list[dict]:
    """Flatten each offer into the numbers the panel actually shows."""
    latest_run = _latest_run(history)
    out: list[dict] = []
    for key, entry in history["offers"].items():
        runs = entry.get("runs") or []
        if not runs:
            continue
        last = runs[-1]
        previous = runs[-2] if len(runs) > 1 else None
        out.append({
            "key": key,
            "page_name": entry.get("page_name") or "(sem nome)",
            "domain": entry.get("domain") or "",
            "lusofono": bool(entry.get("lusofono")),
            "runs_count": len(runs),
            "first_seen_run": entry.get("first_seen_run", ""),
            "last_seen_run": entry.get("last_seen_run", ""),
            "score": last.get("score", 0.0),
            "days_live": last.get("days_live", 0),
            "reach": last.get("reach", 0),
            "delta": (None if previous is None
                      else last.get("score", 0.0) - previous.get("score", 0.0)),
            "alive": entry.get("last_seen_run") == latest_run,
        })
    return out


def _fmt_delta(delta: float | None) -> str:
    """Em dash for a first appearance — zero would imply it held steady."""
    if delta is None:
        return "—"
    return f"{delta:+.2f}"


def _lang(row: dict) -> str:
    return "PT" if row["lusofono"] else "EN"


def _frontmatter(generated_on: str) -> str:
    return (
        "---\n"
        "type: radar-panel\n"
        'name: "Radar Infoproduto — Painel"\n'
        'project: "[[Radar Infoproduto]]"\n'
        f"last_updated: {generated_on}\n"
        "tags:\n"
        "  - project/radar-infoproduto\n"
        "---\n\n"
    )


def _summary(history: dict, rows: list[dict], generated_on: str) -> str:
    alive = [r for r in rows if r["alive"]]
    veterans = [r for r in alive if r["runs_count"] >= 4]
    return (
        "# Radar Infoproduto — Painel\n\n"
        f"Atualizado em {generated_on}. Reescrito a cada rodada.\n\n"
        f"- Ofertas rastreadas: **{len(rows)}**\n"
        f"- Vivas na última rodada: **{len(alive)}**\n"
        f"- Sobreviveram 4 rodadas ou mais: **{len(veterans)}**\n"
        f"- Série começa em {_first_run(history) or '—'} e termina em "
        f"{_latest_run(history) or '—'}\n\n"
    )


def _survivors(rows: list[dict]) -> str:
    alive = [r for r in rows if r["alive"]]
    if not alive:
        return ("## Sobreviventes\n\n"
                "Nenhuma oferta rastreada ainda. Rode o radar.\n\n")
    alive.sort(key=lambda r: (r["runs_count"], r["score"]), reverse=True)
    lines = [
        "## Sobreviventes\n",
        "Ordenado por quantas rodadas a oferta aguentou — persistência vale "
        "mais que uma semana barulhenta.\n",
        "| Rodadas | Anunciante | Domínio | Idioma | Dias no ar | Score | Variação |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in alive:
        lines.append(
            f"| {r['runs_count']} | {r['page_name']} | `{r['domain']}` | "
            f"{_lang(r)} | {r['days_live']} | {r['score']:.2f} | "
            f"{_fmt_delta(r['delta'])} |"
        )
    return "\n".join(lines) + "\n\n"


def _dead(rows: list[dict]) -> str:
    gone = [r for r in rows if not r["alive"]]
    if not gone:
        return ""
    gone.sort(key=lambda r: r["last_seen_run"], reverse=True)
    lines = [
        "## Já morreram\n",
        "Sumiram do ar. Quantas rodadas aguentaram antes de parar é o dado "
        "útil aqui: oferta que durou muito e caiu vale estudar.\n",
        "| Anunciante | Domínio | Rodadas | Vista pela última vez |",
        "|---|---|---|---|",
    ]
    for r in gone:
        lines.append(f"| {r['page_name']} | `{r['domain']}` | "
                     f"{r['runs_count']} | {r['last_seen_run']} |")
    return "\n".join(lines) + "\n\n"


def build_dashboard(history: dict, *, generated_on: str) -> str:
    rows = _rows(history)
    return (
        _frontmatter(generated_on)
        + _summary(history, rows, generated_on)
        + _survivors(rows)
        + _dead(rows)
        + "---\n**See also:** [[Radar Infoproduto]]\n"
    )


def write_dashboard(history: dict, path: Path, *, generated_on: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_dashboard(history, generated_on=generated_on),
                    encoding="utf-8")
    return path
