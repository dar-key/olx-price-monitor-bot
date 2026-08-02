from aiogram import Router
from aiogram.types import Message

from src.bot.config import MAX_MONITOR_COUNT
from src.bot.db.monitors import get_user_monitors_count, save_monitor
from src.bot.scraping.browser import BrowserManager
from src.bot.scraping.olx_parser import is_valid_olx_url, parse_olx_first_price
from src.bot.services.formatting import (
    monitor_added_message,
    monitor_limit_reached_message,
)
from src.bot.services.monitoring import scrape_semaphore

router = Router(name="link")


@router.message()
async def handle_link(message: Message, browser_manager: BrowserManager) -> None:
    if not message.from_user:
        return

    url = message.text

    if not url or not is_valid_olx_url(url):
        await message.answer("Пожалуйста, отправь корректную ссылку на сайт olx.kz")
        return

    waiting_msg = await message.answer(
        "Парсим данные через Headless-браузер, подождите..."
    )
    async with scrape_semaphore:
        current_price = await parse_olx_first_price(browser_manager, url)
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
            monitor_added_message(current_price),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await message.answer(
            monitor_limit_reached_message(MAX_MONITOR_COUNT, current_price),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
