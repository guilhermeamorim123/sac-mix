"""Classificacao e sugestao de resposta via Claude.

Duas decisoes que valem explicar:

1. Mensagens sao classificadas em LOTE. Chat de live chega em rajada; mandar
   uma request por mensagem multiplica custo e latencia sem ganho de qualidade.

2. O system prompt e cortado em dois blocos, com o cache_control no ultimo. As
   instrucoes e o catalogo nao mudam durante a live, entao viram prefixo
   cacheado (~10% do preco de input); so as mensagens da rajada pagam cheio.
"""
from __future__ import annotations

import asyncio
import json
import logging

import anthropic

from catalog import Catalog
from config import Settings
from models import Analysis, ChatMessage

log = logging.getLogger(__name__)

INSTRUCOES = """\
Voce e o copiloto de um vendedor brasileiro que esta AO VIVO no TikTok vendendo \
os produtos do catalogo abaixo. A cada rajada voce recebe as mensagens novas do \
chat e classifica cada uma.

Para cada mensagem, devolva:

- intent: a intencao da pessoa.
- lead_score: 0 a 10, quao perto de comprar ela esta.
  0-2 = so passando, comentario solto, emoji, spam.
  3-6 = curiosa, perguntou preco ou detalhe do produto.
  7-8 = intencao clara ("quero", "como pago", "ainda tem?", mandou o WhatsApp).
  9-10 = pronta para fechar ("vou levar 2", "manda o link", "ja fiz o Pix").
- suggested_reply: a resposta pronta, na voz do vendedor.
- requires_human: true quando a resposta depende de algo que voce NAO tem.
- product_mentioned: o nome exato do produto do catalogo, ou null.
- reasoning: no maximo uma frase curta.

Regras da suggested_reply:

- Portugues do Brasil, tom de live de venda: direto, animado, sem formalidade.
- Maximo 200 caracteres. Chat de live rola rapido, texto longo ninguem le.
- Chame a pessoa pelo primeiro nome quando der.
- NUNCA invente preco, prazo, frete, estoque, cor ou tamanho. Se o dado nao \
esta no catalogo, marque requires_human=true e escreva na suggested_reply o que \
voce precisa saber para responder.
- Produto com estoque 0: nao ofereca. Diga que esgotou e puxe para outro item.
- Quem demonstrou intencao de compra: termine chamando para a acao (link da \
sacolinha, WhatsApp, "comenta EU QUERO").
- Sem hashtag, sem emoji em excesso (no maximo um).

Marque requires_human=true tambem para: reclamacao, pedido ja feito, problema \
de entrega, negociacao de desconto, e qualquer coisa que envolva dado pessoal \
de um cliente especifico.
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "analises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "intent": {
                        "type": "string",
                        "enum": [
                            "preco", "frete", "prazo", "estoque", "tamanho",
                            "pagamento", "como_comprar", "elogio", "reclamacao",
                            "spam", "outro",
                        ],
                    },
                    "lead_score": {"type": "integer"},
                    "suggested_reply": {"type": "string"},
                    "requires_human": {"type": "boolean"},
                    "product_mentioned": {"type": ["string", "null"]},
                    "reasoning": {"type": "string"},
                },
                "required": [
                    "message_id", "intent", "lead_score", "suggested_reply",
                    "requires_human", "product_mentioned", "reasoning",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["analises"],
    "additionalProperties": False,
}


class Classifier:
    def __init__(self, api_key: str, model: str, catalogo: Catalog, settings: Settings):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._system: list[dict] = []
        self.recarregar(catalogo, settings)

    def recarregar(self, catalogo: Catalog, settings: Settings) -> None:
        """Reconstroi o system prompt.

        Chamado quando o lojista mexe no catalogo ou no tom de voz pelo painel
        no meio da live. Custa um cache-miss na proxima rajada -- barato perto
        de responder com preco velho.
        """
        contexto = catalogo.as_prompt_block()
        extra = settings.prompt_extra()
        if extra:
            contexto += f"\n\n{extra}"

        self._system = [
            {"type": "text", "text": INSTRUCOES},
            {
                "type": "text",
                "text": contexto,
                # Breakpoint do cache: tudo acima e estavel durante a live.
                "cache_control": {"type": "ephemeral"},
            },
        ]

    async def analyze(self, batch: list[ChatMessage]) -> list[Analysis]:
        if not batch:
            return []

        linhas = [
            f"[{m.message_id}] {m.nickname} (@{m.username}): {m.text}"
            for m in batch
        ]
        pergunta = "Mensagens novas do chat:\n" + "\n".join(linhas)

        try:
            resp = await self._client.messages.create(
                model=self._model,
                max_tokens=4000,
                system=self._system,
                output_config={
                    "effort": "low",  # classificacao curta: latencia importa mais que profundidade
                    "format": {"type": "json_schema", "schema": _SCHEMA},
                },
                messages=[{"role": "user", "content": pergunta}],
            )
        except anthropic.APIError as exc:
            # Uma falha da API nao pode derrubar a live. Devolve fallback
            # neutro: tudo vai para o vendedor decidir na mao.
            log.error("Falha ao classificar lote de %d msg: %s", len(batch), exc)
            return [_fallback(m) for m in batch]

        if resp.stop_reason == "refusal":
            log.warning("Lote recusado pelos filtros de seguranca; caindo para manual.")
            return [_fallback(m) for m in batch]

        texto = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            payload = json.loads(texto)
        except json.JSONDecodeError:
            log.error("Resposta nao-JSON do modelo: %.200s", texto)
            return [_fallback(m) for m in batch]

        por_id = {}
        for item in payload.get("analises", []):
            por_id[item["message_id"]] = Analysis(
                message_id=item["message_id"],
                intent=item["intent"],
                lead_score=max(0, min(10, int(item["lead_score"]))),
                suggested_reply=item["suggested_reply"].strip(),
                requires_human=bool(item["requires_human"]),
                product_mentioned=item.get("product_mentioned"),
                reasoning=item.get("reasoning", ""),
            )

        # Garante uma analise por mensagem mesmo se o modelo pular alguma.
        return [por_id.get(m.message_id) or _fallback(m) for m in batch]


def _fallback(msg: ChatMessage) -> Analysis:
    return Analysis(
        message_id=msg.message_id,
        intent="outro",
        lead_score=0,
        suggested_reply="",
        requires_human=True,
        reasoning="nao classificado",
    )


async def warmup(classifier: Classifier) -> None:
    """Grava o cache do prefixo antes da live comecar.

    Sem isso a primeira rajada real paga cache-miss justo no pior momento --
    quando o chat abre e chega tudo de uma vez.
    """
    try:
        await classifier._client.messages.create(
            model=classifier._model,
            max_tokens=0,
            system=classifier._system,
            messages=[{"role": "user", "content": "warmup"}],
        )
        log.info("Cache do prompt aquecido.")
    except (anthropic.APIError, asyncio.TimeoutError) as exc:
        log.warning("Warmup falhou (segue normal): %s", exc)
