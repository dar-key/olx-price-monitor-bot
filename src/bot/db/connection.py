import aiosqlite

from src.bot.config import DB_NAME


async def init_db() -> None:
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
