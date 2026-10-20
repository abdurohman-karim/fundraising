"""Тексты бота на русском и узбекском."""
from __future__ import annotations

DEFAULT_LANG = "ru"

CHOOSE_LANG = "🌐 Выберите язык / Tilni tanlang"

TEXTS = {
    "ru": {
        "menu_group": (
            "💰 <b>Общие сборы</b>\n\n"
            "1. Жильцы нажимают «🙋 Я в доле»\n"
            "2. Кто оплатил — жмёт «➕ Новый сбор» и пишет сумму\n"
            "3. Остальные переводят свою долю на карту и жмут «✅ Я оплатил»"
        ),
        "menu_private": (
            "💰 <b>Общие сборы</b>\n\n"
            "Добавьте меня в группу с соседями. Здесь можно сохранить карту "
            "и посмотреть долги по всем группам."
        ),
        "btn_new": "➕ Новый сбор",
        "btn_list": "📋 Открытые сборы",
        "btn_debts": "🧾 Мои долги",
        "btn_join": "🙋 Я в доле",
        "btn_members": "👥 Жильцы",
        "btn_leave": "🚪 Выйти из списка",
        "btn_card": "💳 Моя карта",
        "btn_add_card": "💳 Добавить карту",
        "btn_lang": "🌐 Язык",
        "btn_back": "⬅️ Назад",
        "btn_add_group": "➕ Добавить в группу",
        "btn_pay": "✅ Я оплатил",
        "btn_remind": "🔔 Напомнить",
        "btn_close": "🔒 Закрыть",
        "btn_create": "✅ Создать",
        "btn_cancel": "✖️ Отмена",
        "btn_currency": "💱 Валюта: {cur}",
        "cur_UZS": "сум",
        "cur_USD": "доллар",
        "sum": "сум",
        "card": "Карта",
        "groups_only": "Сборы создаются в группе",
        "ask_amount": (
            "{name}, ответьте на это сообщение суммой и названием:\n"
            "<code>300000 Коммуналка</code>\n"
            "<code>50$ Интернет</code>"
        ),
        "ph_amount": "300000 Коммуналка",
        "bad_amount": (
            "Не понял 🤔 Пример: <code>300000 Коммуналка</code> или <code>50$ Интернет</code>.\n"
            "Ответьте ещё раз на сообщение выше."
        ),
        "ask_card": (
            "{name}, ответьте на это сообщение номером карты Uzcard / Humo и именем:\n"
            "<code>8600 1234 5678 9012 Имя Фамилия</code>"
        ),
        "ask_card_current": "\n\nСейчас: {card}\nЧтобы удалить карту, отправьте «-».",
        "ph_card": "8600 1234 5678 9012 Имя",
        "bad_card": "Нужно 16 цифр: <code>8600 1234 5678 9012 Имя Фамилия</code>. Ответьте ещё раз на сообщение выше.",
        "card_saved": "✅ Карта сохранена: {card}",
        "card_deleted": "🗑 Карта удалена",
        "draft": (
            "📝 <b>Новый сбор</b>\n"
            "{title} — {amount}\n"
            "Участников: {n} · с каждого: <b>{share}</b>\n\n"
            "Отметьте, кто участвует, и нажмите «Создать». "
            "Если кого-то нет в списке — пусть нажмёт «🙋 Я в доле»."
        ),
        "draft_cancelled": "✖️ Сбор «{title}» отменён",
        "need_people": "Отметьте хотя бы одного участника кроме себя",
        "only_creator": "Это может сделать только автор сбора",
        "card_line": "💳 {type}: <code>{number}</code>{holder}",
        "no_card_line": "⚠️ {name}, добавьте карту: «💳 Добавить карту» или меню → «💳 Моя карта»",
        "paid_by": "Оплатил(а): <b>{name}</b> — {amount}",
        "per_person": "Участников: {n} · с каждого: <b>{share}</b>",
        "payer_mark": "платил(а)",
        "collected": "Собрано: {paid}/{n} · {sum} из {total}",
        "closed": "🔒 <b>Сбор закрыт</b>",
        "already_closed": "Сбор уже закрыт",
        "not_participant": "Вы не участвуете в этом сборе",
        "creator_pay": "Вы оплатили за всех — ваша доля уже учтена 🙂",
        "marked_paid": "✅ Отмечено как оплачено",
        "unmarked": "Отметка снята",
        "all_paid": "🎉 Все оплатили «{title}». Сбор закрыт.",
        "remind": "🔔 Напоминание по сбору «{title}» — по <b>{share}</b>:\n{people}",
        "closed_ok": "Сбор закрыт",
        "joined": "🙋 Вы в списке жильцов",
        "already_joined": "Вы уже в списке",
        "left": "👋 Вы вышли из списка",
        "not_member": "Вас нет в списке",
        "members_title": "👥 <b>Жильцы ({n})</b>",
        "members_empty": "👥 Список пуст — нажмите «🙋 Я в доле»",
        "list_title": "📋 <b>Открытые сборы</b>\nНажмите, чтобы показать сбор внизу чата:",
        "list_empty": "📋 Открытых сборов нет",
        "debts_none": "🎉 {name}, долгов нет",
        "debts_title": "🧾 Долги {name}:",
        "debt_item": "• {title}: <b>{share}</b> → {creator}{card}",
        "total": "Итого: {sum}",
    },
    "uz": {
        "menu_group": (
            "💰 <b>Umumiy yig'imlar</b>\n\n"
            "1. Ijarachilar «🙋 Men ham» tugmasini bosadi\n"
            "2. To'lagan odam «➕ Yangi yig'im» ni bosib, summani yozadi\n"
            "3. Qolganlar o'z ulushini kartaga o'tkazib, «✅ To'ladim» ni bosadi"
        ),
        "menu_private": (
            "💰 <b>Umumiy yig'imlar</b>\n\n"
            "Meni qo'shnilar bilan guruhga qo'shing. Bu yerda kartangizni saqlashingiz "
            "va barcha guruhlardagi qarzlaringizni ko'rishingiz mumkin."
        ),
        "btn_new": "➕ Yangi yig'im",
        "btn_list": "📋 Ochiq yig'imlar",
        "btn_debts": "🧾 Qarzlarim",
        "btn_join": "🙋 Men ham",
        "btn_members": "👥 Ijarachilar",
        "btn_leave": "🚪 Ro'yxatdan chiqish",
        "btn_card": "💳 Kartam",
        "btn_add_card": "💳 Karta qo'shish",
        "btn_lang": "🌐 Til",
        "btn_back": "⬅️ Orqaga",
        "btn_add_group": "➕ Guruhga qo'shish",
        "btn_pay": "✅ To'ladim",
        "btn_remind": "🔔 Eslatish",
        "btn_close": "🔒 Yopish",
        "btn_create": "✅ Yaratish",
        "btn_cancel": "✖️ Bekor qilish",
        "btn_currency": "💱 Valyuta: {cur}",
        "cur_UZS": "so'm",
        "cur_USD": "dollar",
        "sum": "so'm",
        "card": "Karta",
        "groups_only": "Yig'imlar guruhda yaratiladi",
        "ask_amount": (
            "{name}, ushbu xabarga summa va nomini yozib javob bering:\n"
            "<code>300000 Kommunal</code>\n"
            "<code>50$ Internet</code>"
        ),
        "ph_amount": "300000 Kommunal",
        "bad_amount": (
            "Tushunmadim 🤔 Misol: <code>300000 Kommunal</code> yoki <code>50$ Internet</code>.\n"
            "Yuqoridagi xabarga qaytadan javob bering."
        ),
        "ask_card": (
            "{name}, ushbu xabarga Uzcard / Humo karta raqami va ismingizni yozib javob bering:\n"
            "<code>8600 1234 5678 9012 Ism Familiya</code>"
        ),
        "ask_card_current": "\n\nHozirgi karta: {card}\nO'chirish uchun «-» yuboring.",
        "ph_card": "8600 1234 5678 9012 Ism",
        "bad_card": "16 ta raqam kerak: <code>8600 1234 5678 9012 Ism Familiya</code>. Yuqoridagi xabarga qaytadan javob bering.",
        "card_saved": "✅ Karta saqlandi: {card}",
        "card_deleted": "🗑 Karta o'chirildi",
        "draft": (
            "📝 <b>Yangi yig'im</b>\n"
            "{title} — {amount}\n"
            "Ishtirokchilar: {n} · har biridan: <b>{share}</b>\n\n"
            "Kim qatnashishini belgilang va «Yaratish» ni bosing. "
            "Ro'yxatda yo'q odam «🙋 Men ham» ni bossin."
        ),
        "draft_cancelled": "✖️ «{title}» yig'imi bekor qilindi",
        "need_people": "O'zingizdan tashqari kamida bitta ishtirokchini belgilang",
        "only_creator": "Buni faqat yig'im muallifi qila oladi",
        "card_line": "💳 {type}: <code>{number}</code>{holder}",
        "no_card_line": "⚠️ {name}, kartangizni qo'shing: «💳 Karta qo'shish» yoki menyu → «💳 Kartam»",
        "paid_by": "To'lagan: <b>{name}</b> — {amount}",
        "per_person": "Ishtirokchilar: {n} · har biridan: <b>{share}</b>",
        "payer_mark": "to'lagan",
        "collected": "Yig'ildi: {paid}/{n} · {sum} / {total}",
        "closed": "🔒 <b>Yig'im yopildi</b>",
        "already_closed": "Yig'im allaqachon yopilgan",
        "not_participant": "Siz bu yig'imda qatnashmaysiz",
        "creator_pay": "Siz hamma uchun to'lagansiz — ulushingiz hisobga olingan 🙂",
        "marked_paid": "✅ To'landi deb belgilandi",
        "unmarked": "Belgi olib tashlandi",
        "all_paid": "🎉 «{title}» uchun hamma to'ladi. Yig'im yopildi.",
        "remind": "🔔 «{title}» yig'imi bo'yicha eslatma — har biridan <b>{share}</b>:\n{people}",
        "closed_ok": "Yig'im yopildi",
        "joined": "🙋 Siz ro'yxatdasiz",
        "already_joined": "Siz allaqachon ro'yxatdasiz",
        "left": "👋 Siz ro'yxatdan chiqdingiz",
        "not_member": "Siz ro'yxatda yo'qsiz",
        "members_title": "👥 <b>Ijarachilar ({n})</b>",
        "members_empty": "👥 Ro'yxat bo'sh — «🙋 Men ham» ni bosing",
        "list_title": "📋 <b>Ochiq yig'imlar</b>\nChat pastida ko'rsatish uchun bosing:",
        "list_empty": "📋 Ochiq yig'imlar yo'q",
        "debts_none": "🎉 {name}, qarzlaringiz yo'q",
        "debts_title": "🧾 {name} qarzlari:",
        "debt_item": "• {title}: <b>{share}</b> → {creator}{card}",
        "total": "Jami: {sum}",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS[DEFAULT_LANG])[key]
    return text.format(**kwargs) if kwargs else text
