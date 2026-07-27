import logging
import re
import time
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.bot.config import ALLOWED_DOMAIN
from src.bot.scraping.browser import BrowserManager

logger = logging.getLogger("olx_bot")

PRICE_PATTERN = re.compile(r"\d+.*(тг\.|₸)", re.IGNORECASE)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


def is_valid_olx_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return host == ALLOWED_DOMAIN or host.endswith(f".{ALLOWED_DOMAIN}")


async def parse_olx_first_price(browser_manager: BrowserManager, url: str) -> str:
    if not browser_manager.is_ready or browser_manager.browser is None:
        return "Error: browser is not initialized yet"

    if not is_valid_olx_url(url):
        return "Error: invalid or disallowed URL"

    async with await browser_manager.browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=USER_AGENT,
    ) as context:
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            price_locator = page.get_by_text(PRICE_PATTERN)
            await price_locator.first.wait_for(state="visible", timeout=5000)

            raw_price = await price_locator.first.inner_text()
            return raw_price.strip()

        except PlaywrightTimeoutError:
            logger.error(f"Timeout trying to parse: {url}")
            await page.screenshot(path=f"debug_{int(time.time() * 1000)}.png")
            return "Error: Could not find price layout on this page"

        except PlaywrightError as e:
            logger.error(f"Browser action failed while parsing {url}: {e}")
            return f"Error: Browser failure ({type(e).__name__})"
