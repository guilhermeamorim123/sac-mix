"""Métricas da calibração: quanto o corretor erra contra nota conhecida."""

from __future__ import annotations

import csv
import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import schema

# Metas do spec. Passar nelas é a condição para o projeto continuar.
META_ERRO_TOTAL = 80
META_ERRO_COMPETENCIA = 40


@dataclass
class ItemGabarito:
    arquivo: str
    nota_total: int
    competencias: list
    tema: str


COLUNAS = ("arquivo", "nota_total", "c1", "c2", "c3", "c4", "c5", "tema")


def _texto_do_csv(caminho) -> str:
    """Lê o arquivo tolerando o que o Excel produz: BOM e cp1252."""
    dados = Path(caminho).read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        f"{caminho}: não consegui decodificar. Salve a planilha como "
        f"'CSV UTF-8' e tente de novo."
    )


def le_gabarito(caminho) -> list:
    """Lê o CSV de gabarito e valida a coerência de cada linha.

    Tolera o que sai de uma planilha: BOM, cp1252 e separador ponto-e-vírgula.
    """
    texto = _texto_do_csv(caminho)
    primeira_linha = texto.splitlines()[0] if texto.splitlines() else ""
    separador = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","

    leitor = csv.DictReader(texto.splitlines(), delimiter=separador)
    faltando = [coluna for coluna in COLUNAS if coluna not in (leitor.fieldnames or [])]
    if faltando:
        raise ValueError(
            f"{caminho}: faltam as colunas {faltando}. "
            f"O cabeçalho precisa ser: {','.join(COLUNAS)}"
        )

    itens = []
    for numero, linha in enumerate(leitor, start=2):
        competencias = [int(linha[f"c{n}"]) for n in (1, 2, 3, 4, 5)]
        total = int(linha["nota_total"])
        for indice, nota in enumerate(competencias, start=1):
            if nota not in schema.NOTAS_VALIDAS:
                raise ValueError(
                    f"linha {numero} ({linha['arquivo']}): c{indice}={nota} "
                    f"fora do grid {list(schema.NOTAS_VALIDAS)}"
                )
        if sum(competencias) != total:
            raise ValueError(
                f"linha {numero} ({linha['arquivo']}): a soma das "
                f"competências ({sum(competencias)}) não bate com a nota "
                f"total ({total})"
            )
        itens.append(ItemGabarito(
            arquivo=linha["arquivo"],
            nota_total=total,
            competencias=competencias,
            tema=linha["tema"],
        ))
    return itens


def mae(pares) -> float:
    """Erro médio absoluto de uma lista de (oficial, previsto)."""
    if not pares:
        return 0.0
    return sum(abs(previsto - oficial) for oficial, previsto in pares) / len(pares)


def vies(pares) -> float:
    """Erro médio com sinal. Positivo = o corretor está sendo generoso."""
    if not pares:
        return 0.0
    return sum(previsto - oficial for oficial, previsto in pares) / len(pares)


def _tokens(texto: str) -> list:
    """Minúsculas e sem pontuação, mas COM acento — acento é erro de C1."""
    sem_pontuacao = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    return unicodedata.normalize("NFC", sem_pontuacao.lower()).split()


def acuracia_ocr(referencia: str, transcrito: str) -> float:
    """Semelhança palavra a palavra entre o texto digitado e o transcrito."""
    return difflib.SequenceMatcher(
        None, _tokens(referencia), _tokens(transcrito)
    ).ratio()


def veredito(erro_total: float, erro_competencia: float) -> str:
    dentro = (erro_total <= META_ERRO_TOTAL
              and erro_competencia <= META_ERRO_COMPETENCIA)
    return "APROVADO" if dentro else "REPROVADO"
