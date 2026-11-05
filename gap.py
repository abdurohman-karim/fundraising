"""Gap — ежемесячный или еженедельный сбор среди друзей. Не связан с жильцами и их сборами.

Каждый тур все участники платят взнос одному — по очереди списка: в 1-м туре получает первый,
во 2-м — второй и так далее. Деньги идут на одну карту, чеки принимает сборщик.
Gap создаёт админ бота в личке и сам назначает сборщика.
"""
from __future__ import annotations

import random
from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardMarkup, KeyboardButton, KeyboardButtonRequestUsers, Message,
    ReplyKeyboardMarkup, ReplyParameters, User,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import CLOSED, CONFIRMED, DB, DRAFT, MONTH, OPEN, PENDING, REJECTED, WEEK
from handlers import (
    SCREENS, Act, card_text, close_picker, display_name, reset_state, safe_delete, safe_edit, send_receipt,
    show, start_link, try_send,
)
from i18n import DEFAULT_LANG, t
from utils import USD, UZS, esc, fmt_money, mention, parse_amount, parse_card

router = Router()
PRIVATE = F.chat.type == "private"


class G(CallbackData, prefix="g"):
    action: str
    gid: int = 0
    uid: int = 0


class GapForm(StatesGroup):
    amount = State()   # «сумма название» нового Gap
    card = State()
    picker = State()   # выбор сборщика или участников
    receipt = State()


# ---------- помощники ----------

def gback(lang: str, action: str = "glist", gid: int = 0, cancel: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_cancel" if cancel else "btn_back"), callback_data=G(action=action, gid=gid))
    return kb.as_markup()


def is_manager(g, user_id: int, admin_id: Optional[int]) -> bool:
    return user_id == admin_id or user_id == g["collector_id"]


def recipient(g, members):
    idx = g["round"] - 1
    return members[idx] if 0 <= idx < len(members) else None


def gap_card(lang: str, g) -> str:
    if not g["card_number"]:
        return "💳 —"
    return card_text(lang, {"number": g["card_number"], "holder": g["card_holder"]})


async def gap_visible(db: DB, user_id: int, is_admin: bool) -> bool:
    """Показывать ли кнопку «🎯 Gap» в личном меню."""
    return is_admin or bool(await db.user_gaps(user_id, False))


async def render_card(db: DB, bot: Bot, g, lang: str) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """Карточка Gap: тур, кто получает, кто уже заплатил."""
    members = await db.gap_members(g["id"])
    status = await db.gap_round_status(g["id"], g["round"])
    rec = recipient(g, members) if g["status"] == OPEN else None
    fee = fmt_money(g["amount"], g["currency"], lang)
    lines = [
        t(lang, "gap_card_title", title=esc(g["title"])),
        t(lang, "gap_card_fee", fee=fee, period=t(lang, "gap_" + g["period"])),
    ]
    if rec:
        lines.append(t(lang, "gap_card_round", round=g["round"], total=len(members), name=esc(rec["name"]),
                       sum=fmt_money(g["amount"] * (len(members) - 1), g["currency"], lang)))
    else:
        lines.append(t(lang, "gap_finished"))
    lines.append(t(lang, "gap_card_collector", name=esc(g["collector_name"])))
    lines.append(gap_card(lang, g))
    lines.append("")

    paid = 0
    for i, m in enumerate(members):
        if not rec:
            mark = "✔️"
        elif m["user_id"] == rec["user_id"]:
            mark = "🎁"
        else:
            st = status.get(m["user_id"])
            paid += st == CONFIRMED
            mark = {CONFIRMED: "✅", PENDING: "🕓"}.get(st, "⏳")
        note = ""
        if rec and m["user_id"] == rec["user_id"]:
            note = t(lang, "gap_receives")
        elif rec and i < g["round"] - 1:
            note = t(lang, "gap_received")
        lines.append(f"{i + 1}. {mark} {esc(m['name'])}{note}")
    if rec:
        lines.append("")
        lines.append(t(lang, "gap_paid_count", paid=paid, total=len(members) - 1))

    if not rec:
        return "\n".join(lines), None
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_pay"), url=await start_link(bot, f"gpay_{g['id']}"))
    return "\n".join(lines), kb.as_markup()


async def refresh_gap(db: DB, bot: Bot, gid: int) -> None:
    g = await db.get_gap(gid)
    if not g or not g["message_id"] or g["status"] == DRAFT:
        return
    text, markup = await render_card(db, bot, g, await db.get_lang() or DEFAULT_LANG)
    try:
        await bot.edit_message_text(text, chat_id=g["chat_id"], message_id=g["message_id"], reply_markup=markup,
                                    disable_web_page_preview=True)
    except TelegramAPIError:
        pass  # не изменилось или удалено


async def post_card(db: DB, bot: Bot, g, lang: str) -> bool:
    """Присылает карточку в группу заново (внизу чата), прошлую убирает."""
    text, markup = await render_card(db, bot, g, lang)
    sent = await try_send(bot, g["chat_id"], text, reply_markup=markup, disable_web_page_preview=True)
    if not sent:
        return False
    await safe_delete(bot, g["chat_id"], g["message_id"])
    await db.update_gap(g["id"], message_id=sent.message_id)
    return True


async def refresh_open_gaps(db: DB, bot: Bot) -> None:
    for gid in await db.open_gap_ids():
        await refresh_gap(db, bot, gid)


async def sync_gap_user(db: DB, bot: Bot, user: User) -> None:
    stored = await db.gap_stored_name(user.id)
    name = display_name(user)
    if stored is None or stored == name:
        return
    for gid in await db.rename_gap_user(user.id, name):
        await refresh_gap(db, bot, gid)


async def group_menu(db: DB, lang: str, chat_id: int) -> Optional[Tuple[str, InlineKeyboardMarkup]]:
    """Меню группы, где идёт Gap: вместо меню жильцов — кнопки Gap."""
    gaps = await db.chat_gaps(chat_id)
    if not gaps:
        return None
    kb = InlineKeyboardBuilder()
    for g in gaps:
        kb.button(text=f"🎯 {g['title']}"[:60], callback_data=G(action="gshow", gid=g["id"]))
    kb.adjust(1)
    return t(lang, "gap_group_menu"), kb.as_markup()


# ---------- экраны в личке ----------

async def list_view(db: DB, lang: str, user_id: int, is_admin: bool) -> Tuple[str, InlineKeyboardMarkup]:
    gaps = await db.user_gaps(user_id, is_admin)
    kb = InlineKeyboardBuilder()
    for g in gaps:
        mark = "📝" if g["status"] == DRAFT else "🎯"
        kb.button(text=f"{mark} {g['title']} · {g['chat_title']}"[:60], callback_data=G(action="gopen", gid=g["id"]))
    if is_admin:
        kb.button(text=t(lang, "btn_gap_new"), callback_data=G(action="gnew"))
    kb.button(text=t(lang, "btn_back"), callback_data=Act(action="menu"))
    kb.adjust(1)
    empty = "gap_list_empty_admin" if is_admin else "gap_list_empty"
    return t(lang, "gap_list" if gaps else empty), kb.as_markup()


async def draft_view(db: DB, lang: str, g) -> Tuple[str, InlineKeyboardMarkup]:
    members = await db.gap_members(g["id"])
    gid = g["id"]
    lines = [
        t(lang, "gap_draft", title=esc(g["title"]), group=esc(g["chat_title"])),
        t(lang, "gap_card_fee", fee=fmt_money(g["amount"], g["currency"], lang), period=t(lang, "gap_" + g["period"])),
        t(lang, "gap_card_collector", name=esc(g["collector_name"]) or "—"),
        gap_card(lang, g),
        "",
        t(lang, "gap_order"),
    ]
    lines += [f"{i + 1}. {esc(m['name'])}" for i, m in enumerate(members)] or [t(lang, "gap_no_members")]
    if len(members) > 1:
        lines += ["", t(lang, "gap_pot", sum=fmt_money(g["amount"] * (len(members) - 1), g["currency"], lang))]
    lines += ["", t(lang, "gap_draft_hint")]

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_gap_period", period=t(lang, "gap_" + g["period"])), callback_data=G(action="gper", gid=gid))
    kb.button(text=t(lang, "btn_currency", cur="$" if g["currency"] == USD else "so'm" if lang == "uz" else "сум"),
              callback_data=G(action="gcur", gid=gid))
    kb.button(text=t(lang, "btn_gap_collector"), callback_data=G(action="gcol", gid=gid))
    kb.button(text=t(lang, "btn_gap_card"), callback_data=G(action="gcard", gid=gid))
    kb.button(text=t(lang, "btn_gap_add"), callback_data=G(action="gadd", gid=gid))
    sizes = [2, 2, 1]
    if len(members) > 1:
        kb.button(text=t(lang, "btn_gap_shuffle"), callback_data=G(action="gmix", gid=gid))
        sizes[-1] = 2
    for i, m in enumerate(members):
        kb.button(text=f"✖️ {i + 1}. {m['name']}"[:60], callback_data=G(action="grm", gid=gid, uid=m["user_id"]))
    sizes += [1] * len(members)
    kb.button(text=t(lang, "btn_gap_start"), callback_data=G(action="gstart", gid=gid))
    kb.button(text=t(lang, "btn_gap_delete"), callback_data=G(action="gdel", gid=gid))
    kb.button(text=t(lang, "btn_back"), callback_data=G(action="glist"))
    sizes += [2, 1]
    kb.adjust(*sizes)
    return "\n".join(lines), kb.as_markup()


async def open_view(db: DB, bot: Bot, lang: str, g, user_id: int,
                    admin_id: Optional[int]) -> Tuple[str, InlineKeyboardMarkup]:
    """Идущий Gap: сборщику и админу — управление, участнику — карточка и оплата."""
    text, _ = await render_card(db, bot, g, lang)
    kb = InlineKeyboardBuilder()
    gid = g["id"]
    if g["status"] == OPEN:
        members = await db.gap_members(gid)
        rec = recipient(g, members)
        if any(m["user_id"] == user_id for m in members) and rec and rec["user_id"] != user_id:
            kb.button(text=t(lang, "btn_pay"), callback_data=G(action="gpay", gid=gid))
        if is_manager(g, user_id, admin_id):
            kb.button(text=t(lang, "btn_remind"), callback_data=G(action="grem", gid=gid))
            kb.button(text=t(lang, "btn_gap_mark"), callback_data=G(action="gmark", gid=gid))
            kb.button(text=t(lang, "btn_gap_change_card"), callback_data=G(action="gcard", gid=gid))
            kb.button(text=t(lang, "btn_gap_next"), callback_data=G(action="gnext", gid=gid))
        if user_id == admin_id:
            kb.button(text=t(lang, "btn_gap_change_collector"), callback_data=G(action="gcol", gid=gid))
            kb.button(text=t(lang, "btn_close"), callback_data=G(action="gclose", gid=gid))
    kb.button(text=t(lang, "btn_back"), callback_data=G(action="glist"))
    kb.adjust(1)
    return text, kb.as_markup()


async def screen(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    await safe_edit(call.message, text, markup)
    SCREENS[call.message.chat.id] = call.message.message_id


async def admin_draft(call: CallbackQuery, db: DB, lang: str, gid: int, admin_id: Optional[int]):
    """Черновик Gap, если кнопку нажал админ; иначе — ответ-подсказка."""
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "admin_only"), show_alert=True)
        return None
    g = await db.get_gap(gid)
    if not g or g["status"] != DRAFT:
        await call.answer(t(lang, "already_closed"))
        return None
    return g


async def manager_open(call: CallbackQuery, db: DB, lang: str, gid: int, admin_id: Optional[int]):
    g = await db.get_gap(gid)
    if not g or g["status"] != OPEN:
        await call.answer(t(lang, "already_closed"))
        return None
    if not is_manager(g, call.from_user.id, admin_id):
        await call.answer(t(lang, "gap_only_collector"), show_alert=True)
        return None
    return g


# ---------- входы ----------

@router.message(CommandStart(deep_link=True, magic=F.args.regexp(r"^(gpay_\d+|gaps)$")), PRIVATE)
async def cmd_start_gap(message: Message, command: CommandObject, db: DB, lang: str,
                        state: FSMContext, bot: Bot, admin_id: Optional[int]):
    chat_id, user = message.chat.id, message.from_user
    await reset_state(bot, chat_id, state)
    await safe_delete(bot, chat_id, message.message_id)
    if command.args == "gaps":
        await show(bot, db, chat_id, *await list_view(db, lang, user.id, user.id == admin_id), new=True)
    else:
        await start_pay(chat_id, user.id, db, lang, state, bot, int(command.args[5:]), new=True)


@router.callback_query(G.filter(F.action == "gshow"))
async def cb_show(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot):
    """Кнопка в меню группы: карточка Gap заново внизу чата."""
    g = await db.get_gap(callback_data.gid)
    if not g or g["status"] != OPEN:
        await call.answer(t(lang, "already_closed"))
        return
    await call.answer()
    await post_card(db, bot, g, lang)


@router.callback_query(G.filter(F.action == "glist"))
async def cb_list(call: CallbackQuery, db: DB, lang: str, state: FSMContext, bot: Bot, admin_id: Optional[int]):
    await call.answer()
    await reset_state(bot, call.message.chat.id, state)
    await screen(call, *await list_view(db, lang, call.from_user.id, call.from_user.id == admin_id))


@router.callback_query(G.filter(F.action == "gopen"))
async def cb_open(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext, bot: Bot,
                  admin_id: Optional[int]):
    await reset_state(bot, call.message.chat.id, state)
    g = await db.get_gap(callback_data.gid)
    if not g or g["status"] == CLOSED:
        await call.answer(t(lang, "already_closed"))
        return
    if g["status"] == DRAFT:
        if call.from_user.id != admin_id:
            await call.answer(t(lang, "admin_only"), show_alert=True)
            return
        await call.answer()
        await screen(call, *await draft_view(db, lang, g))
        return
    await call.answer()
    await screen(call, *await open_view(db, bot, lang, g, call.from_user.id, admin_id))


# ---------- новый Gap (админ, в личке) ----------

@router.callback_query(G.filter(F.action == "gnew"))
async def cb_new(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext, bot: Bot,
                 admin_id: Optional[int]):
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "admin_only"), show_alert=True)
        return
    await call.answer()
    chat_id = call.message.chat.id
    SCREENS[chat_id] = call.message.message_id
    group_id = callback_data.uid
    if not group_id:
        groups = []
        for gid in await db.known_groups():
            try:
                groups.append(await bot.get_chat(gid))
            except TelegramAPIError:
                pass  # бота удалили из группы
        if not groups:
            await show(bot, db, chat_id, t(lang, "no_groups"), gback(lang))
            return
        if len(groups) > 1:
            kb = InlineKeyboardBuilder()
            for grp in groups:
                kb.button(text=(grp.title or str(grp.id))[:60], callback_data=G(action="gnew", uid=grp.id))
            kb.button(text=t(lang, "btn_back"), callback_data=G(action="glist"))
            kb.adjust(1)
            await show(bot, db, chat_id, t(lang, "choose_group"), kb.as_markup())
            return
        group_id = groups[0].id
    try:
        group = await bot.get_chat(group_id)
    except TelegramAPIError:
        await show(bot, db, chat_id, t(lang, "not_in_group"), gback(lang))
        return
    await show(bot, db, chat_id, t(lang, "gap_ask_amount", group=esc(group.title or "")), gback(lang, cancel=True))
    await state.set_state(GapForm.amount)
    await state.update_data(group_id=group_id, group_title=group.title or "")


@router.message(GapForm.amount, PRIVATE, F.text)
async def on_amount(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    await safe_delete(bot, chat_id, message.message_id)
    parsed = parse_amount(message.text)
    data = await state.get_data()
    if not parsed:
        await show(bot, db, chat_id, t(lang, "gap_ask_amount", group=esc(data["group_title"]))
                   + f"\n\n⚠️ {t(lang, 'bad_amount')}", gback(lang, cancel=True))
        return
    amount, currency, title = parsed
    if title == "Сбор":
        title = "Gap"
    await state.clear()
    gid = await db.create_gap(data["group_id"], data["group_title"], title, amount, currency)
    await show(bot, db, chat_id, *await draft_view(db, lang, await db.get_gap(gid)))


@router.callback_query(G.filter(F.action == "gdraft"))
async def cb_draft(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext, bot: Bot,
                   admin_id: Optional[int]):
    await reset_state(bot, call.message.chat.id, state)
    g = await admin_draft(call, db, lang, callback_data.gid, admin_id)
    if g:
        await call.answer()
        await screen(call, *await draft_view(db, lang, g))


@router.callback_query(G.filter(F.action.in_({"gper", "gcur", "gmix", "grm"})))
async def cb_draft_edit(call: CallbackQuery, callback_data: G, db: DB, lang: str, admin_id: Optional[int]):
    g = await admin_draft(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    action = callback_data.action
    if action == "gper":
        await db.update_gap(g["id"], period=WEEK if g["period"] == MONTH else MONTH)
    elif action == "gcur":
        # Число остаётся тем же, меняется только валюта: 500 000 сум <-> $500 000.
        new = USD if g["currency"] == UZS else UZS
        amount = g["amount"] * 100 if new == USD else max(g["amount"] // 100, 1)
        await db.update_gap(g["id"], amount=amount, currency=new)
    elif action == "gmix":
        order = [m["user_id"] for m in await db.gap_members(g["id"])]
        random.shuffle(order)
        await db.set_gap_order(g["id"], order)
    else:
        await db.remove_gap_member(g["id"], callback_data.uid)
    await call.answer()
    await screen(call, *await draft_view(db, lang, await db.get_gap(g["id"])))


@router.callback_query(G.filter(F.action == "gcard"))
async def cb_card(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext,
                  admin_id: Optional[int]):
    """Карту задаёт админ в черновике, а в идущем Gap её может сменить и сборщик."""
    g = await db.get_gap(callback_data.gid)
    if g and g["status"] == OPEN:
        g = await manager_open(call, db, lang, g["id"], admin_id)
    else:
        g = await admin_draft(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    await call.answer()
    text = t(lang, "gap_ask_card")
    if g["card_number"]:
        text += t(lang, "gap_card_current", card=gap_card(lang, g))
    await screen(call, text, gback(lang, "gopen", g["id"], cancel=True))
    await state.set_state(GapForm.card)
    await state.update_data(gid=g["id"])


@router.message(GapForm.card, PRIVATE, F.text)
async def on_card(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot, admin_id: Optional[int]):
    chat_id = message.chat.id
    await safe_delete(bot, chat_id, message.message_id)
    gid = (await state.get_data())["gid"]
    parsed = parse_card(message.text)
    if not parsed:
        await show(bot, db, chat_id, f"{t(lang, 'gap_ask_card')}\n\n⚠️ {t(lang, 'bad_card')}",
                   gback(lang, "gopen", gid, cancel=True))
        return
    await state.clear()
    g = await db.get_gap(gid)
    if not g or g["status"] == CLOSED:
        await show(bot, db, chat_id, t(lang, "already_closed"), gback(lang))
        return
    await db.update_gap(gid, card_number=parsed[0], card_holder=parsed[1])
    g = await db.get_gap(gid)
    if g["status"] == DRAFT:
        await show(bot, db, chat_id, *await draft_view(db, lang, g))
        return
    # Gap уже идёт: новая карта сразу на карточке в группе.
    await refresh_gap(db, bot, gid)
    text, markup = await open_view(db, bot, lang, g, message.from_user.id, admin_id)
    await show(bot, db, chat_id, f"{t(lang, 'gap_card_changed')}\n\n{text}", markup)


@router.callback_query(G.filter(F.action.in_({"gcol", "gadd"})))
async def cb_pick(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext, bot: Bot,
                  admin_id: Optional[int]):
    """Участников выбирают в черновике; сборщика админ может сменить и в идущем Gap."""
    single = callback_data.action == "gcol"
    g = await db.get_gap(callback_data.gid)
    if single and g and g["status"] == OPEN:
        if call.from_user.id != admin_id:
            await call.answer(t(lang, "admin_only"), show_alert=True)
            return
    else:
        g = await admin_draft(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    await call.answer()
    chat_id = call.message.chat.id
    await screen(call, t(lang, "gap_ask_collector" if single else "gap_ask_members"),
                 gback(lang, "gopen", g["id"], cancel=True))
    # Выбор людей работает только через обычную клавиатуру, поэтому для неё нужно отдельное сообщение.
    picker = KeyboardButton(
        text=t(lang, "btn_pick_users"),
        request_users=KeyboardButtonRequestUsers(
            request_id=2 if single else 3, user_is_bot=False, max_quantity=1 if single else 10,
            request_name=True, request_username=True,
        ),
    )
    markup = ReplyKeyboardMarkup(keyboard=[[picker]], resize_keyboard=True, one_time_keyboard=True)
    sent = await bot.send_message(chat_id, "👇", reply_markup=markup)
    await state.set_state(GapForm.picker)
    await state.update_data(gid=g["id"], single=single, picker=sent.message_id)


@router.message(GapForm.picker, PRIVATE, F.users_shared)
async def on_users_shared(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot,
                          admin_id: Optional[int]):
    chat_id = message.chat.id
    data = await state.get_data()
    await state.clear()
    await safe_delete(bot, chat_id, message.message_id)
    await close_picker(bot, chat_id, data)
    gid = data["gid"]
    g = await db.get_gap(gid)
    if g and g["status"] == OPEN and data["single"]:
        u = message.users_shared.users[0]
        name = f"@{u.username}" if u.username else (" ".join(filter(None, [u.first_name, u.last_name])) or str(u.user_id))
        await change_collector(db, bot, lang, g, u.user_id, name)
        text, markup = await open_view(db, bot, lang, await db.get_gap(gid), message.from_user.id, admin_id)
        await show(bot, db, chat_id, f"{t(lang, 'gap_collector_changed')}\n\n{text}", markup)
        return
    for u in message.users_shared.users:
        name = f"@{u.username}" if u.username else (" ".join(filter(None, [u.first_name, u.last_name])) or str(u.user_id))
        if data["single"]:
            await db.update_gap(gid, collector_id=u.user_id, collector_name=name)
            g = await db.get_gap(gid)
            card = await db.get_card(u.user_id)
            if card and not g["card_number"]:
                await db.update_gap(gid, card_number=card["number"], card_holder=card["holder"])
        else:
            await db.add_gap_member(gid, u.user_id, name)
    g = await db.get_gap(gid)
    if g and g["status"] == DRAFT:
        await show(bot, db, chat_id, *await draft_view(db, lang, g))


async def change_collector(db: DB, bot: Bot, lang: str, g, user_id: int, name: str) -> None:
    """Новый сборщик идущего Gap: чеки на проверке переходят к нему, прежнему — уведомление."""
    old = g["collector_id"]
    if user_id == old:
        return
    await db.update_gap(g["id"], collector_id=user_id, collector_name=name)
    await refresh_gap(db, bot, g["id"])
    title, group = esc(g["title"]), esc(g["chat_title"])
    await try_send(bot, user_id, t(lang, "gap_you_collect", title=title, group=group))
    if old:
        await try_send(bot, old, t(lang, "gap_not_collector", title=title, name=esc(name)))
    for p in await db.gap_pending(g["id"]):
        caption = t(lang, "gap_receipt_caption", name=esc(p["name"]), title=title, round=p["round"],
                    amount=fmt_money(g["amount"], g["currency"], lang))
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "btn_confirm"), callback_data=G(action="gok", gid=g["id"], uid=p["id"]))
        kb.button(text=t(lang, "btn_reject"), callback_data=G(action="gno", gid=g["id"], uid=p["id"]))
        try:
            await send_receipt(bot, user_id, p["file_type"], p["file_id"], caption, kb.as_markup())
        except TelegramAPIError:
            break  # новый сборщик ещё не открывал личку с ботом


@router.message(GapForm.picker, PRIVATE)
async def on_picker_other(message: Message, bot: Bot):
    """Пока открыт выбор людей, лишние сообщения не копим."""
    await safe_delete(bot, message.chat.id, message.message_id)


@router.callback_query(G.filter(F.action == "gstart"))
async def cb_start(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    g = await admin_draft(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    if not g["collector_id"]:
        error = "gap_need_collector"
    elif not g["card_number"]:
        error = "gap_need_card"
    elif len(await db.gap_members(g["id"])) < 2:
        error = "gap_need_members"
    else:
        error = None
    if error:
        await call.answer(t(lang, error), show_alert=True)
        return
    await db.update_gap(g["id"], status=OPEN, round=1)
    g = await db.get_gap(g["id"])
    if not await post_card(db, bot, g, lang):
        await db.update_gap(g["id"], status=DRAFT)
        await call.answer(t(lang, "publish_failed"), show_alert=True)
        return
    await call.answer(t(lang, "gap_started"))
    await screen(call, *await open_view(db, bot, lang, await db.get_gap(g["id"]), call.from_user.id, admin_id))
    if g["collector_id"] != call.from_user.id:
        await try_send(bot, g["collector_id"], t(lang, "gap_you_collect", title=esc(g["title"]),
                                                 group=esc(g["chat_title"])))


@router.callback_query(G.filter(F.action == "gdel"))
async def cb_delete(call: CallbackQuery, callback_data: G, db: DB, lang: str, admin_id: Optional[int]):
    g = await admin_draft(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    await db.delete_gap(g["id"])
    await call.answer(t(lang, "cancelled"))
    await screen(call, *await list_view(db, lang, call.from_user.id, True))


# ---------- сборщик: напомнить, отметить, следующий тур ----------

async def debtors(db: DB, g):
    members = await db.gap_members(g["id"])
    rec = recipient(g, members)
    status = await db.gap_round_status(g["id"], g["round"])
    return [m for m in members if m["user_id"] != rec["user_id"] and status.get(m["user_id"]) != CONFIRMED], status


@router.callback_query(G.filter(F.action == "grem"))
async def cb_remind(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    g = await manager_open(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    unpaid, status = await debtors(db, g)
    unpaid = [m for m in unpaid if status.get(m["user_id"]) != PENDING]
    if not unpaid:
        await call.answer(t(lang, "nobody_to_remind"), show_alert=True)
        return
    text = t(lang, "gap_remind", title=esc(g["title"]), fee=fmt_money(g["amount"], g["currency"], lang),
             people=", ".join(mention(m["user_id"], m["name"]) for m in unpaid))
    reply = ReplyParameters(message_id=g["message_id"], allow_sending_without_reply=True) if g["message_id"] else None
    sent = await try_send(bot, g["chat_id"], text, reply_parameters=reply)
    await call.answer(t(lang, "reminded" if sent else "publish_failed"), show_alert=not sent)


async def mark_view(db: DB, lang: str, g) -> Tuple[str, InlineKeyboardMarkup]:
    members = await db.gap_members(g["id"])
    rec = recipient(g, members)
    status = await db.gap_round_status(g["id"], g["round"])
    kb = InlineKeyboardBuilder()
    for m in members:
        if m["user_id"] == rec["user_id"]:
            continue
        mark = {CONFIRMED: "✅", PENDING: "🕓"}.get(status.get(m["user_id"]), "⏳")
        kb.button(text=f"{mark} {m['name']}"[:60], callback_data=G(action="gtg", gid=g["id"], uid=m["user_id"]))
    kb.button(text=t(lang, "btn_back"), callback_data=G(action="gopen", gid=g["id"]))
    kb.adjust(1)
    return t(lang, "gap_mark_title", round=g["round"]), kb.as_markup()


@router.callback_query(G.filter(F.action == "gmark"))
async def cb_mark(call: CallbackQuery, callback_data: G, db: DB, lang: str, admin_id: Optional[int]):
    g = await manager_open(call, db, lang, callback_data.gid, admin_id)
    if g:
        await call.answer()
        await screen(call, *await mark_view(db, lang, g))


@router.callback_query(G.filter(F.action == "gtg"))
async def cb_toggle(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    """Сборщик сам отмечает, кто отдал взнос (например, наличными), или снимает отметку."""
    g = await manager_open(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    member = next((m for m in await db.gap_members(g["id"]) if m["user_id"] == callback_data.uid), None)
    if not member:
        await call.answer()
        return
    status = await db.gap_round_status(g["id"], g["round"])
    if status.get(member["user_id"]) == CONFIRMED:
        await db.unmark_gap_paid(g["id"], g["round"], member["user_id"])
    else:
        await db.add_gap_payment(g["id"], g["round"], member["user_id"], member["name"], "", "manual", CONFIRMED)
    await call.answer()
    await refresh_gap(db, bot, g["id"])
    await screen(call, *await mark_view(db, lang, g))


@router.callback_query(G.filter(F.action == "gnext"))
async def cb_next(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    """Деньги отданы получателю — следующий тур. После последнего Gap завершается."""
    g = await manager_open(call, db, lang, callback_data.gid, admin_id)
    if not g:
        return
    unpaid, _ = await debtors(db, g)
    if unpaid:
        await call.answer(t(lang, "gap_not_all", n=len(unpaid)), show_alert=True)
        return
    members = await db.gap_members(g["id"])
    if g["round"] >= len(members):
        await db.update_gap(g["id"], status=CLOSED)
        await refresh_gap(db, bot, g["id"])
        await call.answer(t(lang, "gap_done"), show_alert=True)
    else:
        await db.update_gap(g["id"], round=g["round"] + 1)
        await post_card(db, bot, await db.get_gap(g["id"]), lang)
        await call.answer(t(lang, "gap_next_started", round=g["round"] + 1))
    await screen(call, *await open_view(db, bot, lang, await db.get_gap(g["id"]), call.from_user.id, admin_id))


@router.callback_query(G.filter(F.action.in_({"gclose", "gclose2"})))
async def cb_close(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    g = await db.get_gap(callback_data.gid)
    if call.from_user.id != admin_id:
        await call.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not g or g["status"] != OPEN:
        await call.answer(t(lang, "already_closed"))
        return
    await call.answer()
    if callback_data.action == "gclose":
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "btn_gap_close_yes"), callback_data=G(action="gclose2", gid=g["id"]))
        kb.button(text=t(lang, "btn_back"), callback_data=G(action="gopen", gid=g["id"]))
        kb.adjust(1)
        await screen(call, t(lang, "gap_close_confirm", title=esc(g["title"])), kb.as_markup())
        return
    await db.update_gap(g["id"], status=CLOSED)
    await refresh_gap(db, bot, g["id"])
    await screen(call, *await list_view(db, lang, call.from_user.id, True))


# ---------- оплата взноса (в личке) ----------

async def pay_error(db: DB, g, user_id: int) -> Optional[str]:
    if not g or g["status"] != OPEN:
        return "already_closed"
    members = await db.gap_members(g["id"])
    if not any(m["user_id"] == user_id for m in members):
        return "gap_not_member"
    if recipient(g, members)["user_id"] == user_id:
        return "gap_you_receive"
    st = (await db.gap_round_status(g["id"], g["round"])).get(user_id)
    if st == CONFIRMED:
        return "gap_already_paid"
    if st == PENDING:
        return "already_pending"
    return None


async def start_pay(chat_id: int, user_id: int, db: DB, lang: str, state: FSMContext, bot: Bot, gid: int,
                    new: bool = False) -> None:
    g = await db.get_gap(gid)
    error = await pay_error(db, g, user_id)
    if error:
        await show(bot, db, chat_id, t(lang, error), gback(lang), new=new)
        return
    rec = recipient(g, await db.gap_members(gid))
    text = t(lang, "gap_pay", title=esc(g["title"]), round=g["round"], name=esc(rec["name"]),
             fee=fmt_money(g["amount"], g["currency"], lang), card=gap_card(lang, g),
             collector=esc(g["collector_name"]))
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_cash"), callback_data=G(action="gcash", gid=gid))
    kb.button(text=t(lang, "btn_cancel"), callback_data=G(action="glist"))
    kb.adjust(1)
    await show(bot, db, chat_id, text, kb.as_markup(), new=new)
    await state.set_state(GapForm.receipt)
    await state.update_data(gid=gid, prompt=text)


@router.callback_query(G.filter(F.action == "gpay"))
async def cb_pay(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext, bot: Bot):
    await call.answer()
    SCREENS[call.message.chat.id] = call.message.message_id
    await start_pay(call.message.chat.id, call.from_user.id, db, lang, state, bot, callback_data.gid)


async def after_confirm(db: DB, bot: Bot, lang: str, gid: int) -> None:
    """Если все заплатили — напоминаем сборщику передать деньги и начать следующий тур."""
    await refresh_gap(db, bot, gid)
    g = await db.get_gap(gid)
    unpaid, _ = await debtors(db, g)
    if not unpaid:
        rec = recipient(g, await db.gap_members(gid))
        await try_send(bot, g["collector_id"], t(lang, "gap_all_paid", title=esc(g["title"]), name=esc(rec["name"])))


@router.callback_query(G.filter(F.action == "gcash"))
async def cb_cash(call: CallbackQuery, callback_data: G, db: DB, lang: str, state: FSMContext, bot: Bot):
    """Отдал взнос сборщику наличными: без чека, сборщику — уведомление."""
    g = await db.get_gap(callback_data.gid)
    user = call.from_user
    error = await pay_error(db, g, user.id)
    if error:
        await call.answer(t(lang, error), show_alert=True)
        return
    await state.clear()
    name = display_name(user)
    await db.add_gap_payment(g["id"], g["round"], user.id, name, "", "cash", CONFIRMED)
    await call.answer()
    await safe_edit(call.message, t(lang, "cash_saved"), gback(lang))
    if user.id != g["collector_id"]:
        await try_send(bot, g["collector_id"], t(lang, "cash_notice", name=esc(name), title=esc(g["title"]),
                                                 amount=fmt_money(g["amount"], g["currency"], lang)))
    await after_confirm(db, bot, lang, g["id"])


@router.message(GapForm.receipt, PRIVATE)
async def on_receipt(message: Message, db: DB, lang: str, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    data = await state.get_data()
    if message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"
    else:
        await safe_delete(bot, chat_id, message.message_id)
        await show(bot, db, chat_id, f"{data['prompt']}\n\n⚠️ {t(lang, 'send_photo')}", gback(lang, cancel=True))
        return

    await state.clear()
    g = await db.get_gap(data["gid"])
    user = message.from_user
    error = await pay_error(db, g, user.id)
    if error:
        await show(bot, db, chat_id, t(lang, error), gback(lang))
        return

    name = display_name(user)
    if user.id == g["collector_id"]:
        # Сборщик сам заплатил свой взнос — подтверждать некому.
        await db.add_gap_payment(g["id"], g["round"], user.id, name, file_id, file_type, CONFIRMED)
        await show(bot, db, chat_id, t(lang, "payment_saved"), gback(lang))
        await after_confirm(db, bot, lang, g["id"])
        return

    pid = await db.add_gap_payment(g["id"], g["round"], user.id, name, file_id, file_type, PENDING)
    caption = t(lang, "gap_receipt_caption", name=esc(name), title=esc(g["title"]), round=g["round"],
                amount=fmt_money(g["amount"], g["currency"], lang))
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_confirm"), callback_data=G(action="gok", gid=g["id"], uid=pid))
    kb.button(text=t(lang, "btn_reject"), callback_data=G(action="gno", gid=g["id"], uid=pid))
    try:
        await send_receipt(bot, g["collector_id"], file_type, file_id, caption, kb.as_markup())
    except TelegramAPIError:
        # Сборщик не открывал личку с ботом — чек в группе, подтвердить может только он.
        await send_receipt(bot, g["chat_id"], file_type, file_id, caption, kb.as_markup())

    await show(bot, db, chat_id, t(lang, "receipt_sent", name=esc(g["collector_name"])), gback(lang))
    await refresh_gap(db, bot, g["id"])


@router.callback_query(G.filter(F.action.in_({"gok", "gno"})))
async def cb_receipt(call: CallbackQuery, callback_data: G, db: DB, lang: str, bot: Bot, admin_id: Optional[int]):
    g = await db.get_gap(callback_data.gid)
    p = await db.get_gap_payment(callback_data.uid)
    if not g or not p or p["status"] != PENDING:
        await call.answer(t(lang, "already_handled"))
        return
    if not is_manager(g, call.from_user.id, admin_id):
        await call.answer(t(lang, "gap_only_collector"), show_alert=True)
        return

    title = esc(g["title"])
    collector = esc(g["collector_name"])
    if callback_data.action == "gok":
        await db.set_gap_payment_status(p["id"], CONFIRMED)
        await try_send(bot, p["user_id"], t(lang, "payer_confirmed", creator=collector, title=title))
        await after_confirm(db, bot, lang, g["id"])
        result = t(lang, "confirmed")
    else:
        await db.set_gap_payment_status(p["id"], REJECTED)
        await refresh_gap(db, bot, g["id"])
        await try_send(bot, p["user_id"], t(lang, "payer_rejected", creator=collector, title=title))
        result = t(lang, "rejected")

    await call.answer(result)
    try:
        await call.message.edit_caption(caption=f"{call.message.html_text}\n\n{result}", reply_markup=None)
    except TelegramAPIError:
        pass
