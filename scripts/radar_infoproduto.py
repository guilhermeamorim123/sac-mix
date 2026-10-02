#!/usr/bin/env python3
"""Radar de infoproduto em alta na UE e no Reino Unido.

Usage:
    python scripts/radar_infoproduto.py
    python scripts/radar_infoproduto.py --date 2026-08-20
    python scripts/radar_infoproduto.py --force        # ignora o cache bruto
    python scripts/radar_infoproduto.py --render-only  # re-renderiza sem gastar cota

Requer META_AD_LIBRARY_TOKEN no ambiente ou em .env na raiz do vault.
A primeira execucao cria um virtualenv privado em scripts/.venv-radar/.
"""

from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
VENV = VAULT / "scripts" / ".venv-radar"
VENV_PY = VENV / "bin" / "python"

REQUIREMENTS = ["requests", "pytest"]


def ensure_venv() -> None:
    """Re-exec inside a private venv so the caller can use any python."""
    try:
        import requests  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("_RADAR_REEXEC"):
        sys.exit(
            "Erro: requests não importa nem dentro do venv.\n"
            f"Tente apagar {VENV} e rodar de novo."
        )

    if not VENV_PY.exists():
        print(f"Criando ambiente em {VENV.relative_to(VAULT)} (só na primeira vez)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                       check=True)
        print(f"Instalando {', '.join(REQUIREMENTS)}...")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", *REQUIREMENTS],
                       check=True)
        print("Ambiente pronto.\n")

    os.environ["_RADAR_REEXEC"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def load_token() -> str:
    """Token from the environment, falling back to .env at the vault root."""
    token = os.environ.get("META_AD_LIBRARY_TOKEN")
    if token:
        return token
    env_file = VAULT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("META_AD_LIBRARY_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(
        "Erro: META_AD_LIBRARY_TOKEN não encontrado.\n"
        "Gere um token em developers.facebook.com (app com acesso à Ad Library) "
        "e exporte:\n"
        '  export META_AD_LIBRARY_TOKEN="<token>"\n'
        "Ou coloque a linha META_AD_LIBRARY_TOKEN=<token> no .env da raiz do vault."
    )


def main() -> None:
    import argparse
    from datetime import date

    sys.path.insert(0, str(VAULT / "scripts"))
    from radar import (classify, config, dashboard, meta_client, offers,
                       render, store)

    parser = argparse.ArgumentParser(
        description="Radar de infoproduto em alta na UE e no Reino Unido.")
    parser.add_argument("--date", help="data da rodada (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--force", action="store_true",
                        help="ignora o cache bruto e coleta de novo")
    parser.add_argument("--render-only", action="store_true",
                        help="re-renderiza a partir do cache, sem gastar cota")
    args = parser.parse_args()

    run_date = args.date or date.today().isoformat()
    base = VAULT / "projects" / "radar-infoproduto"
    raw_path = base / "data" / "runs" / run_date / "raw.json"
    history_path = base / "data" / "history.json"
    runs_dir = base / "runs"

    meta_client.assert_countries_supported(config.COUNTRIES)

    if raw_path.is_file() and not args.force:
        print(f"Usando cache de {raw_path.relative_to(VAULT)} "
              f"(--force para recoletar)")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        failed: list[str] = []
    elif args.render_only:
        sys.exit(f"Erro: --render-only exige o cache em "
                 f"{raw_path.relative_to(VAULT)}, que não existe.")
    else:
        # Token first: announcing the collection before checking credentials
        # tells the owner it started when it never did.
        token = load_token()
        print(f"Coletando {len(config.SEARCH_TERMS)} termos em "
              f"{len(config.COUNTRIES)} países...")
        raw, failed = meta_client.fetch_all(token, config.SEARCH_TERMS,
                                            config.COUNTRIES)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        print(f"Bruto salvo em {raw_path.relative_to(VAULT)}")

    kept, stats = classify.keep_infoproducts(raw, with_stats=True)
    grouped = offers.group(kept, today=date.fromisoformat(run_date))
    mature, emerging = offers.partition(grouped)

    history = store.load(history_path)
    diff = store.merge(history, mature + emerging, run_date=run_date)
    store.save(history, history_path)

    note_path = render.write_note(mature, emerging, diff, stats,
                                  run_date=run_date, runs_dir=runs_dir)
    panel_path = dashboard.write_dashboard(history, base / "Painel.md",
                                           generated_on=run_date)

    print(f"\n{stats['total']} anúncios, {stats['kept']} passaram no filtro")
    print(f"{len(mature)} ofertas maduras, {len(emerging)} emergentes")
    print(f"{len(diff['new'])} novas, {len(diff['survived'])} sobreviveram, "
          f"{len(diff['died'])} morreram")
    if failed:
        print(f"\nAVISO: {len(failed)} termos falharam ({', '.join(failed)}). "
              f"Rode de novo em 1h com --force para completar.")
    print(f"\nNota da rodada: {note_path.relative_to(VAULT)}")
    print(f"Painel acumulado: {panel_path.relative_to(VAULT)}")


if __name__ == "__main__":
    ensure_venv()
    main()
