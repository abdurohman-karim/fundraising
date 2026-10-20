"""Меню на inline-кнопках, сборы и карты."""
from __future__ import annotations

from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ChatMemberUpdated, ForceReply, InlineKeyboardMarkup, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import DB, DRAFT, OPEN
from i18n import CHOOSE_LANG, DEFAULT_LANG, t
from utils import USD, UZS, card_type, esc, fmt_card, fmt_money, mention, parse_amount, parse_card, split_share

router = Router()


class Act(CallbackData, prefix="a"):
    action: str
    cid: int = 0
    uid: int = 0
    val: str = ""


class Form(StatesGroup):
    amount = State()
    card = State()


# ---------- помощники ----------

def display_name(user: User) -> str:
    return user.full_name or (user.username and "@" + user.username) or str(user.id)


def is_private(chat_type: str) -> bool:
    return chat_type == "private"


async def chat_lang(db: DB, chat_id: int) -> str:
    return await db.get_lang(chat_id) or DEFAULT_LANG


async def safe_edit(message: Message, text: str, markup: Optional[InlineKeyboardMarkup] = None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except TelegramBadRequest:
        pass  # текст не изменился


async def safe_delete(bot: Bot, chat_id: int, message_id: Optional[int]) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass  # нет прав или уже удалено


def card_text(lang: str, card) -> str:
    holder = f" ({esc(card['holder'])})" if card["holder"] else ""
    kind = card_type(card["number"]) or t(lang, "card")
    return t(lang, "card_line", type=kind, number=fmt_card(card["number"]), holder=holder)


# ---------- меню ----------

def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data=Act(action="setlang", val="ru"))
    kb.button(text="🇺🇿 O'zbekcha", callback_data=Act(action="setlang", val="uz"))
    return kb.as_markup()


async def menu_view(bot: Bot, lang: str, chat_type: str) -> Tuple[str, InlineKeyboardMarkup]:
    kb = InlineKeyboardBuilder()
    if is_private(chat_type):
        me = await bot.me()
        kb.button(text=t(lang, "btn_card"), callback_data=Act(action="card"))
        kb.button(text=t(lang, "btn_debts"), callback_data=Act(action="debts"))
        kb.button(text=t(lang, "btn_lang"), callback_data=Act(action="lang"))
        kb.button(text=t(lang, "btn_add_group"), url=f"https://t.me/{me.username}?startgroup=1")
        kb.adjust(2, 1, 1)
        return t(lang, "menu_private"), kb.as_markup()

    kb.button(text=t(lang, "btn_new"), callback_data=Act(action="new"))
    kb.button(text=t(lang, "btn_list"), callback_data=Act(action="list"))
    kb.button(text=t(lang, "btn_debts"), callback_data=Act(action="debts"))
    kb.button(text=t(lang, "btn_join"), callback_data=Act(action="join"))
    kb.button(text=t(lang, "btn_members"), callback_data=Act(action="members"))
    kb.button(text=t(lang, "btn_card"), callback_data=Act(action="card"))
    kb.button(text=t(lang, "btn_lang"), callback_data=Act(action="lang"))
    kb.adjust(1, 2, 2, 2)
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
        label = f"{c['title']} · {fmt_money(c['share'], c['currency'], lang)} · {c['paid_count']}/{c['total']}"
        kb.button(text=label[:60], callback_data=Act(action="show", cid=c["id"]))
    back_button(kb, lang)
    kb.adjust(1)
    return t(lang, "list_title" if items else "list_empty"), kb.as_markup()


# ---------- карточка сбора ----------

async def render(db: DB, cid: int) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    c = await db.get_collection(cid)
    lang = await chat_lang(db, c["chat_id"])
    shares = await db.get_shares(cid)
    cur = c["currency"]
    card = await db.get_card(c["creator_id"])
    card_line = card_text(lang, card) if card else t(lang, "no_card_line", name=esc(c["creator_name"]))

    if c["status"] == DRAFT:
        share = split_share(c["amount"], cur, len(shares)) if shares else 0
        text = "\n".join([
            t(lang, "draft", title=esc(c["title"]), amount=fmt_money(c["amount"], cur, lang),
              n=len(shares), share=fmt_money(share, cur, lang)),
            "",
            card_line,
        ])
        selected = {s["user_id"] for s in shares}
        people = {m["user_id"]: m["name"] for m in await db.get_members(c["chat_id"])}
        people.update({s["user_id"]: s["name"] for s in shares})

        kb = InlineKeyboardBuilder()
        for uid, name in sorted(people.items(), key=lambda p: p[1].lower()):
            mark = "✅" if uid in selected else "⬜"
            kb.button(text=f"{mark} {name}"[:40], callback_data=Act(action="tg", cid=cid, uid=uid))
        sizes = [2] * (len(people) // 2) + [1] * (len(people) % 2)
        kb.button(text=t(lang, "btn_join"), callback_data=Act(action="join", cid=cid))
        other = USD if cur == UZS else UZS
        kb.button(text=t(lang, "btn_currency", cur=t(lang, "cur_" + cur)), callback_data=Act(action="cur", cid=cid, val=other))
        sizes.append(2)
        if not card:
            kb.button(text=t(lang, "btn_add_card"), callback_data=Act(action="card"))
            sizes.append(1)
        kb.button(text=t(lang, "btn_create"), callback_data=Act(action="create", cid=cid))
        kb.button(text=t(lang, "btn_cancel"), callback_data=Act(action="cancel", cid=cid))
        sizes.append(2)
        kb.adjust(*sizes)
        return text, kb.as_markup()

    share = c["share"]
    paid = sum(1 for s in shares if s["paid"])
    lines = [
        f"💰 <b>{esc(c['title'])}</b>",
        t(lang, "paid_by", name=esc(c["creator_name"]), amount=fmt_money(c["amount"], cur, lang)),
        t(lang, "per_person", n=len(shares), share=fmt_money(share, cur, lang)),
        "",
        card_line,
        "",
    ]
    for s in shares:
        if s["user_id"] == c["creator_id"]:
            lines.append(f"💳 {esc(s['name'])} — {t(lang, 'payer_mark')}")
        else:
            lines.append(f"{'✅' if s['paid'] else '⏳'} {esc(s['name'])}")

    collected = min(paid * share, c["amount"])
    lines += ["", t(lang, "collected", paid=paid, n=len(shares),
                    sum=fmt_money(collected, cur, lang), total=fmt_money(c["amount"], cur, lang))]

    if c["status"] != OPEN:
        lines.append(t(lang, "closed"))
        return "\n".join(lines), None

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_pay"), callback_data=Act(action="pay", cid=cid))
    kb.button(text=t(lang, "btn_remind"), callback_data=Act(action="remind", cid=cid))
    kb.button(text=t(lang, "btn_close"), callback_data=Act(action="close", cid=cid))
    kb.adjust(1, 2)
    return "\n".join(lines), kb.as_markup()


async def refresh(db: DB, bot: Bot, cid: int) -> None:
    c = await db.get_collection(cid)
    if not c or not c["message_id"]:
        return
    text, markup = await render(db, cid)
    try:
        await bot.edit_message_text(text, chat_id=c["chat_id"], message_id=c["message_id"], reply_markup=markup)
    except TelegramBadRequest:
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


# ---------- команды-входы ----------

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_added(event: ChatMemberUpdated, bot: Bot):
    await bot.send_message(event.chat.id, CHOOSE_LANG, reply_markup=lang_kb())


@router.message(CommandStart())
@router.message(Command("menu", "help"))
async def cmd_menu(message: Message, db: DB, bot: Bot):
    lang = await db.get_lang(message.chat.id)
    if not lang:
        await message.answer(CHOOSE_LANG, reply_markup=lang_kb())
        return
    text, markup = await menu_view(bot, lang, message.chat.type)
    await message.answer(text, reply_markup=markup)


# ---------- меню и навигация ----------

@router.callback_query(Act.filter(F.action == "setlang"))
async def cb_setlang(call: CallbackQuery, callback_data: Act, db: DB, bot: Bot):
    lang = callback_data.val
    await db.set_lang(call.message.chat.id, lang)
    await call.answer()
    text, markup = await menu_view(bot, lang, call.message.chat.type)
    await safe_edit(call.message, text, markup)


@router.callback_query(Act.filter(F.action == "lang"))
async def cb_lang(call: CallbackQuery):
    await call.answer()
    await safe_edit(call.message, CHOOSE_LANG, lang_kb())


@router.callback_query(Act.filter(F.action == "menu"))
async def cb_menu(call: CallbackQuery, lang: str, bot: Bot):
    await call.answer()
    text, markup = await menu_view(bot, lang, call.message.chat.type)
    await safe_edit(call.message, text, markup)


@router.callback_query(Act.filter(F.action == "members"))
async def cb_members(call: CallbackQuery, db: DB, lang: str):
    await call.answer()
    text, markup = await members_view(db, lang, call.message.chat.id)
    await safe_edit(call.message, text, markup)


@router.callback_query(Act.filter(F.action == "list"))
async def cb_list(call: CallbackQuery, db: DB, lang: str):
    await call.answer()
    text, markup = await list_view(db, lang, call.message.chat.id)
    await safe_edit(call.message, text, markup)


@router.callback_query(Act.filter(F.action == "show"))
async def cb_show(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    """Переотправляет карточку сбора вниз чата."""
    c = await db.get_collection(callback_data.cid)
    if not c or c["status"] != OPEN:
        await call.answer(t(lang, "already_closed"))
        return
    await call.answer()
    text, markup = await render(db, c["id"])
    sent = await call.message.answer(text, reply_markup=markup)
    await safe_delete(bot, c["chat_id"], c["message_id"])
    await db.set_message_id(c["id"], sent.message_id)


# ---------- жильцы ----------

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


# ---------- долги ----------

@router.callback_query(Act.filter(F.action == "debts"))
async def cb_debts(call: CallbackQuery, db: DB, lang: str):
    user = call.from_user
    chat_id = None if is_private(call.message.chat.type) else call.message.chat.id
    debts = await db.user_debts(user.id, chat_id)
    await call.answer()
    who = mention(user.id, display_name(user))
    if not debts:
        await call.message.answer(t(lang, "debts_none", name=who))
        return

    lines = [t(lang, "debts_title", name=who)]
    totals = {}
    for c in debts:
        card = await db.get_card(c["creator_id"])
        card_txt = f" <code>{fmt_card(card['number'])}</code>" if card else ""
        lines.append(t(lang, "debt_item", title=esc(c["title"]), share=fmt_money(c["share"], c["currency"], lang),
                       creator=esc(c["creator_name"]), card=card_txt))
        totals[c["currency"]] = totals.get(c["currency"], 0) + c["share"]
    lines.append("\n" + t(lang, "total", sum=" + ".join(fmt_money(v, k, lang) for k, v in totals.items())))
    await call.message.answer("\n".join(lines))


# ---------- карта ----------

@router.callback_query(Act.filter(F.action == "card"))
async def cb_card(call: CallbackQuery, db: DB, lang: str, state: FSMContext):
    user = call.from_user
    await call.answer()
    text = t(lang, "ask_card", name=mention(user.id, display_name(user)))
    card = await db.get_card(user.id)
    if card:
        text += t(lang, "ask_card_current", card=card_text(lang, card))
    prompt = await call.message.answer(
        text, reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "ph_card"))
    )
    await state.set_state(Form.card)
    await state.update_data(prompt=prompt.message_id)


def answers_prompt(message: Message, data: dict) -> bool:
    """В группе принимаем только ответ на наш вопрос, в личке — любое сообщение."""
    if is_private(message.chat.type):
        return True
    reply = message.reply_to_message
    return bool(reply and reply.message_id == data.get("prompt"))


@router.message(Form.card, F.text)
async def on_card(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not answers_prompt(message, data):
        return
    user_id = message.from_user.id
    if message.text.strip() == "-":
        await db.delete_card(user_id)
        reply = t(lang, "card_deleted")
    else:
        parsed = parse_card(message.text)
        if not parsed:
            await message.reply(t(lang, "bad_card"))
            return
        number, holder = parsed
        await db.set_card(user_id, number, holder)
        reply = t(lang, "card_saved", card=card_text(lang, {"number": number, "holder": holder}))

    await state.clear()
    await safe_delete(bot, message.chat.id, data.get("prompt"))
    await message.reply(reply)
    for c in await db.creator_active(user_id):
        await refresh(db, bot, c["id"])


# ---------- новый сбор ----------

@router.callback_query(Act.filter(F.action == "new"))
async def cb_new(call: CallbackQuery, lang: str, state: FSMContext):
    if is_private(call.message.chat.type):
        await call.answer(t(lang, "groups_only"), show_alert=True)
        return
    user = call.from_user
    await call.answer()
    prompt = await call.message.answer(
        t(lang, "ask_amount", name=mention(user.id, display_name(user))),
        reply_markup=ForceReply(selective=True, input_field_placeholder=t(lang, "ph_amount")),
    )
    await state.set_state(Form.amount)
    await state.update_data(prompt=prompt.message_id)


@router.message(Form.amount, F.text)
async def on_amount(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not answers_prompt(message, data):
        return
    parsed = parse_amount(message.text)
    if not parsed:
        await message.reply(t(lang, "bad_amount"))
        return
    await state.clear()
    await safe_delete(bot, message.chat.id, data.get("prompt"))

    amount, currency, title = parsed
    user = message.from_user
    name = display_name(user)
    await db.add_member(message.chat.id, user.id, name)
    cid = await db.create_draft(message.chat.id, user.id, name, title, amount, currency)
    text, markup = await render(db, cid)
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
    if not any(s["user_id"] != c["creator_id"] for s in shares):
        await call.answer(t(lang, "need_people"), show_alert=True)
        return
    await db.open_draft(c["id"], split_share(c["amount"], c["currency"], len(shares)))
    await call.answer()
    await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "cancel"))
async def cb_cancel(call: CallbackQuery, callback_data: Act, db: DB, lang: str):
    c = await creator_only(call, db, callback_data.cid, lang, DRAFT)
    if not c:
        return
    await db.delete_collection(c["id"])
    await call.answer()
    await safe_edit(call.message, t(lang, "draft_cancelled", title=esc(c["title"])))


# ---------- открытый сбор ----------

@router.callback_query(Act.filter(F.action == "pay"))
async def cb_pay(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await db.get_collection(callback_data.cid)
    if not c or c["status"] != OPEN:
        await call.answer(t(lang, "already_closed"), show_alert=True)
        return
    if call.from_user.id == c["creator_id"]:
        await call.answer(t(lang, "creator_pay"), show_alert=True)
        return

    state = await db.toggle_paid(c["id"], call.from_user.id)
    if state is None:
        await call.answer(t(lang, "not_participant"), show_alert=True)
        return
    await call.answer(t(lang, "marked_paid" if state else "unmarked"))

    if all(s["paid"] for s in await db.get_shares(c["id"])):
        await db.close_collection(c["id"])
        await refresh(db, bot, c["id"])
        await call.message.reply(t(lang, "all_paid", title=esc(c["title"])))
    else:
        await refresh(db, bot, c["id"])


@router.callback_query(Act.filter(F.action == "remind"))
async def cb_remind(call: CallbackQuery, callback_data: Act, db: DB, lang: str):
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    debtors = [s for s in await db.get_shares(c["id"]) if not s["paid"]]
    await call.answer()
    await call.message.reply(t(
        lang, "remind", title=esc(c["title"]), share=fmt_money(c["share"], c["currency"], lang),
        people=", ".join(mention(s["user_id"], s["name"]) for s in debtors),
    ))


@router.callback_query(Act.filter(F.action == "close"))
async def cb_close(call: CallbackQuery, callback_data: Act, db: DB, lang: str, bot: Bot):
    c = await creator_only(call, db, callback_data.cid, lang, OPEN)
    if not c:
        return
    await db.close_collection(c["id"])
    await call.answer(t(lang, "closed_ok"))
    await refresh(db, bot, c["id"])
