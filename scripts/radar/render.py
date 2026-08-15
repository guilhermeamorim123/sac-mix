"""Render offers into the vault's markdown note for one run."""

from __future__ import annotations

from pathlib import Path

from radar import config


def _fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _lang(offer: dict) -> str:
    """Language marker. Lusophone offers are the low-friction ones for the
    owner to read and model, so they earn a mark of their own."""
    return "PT" if offer.get("lusofono") else "EN"


def _frontmatter(run_date: str) -> str:
    return (
        "---\n"
        "type: radar-run\n"
        f'name: "Radar Infoproduto — {run_date}"\n'
        'project: "[[Radar Infoproduto]]"\n'
        f"date: {run_date}\n"
        "tags:\n"
        "  - project/radar-infoproduto\n"
        "---\n\n"
    )


def _summary(stats: dict, mature: list[dict], emerging: list[dict],
             diff: dict) -> str:
    return (
        f"# Radar Infoproduto — rodada de {stats.get('run_date', '')}\n\n"
        "## Resumo\n\n"
        f"- Anúncios coletados: **{_fmt_int(stats['total'])}**\n"
        f"- Passaram no filtro: **{_fmt_int(stats['kept'])}**"
        f" — {_fmt_int(stats['lusophone'])} lusófonos\n"
        f"- Descartados: {_fmt_int(stats['not_infoproduct'])} não-infoproduto, "
        f"{_fmt_int(stats['no_domain'])} sem domínio\n"
        f"- Ofertas maduras: **{len(mature)}** | emergentes: {len(emerging)}\n"
        f"- Novas: {len(diff['new'])} | sobreviveram: {len(diff['survived'])} "
        f"| morreram: {len(diff['died'])}\n\n"
    )


def _ranking(mature: list[dict]) -> str:
    if not mature:
        return ("## Ranking\n\n"
                "Nenhuma oferta madura nesta rodada.\n\n")
    lines = ["## Ranking\n",
             "| # | Anunciante | Domínio | Idioma | Dias no ar | Criativos "
             "| Alcance | Score |",
             "|---|---|---|---|---|---|---|---|"]
    for i, o in enumerate(mature, start=1):
        lines.append(
            f"| {i} | {o['page_name']} | `{o['domain']}` | {_lang(o)} | "
            f"{o['days_live']} | "
            f"{o['active_creatives']}/{o['total_creatives']} | "
            f"{_fmt_int(o['reach'])} | {o['score']:.2f} |"
        )
    return "\n".join(lines) + "\n\n"


def _profiles(mature: list[dict]) -> str:
    if not mature:
        return ""
    out = [f"## Fichas — top {min(config.TOP_N_PROFILES, len(mature))}\n\n"]
    for i, o in enumerate(mature[:config.TOP_N_PROFILES], start=1):
        out.append(f"### {i}. {o['page_name']} — score {o['score']:.2f}\n")
        out.append(
            f"- Domínio: https://{o['domain']}\n"
            f"- No ar desde {o['earliest_ad_start']} ({o['days_live']} dias)\n"
            f"- Criativos ativos: {o['active_creatives']} de "
            f"{o['total_creatives']} totais\n"
            f"- Alcance UE: {_fmt_int(o['reach'])}\n"
            f"- Países: {', '.join(o['countries']) or '—'}\n"
            f"- Idioma: {'lusófono' if o.get('lusofono') else 'inglês'}\n"
        )
        if o["sample_copy"]:
            out.append("\n**Promessa:**\n")
            for copy in o["sample_copy"]:
                out.append(f"\n> {copy}\n")
        if o["snapshot_urls"]:
            links = " · ".join(f"[criativo {n}]({u})"
                               for n, u in enumerate(o["snapshot_urls"], start=1))
            out.append(f"\n{links}\n")
        out.append("\n")
    return "".join(out)


def _emerging(emerging: list[dict]) -> str:
    if not emerging:
        return ""
    lines = [f"## Emergentes (menos de {config.MATURITY_GATE_DAYS} dias)\n",
             "Sem ranking — podem ser teste e morrer semana que vem.\n",
             "| Anunciante | Domínio | Dias no ar | Criativos |",
             "|---|---|---|---|"]
    for o in emerging:
        lines.append(f"| {o['page_name']} | `{o['domain']}` | {o['days_live']} "
                     f"| {o['active_creatives']} |")
    return "\n".join(lines) + "\n\n"


def _died(diff: dict) -> str:
    if not diff["died"]:
        return ""
    lines = ["## Mortas nesta rodada\n",
             "Estavam na rodada anterior e sumiram. Oferta que não sustentou.\n"]
    for key in diff["died"]:
        lines.append(f"- `{key}`")
    return "\n".join(lines) + "\n\n"


def build_note(mature: list[dict], emerging: list[dict], diff: dict,
               stats: dict, *, run_date: str) -> str:
    stats = dict(stats, run_date=run_date)
    return (
        _frontmatter(run_date)
        + _summary(stats, mature, emerging, diff)
        + _ranking(mature)
        + _profiles(mature)
        + _emerging(emerging)
        + _died(diff)
        + "---\n**See also:** [[Radar Infoproduto]]\n"
    )


def write_note(mature: list[dict], emerging: list[dict], diff: dict,
               stats: dict, *, run_date: str, runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run_date}.md"
    path.write_text(build_note(mature, emerging, diff, stats,
                               run_date=run_date), encoding="utf-8")
    return path
