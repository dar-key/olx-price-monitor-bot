from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот-монитор OLX.\n"
        "Отправь мне ссылку на поисковую выдачу или объявление OLX, и я покажу "
        "тебе актуальную цену последнего объявления. Я также могу следить за "
        "изменениями цены"
    )
