"""Tipos de dominio que circulam entre ingest -> ai -> store -> sender."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Intent = Literal[
    "preco",
    "frete",
    "prazo",
    "estoque",
    "tamanho",
    "pagamento",
    "como_comprar",
    "elogio",
    "reclamacao",
    "spam",
    "outro",
]

# Intents que a IA pode responder sozinha sem risco: resposta e factual e sai
# direto do catalogo. Qualquer coisa fora dessa lista vai para o vendedor.
AUTO_SAFE_INTENTS: frozenset[str] = frozenset({"preco", "frete", "prazo", "como_comprar"})

# Numero de celular BR: aceita +55, DDD com ou sem parenteses, separadores
# variados. Exige o 9 inicial do celular para nao capturar telefone fixo/CEP.
_PHONE_RE = re.compile(
    r"(?:\+?55[\s.-]?)?"      # DDI opcional
    r"\(?([1-9]{2})\)?"        # DDD
    r"[\s.-]?"
    r"(9[\s.-]?\d{4})"         # primeiro bloco, celular comeca com 9
    r"[\s.-]?"
    r"(\d{4})"                 # segundo bloco
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def extract_whatsapp(text: str) -> str | None:
    """Extrai o primeiro celular BR do texto, normalizado como 55DDDNNNNNNNNN.

    Retorna None se nao houver match. Roda antes da IA -- e deterministico e de
    graca, nao faz sentido gastar token com isso.
    """
    match = _PHONE_RE.search(text)
    if not match:
        return None
    ddd, first, second = match.groups()
    digits = f"55{ddd}{first}{second}"
    return re.sub(r"\D", "", digits)


@dataclass(slots=True)
class ChatMessage:
    """Uma mensagem crua vinda do chat da live."""

    message_id: str
    user_id: str
    username: str      # @handle, estavel
    nickname: str      # nome de exibicao, pode mudar
    text: str
    received_at: datetime = field(default_factory=now)

    @property
    def whatsapp(self) -> str | None:
        return extract_whatsapp(self.text)


@dataclass(slots=True)
class Analysis:
    """O que a IA concluiu sobre uma mensagem."""

    message_id: str
    intent: Intent
    lead_score: int              # 0-10, quao perto de comprar
    suggested_reply: str
    requires_human: bool
    reasoning: str = ""
    product_mentioned: str | None = None

    @property
    def can_auto_send(self) -> bool:
        """Auto-envio so quando a IA nao pediu humano E o intent e seguro."""
        return not self.requires_human and self.intent in AUTO_SAFE_INTENTS


@dataclass(slots=True)
class OutgoingReply:
    """Mensagem aprovada para ser digitada no chat da live."""

    text: str
    in_reply_to: str        # message_id que originou
    source: Literal["auto", "manual"]
