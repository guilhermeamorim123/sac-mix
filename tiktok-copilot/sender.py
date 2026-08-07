"""Envio automatico de mensagens no chat da live via Playwright.

AVISO: o TikTok nao tem API de envio. Isto automatiza a interface web, o que
contraria os Termos de Uso e pode levar a banimento da conta. Decisao do dono
do projeto, tomada com ciencia do risco. Teste em conta secundaria antes.

Tres travas embutidas, todas checadas antes de cada envio:

1. kill switch  -- `enabled`, desligavel em runtime sem parar o resto do agente
2. throttle     -- teto de mensagens por minuto, com intervalo aleatorio
3. supervisao   -- callback externo que precisa autorizar (usado no replay)

O agente NAO faz login. O vendedor abre o Chrome em modo debug e loga na mao;
o Playwright so se anexa a essa sessao. Assim a senha do TikTok nunca passa
por este codigo.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from collections import deque
from typing import Awaitable, Callable

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

log = logging.getLogger(__name__)

LIVE_CENTER_URL = "https://livecenter.tiktok.com/live_monitor"

# O DOM do TikTok muda sem aviso. Tentamos varios seletores em ordem; se todos
# falharem, o log diz exatamente isso em vez de o envio sumir em silencio.
INPUT_SELECTORS = [
    'div[contenteditable="true"][data-e2e*="comment"]',
    'div[contenteditable="true"][placeholder]',
    'textarea[data-e2e*="comment"]',
    'input[data-e2e*="comment"]',
    'div[contenteditable="true"]',
]

# Depois de tantas falhas seguidas de envio, o auto-envio se trava sozinho.
# Falhar tres vezes em sequencia nao e azar: ou o DOM mudou, ou tem alguma
# coisa barrando do outro lado.
LIMITE_FALHAS_SEGUIDAS = 3

# Idem para mensagens que "saem" sem erro e nao aparecem no chat -- o sinal
# classico de shadow-block. E o caso mais perigoso, porque nao avisa.
LIMITE_SEM_ECO = 2

# Coleta o texto so de elementos que sao aviso/toast/modal. De proposito NAO
# varre a pagina inteira: o chat da live esta no DOM, e um espectador digitando
# "isso e violacao" travaria o envio a toa.
_JS_COLETA_ALERTAS = """
() => {
  const seletores = [
    '[role="alert"]', '[role="dialog"]', '[role="status"]', '[aria-live]',
    '[class*="toast" i]', '[class*="notice" i]', '[class*="notif" i]',
    '[class*="warn" i]', '[class*="alert" i]', '[class*="banner" i]',
    '[class*="violation" i]', '[class*="penalty" i]', '[class*="modal" i]'
  ];
  const vistos = new Set();
  for (const s of seletores) {
    for (const el of document.querySelectorAll(s)) {
      const t = (el.innerText || '').trim();
      if (t && t.length < 400) vistos.add(t);
    }
  }
  return Array.from(vistos).slice(0, 40);
}
"""

# A interface do LIVE Center aparece em portugues ou em ingles conforme a
# conta, entao os dois idiomas entram.
AVISO_PADROES = [
    r"viola[cç]",
    r"violat",
    r"advert[eê]nc",
    r"\bwarning\b",
    r"restri[cç]",
    r"restrict",
    r"diretrizes da comunidade",
    r"community guidelines",
    r"penalidad",
    r"\bpenalt",
    r"suspens",
    r"\bbanid",
    r"n[aã]o foi poss[ií]vel enviar",
    r"coment[aá]rio[^.]{0,30}(removid|bloquead|ocultad)",
    r"comment[^.]{0,30}(removed|blocked|hidden)",
    r"sua live[^.]{0,40}(aviso|advert|encerrad)",
    r"your live[^.]{0,40}(warning|ended)",
    r"conta[^.]{0,30}(restrit|suspens|limitad)",
    r"account[^.]{0,30}(restrict|suspend|limit)",
]

_AVISO_RE = re.compile("|".join(AVISO_PADROES), re.IGNORECASE)


class ChatSender:
    def __init__(
        self,
        cdp_url: str,
        max_per_min: int,
        enabled: bool = False,
        supervision_check: Callable[[], Awaitable[bool]] | None = None,
    ):
        self._cdp_url = cdp_url
        # publico: o painel pode mudar o teto no meio da live
        self.max_per_min = max_per_min
        self.enabled = enabled
        self._supervision_check = supervision_check

        self._playwright = None
        self._browser = None
        self._page = None
        self._sent_at: deque[float] = deque()
        self._lock = asyncio.Lock()

        # Trava de seguranca. Uma vez acionada, nenhum envio passa ate um
        # humano rearmar pelo painel -- nem o comando "Enviar", que e aprovacao
        # humana de UMA mensagem, nao de continuar automatizando.
        self.travado = False
        self.motivo_trava: str | None = None
        self._falhas_seguidas = 0
        self._sem_eco = 0

    # -- ciclo de vida -----------------------------------------------------

    async def connect(self) -> bool:
        """Anexa ao Chrome ja aberto e logado. Ver README para o comando."""
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect_over_cdp(self._cdp_url)
        except PlaywrightError as exc:
            log.error(
                "Nao consegui anexar ao Chrome em %s (%s). "
                "Auto-envio fica desligado; o painel segue sugerindo normalmente.",
                self._cdp_url, exc,
            )
            self.enabled = False
            return False

        contexts = self._browser.contexts
        if not contexts:
            log.error("Chrome anexado mas sem aba aberta.")
            self.enabled = False
            return False

        # Procura uma aba ja no LIVE Studio; se nao houver, abre uma.
        for ctx in contexts:
            for page in ctx.pages:
                if "livecenter.tiktok.com" in page.url or "tiktok.com/live" in page.url:
                    self._page = page
                    log.info("Aba da live encontrada: %s", page.url)
                    return True

        self._page = await contexts[0].new_page()
        await self._page.goto(LIVE_CENTER_URL)
        log.info("Abri o LIVE Center. Faca login se ele pedir.")
        return True

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # -- trava de seguranca -------------------------------------------------

    def travar(self, motivo: str) -> None:
        """Desliga o auto-envio de vez, nesta sessao.

        Nao mexe na leitura do chat: o vendedor continua vendo tudo e
        recebendo sugestao. O que para e o robo digitando.
        """
        if self.travado:
            return
        self.travado = True
        self.motivo_trava = motivo
        self.enabled = False
        log.error("AUTO-ENVIO TRAVADO -- %s", motivo)
        log.error("A leitura do chat continua. Rearme pelo painel se for falso alarme.")

    def destravar(self) -> None:
        """Só o painel chama, e só por ação humana explícita."""
        if not self.travado:
            return
        log.warning("Auto-envio rearmado (trava anterior: %s).", self.motivo_trava)
        self.travado = False
        self.motivo_trava = None
        self._falhas_seguidas = 0
        self._sem_eco = 0

    async def checar_avisos(self) -> str | None:
        """Procura aviso do TikTok na tela. Devolve o texto, ou None.

        Le so caixas de aviso/modal, nunca o chat -- ver `_JS_COLETA_ALERTAS`.
        """
        if self._page is None or self.travado:
            return None
        try:
            textos = await self._page.evaluate(_JS_COLETA_ALERTAS)
        except PlaywrightError as exc:
            log.debug("Nao consegui varrer avisos: %s", exc)
            return None

        for texto in textos or []:
            if _AVISO_RE.search(texto):
                return " ".join(texto.split())[:200]
        return None

    async def _confirmar_eco(self, texto: str) -> bool:
        """A mensagem enviada apareceu mesmo no chat?

        Envio que nao da erro e nao aparece e o sinal de shadow-block, e e o
        pior caso: sem isso o agente seguiria falando sozinho para ninguem,
        acumulando strike. Na duvida (nao consegui verificar) devolve True --
        nao vale travar o envio por causa de um seletor que mudou.
        """
        if self._page is None:
            return True
        trecho = texto.strip()[:40]
        if not trecho:
            return True
        try:
            await asyncio.sleep(2.5)  # o chat leva um instante para refletir
            return await self._page.evaluate(
                "(t) => (document.body.innerText || '').includes(t)", trecho
            )
        except PlaywrightError as exc:
            log.debug("Nao consegui confirmar o eco: %s", exc)
            return True

    # -- throttle ----------------------------------------------------------

    def _within_rate_limit(self) -> bool:
        agora = time.monotonic()
        while self._sent_at and agora - self._sent_at[0] > 60:
            self._sent_at.popleft()
        return len(self._sent_at) < self.max_per_min

    # -- envio -------------------------------------------------------------

    async def send(self, texto: str) -> bool:
        """Digita `texto` no chat. Retorna True se realmente enviou."""
        if self.travado:
            log.warning("Envio recusado: auto-envio travado (%s).", self.motivo_trava)
            return False
        if not self.enabled:
            return False
        if not texto.strip():
            return False

        if self._supervision_check is not None and not await self._supervision_check():
            log.warning("Envio bloqueado: nenhum supervisor presente.")
            return False

        async with self._lock:
            if not self._within_rate_limit():
                log.info("Throttle: teto de %d msg/min atingido, pulando.", self.max_per_min)
                return False

            if self._page is None:
                log.error("Sem pagina conectada; envio ignorado.")
                return False

            campo = None
            for seletor in INPUT_SELECTORS:
                try:
                    candidato = self._page.locator(seletor).first
                    if await candidato.is_visible(timeout=1500):
                        campo = candidato
                        break
                except PlaywrightError:
                    continue

            if campo is None:
                log.error(
                    "Campo de comentario nao encontrado. O DOM do TikTok mudou -- "
                    "atualize INPUT_SELECTORS em sender.py."
                )
                self._registrar_falha("campo de comentario sumiu da pagina")
                return False

            try:
                # Pausa antes de comecar e digitacao caractere a caractere. Uma
                # mensagem que aparece instantaneamente e o padrao mais obvio de
                # bot; isso deixa o ritmo parecido com o de uma pessoa.
                await asyncio.sleep(random.uniform(0.8, 2.4))
                await campo.click()
                await campo.type(texto, delay=random.uniform(45, 110))
                await asyncio.sleep(random.uniform(0.2, 0.6))
                await campo.press("Enter")
            except PlaywrightError as exc:
                log.error("Falha ao digitar no chat: %s", exc)
                self._registrar_falha(f"erro ao digitar: {exc}")
                return False

            self._sent_at.append(time.monotonic())
            self._falhas_seguidas = 0
            log.info("Enviado: %s", texto)

        # Fora do lock de proposito: a confirmacao espera alguns segundos e nao
        # pode segurar a fila de envio inteira.
        if await self._confirmar_eco(texto):
            self._sem_eco = 0
        else:
            self._sem_eco += 1
            log.warning(
                "Mensagem enviada mas nao apareceu no chat (%d de %d). "
                "Pode ser atraso -- ou shadow-block.",
                self._sem_eco, LIMITE_SEM_ECO,
            )
            if self._sem_eco >= LIMITE_SEM_ECO:
                self.travar(
                    f"{self._sem_eco} mensagens sairam sem aparecer no chat "
                    "(suspeita de shadow-block)"
                )
        return True

    def _registrar_falha(self, motivo: str) -> None:
        self._falhas_seguidas += 1
        if self._falhas_seguidas >= LIMITE_FALHAS_SEGUIDAS:
            self.travar(f"{self._falhas_seguidas} envios seguidos falharam -- {motivo}")


class SupervisionGate:
    """Exige presenca humana confirmada de tempos em tempos.

    Usado quando a live e um replay gravado: sem check-in recente de um
    supervisor, o auto-envio para.
    """

    def __init__(self, intervalo_min: int = 15):
        self._intervalo = intervalo_min * 60
        self._ultimo_checkin: float | None = None
        self.supervisor: str | None = None

    def checkin(self, supervisor: str) -> None:
        self.supervisor = supervisor
        self._ultimo_checkin = time.monotonic()
        log.info("Check-in de supervisao: %s", supervisor)

    @property
    def presente(self) -> bool:
        if self._ultimo_checkin is None:
            return False
        return (time.monotonic() - self._ultimo_checkin) < self._intervalo

    async def check(self) -> bool:
        if not self.presente:
            log.warning(
                "Supervisao vencida (ultimo check-in ha mais de %d min).",
                self._intervalo // 60,
            )
            return False
        return True
