import aiosqlite

from src.bot.config import DB_NAME


async def save_monitor(user_id: int, url: str, price: str) -> None:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO monitors (user_id, url, last_price) VALUES (?, ?, ?)",
            (user_id, url, price),
        )
        await db.commit()


async def get_all_monitors():
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute("SELECT user_id, url, last_price FROM monitors") as cursor,
    ):
        return await cursor.fetchall()


async def get_user_monitors(user_id: int):
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT url, last_price FROM monitors WHERE user_id = ?", (user_id,)
        ) as cursor,
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


async def get_monitor_url_by_index(user_id: int, index_1_based: int) -> str | None:
    async with (
        aiosqlite.connect(DB_NAME) as db,
        db.execute(
            "SELECT url FROM monitors WHERE user_id = ? LIMIT 1 OFFSET ?",
            (user_id, index_1_based - 1),
        ) as cursor,
    ):
        row = await cursor.fetchone()
        return row[0] if row else None


async def delete_single_monitor(user_id: int, url: str) -> None:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM monitors WHERE user_id = ? AND url = ?", (user_id, url)
        )
        await db.commit()


async def delete_all_user_monitors(user_id: int) -> None:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM monitors WHERE user_id = ?", (user_id,))
        await db.commit()
