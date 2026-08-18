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


def le_gabarito(caminho) -> list:
    """Lê o CSV de gabarito e valida a coerência de cada linha."""
    itens = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for numero, linha in enumerate(csv.DictReader(f), start=2):
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
