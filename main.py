import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, TelegramObject
from dotenv import load_dotenv

from db import DB
from handlers import refresh_open, router
from i18n import DEFAULT_LANG


class LangMiddleware(BaseMiddleware):
    """Кладёт язык бота в аргумент `lang` обработчиков."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["lang"] = await data["db"].get_lang() or DEFAULT_LANG
        return await handler(event, data)


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN не задан (см. .env.example)")

    admin = os.getenv("ADMIN_CHAT_ID", "").strip()
    admin_id = int(admin) if admin else None

    db = DB(os.getenv("DB_PATH", "data/bot.db"))
    await db.connect()

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(db=db, admin_id=admin_id)
    dp.message.middleware(LangMiddleware())
    dp.callback_query.middleware(LangMiddleware())
    dp.include_router(router)

    await bot.set_my_commands([BotCommand(command="menu", description="Меню / Menyu")])
    await refresh_open(db, bot)
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
