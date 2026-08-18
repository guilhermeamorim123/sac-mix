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

# O thinking do Opus 5 vem ligado e conta para max_tokens e para o custo.
# Transcrição é OCR, não raciocínio — roda barato. Avaliação é julgamento.
# Estes dois são a alavanca de custo mais direta: meça antes de baixar.
EFFORT_TRANSCRICAO = "low"
EFFORT_AVALIACAO = "high"

FORMATOS_ACEITOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class RecusaDaAPI(RuntimeError):
    """A API recusou a requisição (stop_reason == 'refusal')."""


class FotoIlegivel(ValueError):
    """O modelo não conseguiu ler a foto."""


class RespostaSemTexto(RuntimeError):
    """A resposta não trouxe bloco de texto — normalmente max_tokens curto."""


class TranscricaoSemContagem(RuntimeError):
    """A transcrição não trouxe o cabeçalho LINHAS: — sem ele não dá para avaliar."""


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
        output_config={"effort": EFFORT_TRANSCRICAO},
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
    if not cabecalho:
        raise TranscricaoSemContagem(
            "a transcrição veio sem o cabeçalho 'LINHAS: <n>'. Esse número "
            "dispara a regra de anulação por texto insuficiente — sem ele, "
            "avaliar produziria nota errada. Tente de novo."
        )
    linhas = int(cabecalho.group(1))
    texto = bruto[cabecalho.end():].strip()

    return Transcricao(texto=texto, linhas=linhas), resposta.usage


# Preço do claude-opus-5 em USD por 1M de tokens (referência de 17/08/2026).
PRECO_ENTRADA = 5.00
PRECO_SAIDA = 25.00
FATOR_ESCRITA_CACHE = 1.25
FATOR_LEITURA_CACHE = 0.10


def avaliar(cliente, texto: str, tema: str, linhas: int, linhas_copiadas: int = 0):
    """Avalia o texto transcrito. Devolve (avaliação normalizada, usage).

    `linhas` vem da transcrição, não do modelo avaliador — ele não vê a foto,
    e esse número dispara a regra de anulação por texto insuficiente.
    `linhas_copiadas` só é diferente de zero quando quem chama tem os textos
    motivadores para comparar; o harness não tem, o app terá.
    """
    resposta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        output_config={
            "effort": EFFORT_AVALIACAO,
            "format": {"type": "json_schema", "schema": schema.AVALIACAO_SCHEMA},
        },
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
    )
    crua = json.loads(_texto_da_resposta(resposta))
    crua["linhas"] = linhas
    crua["linhas_copiadas"] = linhas_copiadas
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
