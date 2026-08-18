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


def cmd_corrigir(args) -> None:
    import api

    cliente = cria_cliente()
    caminho = Path(args.foto)

    print(f"Lendo {caminho.name}...")
    transcricao, uso_transcricao = api.transcrever(cliente, caminho)

    print(f"\n--- TRANSCRIÇÃO ({transcricao.linhas} linhas) ---")
    print(transcricao.texto)
    print("--- fim ---\n")

    if not args.sem_confirmar:
        resposta = input("Li a letra direito? [S/n] ").strip().lower()
        if resposta and resposta not in ("s", "sim"):
            print("\nTire outra foto com mais luz e a folha reta, e rode de novo.")
            return

    print("Avaliando...")
    avaliacao, uso_avaliacao = api.avaliar(cliente, transcricao.texto, args.tema)

    print(f"\n=== NOTA: {avaliacao['nota_total']} ===")
    for penalidade in avaliacao["penalidades"]:
        print(f"!! {penalidade}")
    print(f"enquadramento: {avaliacao['enquadramento']}")
    if avaliacao["linhas_copiadas"]:
        print(f"linhas copiadas descontadas: {avaliacao['linhas_copiadas']} "
              f"({avaliacao['linhas_validas']} válidas)")
    if avaliacao["fere_direitos_humanos"]:
        print("proposta de intervenção fere direitos humanos: C5 zerada")
    print()

    for competencia in avaliacao["competencias"]:
        print(f"C{competencia['numero']}: {competencia['nota']}")
        print(f"   {competencia['justificativa']}")
        for melhoria in competencia["melhorias"]:
            print(f"   → {melhoria}")
        print()

    print(avaliacao["resumo"])

    custo = api.custo_usd(uso_transcricao) + api.custo_usd(uso_avaliacao)
    print(f"\ncusto desta correção: US$ {custo:.4f}")


def cmd_calibrar(args) -> None:
    import api
    import calibra

    base = Path(args.dataset)
    gabarito = base / "gabarito.csv"
    if not gabarito.exists():
        sys.exit(
            f"Erro: {gabarito} não existe.\n"
            f"Monte o conjunto assim:\n"
            f"  {base}/gabarito.csv   cabeçalho: "
            f"arquivo,nota_total,c1,c2,c3,c4,c5,tema\n"
            f"  {base}/fotos/         uma foto por linha do gabarito\n"
            f"  {base}/transcricoes/  opcional, texto digitado para medir a leitura"
        )
    itens = calibra.le_gabarito(gabarito)
    cliente = cria_cliente()

    pares_total = []
    pares_competencia = []
    acuracias = []
    custo_total = 0.0
    falhas = []

    for indice, item in enumerate(itens, start=1):
        print(f"[{indice}/{len(itens)}] {item.arquivo}...", end=" ", flush=True)
        try:
            transcricao, uso_t = api.transcrever(cliente, base / "fotos" / item.arquivo)
            avaliacao, uso_a = api.avaliar(cliente, transcricao.texto, item.tema)
        except (api.FotoIlegivel, api.RecusaDaAPI, api.RespostaSemTexto, ValueError) as erro:
            print(f"FALHOU ({erro})")
            falhas.append((item.arquivo, str(erro)))
            continue

        custo_total += api.custo_usd(uso_t) + api.custo_usd(uso_a)
        pares_total.append((item.nota_total, avaliacao["nota_total"]))
        for oficial, obtida in zip(item.competencias, avaliacao["competencias"]):
            pares_competencia.append((oficial, obtida["nota"]))

        referencia = base / "transcricoes" / f"{Path(item.arquivo).stem}.txt"
        if referencia.exists():
            acuracias.append(calibra.acuracia_ocr(
                referencia.read_text(encoding="utf-8"), transcricao.texto))

        diferenca = avaliacao["nota_total"] - item.nota_total
        print(f"oficial {item.nota_total} / obtida {avaliacao['nota_total']} "
              f"({diferenca:+d})")

    if not pares_total:
        print("\nNenhuma redação avaliada com sucesso — nada a medir.")
        return

    erro_total = calibra.mae(pares_total)
    erro_competencia = calibra.mae(pares_competencia)
    vies_total = calibra.vies(pares_total)

    print("\n" + "=" * 52)
    print(f"redações avaliadas:        {len(pares_total)} de {len(itens)}")
    print(f"erro médio (nota total):   {erro_total:.1f}  (meta ≤ {calibra.META_ERRO_TOTAL})")
    print(f"erro médio (competência):  {erro_competencia:.1f}  (meta ≤ {calibra.META_ERRO_COMPETENCIA})")
    print(f"viés:                      {vies_total:+.1f}"
          f"  ({'generoso' if vies_total > 0 else 'duro'})")
    if acuracias:
        media_ocr = sum(acuracias) / len(acuracias)
        print(f"leitura da letra:          {media_ocr:.1%}  (meta ≥ 90%)")
    print(f"custo total:               US$ {custo_total:.2f}")
    print(f"custo por correção:        US$ {custo_total / len(pares_total):.4f}")
    if falhas:
        print(f"\nfalhas ({len(falhas)}):")
        for arquivo, erro in falhas:
            print(f"  {arquivo}: {erro}")
    print("=" * 52)
    print(f"\n{calibra.veredito(erro_total, erro_competencia)}")


def main() -> None:
    garante_venv()

    parser = argparse.ArgumentParser(description="Corretor de redação do ENEM")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_smoke = sub.add_parser("smoke", help="confirma que a chave e o modelo respondem")
    p_smoke.set_defaults(func=cmd_smoke)

    p_corrigir = sub.add_parser("corrigir", help="corrige uma foto de redação")
    p_corrigir.add_argument("foto", help="caminho da foto")
    p_corrigir.add_argument("--tema", required=True, help="tema proposto da redação")
    p_corrigir.add_argument("--sem-confirmar", action="store_true",
                            dest="sem_confirmar",
                            help="pula a conferência da transcrição")
    p_corrigir.set_defaults(func=cmd_corrigir)

    p_calibrar = sub.add_parser("calibrar", help="roda o conjunto de calibração")
    p_calibrar.add_argument("--dataset", default="dataset",
                            help="pasta do conjunto (padrão: dataset)")
    p_calibrar.set_defaults(func=cmd_calibrar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
