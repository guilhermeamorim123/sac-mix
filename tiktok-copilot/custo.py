"""Contabilidade de custo da IA.

Modulo separado de proposito: e logica pura, sem dependencia da biblioteca da
Anthropic, entao roda nos testes sem instalar nada e sem chave de API.
"""
from __future__ import annotations

# Preco por milhao de tokens (USD), tabela da Claude API. Cache de leitura sai
# a 10% da entrada; escrita de cache, a 125% (TTL padrao de 5 min).
PRECOS = {
    "claude-opus-5":    {"in": 5.00, "out": 25.00},
    "claude-opus-4-8":  {"in": 5.00, "out": 25.00},
    "claude-sonnet-5":  {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5": {"in": 1.00, "out":  5.00},
}


class Consumo:
    """Soma o que a API cobrou de verdade durante a live.

    A tabela de preco do `plans/002` inteira e estimativa. Isto aqui e o
    numero real -- o que decide se o preco por faixa se sustenta. Sem isso a
    primeira live gera opiniao; com isso gera decisao.
    """

    def __init__(self, modelo: str):
        self.modelo = modelo
        self.chamadas = 0
        self.entrada = 0
        self.saida = 0
        self.cache_escrito = 0
        self.cache_lido = 0

    def somar(self, usage) -> None:
        self.chamadas += 1
        self.entrada += getattr(usage, "input_tokens", 0) or 0
        self.saida += getattr(usage, "output_tokens", 0) or 0
        self.cache_escrito += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.cache_lido += getattr(usage, "cache_read_input_tokens", 0) or 0

    @property
    def custo_usd(self) -> float:
        p = PRECOS.get(self.modelo)
        if not p:  # modelo fora da tabela: melhor nao inventar numero
            return 0.0
        return (
            self.entrada * p["in"]
            + self.saida * p["out"]
            + self.cache_escrito * p["in"] * 1.25
            + self.cache_lido * p["in"] * 0.10
        ) / 1_000_000

    @property
    def cache_funcionou(self) -> bool:
        """Cache lido zerado depois de varias chamadas = prefixo nao cacheou.

        Acontece silenciosamente quando o system prompt fica abaixo do minimo
        do modelo (4.096 tokens no Haiku 4.5, contra 512 no Opus 5).
        """
        return self.cache_lido > 0

    def resumo(self, duracao_min: int) -> list[str]:
        if not self.chamadas:
            return ["  IA nao foi chamada (nenhuma mensagem passou pela triagem)"]
        por_hora = self.custo_usd * 60 / max(1, duracao_min)
        linhas = [
            f"  {'modelo':<22} {self.modelo}",
            f"  {'chamadas a API':<22} {self.chamadas}",
            f"  {'tokens entrada':<22} {self.entrada:,} (+{self.cache_lido:,} lidos do cache)",
            f"  {'tokens saida':<22} {self.saida:,}",
            f"  {'CUSTO REAL':<22} US$ {self.custo_usd:.4f}  (US$ {por_hora:.2f}/hora)",
        ]
        if not self.cache_funcionou:
            linhas.append(
                "  ATENCAO: o cache do catalogo nao pegou nenhuma vez. "
                "Prompt abaixo do minimo cacheavel deste modelo."
            )
        return linhas
