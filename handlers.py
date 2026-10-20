"""Меню на inline-кнопках, сборы, очереди и чеки.

В группе — только общее: меню, список, жильцы и карточки сборов.
Всё личное (новый сбор, карта, долги, «Я оплатил» с чеком) — в личке с ботом
через ссылки вида t.me/<бот>?start=<действие>.
"""
from __future__ import annotations

from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command, CommandObject, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import CONFIRMED, DB, DRAFT, OPEN, CLOSED, PENDING, QUEUE, REJECTED, SPLIT
from i18n import CHOOSE_LANG, DEFAULT_LANG, t
from utils import USD, UZS, card_type, esc, fmt_card, fmt_money, mention, parse_amount, parse_card, split_share

router = Router()
PRIVATE = F.chat.type == "private"


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


# ---------- помощники ----------

def display_name(user: User) -> str:
    return user.full_name or (user.username and "@" + user.username) or str(user.id)


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


async def try_send(bot: Bot, chat_id: int, text: str, **kwargs) -> Optional[Message]:
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except TelegramAPIError:
        return None  # человек не открывал бота или заблокировал его


def card_text(lang: str, card) -> str:
    holder = f" ({esc(card['holder'])})" if card["holder"] else ""
    kind = card_type(card["number"]) or t(lang, "card")
    return t(lang, "card_line", type=kind, number=fmt_card(card["number"]), holder=holder)


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_cancel"), callback_data=Act(action="stop"))
    return kb.as_markup()


# ---------- меню ----------

def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data=Act(action="setlang", val="ru"))
    kb.button(text="🇺🇿 O'zbekcha", callback_data=Act(action="setlang", val="uz"))
    return kb.as_markup()


async def menu_view(bot: Bot, lang: str, chat_id: int, chat_type: str, is_admin: bool) -> Tuple[str, InlineKeyboardMarkup]:
    kb = InlineKeyboardBuilder()
    if chat_type == "private":
        me = await bot.me()
        kb.button(text=t(lang, "btn_card"), callback_data=Act(action="card"))
        kb.button(text=t(lang, "btn_debts"), callback_data=Act(action="debts"))
        sizes = [2]
        if is_admin:
            kb.button(text=t(lang, "btn_lang"), callback_data=Act(action="lang"))
            sizes.append(1)
        kb.button(text=t(lang, "btn_add_group"), url=f"https://t.me/{me.username}?startgroup=1")
        kb.adjust(*sizes, 1)
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
        for uid in others:
            kb.button(text=f"⬜ {people[uid]}"[:40], callback_data=Act(action="tg", cid=cid, uid=uid))
        sizes = [1] * len(people)
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
        for uid in sorted(people, key=lambda u: people[u].lower()):
            mark = "✅" if uid in selected else "⬜"
            kb.button(text=f"{mark} {people[uid]}"[:40], callback_data=Act(action="tg", cid=cid, uid=uid))
        sizes = [2] * (len(people) // 2) + [1] * (len(people) % 2)
        kb.button(text=t(lang, "btn_currency", cur=t(lang, "cur_" + cur)),
                  callback_data=Act(action="cur", cid=cid, val=other_cur))
        sizes.append(1)
        if not card:
            kb.button(text=t(lang, "btn_card"), callback_data=Act(action="card"))
            sizes.append(1)

    kb.button(text=t(lang, "btn_create"), callback_data=Act(action="create", cid=cid))
    kb.button(text=t(lang, "btn_cancel"), callback_data=Act(action="cancel", cid=cid))
    sizes.append(2)
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
    else:
        share = c["share"]
        paid = sum(1 for s in shares if s["paid"])
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
        lines.append(t(lang, "closed"))
        return "\n".join(lines), None

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_pay"), url=await start_link(bot, f"pay_{cid}"))
    kb.button(text=t(lang, "btn_remind"), callback_data=Act(action="remind", cid=cid))
    kb.button(text=t(lang, "btn_close"), callback_data=Act(action="close", cid=cid))
    kb.adjust(1, 2)
    return "\n".join(lines), kb.as_markup()


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
        await refresh(db, bot, c["id"])
        return
    await db.set_paid(c["id"], user_id)
    if all(s["paid"] for s in await db.get_shares(c["id"])):
        await db.set_status(c["id"], CLOSED)
        await try_send(bot, c["chat_id"], t(await get_lang(db), "all_paid", title=esc(c["title"])))
    await refresh(db, bot, c["id"])


# ---------- входы: команды и добавление в группу ----------

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_added(event: ChatMemberUpdated, db: DB, bot: Bot):
    text, markup = await menu_view(bot, await get_lang(db), event.chat.id, event.chat.type, False)
    await try_send(bot, event.chat.id, text, reply_markup=markup)


@router.message(CommandStart(), PRIVATE)
async def cmd_start_private(message: Message, command: CommandObject, db: DB, lang: str,
                            state: FSMContext, bot: Bot, admin_id: Optional[int]):
    await state.clear()
    args = command.args or ""
    action, _, arg = args.partition("_")
    if action == "new" and arg.lstrip("-").isdigit():
        await start_new(message, db, lang, state, bot, int(arg))
    elif action == "pay" and arg.isdigit():
        await start_pay(message, db, lang, state, int(arg))
    elif args == "card":
        await ask_card(message, message.from_user, db, lang, state)
    elif args == "debts":
        await send_debts(message, message.from_user.id, db, lang)
    else:
        await show_menu(message, bot, lang, admin_id)


@router.message(Command("start", "menu", "help"))
async def cmd_menu(message: Message, lang: str, bot: Bot, admin_id: Optional[int]):
    await show_menu(message, bot, lang, admin_id)


async def show_menu(message: Message, bot: Bot, lang: str, admin_id: Optional[int]) -> None:
    is_admin = message.from_user.id == admin_id
    text, markup = await menu_view(bot, lang, message.chat.id, message.chat.type, is_admin)
    await message.answer(text, reply_markup=markup)


# ---------- меню и навигация ----------

@router.callback_query(Act.filter(F.action == "menu"))
async def cb_menu(call: CallbackQuery, lang: str, bot: Bot, admin_id: Optional[int]):
    await call.answer()
    text, markup = await menu_view(bot, lang, call.message.chat.id, call.message.chat.type,
                                   call.from_user.id == admin_id)
    await safe_edit(call.message, text, markup)


@router.callback_query(Act.filter(F.action == "lang"))
async def cb_lang(call: CallbackQuery, lang: str, admin_id: Optional[int]):
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "lang_admin_only"), show_alert=True)
        return
    await call.answer()
    await safe_edit(call.message, CHOOSE_LANG, lang_kb())


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
    """Переотправляет карточку сбора вниз чата."""
    c = await db.get_collection(callback_data.cid)
    if not c or c["status"] != OPEN:
        await call.answer(t(lang, "already_closed"))
        return
    await call.answer()
    text, markup = await render(db, bot, c["id"])
    sent = await call.message.answer(text, reply_markup=markup)
    try:
        await bot.delete_message(c["chat_id"], c["message_id"])
    except TelegramAPIError:
        pass
    await db.set_message_id(c["id"], sent.message_id)


@router.callback_query(Act.filter(F.action == "stop"))
async def cb_stop(call: CallbackQuery, lang: str, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(call.message, t(lang, "cancelled"))


# ---------- жильцы (в группе) ----------

@router.callback_query(Act.filter(F.action == "join"))
async def cb_join(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    chat_id = call.message.chat.id
    name = display_name(call.from_user)
    added = await db.add_member(chat_id, call.from_user.id, name)
    for d in await db.chat_collections(chat_id, DRAFT):
        await db.add_share(d["id"], call.from_user.id, name)
        await refresh(db, bot, d["id"])
    await call.answer(t(lang, "joined" if added else "already_joined"))
    if callback_data.val == "m":
        await safe_edit(call.message, *await members_view(db, lang, chat_id))


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


# ---------- долги (в личке) ----------

@router.callback_query(Act.filter(F.action == "debts"))
async def cb_debts(call: CallbackQuery, db: DB, lang: str):
    await call.answer()
    await send_debts(call.message, call.from_user.id, db, lang)


async def send_debts(message: Message, user_id: int, db: DB, lang: str) -> None:
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
        await message.answer(t(lang, "debts_none"))
        return
    total = " + ".join(fmt_money(v, k, lang) for k, v in totals.items())
    await message.answer("\n".join([t(lang, "debts_title")] + lines + ["", t(lang, "total", sum=total)]))


# ---------- карта (в личке) ----------

@router.callback_query(Act.filter(F.action == "card"))
async def cb_card(call: CallbackQuery, db: DB, lang: str, state: FSMContext):
    await call.answer()
    await ask_card(call.message, call.from_user, db, lang, state)


async def ask_card(message: Message, user: User, db: DB, lang: str, state: FSMContext) -> None:
    text = t(lang, "ask_card")
    card = await db.get_card(user.id)
    if card:
        text += t(lang, "ask_card_current", card=card_text(lang, card))
    await message.answer(text, reply_markup=cancel_kb(lang))
    await state.set_state(Form.card)


@router.message(Form.card, PRIVATE, F.text)
async def on_card(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    if message.text.strip() == "-":
        await db.delete_card(user_id)
        reply = t(lang, "card_deleted")
    else:
        parsed = parse_card(message.text)
        if not parsed:
            await message.answer(t(lang, "bad_card"), reply_markup=cancel_kb(lang))
            return
        number, holder = parsed
        await db.set_card(user_id, number, holder)
        reply = t(lang, "card_saved", card=card_text(lang, {"number": number, "holder": holder}))

    await state.clear()
    await message.answer(reply)
    for c in await db.creator_active(user_id):
        await refresh(db, bot, c["id"])


# ---------- новый сбор (в личке) ----------

async def start_new(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot, chat_id: int) -> None:
    try:
        member = await bot.get_chat_member(chat_id, message.from_user.id)
        chat = await bot.get_chat(chat_id)
    except TelegramAPIError:
        member = None
    if not member or member.status in ("left", "kicked"):
        await message.answer(t(lang, "not_in_group"))
        return

    await state.set_state(Form.kind)
    await state.update_data(chat_id=chat_id, chat_title=chat.title or "")
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_kind_split"), callback_data=Act(action="kind", val=SPLIT))
    kb.button(text=t(lang, "btn_kind_queue"), callback_data=Act(action="kind", val=QUEUE))
    kb.button(text=t(lang, "btn_cancel"), callback_data=Act(action="stop"))
    kb.adjust(1)
    await message.answer(t(lang, "choose_kind", group=esc(chat.title or "")), reply_markup=kb.as_markup())


@router.callback_query(Form.kind, Act.filter(F.action == "kind"))
async def cb_kind(call: CallbackQuery, callback_data: Act, lang: str, state: FSMContext):
    await state.update_data(kind=callback_data.val)
    await state.set_state(Form.amount)
    await call.answer()
    await safe_edit(call.message, t(lang, f"ask_amount_{callback_data.val}"), cancel_kb(lang))


@router.message(Form.amount, PRIVATE, F.text)
async def on_amount(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    parsed = parse_amount(message.text)
    if not parsed:
        await message.answer(t(lang, "bad_amount"), reply_markup=cancel_kb(lang))
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
    sent = await message.answer(text, reply_markup=markup)
    await db.set_message_id(cid, sent.message_id)


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
        if not any(s["user_id"] != c["creator_id"] for s in shares):
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
    await safe_edit(call.message, t(lang, "draft_published", title=esc(c["title"]), group=esc(c["chat_title"])))


@router.callback_query(Act.filter(F.action == "cancel"))
async def cb_cancel(call: CallbackQuery, callback_data: Act, db: DB, lang: str):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    await db.delete_collection(c["id"])
    await call.answer()
    await safe_edit(call.message, t(lang, "cancelled"))


# ---------- оплата с чеком (в личке) ----------

async def start_pay(message: Message, db: DB, lang: str, state: FSMContext, cid: int) -> None:
    c = await db.get_collection(cid)
    if not c or c["status"] != OPEN:
        await message.answer(t(lang, "already_closed"))
        return
    user_id = message.from_user.id
    shares = {s["user_id"]: s for s in await db.get_shares(cid)}
    if user_id not in shares:
        await message.answer(t(lang, "not_participant"))
        return
    if user_id in await db.pending_users(cid):
        await message.answer(t(lang, "already_pending"))
        return

    cur = c["currency"]
    if c["kind"] == QUEUE:
        text = t(lang, "pay_queue", title=esc(c["title"]), amount=fmt_money(c["amount"], cur, lang))
    else:
        if user_id == c["creator_id"]:
            await message.answer(t(lang, "creator_pay"))
            return
        if shares[user_id]["paid"]:
            await message.answer(t(lang, "already_paid"))
            return
        card = await db.get_card(c["creator_id"])
        text = t(lang, "pay_split", title=esc(c["title"]), amount=fmt_money(c["share"], cur, lang),
                 creator=esc(c["creator_name"]),
                 card=card_text(lang, card) if card else t(lang, "no_card_line", name=esc(c["creator_name"])))

    await state.set_state(Form.receipt)
    await state.update_data(cid=cid)
    await message.answer(text, reply_markup=cancel_kb(lang))


async def send_receipt(bot: Bot, chat_id: int, file_type: str, file_id: str, caption: str,
                       markup: InlineKeyboardMarkup) -> None:
    if file_type == "photo":
        await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=markup)
    else:
        await bot.send_document(chat_id, file_id, caption=caption, reply_markup=markup)


@router.message(Form.receipt, PRIVATE)
async def on_receipt(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    if message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
    else:
        await message.answer(t(lang, "send_photo"), reply_markup=cancel_kb(lang))
        return

    data = await state.get_data()
    await state.clear()
    c = await db.get_collection(data["cid"])
    if not c or c["status"] != OPEN:
        await message.answer(t(lang, "already_closed"))
        return

    user = message.from_user
    name = display_name(user)
    if user.id == c["creator_id"]:
        # Автор очереди сам заплатил свой раз — подтверждать некому.
        await db.add_payment(c["id"], user.id, name, file_id, file_type, CONFIRMED)
        await apply_payment(db, bot, c, user.id)
        await message.answer(t(lang, "payment_saved"))
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

    await message.answer(t(lang, "receipt_sent", name=esc(c["creator_name"])))
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


# ---------- открытый сбор (кнопки в группе) ----------

@router.callback_query(Act.filter(F.action == "remind"))
async def cb_remind(call: CallbackQuery, callback_data: Act, db: DB, lang: str):
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    shares = await db.get_shares(c["id"])
    await call.answer()
    if c["kind"] == QUEUE:
        s = shares[c["pointer"]]
        text = t(lang, "remind_queue", name=mention(s["user_id"], s["name"]), title=esc(c["title"]),
                 amount=fmt_money(c["amount"] * s["owed"], c["currency"], lang))
    else:
        pending = await db.pending_users(c["id"])
        debtors = [s for s in shares if not s["paid"] and s["user_id"] not in pending]
        text = t(lang, "remind", title=esc(c["title"]), share=fmt_money(c["share"], c["currency"], lang),
                 people=", ".join(mention(s["user_id"], s["name"]) for s in debtors))
    await call.message.reply(text)


@router.callback_query(Act.filter(F.action == "close"))
async def cb_close(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    await db.set_status(c["id"], CLOSED)
    await call.answer(t(lang, "closed_ok"))
    await refresh(db, bot, c["id"])
