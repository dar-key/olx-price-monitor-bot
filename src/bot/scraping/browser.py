import logging

from playwright.async_api import Browser, async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger("olx_bot")


class BrowserManager:
    def __init__(self) -> None:
        self._browser: Browser | None = None
        self._stealth_ctx = None

    @property
    def browser(self) -> Browser | None:
        return self._browser

    @property
    def is_ready(self) -> bool:
        return self._browser is not None

    async def start(self) -> None:
        logger.info("Starting global browser...")
        self._stealth_ctx = Stealth().use_async(async_playwright())
        playwright = await self._stealth_ctx.__aenter__()
        self._browser = await playwright.chromium.launch(headless=True)

    async def stop(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
        finally:
            if self._stealth_ctx:
                await self._stealth_ctx.__aexit__(None, None, None)
            self._browser = None
