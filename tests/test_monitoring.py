from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import TelegramForbiddenError

from src.bot.services.monitoring import process_single_monitor


@pytest.mark.asyncio
async def test_process_single_monitor_removes_monitors_on_forbidden():
    bot = AsyncMock()
    bot.send_message.side_effect = TelegramForbiddenError(
        method=AsyncMock(), message="bot was blocked by the user"
    )
    browser_manager = AsyncMock()

    with (
        patch(
            "src.bot.services.monitoring.parse_olx_first_price",
            new=AsyncMock(return_value="2000 тг."),
        ),
        patch(
            "src.bot.services.monitoring.delete_all_user_monitors",
            new=AsyncMock(),
        ) as mock_delete,
    ):
        await process_single_monitor(
            bot, browser_manager, 123, "https://olx.kz/x", "1000 тг."
        )
        mock_delete.assert_awaited_once_with(123)
