import asyncio
import html
import logging
import os
import re
import sys
import time
from urllib.parse import urlparse

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.async_api import (
    async_playwright,
)
from playwright_stealth import Stealth

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: no bot token")
    sys.exit()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

browser = None
monitoring_task = None
DB_NAME = "database.db"
MAX_CONCURRENT_SCRAPES = 5
scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)


def is_valid_olx_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return host == "olx.kz" or host.endswith(".olx.kz")


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS monitors (
            user_id INTEGER,
            url TEXT,
            last_price TEXT,
            UNIQUE(user_id, url)
        )
    """)
        await db.commit()
    logger.info("Database initialized")


async def save_monitor(user_id: int, url: str, price: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        INSERT OR REPLACE INTO monitors (user_id, url, last_price)
        VALUES (?, ?, ?)
    """,
            (user_id, url, price),
        )
        await db.commit()


async def get_all_monitors():
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute("SELECT user_id, url, last_price FROM monitors") as cursor,
    ):
        return await cursor.fetchall()


async def get_user_monitors_count(user_id: int) -> int:
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT COUNT(*) FROM monitors WHERE user_id = ?", (user_id,)
        ) as cursor,
    ):
        row = await cursor.fetchone()
        return row[0] if row else 0


async def delete_single_monitor(user_id: int, url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM monitors WHERE user_id = ? AND url = ?",
            (user_id, url),
        )
        await db.commit()


async def delete_all_user_monitors(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM monitors WHERE user_id = ?", (user_id,))
        await db.commit()


async def parse_olx_first_price(url: str) -> str:
    if not browser:
        return "Error: browser is not initialized yet"

    if not is_valid_olx_url(url):
        return "Error: invalid or disallowed URL"

    async with await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
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
            await page.screenshot(path=f"debug_{int(time.time() * 1000)}.png")
            return "Error: Could not find price layout on this page"

        except PlaywrightError as e:
            logger.error(f"Browser action failed while parsing {url}: {e}")
            return f"Error: Browser failure ({type(e).__name__})"


async def process_single_monitor(user_id: int, url: str, last_price: str):
    try:
        async with scrape_semaphore:
            current_price = await parse_olx_first_price(url)

        if current_price.startswith("Error"):
            logger.warning(f"Background check failed for monitored URL: {url}")
            return

        if current_price == last_price:
            return

        logger.info(
            f"Price shift detected for user {user_id}: {last_price} -> {current_price}"
        )

        await save_monitor(user_id, url, current_price)

        await bot.send_message(
            chat_id=user_id,
            text=(
                f"<b>Изменение цены на OLX!</b>\n\n"
                f"Старая цена: <s>{html.escape(last_price)}</s>\n"
                f"Новая цена: <b>{html.escape(current_price)}</b>\n\n"
                f"<a href='{html.escape(url)}'>Ссылка на объявление</a>"
            ),
            parse_mode="HTML",
            disable_web_page_preview=False,
        )

    except TelegramForbiddenError:
        logger.warning(f"User {user_id} has blocked the bot. Removing monitors.")
        await delete_all_user_monitors(user_id)

    except TelegramRetryAfter as e:
        logger.warning(f"Flood limit reached. Sleeping for {e.retry_after} seconds.")
        await asyncio.sleep(e.retry_after)

    except (TelegramNetworkError, TelegramAPIError) as e:
        logger.error(f"Telegram failed to deliver to {user_id}: {e}")

    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Data parsing error processing monitor for {user_id}: {e}")


async def price_monitoring_loop():
    while True:
        try:
            logger.info("Executing scheduled price monitoring cycle...")
            monitors = await get_all_monitors()

            if monitors:
                tasks = [
                    process_single_monitor(uid, url, price)
                    for uid, url, price in monitors
                ]
                await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            logger.info("Price monitoring loop canceled gracefully.")
            break

        except Exception:
            logger.exception("Critical error in the main loop wrapper.")

        # 15 min
        await asyncio.sleep(900)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-монитор OLX.\nОтправь мне ссылку на поисковую выдачу или объявление OLX, и я покажу тебе актуальную цену последнего объявления. Я также могу следить за изменениями цены"
    )


@dp.message(Command("list"))
async def list_monitors(message: Message):
    if not message.from_user:
        return

    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT url, last_price FROM monitors WHERE user_id = ?",
            (message.from_user.id,),
        ) as cursor,
    ):
        fetched_data = await cursor.fetchall()

    if not fetched_data:
        await message.answer("Вы пока не отслеживаете объявления.")
        return

    ans = "Список всех объявлений, которые вы отслеживаете:"
    for i, (url, last_price) in enumerate(fetched_data, start=1):
        ans += f"\n\n{i}. {url} - {last_price}"

    await message.answer(ans, disable_web_page_preview=True)


@dp.message(Command("delete"))
async def delete_monitor(message: Message, command: CommandObject):
    # guards
    async def send_command_error():
        await message.answer(
            "Ошибка: укажите правильный номер объявления из списка (/list) для удаления. Пример: /delete 2"
        )

    if not command.args or not message.from_user:
        await send_command_error()
        return

    try:
        index_to_delete = int(command.args.strip())
    except ValueError:
        await send_command_error()
        return

    # fetching
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT url FROM monitors WHERE user_id = ? LIMIT 1 OFFSET ?",
            (
                message.from_user.id,
                index_to_delete - 1,
            ),
        ) as cursor,
    ):
        fetched_row = await cursor.fetchone()

    if not fetched_row:
        await send_command_error()
        return

    # deleting
    url_to_delete = fetched_row[0]
    await delete_single_monitor(message.from_user.id, url_to_delete)

    clean_url = url_to_delete.split("?")[0]
    await message.answer(
        f"Объявление №{index_to_delete} было удалено. Ссылка: {clean_url}"
    )


@dp.message()
async def handle_link(message: Message):
    if not message.from_user or not message.text:
        return

    url = message.text.split("?")[0]
    MAX_MONITOR_COUNT = 20

    if not url or not is_valid_olx_url(url):
        await message.answer("Пожалуйста, отправь корректную ссылку на сайт olx.kz")
        return

    waiting_msg = await message.answer(
        "Парсим данные через Headless-браузер, подождите..."
    )
    current_price = await parse_olx_first_price(url)

    await waiting_msg.delete()

    if current_price.startswith("Error"):
        await message.answer(
            "Не удалось получить цену!\n\n"
            "Убедитесь, что объявление актуально и ссылка открывается"
        )
        return

    if await get_user_monitors_count(message.from_user.id) < MAX_MONITOR_COUNT:
        await save_monitor(message.from_user.id, url, current_price)

        await message.answer(
            f"<b>Товар добавлен на мониторинг!</b>\n\n"
            f"<b>Текущая цена:</b> {html.escape(current_price)}\n\n"
            f"Я буду периодически проверять её и пришлю уведомление, если она изменится.",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await message.answer(
            f"Не удалось добавить товар на мониторинг. Лимит исчерпан: отслеживаются {MAX_MONITOR_COUNT} объявлений.\n\n"
            f"<b>Текущая цена:</b> {html.escape(current_price)}\n\n",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


@dp.startup()
async def on_startup():
    global monitoring_task
    await init_db()
    monitoring_task = asyncio.create_task(price_monitoring_loop())
    logger.info("Startup complete. Background loops registered.")


@dp.shutdown()
async def on_shutdown():
    if monitoring_task:
        monitoring_task.cancel()
        logger.info("Background tasks cleaned up.")


async def main():
    global browser

    logger.info("Starting global browser...")

    try:
        async with (
            Stealth().use_async(async_playwright()) as p,
            await p.chromium.launch(headless=True) as b,
        ):
            browser = b
            logger.info("Bot is starting to poll...")
            await dp.start_polling(bot)

    except Exception as e:
        if "Connection closed while reading from the driver" in str(e):
            logger.info("Browser process closed during shutdown sequence")
        else:
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt, SystemExit:
        logger.info("Bot stopped.")
