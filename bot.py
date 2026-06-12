import asyncio
import sqlite3
import logging
import os
import re
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from playwright_stealth import Stealth
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: no bot token")
    exit()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

browser = None


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitors (
            user_id INTEGER,
            url TEXT UNIQUE,
            last_price TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_monitor(user_id: int, url: str, price: str):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO monitors (user_id, url, last_price)
        VALUES (?, ?, ?)
    """,
        (user_id, url, price),
    )
    conn.commit()
    conn.close()


def get_all_monitors():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, url, last_price FROM monitors")
    rows = cursor.fetchall()
    conn.close()
    return rows


async def parse_olx_first_price(url: str) -> str:
    global browser
    if not browser:
        return "Error: browser is not initialized yet"

    async with await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ) as context:

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            price_pattern = re.compile(r"\d+.*(тг\.|₸)", re.IGNORECASE)
            price_locator = page.get_by_text(price_pattern)

            await price_locator.first.wait_for(state="visible", timeout=5000)

            raw_price = await price_locator.first.inner_text()
            return raw_price.strip()

        except PlaywrightTimeoutError:
            logger.error(f"Timeout trying to parse: {url}")
            await page.screenshot(path="debug_screenshot.png")
            return "Error: Could not find price layout on this page"

        except Exception as e:
            logger.error(f"Unexpected error while parsing {url}: {e}")
            return f"Error: Unexpected browser failure ({type(e).__name__})"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-монитор OLX.\nОтправь мне ссылку на поисковую выдачу или объявление OLX, и я покажу тебе актуальную цену последнего объявления."
    )


@dp.message()
async def handle_link(message: Message):
    url = message.text

    if not url or "olx.kz" not in url:
        await message.answer("Пожалуйста, отправь корректную ссылку на сайт olx.kz")
        return

    waiting_msg = await message.answer(
        "Парсим данные через Headless-браузер, подождите..."
    )
    current_price = await parse_olx_first_price(url)

    await waiting_msg.delete()
    await message.answer(
        f"**Последняя цена по вашей ссылке:**\n{current_price}\n\n Ссылка: {url}",
        parse_mode="Markdown",
    )


async def main():
    global browser

    # init_db()

    logger.info("Starting global browser...")
    async with Stealth().use_async(async_playwright()) as p:
        async with await p.chromium.launch(headless=True) as br:
            browser = br
            logger.info("Bot is starting to poll...")
            await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
