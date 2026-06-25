import asyncio
import html
import aiosqlite
import logging
import os
import re
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandObject, CommandStart, Command
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError
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
monitoring_task = None
DB_NAME = "database.db"


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
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, url, last_price FROM monitors"
        ) as cursor:
            return await cursor.fetchall()


async def get_user_monitors_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM monitors WHERE user_id = ?", (user_id,)
        ) as cursor:
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


async def price_monitoring_loop():
    while True:
        try:
            # Check prices every 15 min
            await asyncio.sleep(900)

            logger.info("Executing scheduled price monitoring cycle...")
            monitors = await get_all_monitors()

            for user_id, url, last_price in monitors:
                current_price = await parse_olx_first_price(url)

                if current_price.startswith("Error"):
                    logger.warning(f"Background check failed for monitored URL: {url}")
                    continue

                # Price change
                if current_price != last_price:
                    logger.info(
                        f"Price shift detected for user {user_id}: {last_price} -> {current_price}"
                    )

                    await save_monitor(user_id, url, current_price)

                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=(
                                f"<b>Изменение цены на OLX!</b>\n\n"
                                f"Старая цена: <s>{last_price}</s>\n"
                                f"Новая цена: <b>{current_price}</b>\n\n"
                                f"<a href='{html.escape(url)}'>Ссылка на объявление</a>"
                            ),
                            parse_mode="HTML",
                            disable_web_page_preview=False,
                        )
                    except TelegramForbiddenError:
                        logger.warning(
                            f"User {user_id} has blocked the bot. Removing monitors."
                        )
                        await delete_all_user_monitors(user_id)
                    except Exception as e:
                        logger.error(
                            f"Could not deliver notification to user {user_id}: {e}"
                        )

        except asyncio.CancelledError:
            logger.info("Price monitoring loop canceled gracefully.")
            break
        except Exception as e:
            logger.error(f"Error in price monitoring task: {e}")


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-монитор OLX.\nОтправь мне ссылку на поисковую выдачу или объявление OLX, и я покажу тебе актуальную цену последнего объявления. Я также могу следить за изменениями цены"
    )


@dp.message(Command("list"))
async def list_monitors(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT url, last_price FROM monitors WHERE user_id = ?",
            (message.from_user.id,),
        ) as cursor:
            fetched_data = await cursor.fetchall()

    if not fetched_data:
        await message.answer("Вы пока не отслеживаете объявления.")
        return

    ans = "Список всех объявлений, которые вы отслеживаете:"
    for i, (url, last_price) in enumerate(fetched_data, start=1):
        clean_url = url.split("?")[0]
        ans += f"\n\n{i}. {clean_url} - {last_price}"

    await message.answer(ans, disable_web_page_preview=True)


@dp.message(Command("delete"))
async def delete_monitor(message: Message, command: CommandObject):
    async def send_command_error():
        await message.answer(
            "Ошибка: укажите правильный номер объявления из списка (/list) для удаления. Пример: /delete 2"
        )

    if not command.args:
        await send_command_error()
        return

    try:
        index_to_delete = int(command.args.strip())
    except ValueError:
        await send_command_error()
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT url FROM monitors WHERE user_id = ?", (message.from_user.id,)
        ) as cursor:
            fetched_data = await cursor.fetchall()

    if not fetched_data:
        await message.answer("Вы пока не отслеживаете объявления.")
        return

    if index_to_delete < 1 or index_to_delete > len(fetched_data):
        await send_command_error()
        return

    url_to_delete = fetched_data[index_to_delete - 1][0]
    await delete_single_monitor(message.from_user.id, url_to_delete)

    clean_url = url_to_delete.split("?")[0]
    await message.answer(
        f"Объявление №{index_to_delete} было удалено. Ссылка: {clean_url}"
    )


@dp.message()
async def handle_link(message: Message):
    url = message.text
    MAX_MONITOR_COUNT = 20

    if not url or "olx.kz" not in url:
        await message.answer("Пожалуйста, отправь корректную ссылку на сайт olx.kz")
        return

    waiting_msg = await message.answer(
        "Парсим данные через Headless-браузер, подождите..."
    )
    current_price = await parse_olx_first_price(url)

    await waiting_msg.delete()

    if current_price.startswith("Error"):
        await message.answer(
            f"Не удалось получить цену!\n\n"
            f"Убедитесь, что объявление актуально и ссылка открывается"
        )
        return

    if await get_user_monitors_count(message.from_user.id) < MAX_MONITOR_COUNT:
        await save_monitor(message.from_user.id, url, current_price)

        await message.answer(
            f"<b>Товар добавлен на мониторинг!</b>\n\n"
            f"<b>Текущая цена:</b> {current_price}\n\n"
            f"Я буду периодически проверять её и пришлю уведомление, если она изменится.",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await message.answer(
            f"<b>Текущая цена:</b> {current_price}\n\n"
            f"Не удалось добавить товар на мониторинг. Лимит исчерпан: отслеживаются {MAX_MONITOR_COUNT} объявлений.",
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
    global monitoring_task
    if monitoring_task:
        monitoring_task.cancel()
        logger.info("Background tasks cleaned up.")


async def main():
    global browser

    logger.info("Starting global browser...")

    try:
        async with Stealth().use_async(async_playwright()) as p:
            async with await p.chromium.launch(headless=True) as b:
                browser = b
                logger.info("Bot is starting to poll...")
                await dp.start_polling(bot)

    except Exception as e:
        if "Connection closed while reading from the driver" in str(e):
            logger.info("Browser process closed during shutdown sequence")
        else:
            raise e


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
