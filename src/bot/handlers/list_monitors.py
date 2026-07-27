from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.db.monitors import get_user_monitors

router = Router(name="list")


@router.message(Command("list"))
async def list_monitors(message: Message) -> None:
    if not message.from_user:
        return

    fetched_data = await get_user_monitors(message.from_user.id)

    if not fetched_data:
        await message.answer("Вы пока не отслеживаете объявления.")
        return

    lines = ["Список всех объявлений, которые вы отслеживаете:"]
    for i, (url, last_price) in enumerate(fetched_data, start=1):
        clean_url = url.split("?")[0]
        lines.append(f"\n{i}. {clean_url} - {last_price}")

    await message.answer("\n".join(lines), disable_web_page_preview=True)
