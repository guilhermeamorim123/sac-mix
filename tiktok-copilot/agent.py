"""Orquestrador: junta ingest -> IA -> store -> sender.

Roda na maquina do vendedor, durante a live:

    python agent.py

Encerre com Ctrl+C. Ao encerrar, ele fecha a sessao e grava as metricas da
live (que alimentam a pagina "Lives Prontas" do painel).

De onde vem cada coisa:

- catalogo, frete, base de conhecimento e preferencias da loja -> do banco,
  quando `STORE_BACKEND=supabase` (o lojista edita pelo painel). No modo local
  caem para `products.json` e `.env`.
- comandos do painel (enviar resposta, pausar, check-in) -> tabela `commands`,
  por polling.
- mensagens, leads e a avaliacao da live -> escritos de volta no banco, que e
  o que o painel le em tempo real.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import ai
import store as store_mod
from catalog import Catalog
from config import Config, Settings
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
    """Contadores da live em curso, gravados como uma linha em `lives`.

    O `id` nasce aqui, antes da primeira mensagem, para que cada linha de
    `messages` ja aponte para a live certa enquanto ela acontece.
    """

    def __init__(self, titulo: str, tipo: str = "ao_vivo"):
        self.id = str(uuid4())
        self.titulo = titulo
        self.tipo = tipo
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
            "id": self.id,
            "titulo": self.titulo,
            "tipo": self.tipo,
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
        self.session = LiveSession(
            f"Live {datetime.now():%d/%m %H:%M}",
            tipo="replay" if cfg.replay_mode else "ao_vivo",
        )

        self.store = store_mod.build(cfg)
        self.ingest = ChatIngest(cfg.tiktok_username, self.queue)

        # Preenchidos em `start()`, depois que o banco responde.
        self.catalogo = Catalog()
        self.settings = Settings.from_env(cfg)
        self.classifier: ai.Classifier | None = None

        # A trava de supervisao so entra no modo replay: numa live de verdade o
        # vendedor ja esta na frente da camera.
        self.gate = SupervisionGate(cfg.supervisor_interval_min)
        self.sender = ChatSender(
            cdp_url=cfg.chrome_cdp_url,
            max_per_min=cfg.auto_reply_max_per_min,
            enabled=False,  # definido em `start()`, ja com o valor do banco
            supervision_check=self.gate.check if cfg.replay_mode else None,
        )

    # -- arranque ----------------------------------------------------------

    async def start(self) -> None:
        await self.store.init()
        await self._carregar_contexto()

        self.classifier = ai.Classifier(
            self.cfg.anthropic_api_key, self.cfg.model, self.catalogo, self.settings
        )
        await ai.warmup(self.classifier)

        if self.settings.auto_reply_enabled:
            if self.cfg.replay_mode and not self.gate.presente:
                log.warning(
                    "Modo replay sem check-in de supervisor: auto-envio comeca travado. "
                    "Marque presenca no painel para liberar."
                )
            self.sender.enabled = True
            await self.sender.connect()
        else:
            log.info("Auto-envio DESLIGADO. O painel so sugere; ninguem digita sozinho.")

        tarefas = [
            asyncio.create_task(self.ingest.run(), name="ingest"),
            asyncio.create_task(self._process_loop(), name="process"),
            asyncio.create_task(self._command_loop(), name="commands"),
            asyncio.create_task(self._refresh_loop(), name="refresh"),
            asyncio.create_task(self._watchdog_loop(), name="watchdog"),
        ]

        try:
            await asyncio.gather(*tarefas)
        except asyncio.CancelledError:
            for t in tarefas:
                t.cancel()
            raise

    async def _carregar_contexto(self) -> None:
        """Catalogo e preferencias, do banco quando houver."""
        catalogo = await self.store.fetch_catalog()
        if catalogo is None:
            catalogo = Catalog.from_json()
        self.catalogo = catalogo

        settings = await self.store.fetch_settings()
        if settings is not None:
            self.settings = settings
        self.sender.max_per_min = self.settings.max_por_minuto

        if self.catalogo.vazio:
            # Sem catalogo a IA nao tem o que citar: toda resposta viraria
            # requires_human. Melhor parar aqui do que descobrir no ar.
            raise RuntimeError(
                "Catalogo vazio (origem: {}). Cadastre os produtos na aba Produtos "
                "do painel, ou preencha o products.json no modo local.".format(
                    self.catalogo.origem
                )
            )

        log.info(
            "Catalogo (%s): %d produtos, %d regras de frete, %d artigos.",
            self.catalogo.origem, len(self.catalogo.produtos),
            len(self.catalogo.frete), len(self.catalogo.conhecimento),
        )
        log.info(
            "Configuracoes (%s): auto-resposta %s, teto %d/min, intents [%s], lead quente >= %d.",
            self.settings.origem,
            "LIGADA" if self.settings.auto_reply_enabled else "desligada",
            self.settings.max_por_minuto,
            ", ".join(sorted(self.settings.intents_auto)) or "nenhum",
            self.settings.hot_lead_threshold,
        )

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
        if analise.lead_score >= self.settings.hot_lead_threshold:
            self.session.leads_captados += 1
        if msg.whatsapp:
            self.session.whatsapps.add(msg.whatsapp)

        await self.store.save(msg, analise, live_id=self.session.id)

        quente = analise.lead_score >= self.settings.hot_lead_threshold
        log.info("%s[%s/%d] %s: %s", "HOT " if quente else "    ",
                 analise.intent, analise.lead_score, msg.nickname, msg.text[:60])

        if msg.whatsapp:
            log.info("     WhatsApp capturado: %s (@%s)", msg.whatsapp, msg.username)

        if analise.can_auto_send(self.settings.intents_auto) and analise.suggested_reply:
            if await self.sender.send(analise.suggested_reply):
                self.session.autoenviadas += 1
                await self.store.mark_replied(msg.message_id, analise.suggested_reply, "auto")

    # -- vigia de seguranca ------------------------------------------------

    async def _watchdog_loop(self) -> None:
        """Procura aviso do TikTok na tela e corta o auto-envio na hora.

        Só o auto-envio. A leitura do chat continua, e encerrar a live segue
        sendo decisão do vendedor: um falso positivo não pode custar a
        transmissão inteira. O que ele perde no pior caso é o robô digitando
        por ele — o que, se o TikTok já está avisando, é o que ele quer perder.
        """
        while True:
            await asyncio.sleep(self.cfg.watchdog_seconds)
            if self.sender.travado:
                continue
            try:
                aviso = await self.sender.checar_avisos()
            except Exception as exc:  # noqa: BLE001
                log.debug("Watchdog falhou nesta volta: %s", exc)
                continue
            if aviso:
                await self._travar_envio(f"aviso do TikTok na tela: \"{aviso}\"")

    async def _travar_envio(self, motivo: str) -> None:
        self.sender.travar(motivo)
        # Desliga na origem para a chave aparecer desligada no painel; sem isso
        # o vendedor não fica sabendo, e o próximo refresh acharia que está tudo
        # bem.
        await self.store.desligar_auto_reply(motivo)
        self.settings = replace(self.settings, auto_reply_enabled=False)

    # -- catalogo e configuracoes durante a live ---------------------------

    async def _refresh_loop(self) -> None:
        """Rele o banco de tempos em tempos.

        O lojista importa planilha, corrige preco ou desliga a auto-resposta no
        meio da live -- e isso precisa chegar aqui sem reiniciar o agente.
        """
        if not self.cfg.usa_banco:
            return

        while True:
            await asyncio.sleep(self.cfg.refresh_seconds)
            try:
                await self._aplicar_refresh()
            except Exception as exc:  # noqa: BLE001
                # Mantem o que ja estava valendo. A live nao para por causa de
                # uma falha de rede.
                log.warning("Refresh falhou (seguindo com o contexto atual): %s", exc)

    async def _aplicar_refresh(self) -> None:
        novo_catalogo = await self.store.fetch_catalog()
        novas_settings = await self.store.fetch_settings()

        mudou_catalogo = (
            novo_catalogo is not None
            and not novo_catalogo.vazio
            and novo_catalogo.fingerprint != self.catalogo.fingerprint
        )
        if mudou_catalogo:
            self.catalogo = novo_catalogo
            log.info("Catalogo atualizado pelo painel: %d produtos.",
                     len(self.catalogo.produtos))

        if novas_settings is None:
            if mudou_catalogo:
                self.classifier.recarregar(self.catalogo, self.settings)
            return

        anterior, self.settings = self.settings, novas_settings

        if novas_settings.max_por_minuto != anterior.max_por_minuto:
            self.sender.max_per_min = novas_settings.max_por_minuto
            log.info("Teto de auto-envio agora e %d/min.", novas_settings.max_por_minuto)

        # So mexe no interruptor quando o valor MUDOU no banco. Do contrario um
        # "PARAR TUDO" dado pelo painel seria desfeito no proximo refresh.
        if novas_settings.auto_reply_enabled != anterior.auto_reply_enabled:
            log.warning("Auto-envio %s pelas Configuracoes do painel.",
                        "LIGADO" if novas_settings.auto_reply_enabled else "DESLIGADO")
            if novas_settings.auto_reply_enabled:
                # Religar a chave no painel e o rearme humano da trava: a
                # pessoa viu a chave desligada e decidiu ligar de novo.
                self.sender.destravar()
                self.sender.enabled = True
                await self.sender.connect()
            else:
                self.sender.enabled = False

        if novas_settings.intents_auto != anterior.intents_auto:
            log.info("Intents com auto-resposta agora: %s",
                     ", ".join(sorted(novas_settings.intents_auto)) or "nenhum")

        mudou_voz = (
            novas_settings.tom_de_voz != anterior.tom_de_voz
            or novas_settings.instrucoes_extras != anterior.instrucoes_extras
        )
        if mudou_catalogo or mudou_voz:
            self.classifier.recarregar(self.catalogo, self.settings)

    # -- comandos vindos do painel ----------------------------------------

    async def _command_loop(self) -> None:
        while True:
            await asyncio.sleep(2)
            for cmd in await self.store.pending_commands():
                await self._run_command(cmd)

    async def _run_command(self, cmd: dict) -> None:
        kind = cmd.get("kind")
        payload = cmd.get("payload") or {}
        status = "done"

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
            if not enviado:
                status = "failed"

        elif kind == "pause_auto":
            self.sender.enabled = False
            log.warning("Auto-envio PAUSADO pelo painel.")

        elif kind == "resume_auto":
            self.sender.enabled = True
            log.warning("Auto-envio RETOMADO pelo painel.")

        elif kind == "supervisor_checkin":
            self.gate.checkin(payload.get("supervisor", "desconhecido"))

        elif kind == "replay_live":
            # O contador de replays ja e incrementado por trigger no banco. O
            # que falta e o modulo que joga o video no RTMP -- ate ele existir,
            # o comando volta como falho em vez de fingir que rodou.
            log.error(
                "Comando replay_live recebido (live %s), mas o modulo de RTMP/OBS "
                "ainda nao existe. Reexiba manualmente pelo OBS.",
                payload.get("live_id", "?"),
            )
            status = "failed"

        else:
            log.warning("Comando desconhecido: %s", kind)
            status = "failed"

        await self.store.ack_command(cmd["id"], status)

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
        try:
            await tarefa
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            # Falha no arranque (catalogo vazio, banco fora do ar). Nao grava
            # uma live vazia no painel so porque o agente nao subiu.
            log.error("O agente nao subiu: %s", exc)
            await copilot.store.close()
            return
        await copilot.shutdown()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
