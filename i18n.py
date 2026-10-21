"""Тексты бота на русском и узбекском."""
from __future__ import annotations

DEFAULT_LANG = "ru"

CHOOSE_LANG = "🌐 Выберите язык / Tilni tanlang"

TEXTS = {
    "ru": {
        # --- меню ---
        "menu_group": (
            "💰 <b>Общие сборы</b>\n\n"
            "1. Жильцы нажимают «🙋 Я в доле»\n"
            "2. Кто платит — жмёт «➕ Новый сбор», бот продолжит в личке\n"
            "3. Оплатили — жмите «✅ Я оплатил» и отправьте боту фото чека"
        ),
        "menu_private": (
            "💰 <b>Общие сборы</b>\n\n"
            "Сбор создаётся кнопкой «➕ Новый сбор» в группе, дальше всё — здесь, в личке. "
            "Здесь же ваша карта и долги."
        ),
        "btn_new": "➕ Новый сбор",
        "btn_list": "📋 Открытые сборы",
        "btn_debts": "🧾 Мои долги",
        "btn_join": "🙋 Я в доле",
        "btn_members": "👥 Жильцы",
        "btn_leave": "🚪 Выйти из списка",
        "btn_add_member": "➕ Добавить жильца",
        "btn_pick_users": "👥 Выбрать людей",
        "btn_card": "💳 Моя карта",
        "btn_lang": "🌐 Язык",
        "btn_back": "⬅️ Назад",
        "btn_add_group": "➕ Добавить в группу",
        "btn_pay": "✅ Я оплатил",
        "btn_remind": "🔔 Напомнить",
        "btn_close": "🔒 Закрыть",
        "btn_create": "✅ Создать",
        "btn_cancel": "✖️ Отмена",
        "btn_currency": "💱 Валюта: {cur}",
        "btn_reset_order": "🔄 Сбросить порядок",
        "btn_edit": "✏️ Изменить",
        "btn_mine": "✏️ Мои сборы",
        "btn_prepaid": "уже оплатил",
        "btn_kind_split": "💰 Поделить сумму",
        "btn_kind_queue": "🔁 По очереди",
        "btn_confirm": "✅ Подтвердить",
        "btn_reject": "❌ Отклонить",
        "cur_UZS": "сум",
        "cur_USD": "доллар",
        "card": "Карта",
        "lang_admin_only": "Язык меняет только администратор бота",
        "cancelled": "✖️ Отменено",
        # --- жильцы и список ---
        "joined": "🙋 Вы в списке жильцов",
        "already_joined": "Вы уже в списке",
        "left": "👋 Вы вышли из списка",
        "not_member": "Вас нет в списке",
        "members_title": "👥 <b>Жильцы ({n})</b>",
        "members_empty": "👥 Список пуст — нажмите «🙋 Я в доле»",
        "admin_only": "Это может сделать только администратор бота",
        "ask_members": (
            "Нажмите «👥 Выбрать людей» внизу и отметьте, кого добавить в жильцы «{group}». "
            "Можно выбрать сразу несколько."
        ),
        "members_added": "✅ Добавлены в жильцы «{group}»: {names}",
        "members_none_new": "Все выбранные уже в списке жильцов",
        "choose_group": "В какую группу добавить жильцов?",
        "no_groups": "Бот пока не знает ни одной группы. Добавьте его в группу и напишите там /menu.",
        "list_title": "📋 <b>Открытые сборы</b>\nНажмите, чтобы показать сбор внизу чата:",
        "list_empty": "📋 Открытых сборов нет",
        # --- карта ---
        "ask_card": "Отправьте номер карты Uzcard / Humo и имя:\n<code>8600 1234 5678 9012 Имя Фамилия</code>",
        "ask_card_current": "\n\nСейчас: {card}\nЧтобы удалить карту, отправьте «-».",
        "bad_card": "Нужно 16 цифр: <code>8600 1234 5678 9012 Имя Фамилия</code>",
        "card_saved": "✅ Карта сохранена: {card}",
        "card_deleted": "🗑 Карта удалена",
        "card_line": "💳 {type}: <code>{number}</code>{holder}",
        "no_card_line": "⚠️ {name}, добавьте карту — кнопка «💳 Моя карта»",
        # --- создание сбора ---
        "not_in_group": "Вы не состоите в этой группе",
        "choose_kind": (
            "Какой сбор создаём в «{group}»?\n\n"
            "💰 <b>Поделить сумму</b> — вы оплатили, сумма делится на всех.\n"
            "🔁 <b>По очереди</b> — каждый раз платит следующий по списку "
            "(например, свет по 100 000 сум)."
        ),
        "ask_amount_split": "Отправьте сумму и название:\n<code>300000 Коммуналка</code>\n<code>50$ Интернет</code>",
        "ask_amount_queue": "Сколько платят каждый раз и за что:\n<code>100000 Свет</code>",
        "bad_amount": "Не понял 🤔 Пример: <code>300000 Коммуналка</code> или <code>50$ Интернет</code>",
        "draft_split": (
            "📝 <b>Новый сбор</b> · {group}\n"
            "{title} — {amount}\n"
            "Участников: {n} · с каждого: <b>{share}</b>\n\n"
            "Отметьте, кто участвует, и нажмите «Создать».\n"
            "«✅ уже оплатил» — человек уже отдал свою долю (например, наличными): "
            "сумма делится и на него, но платить ему не нужно.\n"
            "Если кого-то нет в списке — пусть нажмёт «🙋 Я в доле» в группе."
        ),
        "draft_queue": (
            "📝 <b>Новая очередь</b> · {group}\n"
            "{title} — каждый раз {amount}\n\n"
            "Нажимайте на участников в порядке очереди: первый в списке платит первым.\n"
            "«✅ уже оплатил» — человек уже заплатил в этом круге (например, до бота): "
            "сейчас он пропускает очередь, со следующего круга платит как все.\n"
            "Если кого-то нет в списке — пусть нажмёт «🙋 Я в доле» в группе."
        ),
        "draft_published": "✅ «{title}» опубликован в группе «{group}»",
        "publish_failed": "Не получилось отправить в группу — бот всё ещё в ней?",
        "need_people": "Нужен хотя бы один участник кроме вас, который ещё не заплатил",
        "need_queue": "В очереди должно быть хотя бы 2 человека",
        "queue_admin_only": "Очередь может создать только администратор бота",
        "only_creator": "Это может сделать только автор сбора",
        "ask_title": "Сейчас: <b>{title}</b>\nОтправьте новое название сбора:",
        "title_saved": "✅ Название изменено: <b>{title}</b>",
        "mine_title": "Ваши открытые сборы — нажмите, чтобы изменить название:",
        "mine_empty": "У вас нет открытых сборов",
        # --- карточка: поделить сумму ---
        "paid_by": "Оплатил(а): <b>{name}</b> — {amount}",
        "per_person": "Участников: {n} · с каждого: <b>{share}</b>",
        "payer_mark": "платил(а)",
        "collected": "Собрано: {paid}/{n} · {sum} из {total}",
        "all_paid": "🎉 Все оплатили «{title}». Сбор закрыт.",
        "remind": "🔔 Напоминание по сбору «{title}» — по <b>{share}</b>:\n{people}",
        # --- карточка: очередь ---
        "queue_head": "🔁 <b>{title}</b> — по очереди\nКаждый раз: <b>{amount}</b> · круг {round}",
        "queue_now": "👉 Сейчас очередь: <b>{name}</b>",
        "turn_mark": "← сейчас",
        "debt_mark": "долг",
        "remind_queue": "🔔 {name}, сейчас ваша очередь платить «{title}» — <b>{amount}</b>",
        # --- общее по сбору ---
        "closed": "🔒 <b>Сбор закрыт</b>",
        "closed_ok": "Сбор закрыт",
        "already_closed": "Сбор уже закрыт",
        "not_participant": "Вы не участвуете в этом сборе",
        "creator_pay": "Вы оплатили за всех — ваша доля уже учтена 🙂",
        # --- оплата и чеки ---
        "pay_split": (
            "🧾 <b>{title}</b>\n"
            "Ваша доля: <b>{amount}</b> → {creator}\n"
            "{card}\n\n"
            "Переведите и отправьте сюда <b>фото чека</b>."
        ),
        "pay_queue": "🧾 <b>{title}</b> — {amount}\n\nОплатите и отправьте сюда <b>фото чека</b>.",
        "already_paid": "Вы уже оплатили этот сбор ✅",
        "already_pending": "Ваш чек уже на проверке 🕓",
        "send_photo": "Отправьте фото чека 📷",
        "receipt_sent": "📨 Чек отправлен {name}. Когда он(а) подтвердит — отметка появится в группе.",
        "receipt_caption": "🧾 <b>{name}</b> оплатил(а) «{title}» — {amount}",
        "payment_saved": "✅ Оплата записана",
        "confirmed": "✅ Подтверждено",
        "rejected": "❌ Отклонено",
        "payer_confirmed": "✅ {creator} подтвердил(а) оплату «{title}»",
        "payer_rejected": (
            "❌ {creator} отклонил(а) чек по «{title}».\n"
            "Отправьте чек ещё раз через кнопку «✅ Я оплатил» в группе."
        ),
        "already_handled": "Уже обработано",
        # --- долги ---
        "debts_none": "🎉 Долгов нет",
        "debts_title": "🧾 <b>Ваши долги</b>",
        "debt_item": "• {title}: <b>{share}</b> → {creator}{card}",
        "debt_queue": "• 🔁 {title}: ваша очередь — <b>{amount}</b>",
        "debt_queue_late": "• 🔁 {title}: долг за пропущенную очередь — <b>{amount}</b>",
        "total": "Итого: {sum}",
    },
    "uz": {
        # --- menyu ---
        "menu_group": (
            "💰 <b>Umumiy yig'imlar</b>\n\n"
            "1. Ijarachilar «🙋 Men ham» ni bosadi\n"
            "2. To'lovchi «➕ Yangi yig'im» ni bosadi — bot shaxsiy chatda davom etadi\n"
            "3. To'lagach «✅ To'ladim» ni bosing va botga chek rasmini yuboring"
        ),
        "menu_private": (
            "💰 <b>Umumiy yig'imlar</b>\n\n"
            "Yig'im guruhdagi «➕ Yangi yig'im» tugmasi orqali yaratiladi, qolgani shu yerda — shaxsiy chatda. "
            "Kartangiz va qarzlaringiz ham shu yerda."
        ),
        "btn_new": "➕ Yangi yig'im",
        "btn_list": "📋 Ochiq yig'imlar",
        "btn_debts": "🧾 Qarzlarim",
        "btn_join": "🙋 Men ham",
        "btn_members": "👥 Ijarachilar",
        "btn_leave": "🚪 Ro'yxatdan chiqish",
        "btn_add_member": "➕ Ijarachi qo'shish",
        "btn_pick_users": "👥 Odamlarni tanlash",
        "btn_card": "💳 Kartam",
        "btn_lang": "🌐 Til",
        "btn_back": "⬅️ Orqaga",
        "btn_add_group": "➕ Guruhga qo'shish",
        "btn_pay": "✅ To'ladim",
        "btn_remind": "🔔 Eslatish",
        "btn_close": "🔒 Yopish",
        "btn_create": "✅ Yaratish",
        "btn_cancel": "✖️ Bekor qilish",
        "btn_currency": "💱 Valyuta: {cur}",
        "btn_reset_order": "🔄 Tartibni tozalash",
        "btn_edit": "✏️ Tahrirlash",
        "btn_mine": "✏️ Mening yig'imlarim",
        "btn_prepaid": "to'lagan",
        "btn_kind_split": "💰 Summani bo'lish",
        "btn_kind_queue": "🔁 Navbat bilan",
        "btn_confirm": "✅ Tasdiqlash",
        "btn_reject": "❌ Rad etish",
        "cur_UZS": "so'm",
        "cur_USD": "dollar",
        "card": "Karta",
        "lang_admin_only": "Tilni faqat bot administratori o'zgartiradi",
        "cancelled": "✖️ Bekor qilindi",
        # --- ijarachilar va ro'yxat ---
        "joined": "🙋 Siz ro'yxatdasiz",
        "already_joined": "Siz allaqachon ro'yxatdasiz",
        "left": "👋 Siz ro'yxatdan chiqdingiz",
        "not_member": "Siz ro'yxatda yo'qsiz",
        "members_title": "👥 <b>Ijarachilar ({n})</b>",
        "members_empty": "👥 Ro'yxat bo'sh — «🙋 Men ham» ni bosing",
        "admin_only": "Buni faqat bot administratori qila oladi",
        "ask_members": (
            "Pastdagi «👥 Odamlarni tanlash» tugmasini bosing va «{group}» ijarachilariga kimni qo'shishni belgilang. "
            "Bir nechtasini birdan tanlash mumkin."
        ),
        "members_added": "✅ «{group}» ijarachilariga qo'shildi: {names}",
        "members_none_new": "Tanlanganlar allaqachon ijarachilar ro'yxatida",
        "choose_group": "Ijarachilarni qaysi guruhga qo'shamiz?",
        "no_groups": "Bot hali birorta guruhni bilmaydi. Uni guruhga qo'shing va u yerda /menu yozing.",
        "list_title": "📋 <b>Ochiq yig'imlar</b>\nChat pastida ko'rsatish uchun bosing:",
        "list_empty": "📋 Ochiq yig'imlar yo'q",
        # --- karta ---
        "ask_card": "Uzcard / Humo karta raqami va ismingizni yuboring:\n<code>8600 1234 5678 9012 Ism Familiya</code>",
        "ask_card_current": "\n\nHozirgi karta: {card}\nO'chirish uchun «-» yuboring.",
        "bad_card": "16 ta raqam kerak: <code>8600 1234 5678 9012 Ism Familiya</code>",
        "card_saved": "✅ Karta saqlandi: {card}",
        "card_deleted": "🗑 Karta o'chirildi",
        "card_line": "💳 {type}: <code>{number}</code>{holder}",
        "no_card_line": "⚠️ {name}, kartangizni qo'shing — «💳 Kartam» tugmasi",
        # --- yig'im yaratish ---
        "not_in_group": "Siz bu guruh a'zosi emassiz",
        "choose_kind": (
            "«{group}» uchun qanday yig'im yaratamiz?\n\n"
            "💰 <b>Summani bo'lish</b> — siz to'lagansiz, summa hammaga bo'linadi.\n"
            "🔁 <b>Navbat bilan</b> — har safar ro'yxatdagi navbatdagi odam to'laydi "
            "(masalan, svet uchun 100 000 so'm)."
        ),
        "ask_amount_split": "Summa va nomini yuboring:\n<code>300000 Kommunal</code>\n<code>50$ Internet</code>",
        "ask_amount_queue": "Har safar qancha va nima uchun to'lanadi:\n<code>100000 Svet</code>",
        "bad_amount": "Tushunmadim 🤔 Misol: <code>300000 Kommunal</code> yoki <code>50$ Internet</code>",
        "draft_split": (
            "📝 <b>Yangi yig'im</b> · {group}\n"
            "{title} — {amount}\n"
            "Ishtirokchilar: {n} · har biridan: <b>{share}</b>\n\n"
            "Kim qatnashishini belgilang va «Yaratish» ni bosing.\n"
            "«✅ to'lagan» — bu odam o'z ulushini allaqachon bergan (masalan, naqd): "
            "summa unga ham bo'linadi, lekin u to'lamaydi.\n"
            "Ro'yxatda yo'q odam guruhda «🙋 Men ham» ni bossin."
        ),
        "draft_queue": (
            "📝 <b>Yangi navbat</b> · {group}\n"
            "{title} — har safar {amount}\n\n"
            "Ishtirokchilarni navbat tartibida bosing: ro'yxatdagi birinchi odam birinchi to'laydi.\n"
            "«✅ to'lagan» — bu odam joriy aylanada allaqachon to'lagan (masalan, botgacha): "
            "hozir navbatni o'tkazib yuboradi, keyingi aylanadan hamma qatori to'laydi.\n"
            "Ro'yxatda yo'q odam guruhda «🙋 Men ham» ni bossin."
        ),
        "draft_published": "✅ «{title}» «{group}» guruhida e'lon qilindi",
        "publish_failed": "Guruhga yuborib bo'lmadi — bot hali guruhdami?",
        "need_people": "Sizdan tashqari hali to'lamagan kamida bitta ishtirokchi kerak",
        "need_queue": "Navbatda kamida 2 kishi bo'lishi kerak",
        "queue_admin_only": "Navbatni faqat bot administratori yaratadi",
        "only_creator": "Buni faqat yig'im muallifi qila oladi",
        "ask_title": "Hozir: <b>{title}</b>\nYig'imning yangi nomini yuboring:",
        "title_saved": "✅ Nomi o'zgartirildi: <b>{title}</b>",
        "mine_title": "Ochiq yig'imlaringiz — nomini o'zgartirish uchun bosing:",
        "mine_empty": "Sizda ochiq yig'imlar yo'q",
        # --- kartochka: summani bo'lish ---
        "paid_by": "To'lagan: <b>{name}</b> — {amount}",
        "per_person": "Ishtirokchilar: {n} · har biridan: <b>{share}</b>",
        "payer_mark": "to'lagan",
        "collected": "Yig'ildi: {paid}/{n} · {sum} / {total}",
        "all_paid": "🎉 «{title}» uchun hamma to'ladi. Yig'im yopildi.",
        "remind": "🔔 «{title}» yig'imi bo'yicha eslatma — har biridan <b>{share}</b>:\n{people}",
        # --- kartochka: navbat ---
        "queue_head": "🔁 <b>{title}</b> — navbat bilan\nHar safar: <b>{amount}</b> · {round}-aylana",
        "queue_now": "👉 Hozir navbat: <b>{name}</b>",
        "turn_mark": "← hozir",
        "debt_mark": "qarz",
        "remind_queue": "🔔 {name}, «{title}» uchun to'lash navbati sizda — <b>{amount}</b>",
        # --- umumiy ---
        "closed": "🔒 <b>Yig'im yopildi</b>",
        "closed_ok": "Yig'im yopildi",
        "already_closed": "Yig'im allaqachon yopilgan",
        "not_participant": "Siz bu yig'imda qatnashmaysiz",
        "creator_pay": "Siz hamma uchun to'lagansiz — ulushingiz hisobga olingan 🙂",
        # --- to'lov va cheklar ---
        "pay_split": (
            "🧾 <b>{title}</b>\n"
            "Ulushingiz: <b>{amount}</b> → {creator}\n"
            "{card}\n\n"
            "O'tkazing va shu yerga <b>chek rasmini</b> yuboring."
        ),
        "pay_queue": "🧾 <b>{title}</b> — {amount}\n\nTo'lang va shu yerga <b>chek rasmini</b> yuboring.",
        "already_paid": "Siz bu yig'imni to'lagansiz ✅",
        "already_pending": "Chekingiz tekshirilmoqda 🕓",
        "send_photo": "Chek rasmini yuboring 📷",
        "receipt_sent": "📨 Chek {name}ga yuborildi. U tasdiqlagach, guruhda belgi paydo bo'ladi.",
        "receipt_caption": "🧾 <b>{name}</b> «{title}» uchun to'ladi — {amount}",
        "payment_saved": "✅ To'lov yozib qo'yildi",
        "confirmed": "✅ Tasdiqlandi",
        "rejected": "❌ Rad etildi",
        "payer_confirmed": "✅ {creator} «{title}» to'lovini tasdiqladi",
        "payer_rejected": (
            "❌ {creator} «{title}» chekini rad etdi.\n"
            "Guruhdagi «✅ To'ladim» tugmasi orqali chekni qayta yuboring."
        ),
        "already_handled": "Allaqachon ko'rib chiqilgan",
        # --- qarzlar ---
        "debts_none": "🎉 Qarzlaringiz yo'q",
        "debts_title": "🧾 <b>Qarzlaringiz</b>",
        "debt_item": "• {title}: <b>{share}</b> → {creator}{card}",
        "debt_queue": "• 🔁 {title}: navbat sizda — <b>{amount}</b>",
        "debt_queue_late": "• 🔁 {title}: o'tkazib yuborilgan navbat uchun qarz — <b>{amount}</b>",
        "total": "Jami: {sum}",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS[DEFAULT_LANG])[key]
    return text.format(**kwargs) if kwargs else text
