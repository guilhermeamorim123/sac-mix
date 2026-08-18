"""Chamadas ao Claude: transcrever a foto e avaliar o texto.

As duas etapas são separadas de propósito. O maior risco técnico do produto é
o modelo ler a letra errado; separando, o erro de leitura vira uma tela de
conferência de dez segundos em vez de uma correção errada.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path

import prompts
import schema

MODELO = "claude-opus-5"
MAX_TOKENS = 16000

FORMATOS_ACEITOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class RecusaDaAPI(RuntimeError):
    """A API recusou a requisição (stop_reason == 'refusal')."""


class FotoIlegivel(ValueError):
    """O modelo não conseguiu ler a foto."""


class RespostaSemTexto(RuntimeError):
    """A resposta não trouxe bloco de texto — normalmente max_tokens curto."""


@dataclass
class Transcricao:
    texto: str
    linhas: int


def _bloco_imagem(caminho: Path) -> dict:
    media_type, _ = mimetypes.guess_type(Path(caminho).name)
    if media_type not in FORMATOS_ACEITOS:
        raise ValueError(
            f"formato não suportado: {Path(caminho).name} ({media_type}). "
            f"Aceitos: {', '.join(sorted(FORMATOS_ACEITOS))}"
        )
    dados = base64.standard_b64encode(Path(caminho).read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": dados},
    }


def _texto_da_resposta(resposta) -> str:
    if resposta.stop_reason == "refusal":
        raise RecusaDaAPI(f"a API recusou: {resposta.stop_details}")
    for bloco in resposta.content:
        if bloco.type == "text":
            return bloco.text
    raise RespostaSemTexto(
        f"resposta sem bloco de texto (stop_reason={resposta.stop_reason}). "
        f"No Opus 5 o thinking conta para max_tokens — tente aumentar MAX_TOKENS."
    )


def transcrever(cliente, caminho):
    """Lê a foto e devolve (Transcricao, usage). Não avalia nada."""
    resposta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [_bloco_imagem(caminho),
                        {"type": "text", "text": prompts.TRANSCRICAO}],
        }],
    )
    bruto = _texto_da_resposta(resposta).strip()

    if bruto.startswith("FOTO_ILEGIVEL"):
        raise FotoIlegivel(f"o modelo não conseguiu ler {Path(caminho).name}")

    cabecalho = re.match(r"^LINHAS:\s*(\d+)\s*\n+", bruto)
    if cabecalho:
        linhas = int(cabecalho.group(1))
        texto = bruto[cabecalho.end():].strip()
    else:
        texto = bruto
        linhas = len([linha for linha in texto.splitlines() if linha.strip()])

    return Transcricao(texto=texto, linhas=linhas), resposta.usage


# Preço do claude-opus-5 em USD por 1M de tokens (referência de 17/08/2026).
PRECO_ENTRADA = 5.00
PRECO_SAIDA = 25.00
FATOR_ESCRITA_CACHE = 1.25
FATOR_LEITURA_CACHE = 0.10


def avaliar(cliente, texto: str, tema: str):
    """Avalia o texto transcrito. Devolve (avaliação normalizada, usage)."""
    resposta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        system=[{
            "type": "text",
            "text": prompts.RUBRICA,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": (
                f"TEMA PROPOSTO:\n{tema}\n\n"
                f"REDAÇÃO DO ALUNO (transcrita da foto):\n{texto}"
            ),
        }],
        output_config={
            "format": {"type": "json_schema", "schema": schema.AVALIACAO_SCHEMA}
        },
    )
    crua = json.loads(_texto_da_resposta(resposta))
    return schema.normaliza(crua), resposta.usage


def custo_usd(usage) -> float:
    """Custo da chamada em dólares, a partir do objeto `usage` da resposta."""
    escrita_cache = getattr(usage, "cache_creation_input_tokens", 0) or 0
    leitura_cache = getattr(usage, "cache_read_input_tokens", 0) or 0
    entrada = (
        usage.input_tokens
        + escrita_cache * FATOR_ESCRITA_CACHE
        + leitura_cache * FATOR_LEITURA_CACHE
    )
    return entrada * PRECO_ENTRADA / 1e6 + usage.output_tokens * PRECO_SAIDA / 1e6
