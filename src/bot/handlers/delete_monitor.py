from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from src.bot.db.monitors import delete_single_monitor, get_monitor_url_by_index

router = Router(name="delete")

ERROR_TEXT = (
    "Ошибка: укажите правильный номер объявления из списка (/list) для "
    "удаления. Пример: /delete 2"
)


@router.message(Command("delete"))
async def delete_monitor(message: Message, command: CommandObject) -> None:
    if not command.args or not message.from_user:
        await message.answer(ERROR_TEXT)
        return

    try:
        index_to_delete = int(command.args.strip())
    except ValueError:
        await message.answer(ERROR_TEXT)
        return

    url_to_delete = await get_monitor_url_by_index(
        message.from_user.id, index_to_delete
    )

    if not url_to_delete:
        await message.answer(ERROR_TEXT)
        return

    await delete_single_monitor(message.from_user.id, url_to_delete)

    clean_url = url_to_delete.split("?")[0]
    await message.answer(
        f"Объявление №{index_to_delete} было удалено. Ссылка: {clean_url}"
    )
