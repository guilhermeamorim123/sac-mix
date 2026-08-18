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
    return next(b.text for b in resposta.content if b.type == "text")


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
