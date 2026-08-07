"""Persistencia com dois backends intercambiaveis.

- sqlite:   tudo local, zero setup. Bom para o primeiro teste.
- supabase: o painel do Lovable le em tempo real e escreve comandos de volta.

O agente nao sabe qual esta ativo -- so conhece a interface `Store`.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from catalog import Catalog
from config import Settings
from models import Analysis, ChatMessage, now

log = logging.getLogger(__name__)


class Store(ABC):
    @abstractmethod
    async def init(self) -> None: ...

    @abstractmethod
    async def save(self, msg: ChatMessage, analysis: Analysis,
                   live_id: str | None = None) -> None: ...

    @abstractmethod
    async def mark_replied(self, message_id: str, reply: str, source: str) -> None: ...

    @abstractmethod
    async def pending_commands(self) -> list[dict]:
        """Comandos que o painel enfileirou (ex: enviar uma resposta aprovada)."""

    @abstractmethod
    async def ack_command(self, command_id: str, status: str = "done") -> None: ...

    @abstractmethod
    async def save_live(self, resumo: dict) -> None:
        """Grava a live encerrada; alimenta a pagina 'Lives Prontas'."""

    async def fetch_catalog(self) -> Catalog | None:
        """Catalogo mantido pelo painel. None = o agente usa o products.json."""
        return None

    async def fetch_settings(self) -> Settings | None:
        """Preferencias da loja. None = o agente usa o que veio do .env."""
        return None

    async def close(self) -> None:
        return None


def avaliar(resumo: dict) -> tuple[int, str, str]:
    """Nota de 0-100, rating e recomendacao de replay para uma live encerrada.

    Enquanto a API do TikTok Shop nao esta ligada, `vendas` chega zerado e a
    nota sai so do engajamento: ritmo do chat e quanto desse chat virou lead
    quente. Quando as vendas entrarem, elas passam a dominar o calculo -- que e
    o certo, porque e o que de fato paga a conta.
    """
    duracao = max(1, int(resumo.get("duracao_min") or 1))
    comentarios = int(resumo.get("comentarios") or 0)
    leads = int(resumo.get("leads_captados") or 0)
    vendas = int(resumo.get("vendas") or 0)

    comentarios_hora = comentarios * 60 / duracao
    vendas_hora = vendas * 60 / duracao
    taxa_lead = (leads / comentarios * 100) if comentarios else 0.0

    if vendas > 0:
        # 12 vendas/hora = referencia de live muito boa.
        score = min(100, round(vendas_hora / 12 * 100))
    else:
        # 150 comentarios/hora e 10% deles virando lead = referencia.
        # A conversao pesa mais que o volume de propósito: chat cheio de gente
        # que nao compra nao justifica reexibir a live.
        ritmo = min(1.0, comentarios_hora / 150)
        conversao = min(1.0, taxa_lead / 10)
        score = round((ritmo * 0.3 + conversao * 0.7) * 100)

    if score >= 70:
        rating = "boa"
        recomendacao = (
            f"Vale rodar de novo. {leads} leads quentes em {duracao} min "
            f"({taxa_lead:.0f}% do chat). Reexiba em horario de pico."
        )
    elif score >= 40:
        rating = "regular"
        recomendacao = (
            f"Rode de novo so se faltar conteudo. {comentarios_hora:.0f} comentarios/hora "
            f"esta na media -- ajuste a oferta antes de reexibir."
        )
    else:
        rating = "ruim"
        recomendacao = (
            f"Nao reexiba. Engajamento baixo ({comentarios_hora:.0f} comentarios/hora, "
            f"{leads} leads). Regrave com outra abordagem."
        )

    return score, rating, recomendacao


# --------------------------------------------------------------------------
# SQLite
# --------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS messages (
    message_id   TEXT PRIMARY KEY,
    seller_id    TEXT NOT NULL,
    live_id      TEXT,
    user_id      TEXT NOT NULL,
    username     TEXT NOT NULL,
    nickname     TEXT,
    text         TEXT NOT NULL,
    intent       TEXT,
    lead_score   INTEGER DEFAULT 0,
    suggested_reply   TEXT,
    requires_human    INTEGER DEFAULT 1,
    product_mentioned TEXT,
    whatsapp     TEXT,
    replied_with TEXT,
    reply_source TEXT,
    received_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_score ON messages(lead_score DESC);

CREATE TABLE IF NOT EXISTS lives (
    id             TEXT PRIMARY KEY,
    seller_id      TEXT NOT NULL,
    titulo         TEXT NOT NULL,
    tipo           TEXT DEFAULT 'ao_vivo',
    gravada_em     TEXT NOT NULL,
    duracao_min    INTEGER,
    comentarios    INTEGER DEFAULT 0,
    leads_captados INTEGER DEFAULT 0,
    vendas         INTEGER DEFAULT 0,
    receita        REAL DEFAULT 0,
    rating         TEXT,
    score          INTEGER,
    recomendacao   TEXT,
    replays        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS leads (
    seller_id    TEXT NOT NULL,
    username     TEXT NOT NULL,
    nickname     TEXT,
    whatsapp     TEXT,
    best_score   INTEGER DEFAULT 0,
    last_message TEXT,
    messages_count INTEGER DEFAULT 0,
    first_seen_at  TEXT,
    last_seen_at   TEXT,
    PRIMARY KEY (seller_id, username)
);
"""


class SqliteStore(Store):
    def __init__(self, path: str, seller_id: str):
        self._path = Path(path)
        self._seller = seller_id
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.executescript(_DDL)
        # Banco criado por uma versao anterior nao tem live_id. Migra na hora
        # em vez de exigir que o vendedor apague o arquivo.
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE messages ADD COLUMN live_id TEXT")
        self._conn.commit()
        log.info("SQLite pronto em %s", self._path.resolve())

    async def save(self, msg: ChatMessage, analysis: Analysis,
                   live_id: str | None = None) -> None:
        assert self._conn is not None
        whats = msg.whatsapp
        async with self._lock:
            await asyncio.to_thread(self._save_sync, msg, analysis, whats, live_id)

    def _save_sync(self, msg: ChatMessage, a: Analysis, whats: str | None,
                   live_id: str | None) -> None:
        assert self._conn is not None
        ts = msg.received_at.isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO messages
               (message_id, seller_id, live_id, user_id, username, nickname, text,
                intent, lead_score, suggested_reply, requires_human,
                product_mentioned, whatsapp, received_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (msg.message_id, self._seller, live_id, msg.user_id, msg.username,
             msg.nickname, msg.text, a.intent, a.lead_score, a.suggested_reply,
             int(a.requires_human), a.product_mentioned, whats, ts),
        )
        # O lead guarda o MELHOR score que a pessoa ja teve, nao o ultimo: quem
        # disse "quero 2" e depois mandou um emoji continua sendo lead quente.
        self._conn.execute(
            """INSERT INTO leads
               (seller_id, username, nickname, whatsapp, best_score, last_message,
                messages_count, first_seen_at, last_seen_at)
               VALUES (?,?,?,?,?,?,1,?,?)
               ON CONFLICT(seller_id, username) DO UPDATE SET
                 nickname     = excluded.nickname,
                 whatsapp     = COALESCE(excluded.whatsapp, leads.whatsapp),
                 best_score   = MAX(leads.best_score, excluded.best_score),
                 last_message = excluded.last_message,
                 messages_count = leads.messages_count + 1,
                 last_seen_at = excluded.last_seen_at""",
            (self._seller, msg.username, msg.nickname, whats, a.lead_score,
             msg.text, ts, ts),
        )
        self._conn.commit()

    async def mark_replied(self, message_id: str, reply: str, source: str) -> None:
        assert self._conn is not None
        async with self._lock:
            await asyncio.to_thread(
                lambda: (
                    self._conn.execute(
                        "UPDATE messages SET replied_with=?, reply_source=? WHERE message_id=?",
                        (reply, source, message_id),
                    ),
                    self._conn.commit(),
                )
            )

    async def pending_commands(self) -> list[dict]:
        return []  # sem painel remoto no modo local

    async def ack_command(self, command_id: str, status: str = "done") -> None:
        return None

    async def save_live(self, resumo: dict) -> None:
        assert self._conn is not None
        score, rating, recomendacao = avaliar(resumo)
        async with self._lock:
            await asyncio.to_thread(
                lambda: (
                    self._conn.execute(
                        """INSERT INTO lives
                           (id, seller_id, titulo, tipo, gravada_em, duracao_min,
                            comentarios, leads_captados, rating, score, recomendacao)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (resumo.get("id") or str(uuid4()), self._seller,
                         resumo["titulo"], resumo.get("tipo", "ao_vivo"),
                         now().isoformat(), resumo["duracao_min"], resumo["comentarios"],
                         resumo["leads_captados"], rating, score, recomendacao),
                    ),
                    self._conn.commit(),
                )
            )
        log.info("Live avaliada: %s (%d/100) -- %s", rating, score, recomendacao)

    async def close(self) -> None:
        if self._conn:
            self._conn.close()


# --------------------------------------------------------------------------
# Supabase
# --------------------------------------------------------------------------

class SupabaseStore(Store):
    """O client oficial e sincrono, entao cada chamada vai para uma thread."""

    def __init__(self, url: str, service_key: str, seller_id: str):
        if not url or not service_key:
            raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY sao obrigatorios.")
        self._url, self._key, self._seller = url, service_key, seller_id
        self._client = None

    async def init(self) -> None:
        from supabase import create_client

        self._client = await asyncio.to_thread(create_client, self._url, self._key)
        log.info("Supabase conectado (seller_id=%s)", self._seller)

    async def save(self, msg: ChatMessage, analysis: Analysis,
                   live_id: str | None = None) -> None:
        row = {
            "message_id": msg.message_id,
            "seller_id": self._seller,
            "live_id": live_id,
            "user_id": msg.user_id,
            "username": msg.username,
            "nickname": msg.nickname,
            "text": msg.text,
            "intent": analysis.intent,
            "lead_score": analysis.lead_score,
            "suggested_reply": analysis.suggested_reply,
            "requires_human": analysis.requires_human,
            "product_mentioned": analysis.product_mentioned,
            "whatsapp": msg.whatsapp,
            "received_at": msg.received_at.isoformat(),
        }
        try:
            await asyncio.to_thread(
                lambda: self._client.table("messages").upsert(row).execute()
            )
            # A consolidacao do lead vive numa funcao SQL (ver schema.sql) para
            # ficar atomica e nao depender de round-trip extra daqui.
            await asyncio.to_thread(
                lambda: self._client.rpc("upsert_lead", {
                    "p_seller_id": self._seller,
                    "p_username": msg.username,
                    "p_nickname": msg.nickname,
                    "p_whatsapp": msg.whatsapp,
                    "p_score": analysis.lead_score,
                    "p_last_message": msg.text,
                }).execute()
            )
        except Exception as exc:  # noqa: BLE001 - rede/HTTP variam demais
            log.error("Falha ao gravar no Supabase (%s): %s", msg.message_id, exc)

    async def mark_replied(self, message_id: str, reply: str, source: str) -> None:
        try:
            await asyncio.to_thread(
                lambda: self._client.table("messages")
                .update({"replied_with": reply, "reply_source": source})
                .eq("message_id", message_id)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao marcar resposta (%s): %s", message_id, exc)

    async def pending_commands(self) -> list[dict]:
        try:
            res = await asyncio.to_thread(
                lambda: self._client.table("commands")
                .select("*")
                .eq("seller_id", self._seller)
                .eq("status", "pending")
                .order("created_at")
                .limit(20)
                .execute()
            )
            return res.data or []
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao ler comandos: %s", exc)
            return []

    async def ack_command(self, command_id: str, status: str = "done") -> None:
        try:
            await asyncio.to_thread(
                lambda: self._client.table("commands")
                .update({"status": status, "done_at": now().isoformat()})
                .eq("id", command_id)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao confirmar comando %s: %s", command_id, exc)

    async def save_live(self, resumo: dict) -> None:
        score, rating, recomendacao = avaliar(resumo)
        row = {
            "seller_id": self._seller,
            "titulo": resumo["titulo"],
            "tipo": resumo.get("tipo", "ao_vivo"),
            "duracao_min": resumo["duracao_min"],
            "comentarios": resumo["comentarios"],
            "leads_captados": resumo["leads_captados"],
            "rating": rating,
            "score": score,
            "recomendacao": recomendacao,
        }
        # O id nasce no agente, no inicio da live, para que cada mensagem ja
        # grave o live_id certo enquanto a transmissao acontece.
        if resumo.get("id"):
            row["id"] = resumo["id"]
        try:
            await asyncio.to_thread(
                lambda: self._client.table("lives").insert(row).execute()
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao gravar a live: %s", exc)
        log.info("Live avaliada: %s (%d/100) -- %s", rating, score, recomendacao)

    # -- catalogo e configuracoes mantidos pelo painel ---------------------

    async def fetch_catalog(self) -> Catalog:
        """Le produtos, frete e base de conhecimento da loja.

        Diferente do resto desta classe, aqui a excecao SOBE em vez de virar
        log. Catalogo e o que impede a IA de inventar preco: rodar com dado
        velho porque a rede falhou e pior do que nao rodar. Quem chama decide
        -- no arranque o agente aborta, no refresh ele mantem o que ja tinha.
        """
        produtos, frete, conhecimento = await asyncio.gather(
            asyncio.to_thread(
                lambda: self._client.table("produtos")
                .select("nome,preco,estoque,cores,tamanhos,obs")
                .eq("seller_id", self._seller).eq("ativo", True)
                .order("ordem").execute()
            ),
            asyncio.to_thread(
                lambda: self._client.table("frete_regras")
                .select("regiao,descricao")
                .eq("seller_id", self._seller)
                .order("ordem").execute()
            ),
            asyncio.to_thread(
                lambda: self._client.table("base_conhecimento")
                .select("titulo,conteudo")
                .eq("seller_id", self._seller).eq("ativo", True)
                .order("ordem").execute()
            ),
        )
        return Catalog.from_rows(
            produtos.data or [], frete.data or [], conhecimento.data or []
        )

    async def fetch_settings(self) -> Settings | None:
        try:
            res = await asyncio.to_thread(
                lambda: self._client.table("configuracoes")
                .select("*").eq("seller_id", self._seller)
                .limit(1).execute()
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao ler configuracoes: %s", exc)
            return None

        if not res.data:
            log.warning(
                "Sem linha em `configuracoes` para seller_id=%s. "
                "Usando o que veio do .env.", self._seller
            )
            return None
        return Settings.from_row(res.data[0])


def build(cfg) -> Store:
    if cfg.store_backend == "supabase":
        return SupabaseStore(cfg.supabase_url, cfg.supabase_service_key, cfg.seller_id)
    return SqliteStore(cfg.sqlite_path, cfg.seller_id)
