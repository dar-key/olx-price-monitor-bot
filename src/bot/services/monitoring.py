import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)

from src.bot.config import CHECK_INTERVAL_SECONDS, MAX_CONCURRENT_SCRAPES
from src.bot.db.monitors import delete_all_user_monitors, get_all_monitors, save_monitor
from src.bot.scraping.browser import BrowserManager
from src.bot.scraping.olx_parser import parse_olx_first_price
from src.bot.services.formatting import price_change_message

logger = logging.getLogger("olx_bot")
scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)


async def process_single_monitor(
    bot: Bot, browser_manager: BrowserManager, user_id: int, url: str, last_price: str
) -> None:
    try:
        async with scrape_semaphore:
            current_price = await parse_olx_first_price(browser_manager, url)

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
            text=price_change_message(last_price, current_price, url),
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


async def price_monitoring_loop(bot: Bot, browser_manager: BrowserManager) -> None:
    while True:
        try:
            logger.info("Executing scheduled price monitoring cycle...")
            monitors = await get_all_monitors()

            if monitors:
                tasks = [
                    process_single_monitor(bot, browser_manager, uid, url, price)
                    for uid, url, price in monitors
                ]
                await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            logger.info("Price monitoring loop canceled gracefully.")
            break

        except Exception:
            logger.exception("Critical error in the main loop wrapper.")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
