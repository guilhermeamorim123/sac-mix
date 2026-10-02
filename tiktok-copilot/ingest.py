"""Leitura do chat da live via TikTokLive (websocket nao-oficial).

Publica cada comentario numa asyncio.Queue. Quem consome nao precisa saber de
onde veio -- o que facilita trocar a fonte depois (ex: replay de log gravado
para testar sem estar ao vivo).
"""
from __future__ import annotations

import asyncio
import logging

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent

from models import ChatMessage

log = logging.getLogger(__name__)

# De quanto em quanto tempo checar se a live ja abriu. Fixo e curto de
# proposito: o vendedor liga o agente antes de subir a transmissao, e nao pode
# ficar esperando um backoff crescer para o app perceber.
ESPERA_OFFLINE = 15


class ChatIngest:
    def __init__(self, username: str, queue: asyncio.Queue[ChatMessage]):
        self._client = TikTokLiveClient(unique_id=username)
        self._queue = queue
        self._username = username
        self.connected = asyncio.Event()
        self.stats = {"recebidas": 0, "descartadas": 0}
        self._register()

    def _register(self) -> None:
        @self._client.on(ConnectEvent)
        async def _(event: ConnectEvent) -> None:  # noqa: ARG001
            self.connected.set()
            log.info("Conectado a live de %s", self._username)

        @self._client.on(DisconnectEvent)
        async def _(event: DisconnectEvent) -> None:  # noqa: ARG001
            self.connected.clear()
            log.warning("Desconectado da live.")

        @self._client.on(CommentEvent)
        async def _(event: CommentEvent) -> None:
            texto = (event.comment or "").strip()
            if not texto:
                return

            msg = ChatMessage(
                message_id=str(getattr(event, "msg_id", "") or f"{event.user.unique_id}-{id(event)}"),
                user_id=str(event.user.user_id),
                username=event.user.unique_id,
                nickname=event.user.nickname or event.user.unique_id,
                text=texto,
            )
            self.stats["recebidas"] += 1

            try:
                self._queue.put_nowait(msg)
            except asyncio.QueueFull:
                # Fila cheia significa que a IA nao acompanha o ritmo do chat.
                # Descartar a mensagem e melhor que travar o websocket e cair
                # da live -- o log conta quanto se perdeu.
                self.stats["descartadas"] += 1
                log.warning("Fila cheia, mensagem descartada (total: %d)",
                            self.stats["descartadas"])

    async def run(self) -> None:
        """Conecta e fica ouvindo. Reconecta sozinho se a live cair.

        Pode ser iniciado ANTES da live: enquanto o vendedor nao abre a
        transmissao, fica checando em intervalo fixo e curto. "Ainda nao
        abriu" nao e erro -- tratar como erro produziria uma parede de
        ERROR no log e um backoff que faria o agente demorar ate um minuto
        para perceber que a live subiu.
        """
        tentativa = 0
        avisou = False
        while True:
            try:
                await self._client.start()
                # start() so retorna quando a live termina.
                tentativa = 0
                avisou = False
                log.info("A live encerrou. Seguindo de olho, caso volte.")
            except Exception as exc:  # noqa: BLE001 - a lib levanta varios tipos
                if self._esta_offline(exc):
                    if not avisou:
                        log.info(
                            "Aguardando %s abrir a live (checando a cada %ds). "
                            "Pode deixar rodando.", self._username, ESPERA_OFFLINE
                        )
                        avisou = True
                    await asyncio.sleep(ESPERA_OFFLINE)
                    continue

                tentativa += 1
                espera = min(60, 2 ** tentativa)
                log.error("Erro na conexao (%s). Tentando de novo em %ds.", exc, espera)
                await asyncio.sleep(espera)

    @staticmethod
    def _esta_offline(exc: Exception) -> bool:
        """Distingue "ainda nao abriu a live" de falha de verdade.

        Compara pelo NOME da excecao em vez de importar a classe: o caminho de
        import muda entre versoes da TikTokLive, e uma mudanca la nao pode
        transformar essa checagem num ImportError no meio da live.
        """
        nome = type(exc).__name__.lower()
        texto = str(exc).lower()
        return "useroffline" in nome or "offline" in texto or "not live" in texto

    async def stop(self) -> None:
        try:
            await self._client.disconnect()
        except Exception:  # noqa: BLE001
            pass


async def batcher(
    queue: asyncio.Queue[ChatMessage],
    window: float,
    max_size: int,
):
    """Agrupa mensagens numa janela curta e devolve lotes.

    Espera indefinidamente pela primeira mensagem, depois abre uma janela de
    `window` segundos para juntar o resto da rajada. Assim uma mensagem sozinha
    num chat parado nao fica presa esperando o timer fechar.
    """
    while True:
        primeira = await queue.get()
        lote = [primeira]
        prazo = asyncio.get_running_loop().time() + window

        while len(lote) < max_size:
            restante = prazo - asyncio.get_running_loop().time()
            if restante <= 0:
                break
            try:
                lote.append(await asyncio.wait_for(queue.get(), timeout=restante))
            except asyncio.TimeoutError:
                break

        yield lote
