import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: no bot token")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def parse_olx_first_price(url: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            )
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            price_element = await page.query_selector(
                'div[data-testid="prices-wrapper"] h3'
            )

            if not price_element:
                price_element = await page.query_selector('p[data-testid="ad-price"]')

            if not price_element:
                price_element = await page.query_selector(
                    '//p[contains(text(), "тг.")] | //h3[contains(text(), "тг.")]'
                )

            if price_element:
                price = await price_element.inner_text()
                await browser.close()
                return price.strip()

            await page.screenshot(path="debug_screenshot.png")
            await browser.close()
            return "Error: Could not find price layout on this page"

    except Exception as e:
        return f"Error: {str(e)}"


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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
