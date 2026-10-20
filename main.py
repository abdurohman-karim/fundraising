import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv

from db import DB
from handlers import router

COMMANDS = [
    BotCommand(command="new", description="Новый сбор: /new 300000 Коммуналка"),
    BotCommand(command="list", description="Открытые сборы"),
    BotCommand(command="debts", description="Мои долги"),
    BotCommand(command="join", description="Войти в список жильцов"),
    BotCommand(command="leave", description="Выйти из списка"),
    BotCommand(command="members", description="Список жильцов"),
    BotCommand(command="card", description="Моя карта Uzcard / Humo"),
    BotCommand(command="help", description="Как пользоваться"),
]


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN не задан (см. .env.example)")

    db = DB(os.getenv("DB_PATH", "data/bot.db"))
    await db.connect()

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(db=db)
    dp.include_router(router)

    await bot.set_my_commands(COMMANDS)
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
