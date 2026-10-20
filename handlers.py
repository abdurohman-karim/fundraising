"""Команды и кнопки бота."""
from __future__ import annotations

from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import DB
from utils import card_type, esc, fmt_card, fmt_money, mention, parse_amount, parse_card, split_share

router = Router()
GROUPS = F.chat.type.in_({"group", "supergroup"})

HELP = (
    "💰 <b>Бот для общих сборов</b>\n\n"
    "<b>Как пользоваться:</b>\n"
    "1. Каждый жилец нажимает «Я в доле» или пишет /join\n"
    "2. Тот, кто платит, один раз сохраняет карту:\n"
    "   <code>/card 8600 1234 5678 9012 Имя Фамилия</code>\n"
    "3. Создаёт сбор — сумма делится на всех участников:\n"
    "   <code>/new 300000 Коммуналка</code>\n"
    "   <code>/new 300 000 сум Газ за октябрь</code>\n"
    "   <code>/new 50$ Интернет</code>\n"
    "4. Каждый переводит свою долю и жмёт «✅ Я оплатил»\n\n"
    "<b>Команды:</b>\n"
    "/new — новый сбор (сум по умолчанию, $ или usd — доллары)\n"
    "/list — открытые сборы в чате\n"
    "/debts — мои долги\n"
    "/join, /leave — войти / выйти из списка жильцов\n"
    "/members — кто в списке\n"
    "/card — моя карта (<code>/card -</code> — удалить)"
)


class Act(CallbackData, prefix="a"):
    action: str
    cid: int = 0


def display_name(user: User) -> str:
    return user.full_name or (user.username and "@" + user.username) or str(user.id)


def join_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🙋 Я в доле", callback_data=Act(action="join"))
    return kb.as_markup()


def message_link(chat_id: int, message_id: Optional[int]) -> Optional[str]:
    s = str(chat_id)
    if message_id and s.startswith("-100"):
        return f"https://t.me/c/{s[4:]}/{message_id}"
    return None


async def render(db: DB, cid: int) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    c = await db.get_collection(cid)
    shares = await db.get_shares(cid)
    cur = c["currency"]
    share = c["share"]
    paid = sum(1 for s in shares if s["paid"])

    lines = [
        f"💰 <b>{esc(c['title'])}</b>",
        f"Оплатил(а): <b>{esc(c['creator_name'])}</b> — {fmt_money(c['amount'], cur)}",
        f"Участников: {len(shares)} · с каждого: <b>{fmt_money(share, cur)}</b>",
        "",
    ]

    card = await db.get_card(c["creator_id"])
    if card:
        holder = f" ({esc(card['holder'])})" if card["holder"] else ""
        lines.append(f"💳 {card_type(card['number'])}: <code>{fmt_card(card['number'])}</code>{holder}")
    else:
        lines.append(f"⚠️ {esc(c['creator_name'])}, добавьте карту: <code>/card 8600 ...</code>")
    lines.append("")

    for s in shares:
        if s["user_id"] == c["creator_id"]:
            lines.append(f"💳 {esc(s['name'])} — платил(а)")
        else:
            lines.append(f"{'✅' if s['paid'] else '⏳'} {esc(s['name'])}")

    collected = min(paid * share, c["amount"])
    lines += ["", f"Собрано: {paid}/{len(shares)} · {fmt_money(collected, cur)} из {fmt_money(c['amount'], cur)}"]

    if not c["is_open"]:
        lines.append("🔒 <b>Сбор закрыт</b>")
        return "\n".join(lines), None

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я оплатил", callback_data=Act(action="pay", cid=cid))
    kb.button(text="🔔 Напомнить", callback_data=Act(action="remind", cid=cid))
    kb.button(text="🔒 Закрыть", callback_data=Act(action="close", cid=cid))
    kb.adjust(1, 2)
    return "\n".join(lines), kb.as_markup()


async def refresh(db: DB, bot: Bot, cid: int) -> None:
    c = await db.get_collection(cid)
    if not c["message_id"]:
        return
    text, markup = await render(db, cid)
    try:
        await bot.edit_message_text(text, chat_id=c["chat_id"], message_id=c["message_id"], reply_markup=markup)
    except TelegramBadRequest:
        pass  # сообщение не изменилось или удалено


# ---------- общие команды ----------

@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_help(message: Message):
    markup = join_keyboard() if message.chat.type != "private" else None
    await message.answer(HELP, reply_markup=markup)


@router.message(Command("card"))
async def cmd_card(message: Message, command: CommandObject, db: DB):
    user = message.from_user
    args = (command.args or "").strip()

    if not args:
        card = await db.get_card(user.id)
        if not card:
            await message.answer("Карта не сохранена.\nПример: <code>/card 8600 1234 5678 9012 Имя Фамилия</code>")
            return
        holder = f" ({esc(card['holder'])})" if card["holder"] else ""
        await message.answer(f"💳 {card_type(card['number'])}: <code>{fmt_card(card['number'])}</code>{holder}")
        return

    if args in ("-", "удалить", "delete"):
        await db.delete_card(user.id)
        await message.answer("Карта удалена.")
        return

    parsed = parse_card(args)
    if not parsed:
        await message.answer("Не понял номер карты. Нужно 16 цифр:\n<code>/card 8600 1234 5678 9012 Имя Фамилия</code>")
        return
    number, holder = parsed
    await db.set_card(user.id, number, holder)
    await message.answer(f"✅ Карта сохранена: {card_type(number)} <code>{fmt_card(number)}</code>")


@router.message(Command("debts"))
async def cmd_debts(message: Message, db: DB):
    user = message.from_user
    chat_id = None if message.chat.type == "private" else message.chat.id
    debts = await db.user_debts(user.id, chat_id)
    if not debts:
        await message.answer(f"🎉 {esc(display_name(user))}, долгов нет.")
        return

    lines = [f"🧾 Долги {esc(display_name(user))}:"]
    totals = {}
    for c in debts:
        card = await db.get_card(c["creator_id"])
        card_txt = f" → <code>{fmt_card(card['number'])}</code>" if card else ""
        lines.append(f"• {esc(c['title'])}: <b>{fmt_money(c['share'], c['currency'])}</b> "
                     f"для {esc(c['creator_name'])}{card_txt}")
        totals[c["currency"]] = totals.get(c["currency"], 0) + c["share"]
    lines.append("\nИтого: " + " + ".join(fmt_money(v, k) for k, v in totals.items()))
    await message.answer("\n".join(lines))


# ---------- команды в группе ----------

@router.message(Command("join"), GROUPS)
async def cmd_join(message: Message, db: DB):
    user = message.from_user
    added = await db.add_member(message.chat.id, user.id, display_name(user))
    await message.reply("🙋 Вы в списке жильцов." if added else "Вы уже в списке.")


@router.message(Command("leave"), GROUPS)
async def cmd_leave(message: Message, db: DB):
    removed = await db.remove_member(message.chat.id, message.from_user.id)
    await message.reply("👋 Вы вышли из списка. Старые сборы остаются." if removed else "Вас нет в списке.")


@router.message(Command("members"), GROUPS)
async def cmd_members(message: Message, db: DB):
    members = await db.get_members(message.chat.id)
    if not members:
        await message.answer("Список пуст. Нажмите кнопку, чтобы войти:", reply_markup=join_keyboard())
        return
    lines = [f"👥 Жильцы ({len(members)}):"] + [f"• {esc(m['name'])}" for m in members]
    await message.answer("\n".join(lines), reply_markup=join_keyboard())


@router.message(Command("new", "sbor"), GROUPS)
async def cmd_new(message: Message, command: CommandObject, db: DB):
    parsed = parse_amount(command.args or "")
    if not parsed:
        await message.reply(
            "Укажите сумму и название:\n"
            "<code>/new 300000 Коммуналка</code>\n"
            "<code>/new 50$ Интернет</code>"
        )
        return
    amount, currency, title = parsed
    user = message.from_user
    name = display_name(user)

    await db.add_member(message.chat.id, user.id, name)
    members = await db.get_members(message.chat.id)
    if len(members) < 2:
        await message.reply(
            "Пока в списке только вы. Пусть остальные нажмут кнопку, потом создайте сбор ещё раз:",
            reply_markup=join_keyboard(),
        )
        return

    participants = [(m["user_id"], m["name"]) for m in members]
    share = split_share(amount, currency, len(participants))
    cid = await db.create_collection(message.chat.id, user.id, name, title, amount, currency, share, participants)

    text, markup = await render(db, cid)
    sent = await message.answer(text, reply_markup=markup)
    await db.set_message_id(cid, sent.message_id)


@router.message(Command("list"), GROUPS)
async def cmd_list(message: Message, db: DB):
    items = await db.open_collections(message.chat.id)
    if not items:
        await message.answer("Открытых сборов нет.")
        return
    lines = ["📋 Открытые сборы:"]
    for c in items:
        title = esc(c["title"])
        link = message_link(c["chat_id"], c["message_id"])
        if link:
            title = f'<a href="{link}">{title}</a>'
        lines.append(f"• {title} — по {fmt_money(c['share'], c['currency'])} "
                     f"для {esc(c['creator_name'])}, оплатили {c['paid_count']}/{c['total']}")
    await message.answer("\n".join(lines), disable_web_page_preview=True)


# ---------- кнопки ----------

@router.callback_query(Act.filter(F.action == "join"))
async def cb_join(call: CallbackQuery, db: DB):
    user = call.from_user
    added = await db.add_member(call.message.chat.id, user.id, display_name(user))
    await call.answer("🙋 Вы в списке жильцов" if added else "Вы уже в списке")


@router.callback_query(Act.filter(F.action == "pay"))
async def cb_pay(call: CallbackQuery, callback_data: Act, db: DB, bot: Bot):
    c = await db.get_collection(callback_data.cid)
    if not c or not c["is_open"]:
        await call.answer("Сбор уже закрыт", show_alert=True)
        return
    if call.from_user.id == c["creator_id"]:
        await call.answer("Вы оплатили за всех — ваша доля уже учтена 🙂", show_alert=True)
        return

    state = await db.toggle_paid(c["id"], call.from_user.id)
    if state is None:
        await call.answer("Вы не участвуете в этом сборе", show_alert=True)
        return
    await call.answer("✅ Отмечено как оплачено" if state else "Отметка снята")

    shares = await db.get_shares(c["id"])
    if all(s["paid"] for s in shares):
        await db.close_collection(c["id"])
        await refresh(db, bot, c["id"])
        await call.message.reply(f"🎉 Все оплатили «{esc(c['title'])}». Сбор закрыт.")
    else:
        await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "remind"))
async def cb_remind(call: CallbackQuery, callback_data: Act, db: DB):
    c = await db.get_collection(callback_data.cid)
    if not c or not c["is_open"]:
        await call.answer("Сбор уже закрыт", show_alert=True)
        return
    if call.from_user.id != c["creator_id"]:
        await call.answer("Напоминать может только тот, кто создал сбор", show_alert=True)
        return

    debtors = [s for s in await db.get_shares(c["id"]) if not s["paid"]]
    await call.answer()
    await call.message.reply(
        f"🔔 Напоминание по сбору «{esc(c['title'])}» — по <b>{fmt_money(c['share'], c['currency'])}</b>:\n"
        + ", ".join(mention(s["user_id"], s["name"]) for s in debtors)
    )


@router.callback_query(Act.filter(F.action == "close"))
async def cb_close(call: CallbackQuery, callback_data: Act, db: DB, bot: Bot):
    c = await db.get_collection(callback_data.cid)
    if not c or not c["is_open"]:
        await call.answer("Сбор уже закрыт")
        return
    if call.from_user.id != c["creator_id"]:
        await call.answer("Закрыть может только тот, кто создал сбор", show_alert=True)
        return
    await db.close_collection(c["id"])
    await call.answer("Сбор закрыт")
    await refresh(db, bot, c["id"])
