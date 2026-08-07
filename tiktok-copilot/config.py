"""Configuracao em duas camadas.

- `Config`  -- o que e da MAQUINA: chaves de API, @ da live, porta do Chrome,
  qual backend usar. Vem do `.env` e nao muda enquanto o agente roda.
- `Settings` -- o que e da LOJA: se a auto-resposta esta ligada, teto por
  minuto, quais intents podem ser respondidos sozinhos, tom de voz. Vem da
  tabela `configuracoes` quando o backend e Supabase (o lojista edita pelo
  painel) e cai para o `.env` no modo local.

A separacao existe porque o painel precisa mudar o comportamento do agente sem
que ninguem toque no `.env` da maquina do vendedor.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# Intents que a IA pode responder sozinha por padrao: a resposta e factual e
# sai direto do catalogo. O lojista pode restringir mais pelo painel, nunca
# ampliar para reclamacao/negociacao -- ver `Settings.intents_auto`.
INTENTS_AUTO_PADRAO = ("preco", "frete", "prazo", "como_comprar")

# Nem todo intent pode ser liberado para auto-envio, mesmo que alguem marque no
# banco. Reclamacao, negociacao e afins vao para o vendedor. Sempre.
INTENTS_AUTO_PERMITIDOS = frozenset(
    {"preco", "frete", "prazo", "como_comprar", "estoque", "tamanho", "pagamento"}
)


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "sim")


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    model: str
    tiktok_username: str

    auto_reply_enabled: bool
    auto_reply_max_per_min: int
    chrome_cdp_url: str

    # Replay = live gravada sendo reexibida. Nesse modo o auto-envio so libera
    # com check-in de supervisor, porque nao ha ninguem na frente da camera.
    replay_mode: bool
    supervisor_interval_min: int

    store_backend: str
    sqlite_path: str
    supabase_url: str
    supabase_service_key: str
    seller_id: str

    # Janela de agrupamento: mensagens que chegam dentro desse intervalo sao
    # classificadas em uma unica chamada. Chat de live vem em rajada, entao
    # isso corta custo e latencia de forma significativa.
    batch_window_seconds: float = 1.5
    batch_max_size: int = 12

    # De quanto em quanto tempo reler catalogo e configuracoes do banco. O
    # lojista pode importar planilha ou mudar o preco no meio da live.
    refresh_seconds: int = 30

    # Acima disso o lead entra na aba "quentes" do painel. Sobrescrito pelo
    # banco quando ha `configuracoes` para a loja.
    hot_lead_threshold: int = 7

    @property
    def usa_banco(self) -> bool:
        return self.store_backend == "supabase"

    @classmethod
    def load(cls) -> "Config":
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY nao definida. Copie .env.example para .env.")

        username = os.getenv("TIKTOK_USERNAME", "").strip()
        if not username:
            raise RuntimeError("TIKTOK_USERNAME nao definida.")
        if not username.startswith("@"):
            username = "@" + username

        backend = os.getenv("STORE_BACKEND", "sqlite").strip().lower()
        if backend not in ("sqlite", "supabase"):
            raise RuntimeError(f"STORE_BACKEND invalido: {backend!r}. Use 'sqlite' ou 'supabase'.")

        return cls(
            anthropic_api_key=key,
            model=os.getenv("COPILOT_MODEL", "claude-opus-5"),
            tiktok_username=username,
            auto_reply_enabled=_bool("AUTO_REPLY_ENABLED"),
            auto_reply_max_per_min=int(os.getenv("AUTO_REPLY_MAX_PER_MIN", "4")),
            chrome_cdp_url=os.getenv("CHROME_CDP_URL", "http://localhost:9222"),
            replay_mode=_bool("REPLAY_MODE"),
            supervisor_interval_min=int(os.getenv("SUPERVISOR_INTERVAL_MIN", "15")),
            store_backend=backend,
            sqlite_path=os.getenv("SQLITE_PATH", "copilot.db"),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
            seller_id=os.getenv("SELLER_ID", "default"),
            refresh_seconds=int(os.getenv("REFRESH_SECONDS", "30")),
        )


@dataclass(frozen=True)
class Settings:
    """Preferencias da loja. Espelha a tabela `configuracoes`."""

    auto_reply_enabled: bool = False
    max_por_minuto: int = 4
    intents_auto: frozenset[str] = field(default_factory=lambda: frozenset(INTENTS_AUTO_PADRAO))
    tom_de_voz: str = ""
    instrucoes_extras: str = ""
    hot_lead_threshold: int = 7
    origem: str = "env"

    @classmethod
    def from_env(cls, cfg: Config) -> "Settings":
        return cls(
            auto_reply_enabled=cfg.auto_reply_enabled,
            max_por_minuto=cfg.auto_reply_max_per_min,
            intents_auto=frozenset(INTENTS_AUTO_PADRAO),
            hot_lead_threshold=cfg.hot_lead_threshold,
            origem="env",
        )

    @classmethod
    def from_row(cls, row: dict) -> "Settings":
        """Linha de `configuracoes`. Intents fora da lista permitida sao
        descartados aqui, nao no momento do envio -- assim o log de arranque ja
        mostra o que de fato vale."""
        brutos = set(row.get("intents_auto") or INTENTS_AUTO_PADRAO)
        recusados = brutos - INTENTS_AUTO_PERMITIDOS
        if recusados:
            log.warning(
                "Intents ignorados por politica de seguranca: %s. "
                "Essas mensagens continuam indo para o vendedor.",
                ", ".join(sorted(recusados)),
            )
        return cls(
            auto_reply_enabled=bool(row.get("auto_reply_enabled", False)),
            max_por_minuto=int(row.get("max_por_minuto") or 4),
            intents_auto=frozenset(brutos & INTENTS_AUTO_PERMITIDOS),
            tom_de_voz=(row.get("tom_de_voz") or "").strip(),
            instrucoes_extras=(row.get("instrucoes_extras") or "").strip(),
            hot_lead_threshold=int(row.get("hot_lead_threshold") or 7),
            origem="banco",
        )

    def prompt_extra(self) -> str:
        """Bloco que entra no system prompt com a voz configurada pela loja."""
        partes = []
        if self.tom_de_voz:
            partes.append(f"TOM DE VOZ DA LOJA: {self.tom_de_voz}")
        if self.instrucoes_extras:
            partes.append(f"INSTRUCOES DA LOJA:\n{self.instrucoes_extras}")
        return "\n\n".join(partes)
