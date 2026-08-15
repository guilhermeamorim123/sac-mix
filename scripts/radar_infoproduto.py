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
            "Erro: requests nao importa nem dentro do venv.\n"
            f"Tente apagar {VENV} e rodar de novo."
        )

    if not VENV_PY.exists():
        print(f"Criando ambiente em {VENV.relative_to(VAULT)} (so na primeira vez)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                       check=True)
        print(f"Instalando {', '.join(REQUIREMENTS)}...")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", *REQUIREMENTS],
                       check=True)
        print("Ambiente pronto.\n")

    os.environ["_RADAR_REEXEC"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def main() -> None:
    print("Radar Infoproduto — esqueleto. Orquestracao entra na Task 12.")


if __name__ == "__main__":
    ensure_venv()
    main()
