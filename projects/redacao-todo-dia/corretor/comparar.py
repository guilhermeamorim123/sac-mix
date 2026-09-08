#!/usr/bin/env python3
"""Compara configurações de modelo e esforço na MESMA redação.

Baixar custo num corretor é fácil; o difícil é saber se a nota continuou certa.
Este script roda a mesma foto em várias configurações e põe custo e nota lado a
lado — que é a única forma de decidir com dado em vez de esperança.

Uso:
    python comparar.py foto.jpg --tema "..."
    python comparar.py foto.jpg --tema "..." --configs sonnet-medium,opus-high

A transcrição é feita UMA vez e reaproveitada em todas as configurações. Sem
isso, cada configuração leria a letra de um jeito ligeiramente diferente e a
comparação mediria duas coisas ao mesmo tempo.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Configurações candidatas. Nome curto -> (modelo, esforço da avaliação).
CONFIGS = {
    "sonnet-low":    ("claude-sonnet-5", "low"),
    "sonnet-medium": ("claude-sonnet-5", "medium"),
    "sonnet-high":   ("claude-sonnet-5", "high"),
    "opus-medium":   ("claude-opus-5", "medium"),
    "opus-high":     ("claude-opus-5", "high"),
    "haiku-medium":  ("claude-haiku-4-5", "medium"),
}

PADRAO = "sonnet-medium,opus-high"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara configurações do corretor")
    parser.add_argument("foto", help="caminho da foto da redação")
    parser.add_argument("--tema", required=True, help="tema proposto")
    parser.add_argument("--configs", default=PADRAO,
                        help=f"separadas por vírgula. Disponíveis: {', '.join(CONFIGS)}")
    args = parser.parse_args()

    nomes = [n.strip() for n in args.configs.split(",") if n.strip()]
    for nome in nomes:
        if nome not in CONFIGS:
            sys.exit(f"configuração desconhecida: {nome}. Use uma de: {', '.join(CONFIGS)}")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Erro: ANTHROPIC_API_KEY não está definida.")

    foto = Path(args.foto)
    if not foto.exists():
        sys.exit(f"não achei o arquivo {foto}")

    import anthropic
    cliente = anthropic.Anthropic()

    # A transcrição roda uma vez só, na configuração mais barata: ler letra não
    # é raciocínio, e usar a mesma transcrição em todas isola a variável.
    os.environ["CORRETOR_MODELO"] = "claude-sonnet-5"
    import importlib
    import api
    importlib.reload(api)

    print(f"Lendo {foto.name}…")
    transcricao, uso_t = api.transcrever(cliente, foto)
    custo_t = api.custo_usd(uso_t, "claude-sonnet-5")
    print(f"  {transcricao.linhas} linhas · US$ {custo_t:.4f}")
    print(f"\n--- transcrição ---\n{transcricao.texto}\n--- fim ---\n")

    resultados = []
    for nome in nomes:
        modelo, esforco = CONFIGS[nome]
        os.environ["CORRETOR_MODELO"] = modelo
        os.environ["CORRETOR_EFFORT_AVALIACAO"] = esforco
        importlib.reload(api)

        print(f"Avaliando em {nome}…", end=" ", flush=True)
        try:
            avaliacao, uso_a = api.avaliar(
                cliente, transcricao.texto, args.tema, linhas=transcricao.linhas)
        except Exception as erro:
            print(f"FALHOU ({erro})")
            resultados.append((nome, None, None, str(erro)))
            continue

        custo_a = api.custo_usd(uso_a, modelo)
        notas = [c["nota"] for c in avaliacao["competencias"]]
        print(f"{avaliacao['nota_total']} · US$ {custo_a:.4f}")
        resultados.append((nome, avaliacao["nota_total"], notas, custo_t + custo_a))

    print("\n" + "=" * 66)
    print(f"{'configuração':<16}{'total':>7}{'  C1  C2  C3  C4  C5':<22}{'US$':>9}{'R$':>8}")
    print("-" * 66)
    for nome, total, notas, custo in resultados:
        if total is None:
            print(f"{nome:<16}{'falhou':>7}")
            continue
        comps = "".join(f"{n:>4}" for n in notas)
        print(f"{nome:<16}{total:>7}  {comps:<20}{custo:>9.4f}{custo * 5.2:>8.2f}")
    print("=" * 66)

    validos = [(n, t, c) for n, t, _, c in resultados if t is not None]
    if len(validos) >= 2:
        caro = max(validos, key=lambda r: r[2])
        barato = min(validos, key=lambda r: r[2])
        dif = abs(caro[1] - barato[1])
        economia = (1 - barato[2] / caro[2]) * 100
        print(f"\n{barato[0]} custa {economia:.0f}% menos que {caro[0]}.")
        print(f"Diferença de nota: {dif} pontos.")
        if dif <= 40:
            print("→ Dentro de uma faixa de competência. A economia sai de graça.")
        elif dif <= 80:
            print("→ Diferença perceptível. Vale rodar em mais redações antes de decidir.")
        else:
            print("→ Diferença grande. A economia está sendo paga com qualidade.")
        print("\nUma redação não decide nada. Roda em 5 ou 6 antes de escolher.")


if __name__ == "__main__":
    main()
