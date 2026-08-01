import asyncio

from aiogram import Bot, Dispatcher

from src.bot.config import BOT_TOKEN
from src.bot.db.connection import init_db
from src.bot.handlers import delete_monitor, link, list_monitors, start
from src.bot.logging_config import setup_logging
from src.bot.scraping.browser import BrowserManager
from src.bot.services.monitoring import price_monitoring_loop

logger = setup_logging()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(list_monitors.router)
dp.include_router(delete_monitor.router)
dp.include_router(link.router)

browser_manager = BrowserManager()
monitoring_task: asyncio.Task | None = None


@dp.startup()
async def on_startup() -> None:
    global monitoring_task
    await init_db()
    monitoring_task = asyncio.create_task(price_monitoring_loop(bot, browser_manager))
    logger.info("Startup complete. Background loops registered.")


@dp.shutdown()
async def on_shutdown() -> None:
    if monitoring_task:
        monitoring_task.cancel()


async def main() -> None:
    try:
        await browser_manager.start()
        logger.info("Bot is starting to poll...")
        await dp.start_polling(bot, browser_manager=browser_manager)
    except Exception as e:
        if "Connection closed while reading from the driver" in str(e):
            logger.info("Browser process closed during shutdown sequence")
        else:
            raise
    finally:
        await browser_manager.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
