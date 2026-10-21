"""Меню на inline-кнопках, сборы, очереди и чеки.

В группе — только общее: меню, список, жильцы и карточки сборов.
Всё личное (новый сбор, карта, долги, «Я оплатил» с чеком) — в личке с ботом
через ссылки вида t.me/<бот>?start=<действие>.

В личке у каждого один «экран» — сообщение бота, которое меняется на месте.
Сообщения, которые человек пишет в ответ (сумма, карта, название), бот удаляет.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command, CommandObject, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, KeyboardButton, KeyboardButtonRequestUsers, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, ReplyParameters, User,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import CONFIRMED, DB, DRAFT, OPEN, CLOSED, PENDING, QUEUE, REJECTED, SPLIT
from i18n import CHOOSE_LANG, DEFAULT_LANG, t
from utils import USD, UZS, card_type, esc, fmt_card, fmt_money, mention, parse_amount, parse_card, split_share

router = Router()
PRIVATE = F.chat.type == "private"

# Личка: chat_id -> id сообщения-«экрана». Группа: chat_id -> id последнего меню.
SCREENS: Dict[int, int] = {}
GROUP_MENUS: Dict[int, int] = {}


class Act(CallbackData, prefix="a"):
    action: str
    cid: int = 0
    uid: int = 0
    val: str = ""


class Form(StatesGroup):
    kind = State()
    amount = State()
    card = State()
    receipt = State()
    add_members = State()
    title = State()


# ---------- помощники ----------

def display_name(user: User) -> str:
    """@username, а если его нет — имя."""
    return f"@{user.username}" if user.username else (user.full_name or str(user.id))


async def get_lang(db: DB) -> str:
    return await db.get_lang() or DEFAULT_LANG


async def start_link(bot: Bot, payload: str) -> str:
    me = await bot.me()
    return f"https://t.me/{me.username}?start={payload}"


async def safe_edit(message: Message, text: str, markup: Optional[InlineKeyboardMarkup] = None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except TelegramAPIError:
        pass  # текст не изменился


async def safe_delete(bot: Bot, chat_id: int, message_id: Optional[int]) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramAPIError:
        pass  # уже удалено или нет прав


async def try_send(bot: Bot, chat_id: int, text: str, **kwargs) -> Optional[Message]:
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except TelegramAPIError:
        return None  # человек не открывал бота или заблокировал его


async def show(bot: Bot, db: DB, chat_id: int, text: str, markup: Optional[InlineKeyboardMarkup] = None,
               message_id: Optional[int] = None, new: bool = False) -> int:
    """Показывает экран в личке: правит текущее сообщение, а если нельзя (или new) — присылает новое
    и удаляет прошлый экран. Черновик сбора не удаляется — он живёт своим сообщением."""
    target = message_id or SCREENS.get(chat_id)
    if target and not new:
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=target, reply_markup=markup,
                                        disable_web_page_preview=True)
            SCREENS[chat_id] = target
            return target
        except TelegramAPIError as e:
            if "not modified" in str(e):
                SCREENS[chat_id] = target
                return target
    old = SCREENS.get(chat_id)
    if old and not await db.is_draft_message(chat_id, old):
        await safe_delete(bot, chat_id, old)
    sent = await bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)
    SCREENS[chat_id] = sent.message_id
    return sent.message_id


def card_text(lang: str, card) -> str:
    holder = f" ({esc(card['holder'])})" if card["holder"] else ""
    kind = card_type(card["number"]) or t(lang, "card")
    return t(lang, "card_line", type=kind, number=fmt_card(card["number"]), holder=holder)


def back_kb(lang: str, action: str = "menu", cid: int = 0, cancel: bool = False) -> InlineKeyboardMarkup:
    """Одна кнопка «Назад» (или «Отмена» на шаге ввода) на нужный экран."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_cancel" if cancel else "btn_back"), callback_data=Act(action=action, cid=cid))
    return kb.as_markup()


async def reset_state(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """Сбрасывает ввод; если была открыта клавиатура выбора людей — убирает её."""
    if await state.get_state() == Form.add_members.state:
        await close_picker(bot, chat_id, await state.get_data())
    await state.clear()


# ---------- меню ----------

def lang_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data=Act(action="setlang", val="ru"))
    kb.button(text="🇺🇿 O'zbekcha", callback_data=Act(action="setlang", val="uz"))
    kb.button(text=t(lang, "btn_back"), callback_data=Act(action="menu"))
    kb.adjust(2, 1)
    return kb.as_markup()


async def menu_view(bot: Bot, lang: str, chat_id: int, chat_type: str, is_admin: bool) -> Tuple[str, InlineKeyboardMarkup]:
    kb = InlineKeyboardBuilder()
    if chat_type == "private":
        me = await bot.me()
        kb.button(text=t(lang, "btn_card"), callback_data=Act(action="card"))
        kb.button(text=t(lang, "btn_debts"), callback_data=Act(action="debts"))
        kb.button(text=t(lang, "btn_mine"), callback_data=Act(action="mine"))
        sizes = [2, 1]
        if is_admin:
            kb.button(text=t(lang, "btn_add_member"), callback_data=Act(action="addm"))
            kb.button(text=t(lang, "btn_lang"), callback_data=Act(action="lang"))
            kb.button(text=t(lang, "btn_add_group"), url=f"https://t.me/{me.username}?startgroup=1")
            sizes += [1, 1, 1]
        kb.adjust(*sizes)
        return t(lang, "menu_private"), kb.as_markup()

    kb.button(text=t(lang, "btn_new"), url=await start_link(bot, f"new_{chat_id}"))
    kb.button(text=t(lang, "btn_list"), callback_data=Act(action="list"))
    kb.button(text=t(lang, "btn_debts"), url=await start_link(bot, "debts"))
    kb.button(text=t(lang, "btn_join"), callback_data=Act(action="join"))
    kb.button(text=t(lang, "btn_members"), callback_data=Act(action="members"))
    kb.button(text=t(lang, "btn_card"), url=await start_link(bot, "card"))
    kb.adjust(1, 2, 2, 1)
    return t(lang, "menu_group"), kb.as_markup()


def back_button(kb: InlineKeyboardBuilder, lang: str) -> None:
    kb.button(text=t(lang, "btn_back"), callback_data=Act(action="menu"))


async def members_view(db: DB, lang: str, chat_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    members = await db.get_members(chat_id)
    if members:
        text = "\n".join([t(lang, "members_title", n=len(members))] + [f"• {esc(m['name'])}" for m in members])
    else:
        text = t(lang, "members_empty")
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_join"), callback_data=Act(action="join", val="m"))
    kb.button(text=t(lang, "btn_leave"), callback_data=Act(action="leave", val="m"))
    back_button(kb, lang)
    kb.adjust(2, 1)
    return text, kb.as_markup()


async def list_view(db: DB, lang: str, chat_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    items = await db.chat_collections(chat_id, OPEN)
    kb = InlineKeyboardBuilder()
    for c in items:
        if c["kind"] == QUEUE:
            shares = await db.get_shares(c["id"])
            label = f"🔁 {c['title']} · 👉 {shares[c['pointer']]['name']}"
        else:
            label = f"{c['title']} · {fmt_money(c['share'], c['currency'], lang)} · {c['paid_count']}/{c['total']}"
        kb.button(text=label[:60], callback_data=Act(action="show", cid=c["id"]))
    back_button(kb, lang)
    kb.adjust(1)
    return t(lang, "list_title" if items else "list_empty"), kb.as_markup()


async def mine_view(db: DB, lang: str, user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    items = [c for c in await db.creator_active(user_id) if c["status"] == OPEN]
    kb = InlineKeyboardBuilder()
    for c in items:
        icon = "🔁" if c["kind"] == QUEUE else "💰"
        kb.button(text=f"{icon} {c['title']}"[:60], callback_data=Act(action="manage", cid=c["id"]))
    back_button(kb, lang)
    kb.adjust(1)
    return t(lang, "mine_title" if items else "mine_empty"), kb.as_markup()


async def debts_view(db: DB, lang: str, user_id: int) -> str:
    lines, totals = [], {}
    for c in await db.user_open(user_id):
        if user_id in await db.pending_users(c["id"]):
            continue
        cur = c["currency"]
        if c["kind"] == QUEUE:
            idx = [s["user_id"] for s in await db.get_shares(c["id"])].index(user_id)
            if idx == c["pointer"]:
                key, times = "debt_queue", c["owed"]
            else:
                # Пропущенные разы: позади очереди — всё, что должен; впереди — сверх своего раза.
                key, times = "debt_queue_late", c["owed"] if idx < c["pointer"] else c["owed"] - 1
                if times <= 0:
                    continue
            amount = c["amount"] * times
            lines.append(t(lang, key, title=esc(c["title"]), amount=fmt_money(amount, cur, lang)))
        else:
            if c["paid"] or c["creator_id"] == user_id:
                continue
            amount = c["share"]
            card = await db.get_card(c["creator_id"])
            card_txt = f" <code>{fmt_card(card['number'])}</code>" if card else ""
            lines.append(t(lang, "debt_item", title=esc(c["title"]), share=fmt_money(amount, cur, lang),
                           creator=esc(c["creator_name"]), card=card_txt))
        totals[cur] = totals.get(cur, 0) + amount

    if not lines:
        return t(lang, "debts_none")
    total = " + ".join(fmt_money(v, k, lang) for k, v in totals.items())
    return "\n".join([t(lang, "debts_title")] + lines + ["", t(lang, "total", sum=total)])


# ---------- черновик и карточка сбора ----------

async def render_draft(db: DB, c, lang: str) -> Tuple[str, InlineKeyboardMarkup]:
    cid, cur = c["id"], c["currency"]
    shares = await db.get_shares(cid)
    selected = {s["user_id"] for s in shares}
    people = {m["user_id"]: m["name"] for m in await db.get_members(c["chat_id"])}
    people.update({s["user_id"]: s["name"] for s in shares})
    others = sorted((uid for uid in people if uid not in selected), key=lambda u: people[u].lower())
    other_cur = USD if cur == UZS else UZS
    kb = InlineKeyboardBuilder()

    if c["kind"] == QUEUE:
        text = t(lang, "draft_queue", group=esc(c["chat_title"]), title=esc(c["title"]),
                 amount=fmt_money(c["amount"], cur, lang))
        for i, s in enumerate(shares, 1):
            kb.button(text=f"{i}. {s['name']}"[:40], callback_data=Act(action="tg", cid=cid, uid=s["user_id"]))
            mark = "✅" if s["paid"] else "⬜"
            kb.button(text=f"{mark} {t(lang, 'btn_prepaid')}", callback_data=Act(action="prepaid", cid=cid, uid=s["user_id"]))
        for uid in others:
            kb.button(text=f"⬜ {people[uid]}"[:40], callback_data=Act(action="tg", cid=cid, uid=uid))
        sizes = [2] * len(shares) + [1] * len(others)
        kb.button(text=t(lang, "btn_reset_order"), callback_data=Act(action="reset", cid=cid))
        kb.button(text=t(lang, "btn_currency", cur=t(lang, "cur_" + cur)),
                  callback_data=Act(action="cur", cid=cid, val=other_cur))
        sizes.append(2)
    else:
        share = split_share(c["amount"], cur, len(shares)) if shares else 0
        card = await db.get_card(c["creator_id"])
        text = "\n".join([
            t(lang, "draft_split", group=esc(c["chat_title"]), title=esc(c["title"]),
              amount=fmt_money(c["amount"], cur, lang), n=len(shares), share=fmt_money(share, cur, lang)),
            "",
            card_text(lang, card) if card else t(lang, "no_card_line", name=esc(c["creator_name"])),
        ])
        paid = {s["user_id"]: s["paid"] for s in shares}
        sizes = []
        for uid in sorted(people, key=lambda u: people[u].lower()):
            mark = "✅" if uid in selected else "⬜"
            kb.button(text=f"{mark} {people[uid]}"[:40], callback_data=Act(action="tg", cid=cid, uid=uid))
            if uid in selected and uid != c["creator_id"]:
                # Уже отдал свою долю (например, наличными): в делении участвует, платить не нужно.
                mark = "✅" if paid[uid] else "⬜"
                kb.button(text=f"{mark} {t(lang, 'btn_prepaid')}", callback_data=Act(action="prepaid", cid=cid, uid=uid))
                sizes.append(2)
            else:
                sizes.append(1)
        kb.button(text=t(lang, "btn_currency", cur=t(lang, "cur_" + cur)),
                  callback_data=Act(action="cur", cid=cid, val=other_cur))
        sizes.append(1)
        if not card:
            kb.button(text=t(lang, "btn_card"), callback_data=Act(action="card", cid=cid))
            sizes.append(1)

    kb.button(text=t(lang, "btn_edit"), callback_data=Act(action="edit", cid=cid))
    kb.button(text=t(lang, "btn_create"), callback_data=Act(action="create", cid=cid))
    kb.button(text=t(lang, "btn_cancel"), callback_data=Act(action="cancel", cid=cid))
    sizes += [1, 2]
    kb.adjust(*sizes)
    return text, kb.as_markup()


async def render(db: DB, bot: Bot, cid: int) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    c = await db.get_collection(cid)
    lang = await get_lang(db)
    if c["status"] == DRAFT:
        return await render_draft(db, c, lang)

    cur = c["currency"]
    shares = await db.get_shares(cid)
    pending = await db.pending_users(cid)

    if c["kind"] == QUEUE:
        pointer = c["pointer"]
        lines = [
            t(lang, "queue_head", title=esc(c["title"]), amount=fmt_money(c["amount"], cur, lang), round=c["round"]),
            "",
        ]
        for i, s in enumerate(shares):
            times = f" ×{s['owed']}" if s["owed"] > 1 else ""
            if i == pointer:
                mark, tail = "👉", f"{times} {t(lang, 'turn_mark')}"
            elif s["owed"] <= 0:
                mark, tail = "✅", ""
            elif i < pointer:
                mark, tail = "❗", f" — {t(lang, 'debt_mark')}{times}"
            else:
                mark, tail = "⏳", times
            wait = " 🕓" if s["user_id"] in pending else ""
            lines.append(f"{i + 1}. {mark} {esc(s['name'])}{tail}{wait}")
        if c["status"] == OPEN:
            lines += ["", t(lang, "queue_now", name=esc(shares[pointer]["name"]))]
        all_paid = False
    else:
        share = c["share"]
        paid = sum(1 for s in shares if s["paid"])
        all_paid = paid == len(shares)
        card = await db.get_card(c["creator_id"])
        lines = [
            f"💰 <b>{esc(c['title'])}</b>",
            t(lang, "paid_by", name=esc(c["creator_name"]), amount=fmt_money(c["amount"], cur, lang)),
            t(lang, "per_person", n=len(shares), share=fmt_money(share, cur, lang)),
            "",
            card_text(lang, card) if card else t(lang, "no_card_line", name=esc(c["creator_name"])),
            "",
        ]
        for s in shares:
            if s["user_id"] == c["creator_id"]:
                lines.append(f"💳 {esc(s['name'])} — {t(lang, 'payer_mark')}")
            else:
                mark = "✅" if s["paid"] else ("🕓" if s["user_id"] in pending else "⏳")
                lines.append(f"{mark} {esc(s['name'])}")
        collected = min(paid * share, c["amount"])
        lines += ["", t(lang, "collected", paid=paid, n=len(shares),
                        sum=fmt_money(collected, cur, lang), total=fmt_money(c["amount"], cur, lang))]

    if c["status"] != OPEN:
        lines.append(t(lang, "closed_all_paid" if all_paid else "closed"))
        return "\n".join(lines), None

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_pay"), url=await start_link(bot, f"pay_{cid}"))
    return "\n".join(lines), kb.as_markup()


def manage_kb(lang: str, cid: int) -> InlineKeyboardMarkup:
    """Кнопки автора сбора — только в его личке."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_remind"), callback_data=Act(action="remind", cid=cid))
    kb.button(text=t(lang, "btn_edit"), callback_data=Act(action="edit", cid=cid))
    kb.button(text=t(lang, "btn_close"), callback_data=Act(action="close", cid=cid))
    kb.button(text=t(lang, "btn_back"), callback_data=Act(action="mine"))
    kb.adjust(3, 1)
    return kb.as_markup()


async def refresh(db: DB, bot: Bot, cid: int) -> None:
    c = await db.get_collection(cid)
    if not c or not c["message_id"]:
        return
    # Черновик живёт в личке автора, опубликованный сбор — в группе.
    chat_id = c["creator_id"] if c["status"] == DRAFT else c["chat_id"]
    text, markup = await render(db, bot, cid)
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=c["message_id"], reply_markup=markup)
    except TelegramAPIError:
        pass  # сообщение не изменилось или удалено


async def sync_user(db: DB, bot: Bot, user: User) -> None:
    """Если человек сменил имя или @username — обновляем его везде и перерисовываем его сборы."""
    stored = await db.stored_name(user.id)
    name = display_name(user)
    if stored is None or stored == name:
        return
    for cid in await db.rename_user(user.id, name):
        await refresh(db, bot, cid)


async def sync_names(db: DB, bot: Bot) -> None:
    """При запуске сверяет имена всех жильцов с Telegram."""
    seen = set()
    for m in await db.all_members():
        if m["user_id"] in seen:
            continue
        try:
            member = await bot.get_chat_member(m["chat_id"], m["user_id"])
        except TelegramAPIError:
            continue  # человек вышел из группы или бот потерял доступ
        seen.add(m["user_id"])
        name = display_name(member.user)
        if name != m["name"]:
            await db.rename_user(m["user_id"], name)


async def refresh_open(db: DB, bot: Bot) -> None:
    """При запуске перерисовывает открытые карточки — чтобы после обновления бота у них были новые кнопки."""
    for cid in await db.open_ids():
        await refresh(db, bot, cid)


async def creator_only(call: CallbackQuery, db: DB, cid: int, lang: str, status: str):
    """Сбор, если он в нужном статусе и кнопку нажал автор; иначе — ответ-подсказка."""
    c = await db.get_collection(cid)
    if not c or c["status"] != status:
        await call.answer(t(lang, "already_closed"))
        return None
    if call.from_user.id != c["creator_id"]:
        await call.answer(t(lang, "only_creator"), show_alert=True)
        return None
    return c


async def apply_payment(db: DB, bot: Bot, c, user_id: int) -> None:
    """Засчитывает подтверждённый платёж."""
    if c["kind"] == QUEUE:
        await db.queue_pay(c["id"], user_id)
    else:
        await db.set_paid(c["id"], user_id)
        if all(s["paid"] for s in await db.get_shares(c["id"])):
            await db.set_status(c["id"], CLOSED)  # на карточке появится «Все оплатили»
    await refresh(db, bot, c["id"])


# ---------- входы: команды и добавление в группу ----------

async def post_group_menu(db: DB, bot: Bot, chat_id: int, chat_type: str) -> None:
    """Новое меню в группе; прошлое меню бот убирает, если оно не закреплено."""
    old = GROUP_MENUS.get(chat_id)
    if old:
        try:
            pinned = (await bot.get_chat(chat_id)).pinned_message
        except TelegramAPIError:
            pinned = None
        if not pinned or pinned.message_id != old:
            await safe_delete(bot, chat_id, old)
    text, markup = await menu_view(bot, await get_lang(db), chat_id, chat_type, False)
    sent = await try_send(bot, chat_id, text, reply_markup=markup)
    if sent:
        GROUP_MENUS[chat_id] = sent.message_id


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_added(event: ChatMemberUpdated, db: DB, bot: Bot):
    await db.remember_group(event.chat.id)
    await post_group_menu(db, bot, event.chat.id, event.chat.type)


@router.message(CommandStart(), PRIVATE)
async def cmd_start_private(message: Message, command: CommandObject, db: DB, lang: str,
                            state: FSMContext, bot: Bot, admin_id: Optional[int]):
    chat_id, user = message.chat.id, message.from_user
    await reset_state(bot, chat_id, state)
    await safe_delete(bot, chat_id, message.message_id)  # «/start ...» в чате не нужен
    args = command.args or ""
    action, _, arg = args.partition("_")
    if action == "new" and arg.lstrip("-").isdigit():
        await start_new(chat_id, user, db, lang, state, bot, int(arg), user.id == admin_id)
    elif action == "pay" and arg.isdigit():
        await start_pay(chat_id, user.id, db, lang, state, bot, int(arg))
    elif action == "edit" and arg.isdigit():
        await start_edit(chat_id, user.id, db, lang, state, bot, int(arg), new=True)
    elif args == "card":
        await ask_card(chat_id, user.id, db, lang, state, bot, new=True)
    elif args == "debts":
        await show(bot, db, chat_id, await debts_view(db, lang, user.id), back_kb(lang), new=True)
    else:
        text, markup = await menu_view(bot, lang, chat_id, "private", user.id == admin_id)
        await show(bot, db, chat_id, text, markup, new=True)


@router.message(Command("start", "menu", "help"))
async def cmd_menu(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot, admin_id: Optional[int]):
    chat_id = message.chat.id
    await safe_delete(bot, chat_id, message.message_id)  # в группе — если у бота есть права
    if message.chat.type == "private":
        await reset_state(bot, chat_id, state)
        text, markup = await menu_view(bot, lang, chat_id, "private", message.from_user.id == admin_id)
        await show(bot, db, chat_id, text, markup, new=True)
        return
    await db.remember_group(chat_id)
    await post_group_menu(db, bot, chat_id, message.chat.type)


# ---------- меню и навигация ----------

@router.callback_query(Act.filter(F.action == "menu"))
async def cb_menu(call: CallbackQuery, lang: str, state: FSMContext, bot: Bot, admin_id: Optional[int]):
    await call.answer()
    chat = call.message.chat
    if chat.type == "private":
        await reset_state(bot, chat.id, state)
    text, markup = await menu_view(bot, lang, chat.id, chat.type, call.from_user.id == admin_id)
    await safe_edit(call.message, text, markup)
    if chat.type == "private":
        SCREENS[chat.id] = call.message.message_id


@router.callback_query(Act.filter(F.action == "lang"))
async def cb_lang(call: CallbackQuery, lang: str, admin_id: Optional[int]):
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "lang_admin_only"), show_alert=True)
        return
    await call.answer()
    await safe_edit(call.message, CHOOSE_LANG, lang_kb(lang))


@router.callback_query(Act.filter(F.action == "setlang"))
async def cb_setlang(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "lang_admin_only"), show_alert=True)
        return
    await db.set_lang(callback_data.val)
    await call.answer()
    text, markup = await menu_view(bot, callback_data.val, call.message.chat.id, call.message.chat.type, True)
    await safe_edit(call.message, text, markup)


@router.callback_query(Act.filter(F.action == "members"))
async def cb_members(call: CallbackQuery, db: DB, lang: str):
    await call.answer()
    await safe_edit(call.message, *await members_view(db, lang, call.message.chat.id))


@router.callback_query(Act.filter(F.action == "list"))
async def cb_list(call: CallbackQuery, db: DB, lang: str):
    await call.answer()
    await safe_edit(call.message, *await list_view(db, lang, call.message.chat.id))


@router.callback_query(Act.filter(F.action == "show"))
async def cb_show(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    """Переносит карточку сбора вниз чата: присылает заново, старую удаляет."""
    c = await db.get_collection(callback_data.cid)
    if not c or c["status"] != OPEN:
        await call.answer(t(lang, "already_closed"))
        return
    await call.answer()
    text, markup = await render(db, bot, c["id"])
    sent = await call.message.answer(text, reply_markup=markup)
    await safe_delete(bot, c["chat_id"], c["message_id"])
    await db.set_message_id(c["id"], sent.message_id)


# ---------- жильцы (в группе) ----------

@router.callback_query(Act.filter(F.action == "join"))
async def cb_join(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    chat_id = call.message.chat.id
    added = await add_tenant(db, bot, chat_id, call.from_user.id, display_name(call.from_user))
    await call.answer(t(lang, "joined" if added else "already_joined"))
    if callback_data.val == "m":
        await safe_edit(call.message, *await members_view(db, lang, chat_id))


async def add_tenant(db: DB, bot: Bot, chat_id: int, user_id: int, name: str) -> bool:
    """Добавляет жильца и в открытые черновики этого чата. True — если его раньше не было."""
    added = await db.add_member(chat_id, user_id, name)
    for d in await db.chat_collections(chat_id, DRAFT):
        await db.add_share(d["id"], user_id, name)
        await refresh(db, bot, d["id"])
    return added


@router.callback_query(Act.filter(F.action == "leave"))
async def cb_leave(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    chat_id = call.message.chat.id
    removed = await db.remove_member(chat_id, call.from_user.id)
    for d in await db.chat_collections(chat_id, DRAFT):
        if await db.remove_share(d["id"], call.from_user.id):
            await refresh(db, bot, d["id"])
    await call.answer(t(lang, "left" if removed else "not_member"))
    if callback_data.val == "m":
        await safe_edit(call.message, *await members_view(db, lang, chat_id))


# ---------- админ добавляет жильцов (в личке) ----------

@router.callback_query(Act.filter(F.action == "addm"))
async def cb_add_members(call: CallbackQuery, callback_data: Act, db: DB, lang: str, state: FSMContext,
                         bot: Bot, admin_id: Optional[int]):
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "admin_only"), show_alert=True)
        return
    await call.answer()
    chat_id = call.message.chat.id
    SCREENS[chat_id] = call.message.message_id
    if callback_data.cid:
        await start_add_members(chat_id, db, lang, state, bot, callback_data.cid)
        return

    groups = []
    for group_id in await db.known_groups():
        try:
            groups.append(await bot.get_chat(group_id))
        except TelegramAPIError:
            pass  # бота удалили из группы
    if not groups:
        await show(bot, db, chat_id, t(lang, "no_groups"), back_kb(lang))
    elif len(groups) == 1:
        await start_add_members(chat_id, db, lang, state, bot, groups[0].id)
    else:
        kb = InlineKeyboardBuilder()
        for g in groups:
            kb.button(text=(g.title or str(g.id))[:60], callback_data=Act(action="addm", cid=g.id))
        back_button(kb, lang)
        kb.adjust(1)
        await show(bot, db, chat_id, t(lang, "choose_group"), kb.as_markup())


async def start_add_members(chat_id: int, db: DB, lang: str, state: FSMContext, bot: Bot, group_id: int) -> None:
    try:
        group = await bot.get_chat(group_id)
    except TelegramAPIError:
        await show(bot, db, chat_id, t(lang, "not_in_group"), back_kb(lang))
        return

    # Выбор людей работает только через обычную клавиатуру, поэтому для неё нужно отдельное сообщение.
    await show(bot, db, chat_id, t(lang, "ask_members", group=esc(group.title or "")), back_kb(lang, cancel=True))
    picker = KeyboardButton(
        text=t(lang, "btn_pick_users"),
        request_users=KeyboardButtonRequestUsers(
            request_id=1, user_is_bot=False, max_quantity=10, request_name=True, request_username=True,
        ),
    )
    markup = ReplyKeyboardMarkup(keyboard=[[picker]], resize_keyboard=True, one_time_keyboard=True)
    sent = await bot.send_message(chat_id, "👇", reply_markup=markup)
    await state.set_state(Form.add_members)
    await state.update_data(chat_id=group_id, chat_title=group.title or "", picker=sent.message_id)


async def close_picker(bot: Bot, chat_id: int, data: dict) -> None:
    """Убирает сообщение и клавиатуру выбора людей."""
    await safe_delete(bot, chat_id, data.get("picker"))
    msg = await try_send(bot, chat_id, "…", reply_markup=ReplyKeyboardRemove())
    if msg:
        await safe_delete(bot, chat_id, msg.message_id)


@router.message(Form.add_members, PRIVATE, F.users_shared)
async def on_members_shared(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    data = await state.get_data()
    await state.clear()
    await safe_delete(bot, chat_id, message.message_id)
    await close_picker(bot, chat_id, data)
    added = []
    for u in message.users_shared.users:
        name = f"@{u.username}" if u.username else (" ".join(filter(None, [u.first_name, u.last_name])) or str(u.user_id))
        if await add_tenant(db, bot, data["chat_id"], u.user_id, name):
            added.append(esc(name))
    text = (t(lang, "members_added", group=esc(data["chat_title"]), names=", ".join(added))
            if added else t(lang, "members_none_new"))
    await show(bot, db, chat_id, text, back_kb(lang))


@router.message(Form.add_members, PRIVATE)
async def on_members_other(message: Message, bot: Bot):
    """Пока открыт выбор людей, лишние сообщения не копим."""
    await safe_delete(bot, message.chat.id, message.message_id)


# ---------- долги (в личке) ----------

@router.callback_query(Act.filter(F.action == "debts"))
async def cb_debts(call: CallbackQuery, db: DB, lang: str):
    await call.answer()
    await safe_edit(call.message, await debts_view(db, lang, call.from_user.id), back_kb(lang))


# ---------- карта (в личке) ----------

@router.callback_query(Act.filter(F.action == "card"))
async def cb_card(call: CallbackQuery, callback_data: Act, db: DB, lang: str, state: FSMContext, bot: Bot):
    """cid — карту добавляют из черновика, потом вернёмся к нему."""
    await call.answer()
    SCREENS[call.message.chat.id] = call.message.message_id
    await ask_card(call.message.chat.id, call.from_user.id, db, lang, state, bot, draft_cid=callback_data.cid)


async def ask_card(chat_id: int, user_id: int, db: DB, lang: str, state: FSMContext, bot: Bot,
                   draft_cid: int = 0, new: bool = False) -> None:
    text = t(lang, "ask_card")
    card = await db.get_card(user_id)
    if card:
        text += t(lang, "ask_card_current", card=card_text(lang, card))
    back = back_kb(lang, "draft", draft_cid, cancel=True) if draft_cid else back_kb(lang, cancel=True)
    await show(bot, db, chat_id, text, back, new=new)
    await state.set_state(Form.card)
    await state.update_data(draft_cid=draft_cid)


@router.message(Form.card, PRIVATE, F.text)
async def on_card(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id, user_id = message.chat.id, message.from_user.id
    await safe_delete(bot, chat_id, message.message_id)
    data = await state.get_data()
    draft_cid = data.get("draft_cid", 0)
    if message.text.strip() == "-":
        await db.delete_card(user_id)
        result = t(lang, "card_deleted")
    else:
        parsed = parse_card(message.text)
        if not parsed:
            back = back_kb(lang, "draft", draft_cid, cancel=True) if draft_cid else back_kb(lang, cancel=True)
            await show(bot, db, chat_id, t(lang, "bad_card"), back)
            return
        number, holder = parsed
        await db.set_card(user_id, number, holder)
        result = t(lang, "card_saved", card=card_text(lang, {"number": number, "holder": holder}))

    await state.clear()
    for c in await db.creator_active(user_id):
        await refresh(db, bot, c["id"])  # черновик тоже перерисуется на месте
    if not draft_cid:
        await show(bot, db, chat_id, result, back_kb(lang))


# ---------- новый сбор (в личке) ----------

async def start_new(chat_id: int, user: User, db: DB, lang: str, state: FSMContext, bot: Bot,
                    group_id: int, is_admin: bool) -> None:
    try:
        member = await bot.get_chat_member(group_id, user.id)
        group = await bot.get_chat(group_id)
    except TelegramAPIError:
        member = None
    if not member or member.status in ("left", "kicked"):
        await show(bot, db, chat_id, t(lang, "not_in_group"), back_kb(lang), new=True)
        return

    await state.update_data(chat_id=group_id, chat_title=group.title or "")
    if not is_admin:
        # Очередь создаёт только админ бота, остальным сразу «поделить сумму».
        await state.update_data(kind=SPLIT)
        await state.set_state(Form.amount)
        await show(bot, db, chat_id, t(lang, "ask_amount_split"), back_kb(lang, cancel=True), new=True)
        return

    await state.set_state(Form.kind)
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_kind_split"), callback_data=Act(action="kind", val=SPLIT))
    kb.button(text=t(lang, "btn_kind_queue"), callback_data=Act(action="kind", val=QUEUE))
    kb.button(text=t(lang, "btn_cancel"), callback_data=Act(action="menu"))
    kb.adjust(1)
    await show(bot, db, chat_id, t(lang, "choose_kind", group=esc(group.title or "")), kb.as_markup(), new=True)


@router.callback_query(Form.kind, Act.filter(F.action == "kind"))
async def cb_kind(call: CallbackQuery, callback_data: Act, lang: str, state: FSMContext, admin_id: Optional[int]):
    if callback_data.val == QUEUE and call.from_user.id != admin_id:
        await call.answer(t(lang, "queue_admin_only"), show_alert=True)
        return
    await state.update_data(kind=callback_data.val)
    await state.set_state(Form.amount)
    await call.answer()
    SCREENS[call.message.chat.id] = call.message.message_id
    await safe_edit(call.message, t(lang, f"ask_amount_{callback_data.val}"), back_kb(lang, cancel=True))


@router.message(Form.amount, PRIVATE, F.text)
async def on_amount(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    await safe_delete(bot, chat_id, message.message_id)
    parsed = parse_amount(message.text)
    if not parsed:
        await show(bot, db, chat_id, t(lang, "bad_amount"), back_kb(lang, cancel=True))
        return
    data = await state.get_data()
    await state.clear()

    amount, currency, title = parsed
    user = message.from_user
    name = display_name(user)
    await db.add_member(data["chat_id"], user.id, name)
    cid = await db.create_draft(data["chat_id"], data["chat_title"], user.id, name,
                                data["kind"], title, amount, currency)
    text, markup = await render(db, bot, cid)
    await db.set_message_id(cid, await show(bot, db, chat_id, text, markup))


@router.callback_query(Act.filter(F.action == "draft"))
async def cb_draft(call: CallbackQuery, callback_data: Act, db: DB, lang: str, state: FSMContext, bot: Bot):
    """Вернуться к черновику (например, отменив ввод карты или названия)."""
    await reset_state(bot, call.message.chat.id, state)
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    await call.answer()
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "tg"))
async def cb_toggle_member(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    uid = callback_data.uid
    if not await db.remove_share(c["id"], uid):
        members = {m["user_id"]: m["name"] for m in await db.get_members(c["chat_id"])}
        await db.add_share(c["id"], uid, members.get(uid, str(uid)))
    await call.answer()
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "prepaid"))
async def cb_prepaid(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    await db.toggle_paid(c["id"], callback_data.uid)
    await call.answer()
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "reset"))
async def cb_reset(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    await db.clear_shares(c["id"])
    await call.answer()
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "cur"))
async def cb_currency(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    # Число остаётся тем же, меняется только валюта: 50 сум <-> $50.
    new = callback_data.val
    amount = c["amount"] * 100 if new == USD else max(c["amount"] // 100, 1)
    await db.set_amount(c["id"], amount, new)
    await call.answer()
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "create"))
async def cb_create(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    shares = await db.get_shares(c["id"])
    if c["kind"] == QUEUE:
        if len(shares) < 2:
            await call.answer(t(lang, "need_queue"), show_alert=True)
            return
        share = c["amount"]
    else:
        if not any(s["user_id"] != c["creator_id"] and not s["paid"] for s in shares):
            await call.answer(t(lang, "need_people"), show_alert=True)
            return
        share = split_share(c["amount"], c["currency"], len(shares))

    await db.open_draft(c["id"], share)
    text, markup = await render(db, bot, c["id"])
    sent = await try_send(bot, c["chat_id"], text, reply_markup=markup)
    if not sent:
        await db.set_status(c["id"], DRAFT)
        await call.answer(t(lang, "publish_failed"), show_alert=True)
        return
    await db.set_message_id(c["id"], sent.message_id)
    await call.answer()
    await safe_edit(call.message, t(lang, "draft_published", title=esc(c["title"]), group=esc(c["chat_title"])),
                    manage_kb(lang, c["id"]))


@router.callback_query(Act.filter(F.action == "cancel"))
async def cb_cancel(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    await db.delete_collection(c["id"])
    await call.answer(t(lang, "cancelled"))
    await safe_edit(call.message, *await menu_view(bot, lang, call.message.chat.id, "private",
                                                   call.from_user.id == admin_id))


# ---------- мои сборы: напомнить, изменить, закрыть (в личке) ----------

@router.callback_query(Act.filter(F.action == "mine"))
async def cb_mine(call: CallbackQuery, db: DB, lang: str, state: FSMContext, bot: Bot):
    await call.answer()
    await reset_state(bot, call.message.chat.id, state)
    await safe_edit(call.message, *await mine_view(db, lang, call.from_user.id))


@router.callback_query(Act.filter(F.action == "manage"))
async def cb_manage(call: CallbackQuery, callback_data: Act, db: DB, lang: str, state: FSMContext, bot: Bot):
    await reset_state(bot, call.message.chat.id, state)
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    await call.answer()
    text, _ = await render(db, bot, c["id"])
    await safe_edit(call.message, text, manage_kb(lang, c["id"]))


@router.callback_query(Act.filter(F.action == "edit"))
async def cb_edit(call: CallbackQuery, callback_data: Act, db: DB, lang: str, state: FSMContext, bot: Bot):
    await call.answer()
    SCREENS[call.message.chat.id] = call.message.message_id
    await start_edit(call.message.chat.id, call.from_user.id, db, lang, state, bot, callback_data.cid)


async def start_edit(chat_id: int, user_id: int, db: DB, lang: str, state: FSMContext, bot: Bot,
                     cid: int, new: bool = False) -> None:
    c = await db.get_collection(cid)
    if not c or c["status"] == CLOSED:
        await show(bot, db, chat_id, t(lang, "already_closed"), back_kb(lang), new=new)
        return
    if user_id != c["creator_id"]:
        await show(bot, db, chat_id, t(lang, "only_creator"), back_kb(lang), new=new)
        return
    back = back_kb(lang, "draft" if c["status"] == DRAFT else "manage", cid, cancel=True)
    await show(bot, db, chat_id, t(lang, "ask_title", title=esc(c["title"])), back, new=new)
    await state.set_state(Form.title)
    await state.update_data(cid=cid)


@router.message(Form.title, PRIVATE, F.text)
async def on_title(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    await safe_delete(bot, chat_id, message.message_id)
    title = message.text.strip()[:100]
    data = await state.get_data()
    await state.clear()
    c = await db.get_collection(data["cid"])
    if not c or c["status"] == CLOSED:
        await show(bot, db, chat_id, t(lang, "already_closed"), back_kb(lang))
        return
    await db.set_title(c["id"], title)
    await refresh(db, bot, c["id"])  # черновик перерисуется на месте, карточка — в группе
    if c["status"] == OPEN:
        text, _ = await render(db, bot, c["id"])
        await show(bot, db, chat_id, f"{t(lang, 'title_saved', title=esc(title))}\n\n{text}", manage_kb(lang, c["id"]))


@router.callback_query(Act.filter(F.action == "remind"))
async def cb_remind(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    shares = await db.get_shares(c["id"])
    if c["kind"] == QUEUE:
        s = shares[c["pointer"]]
        text = t(lang, "remind_queue", name=mention(s["user_id"], s["name"]), title=esc(c["title"]),
                 amount=fmt_money(c["amount"] * s["owed"], c["currency"], lang))
    else:
        pending = await db.pending_users(c["id"])
        debtors = [s for s in shares if not s["paid"] and s["user_id"] not in pending]
        if not debtors:
            await call.answer(t(lang, "nobody_to_remind"), show_alert=True)
            return
        text = t(lang, "remind", title=esc(c["title"]), share=fmt_money(c["share"], c["currency"], lang),
                 people=", ".join(mention(s["user_id"], s["name"]) for s in debtors))
    # Напоминание — в группу, ответом на карточку сбора.
    reply = ReplyParameters(message_id=c["message_id"], allow_sending_without_reply=True) if c["message_id"] else None
    sent = await try_send(bot, c["chat_id"], text, reply_parameters=reply)
    await call.answer(t(lang, "reminded" if sent else "publish_failed"), show_alert=not sent)


@router.callback_query(Act.filter(F.action == "close"))
async def cb_close(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    await db.set_status(c["id"], CLOSED)
    await call.answer(t(lang, "closed_ok"))
    await refresh(db, bot, c["id"])
    if call.message.chat.type == "private":
        text, _ = await render(db, bot, c["id"])
        await safe_edit(call.message, text, back_kb(lang, "mine"))


# ---------- оплата с чеком (в личке) ----------

async def start_pay(chat_id: int, user_id: int, db: DB, lang: str, state: FSMContext, bot: Bot, cid: int) -> None:
    c = await db.get_collection(cid)
    error = None
    if not c or c["status"] != OPEN:
        error = "already_closed"
    else:
        shares = {s["user_id"]: s for s in await db.get_shares(cid)}
        if user_id not in shares:
            error = "not_participant"
        elif user_id in await db.pending_users(cid):
            error = "already_pending"
        elif c["kind"] == SPLIT and user_id == c["creator_id"]:
            error = "creator_pay"
        elif c["kind"] == SPLIT and shares[user_id]["paid"]:
            error = "already_paid"
    if error:
        await show(bot, db, chat_id, t(lang, error), back_kb(lang), new=True)
        return

    cur = c["currency"]
    if c["kind"] == QUEUE:
        text = t(lang, "pay_queue", title=esc(c["title"]), amount=fmt_money(c["amount"], cur, lang))
    else:
        card = await db.get_card(c["creator_id"])
        text = t(lang, "pay_split", title=esc(c["title"]), amount=fmt_money(c["share"], cur, lang),
                 creator=esc(c["creator_name"]),
                 card=card_text(lang, card) if card else t(lang, "no_card_line", name=esc(c["creator_name"])))

    await show(bot, db, chat_id, text, back_kb(lang, cancel=True), new=True)
    await state.set_state(Form.receipt)
    await state.update_data(cid=cid, prompt=text)


async def send_receipt(bot: Bot, chat_id: int, file_type: str, file_id: str, caption: str,
                       markup: InlineKeyboardMarkup) -> None:
    if file_type == "photo":
        await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=markup)
    else:
        await bot.send_document(chat_id, file_id, caption=caption, reply_markup=markup)


@router.message(Form.receipt, PRIVATE)
async def on_receipt(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    data = await state.get_data()
    if message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
    else:
        await safe_delete(bot, chat_id, message.message_id)
        await show(bot, db, chat_id, f"{data['prompt']}\n\n⚠️ {t(lang, 'send_photo')}", back_kb(lang, cancel=True))
        return

    # Фото чека остаётся в чате — это подтверждение оплаты для самого человека.
    await state.clear()
    c = await db.get_collection(data["cid"])
    if not c or c["status"] != OPEN:
        await show(bot, db, chat_id, t(lang, "already_closed"), back_kb(lang))
        return

    user = message.from_user
    name = display_name(user)
    if user.id == c["creator_id"]:
        # Автор очереди сам заплатил свой раз — подтверждать некому.
        await db.add_payment(c["id"], user.id, name, file_id, file_type, CONFIRMED)
        await apply_payment(db, bot, c, user.id)
        await show(bot, db, chat_id, t(lang, "payment_saved"), back_kb(lang))
        return

    pid = await db.add_payment(c["id"], user.id, name, file_id, file_type, PENDING)
    amount = c["amount"] if c["kind"] == QUEUE else c["share"]
    caption = t(lang, "receipt_caption", name=esc(name), title=esc(c["title"]),
                amount=fmt_money(amount, c["currency"], lang))
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_confirm"), callback_data=Act(action="ok", cid=c["id"], uid=pid))
    kb.button(text=t(lang, "btn_reject"), callback_data=Act(action="no", cid=c["id"], uid=pid))
    try:
        await send_receipt(bot, c["creator_id"], file_type, file_id, caption, kb.as_markup())
    except TelegramAPIError:
        # Автор закрыл личку с ботом — показываем чек в группе, подтвердить может только он.
        await send_receipt(bot, c["chat_id"], file_type, file_id, caption, kb.as_markup())

    await show(bot, db, chat_id, t(lang, "receipt_sent", name=esc(c["creator_name"])), back_kb(lang))
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action.in_({"ok", "no"})))
async def cb_receipt(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await db.get_collection(callback_data.cid)
    p = await db.get_payment(callback_data.uid)
    if not c or not p:
        await call.answer(t(lang, "already_handled"))
        return
    if call.from_user.id != c["creator_id"]:
        await call.answer(t(lang, "only_creator"), show_alert=True)
        return
    if p["status"] != PENDING:
        await call.answer(t(lang, "already_handled"))
        return

    title = esc(c["title"])
    creator = esc(c["creator_name"])
    if callback_data.action == "ok":
        if c["status"] != OPEN:
            await call.answer(t(lang, "already_closed"), show_alert=True)
            return
        await db.set_payment_status(p["id"], CONFIRMED)
        await apply_payment(db, bot, c, p["user_id"])
        await try_send(bot, p["user_id"], t(lang, "payer_confirmed", creator=creator, title=title))
        result = t(lang, "confirmed")
    else:
        await db.set_payment_status(p["id"], REJECTED)
        await refresh(db, bot, c["id"])
        await try_send(bot, p["user_id"], t(lang, "payer_rejected", creator=creator, title=title))
        result = t(lang, "rejected")

    await call.answer(result)
    try:
        await call.message.edit_caption(caption=f"{call.message.html_text}\n\n{result}", reply_markup=None)
    except TelegramAPIError:
        pass
