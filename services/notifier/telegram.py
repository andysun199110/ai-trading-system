from typing import Any

import httpx

from shared.config.settings import get_settings


class TelegramNotifier:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send(self, message: str, payload: dict[str, Any] | None = None) -> None:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
                json={"chat_id": self.settings.telegram_chat_id, "text": f"{message} | {payload or {}}"},
            )
