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


class ChatSender:
    def __init__(
        self,
        cdp_url: str,
        max_per_min: int,
        enabled: bool = False,
        supervision_check: Callable[[], Awaitable[bool]] | None = None,
    ):
        self._cdp_url = cdp_url
        self._max_per_min = max_per_min
        self.enabled = enabled
        self._supervision_check = supervision_check

        self._playwright = None
        self._browser = None
        self._page = None
        self._sent_at: deque[float] = deque()
        self._lock = asyncio.Lock()

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

    # -- throttle ----------------------------------------------------------

    def _within_rate_limit(self) -> bool:
        agora = time.monotonic()
        while self._sent_at and agora - self._sent_at[0] > 60:
            self._sent_at.popleft()
        return len(self._sent_at) < self._max_per_min

    # -- envio -------------------------------------------------------------

    async def send(self, texto: str) -> bool:
        """Digita `texto` no chat. Retorna True se realmente enviou."""
        if not self.enabled:
            return False
        if not texto.strip():
            return False

        if self._supervision_check is not None and not await self._supervision_check():
            log.warning("Envio bloqueado: nenhum supervisor presente.")
            return False

        async with self._lock:
            if not self._within_rate_limit():
                log.info("Throttle: teto de %d msg/min atingido, pulando.", self._max_per_min)
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
                return False

            self._sent_at.append(time.monotonic())
            log.info("Enviado: %s", texto)
            return True


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
