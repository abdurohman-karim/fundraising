"""Парсинг сумм, карт и форматирование денег."""
from __future__ import annotations

import html
import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

UZS = "UZS"
USD = "USD"

# Суммы храним в минимальных единицах: сум — целые сумы, доллар — центы.
MINOR = {UZS: 1, USD: 100}
# Долю округляем вверх до этого шага (в минимальных единицах):
# сум — до 100 сум, доллар — до цента.
ROUND_STEP = {UZS: 100, USD: 1}

_CUR = r"(?P<cur>\$|usd|dollars?|долл\w*|дол|сум\w*|сўм|sum|som|so['ʻ’`]?m|uzs)"
AMOUNT_RE = re.compile(
    r"^\s*(?P<pre>\$)?\s*"
    r"(?P<num>\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*"
    r"(?P<mul>k|к|тыс\.?)?\s*"
    + _CUR + r"?"
    r"(?=\s|$)\s*(?P<title>.*)$",
    re.IGNORECASE | re.DOTALL,
)

CARD_RE = re.compile(r"^\s*(?P<num>(?:\d[\s-]?){15}\d)\s*(?P<holder>.*)$", re.DOTALL)


def parse_amount(text: str) -> Optional[Tuple[int, str, str]]:
    """'300 000 сум Коммуналка' -> (300000, 'UZS', 'Коммуналка').
    '50$ Интернет' -> (5000, 'USD', 'Интернет'). Без валюты — сум."""
    m = AMOUNT_RE.match(text or "")
    if not m:
        return None
    raw = m.group("num").replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if m.group("mul"):
        value *= 1000

    cur = (m.group("cur") or "").lower()
    currency = USD if m.group("pre") or cur in ("$", "usd", "dollar", "dollars", "дол") or cur.startswith("долл") else UZS

    minor = int((value * MINOR[currency]).to_integral_value())
    if minor <= 0:
        return None
    title = m.group("title").strip() or "Сбор"
    return minor, currency, title


def split_share(amount: int, currency: str, people: int) -> int:
    """Доля одного человека, округлённая вверх."""
    step = ROUND_STEP[currency]
    return -(-amount // (people * step)) * step


def fmt_money(minor: int, currency: str) -> str:
    if currency == USD:
        if minor % 100 == 0:
            s = f"{minor // 100:,}"
        else:
            s = f"{minor / 100:,.2f}"
        return "$" + s.replace(",", " ")
    return f"{minor:,}".replace(",", " ") + " сум"


def parse_card(text: str) -> Optional[Tuple[str, str]]:
    """'8600 1234 5678 9012 Ivan I' -> ('8600123456789012', 'Ivan I')."""
    m = CARD_RE.match(text or "")
    if not m:
        return None
    number = re.sub(r"\D", "", m.group("num"))
    return number, m.group("holder").strip()


def card_type(number: str) -> str:
    if number.startswith("9860"):
        return "Humo"
    if number.startswith(("8600", "5614")):
        return "Uzcard"
    return "Карта"


def fmt_card(number: str) -> str:
    return " ".join(number[i:i + 4] for i in range(0, len(number), 4))


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{esc(name)}</a>'
