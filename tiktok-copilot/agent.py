"""Orquestrador: junta ingest -> IA -> store -> sender.

Roda na maquina do vendedor, durante a live:

    python agent.py

Encerre com Ctrl+C. Ao encerrar, ele fecha a sessao e grava as metricas da
live (que alimentam a pagina "Lives Prontas" do painel).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from datetime import datetime, timezone

import ai
import catalog
import store as store_mod
from config import Config
from ingest import ChatIngest, batcher
from models import Analysis, ChatMessage
from sender import ChatSender, SupervisionGate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)-10s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent")


class LiveSession:
    """Contadores da live em curso, gravados como uma linha em `lives`."""

    def __init__(self, titulo: str):
        self.titulo = titulo
        self.inicio = datetime.now(timezone.utc)
        self.comentarios = 0
        self.leads_captados = 0
        self.whatsapps: set[str] = set()
        self.autoenviadas = 0

    @property
    def duracao_min(self) -> int:
        delta = datetime.now(timezone.utc) - self.inicio
        return max(1, int(delta.total_seconds() // 60))

    def resumo(self) -> dict:
        return {
            "titulo": self.titulo,
            "duracao_min": self.duracao_min,
            "comentarios": self.comentarios,
            "leads_captados": self.leads_captados,
            "whatsapps": len(self.whatsapps),
            "respostas_automaticas": self.autoenviadas,
        }


class Copilot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.queue: asyncio.Queue[ChatMessage] = asyncio.Queue(maxsize=500)
        self.session = LiveSession(f"Live {datetime.now():%d/%m %H:%M}")

        produtos = catalog.load()
        frete = catalog.load_frete()
        log.info("Catalogo carregado: %d produtos.", len(produtos))

        self.store = store_mod.build(cfg)
        self.classifier = ai.Classifier(cfg.anthropic_api_key, cfg.model, produtos, frete)
        self.ingest = ChatIngest(cfg.tiktok_username, self.queue)

        # A trava de supervisao so entra no modo replay: numa live de verdade o
        # vendedor ja esta na frente da camera.
        self.gate = SupervisionGate(cfg.supervisor_interval_min)
        self.sender = ChatSender(
            cdp_url=cfg.chrome_cdp_url,
            max_per_min=cfg.auto_reply_max_per_min,
            enabled=cfg.auto_reply_enabled,
            supervision_check=self.gate.check if cfg.replay_mode else None,
        )

    async def start(self) -> None:
        await self.store.init()
        await ai.warmup(self.classifier)

        if self.cfg.auto_reply_enabled:
            if self.cfg.replay_mode and not self.gate.presente:
                log.warning(
                    "Modo replay sem check-in de supervisor: auto-envio comeca travado. "
                    "Marque presenca no painel para liberar."
                )
            await self.sender.connect()
        else:
            log.info("Auto-envio DESLIGADO. O painel so sugere; ninguem digita sozinho.")

        tarefas = [
            asyncio.create_task(self.ingest.run(), name="ingest"),
            asyncio.create_task(self._process_loop(), name="process"),
            asyncio.create_task(self._command_loop(), name="commands"),
        ]

        try:
            await asyncio.gather(*tarefas)
        except asyncio.CancelledError:
            for t in tarefas:
                t.cancel()
            raise

    # -- laco principal ----------------------------------------------------

    async def _process_loop(self) -> None:
        async for lote in batcher(self.queue, self.cfg.batch_window_seconds,
                                  self.cfg.batch_max_size):
            try:
                analises = await self.classifier.analyze(lote)
            except Exception:  # noqa: BLE001
                log.exception("Erro inesperado ao classificar; lote descartado.")
                continue

            for msg, analise in zip(lote, analises):
                await self._handle(msg, analise)

    async def _handle(self, msg: ChatMessage, analise: Analysis) -> None:
        self.session.comentarios += 1
        if analise.lead_score >= self.cfg.hot_lead_threshold:
            self.session.leads_captados += 1
        if msg.whatsapp:
            self.session.whatsapps.add(msg.whatsapp)

        await self.store.save(msg, analise)

        marcador = "HOT " if analise.lead_score >= self.cfg.hot_lead_threshold else "    "
        log.info("%s[%s/%d] %s: %s", marcador, analise.intent, analise.lead_score,
                 msg.nickname, msg.text[:60])

        if msg.whatsapp:
            log.info("     WhatsApp capturado: %s (@%s)", msg.whatsapp, msg.username)

        if analise.can_auto_send and analise.suggested_reply:
            if await self.sender.send(analise.suggested_reply):
                self.session.autoenviadas += 1
                await self.store.mark_replied(msg.message_id, analise.suggested_reply, "auto")

    # -- comandos vindos do painel ----------------------------------------

    async def _command_loop(self) -> None:
        while True:
            await asyncio.sleep(2)
            for cmd in await self.store.pending_commands():
                await self._run_command(cmd)

    async def _run_command(self, cmd: dict) -> None:
        kind = cmd.get("kind")
        payload = cmd.get("payload") or {}

        if kind == "send_reply":
            texto = payload.get("text", "")
            # Aprovacao humana explicita: passa por cima do filtro de intent,
            # mas continua respeitando throttle e supervisao.
            antes = self.sender.enabled
            self.sender.enabled = True
            try:
                enviado = await self.sender.send(texto)
            finally:
                self.sender.enabled = antes
            if enviado and payload.get("message_id"):
                await self.store.mark_replied(payload["message_id"], texto, "manual")

        elif kind == "pause_auto":
            self.sender.enabled = False
            log.warning("Auto-envio PAUSADO pelo painel.")

        elif kind == "resume_auto":
            self.sender.enabled = True
            log.warning("Auto-envio RETOMADO pelo painel.")

        elif kind == "supervisor_checkin":
            self.gate.checkin(payload.get("supervisor", "desconhecido"))

        await self.store.ack_command(cmd["id"])

    # -- encerramento ------------------------------------------------------

    async def shutdown(self) -> None:
        log.info("Encerrando...")
        resumo = self.session.resumo()
        await self.store.save_live(resumo)
        await self.ingest.stop()
        await self.sender.close()
        await self.store.close()

        log.info("--- Resumo da live ---")
        for chave, valor in resumo.items():
            log.info("  %-22s %s", chave, valor)
        log.info("  mensagens descartadas  %s", self.ingest.stats["descartadas"])


async def main() -> None:
    cfg = Config.load()
    copilot = Copilot(cfg)

    parar = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows nao tem SIGTERM
            loop.add_signal_handler(sig, parar.set)

    tarefa = asyncio.create_task(copilot.start())
    try:
        await asyncio.wait([tarefa, asyncio.create_task(parar.wait())],
                           return_when=asyncio.FIRST_COMPLETED)
    finally:
        tarefa.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tarefa
        await copilot.shutdown()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
