#!/usr/bin/env python3
"""Corretor de redação do ENEM — CLI de calibração.

Uso:
    python run.py smoke                      # confirma chave e modelo
    python run.py corrigir foto.jpg --tema "..."
    python run.py calibrar                   # roda o conjunto inteiro

A primeira execução cria um venv privado em `corretor/.venv/`.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VENV = AQUI / ".venv"
VENV_PY = VENV / "bin" / "python"
REQUIREMENTS = AQUI / "requirements.txt"


def garante_venv() -> None:
    try:
        import anthropic  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("_CORRETOR_REEXEC"):
        sys.exit(f"Erro: anthropic não importa nem dentro do venv.\n"
                 f"Apague {VENV} e rode de novo.")

    if not VENV_PY.exists():
        print(f"Criando ambiente em {VENV.name}/ (só na primeira vez)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"],
                       check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)],
                       check=True)
        print("Ambiente pronto.\n")

    os.environ["_CORRETOR_REEXEC"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def cria_cliente():
    import anthropic
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Erro: ANTHROPIC_API_KEY não está definida. Ver os pré-requisitos do plano.")
    return anthropic.Anthropic()


def cmd_smoke(args) -> None:
    cliente = cria_cliente()
    resposta = cliente.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Responda apenas: ok"}],
    )
    if resposta.stop_reason == "refusal":
        sys.exit(f"A API recusou: {resposta.stop_details}")
    texto = next(b.text for b in resposta.content if b.type == "text")
    print(f"modelo: {resposta.model}")
    print(f"resposta: {texto.strip()}")
    print(f"tokens: {resposta.usage.input_tokens} entrada / {resposta.usage.output_tokens} saída")


def main() -> None:
    garante_venv()

    parser = argparse.ArgumentParser(description="Corretor de redação do ENEM")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_smoke = sub.add_parser("smoke", help="confirma que a chave e o modelo respondem")
    p_smoke.set_defaults(func=cmd_smoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
