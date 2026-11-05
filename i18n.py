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
        "btn_mine": "📂 Мои сборы",
        "btn_prepaid": "уже оплатил",
        "btn_kind_split": "💰 Поделить сумму",
        "btn_kind_queue": "🔁 По очереди",
        "btn_confirm": "✅ Подтвердить",
        "btn_cash": "💵 Отдал наличными",
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
        "mine_title": "📂 Ваши открытые сборы — выберите, чтобы напомнить, изменить или закрыть:",
        "reminded": "🔔 Напоминание отправлено в группу",
        "nobody_to_remind": "Напоминать некому — все оплатили или их чеки на проверке",
        "mine_empty": "У вас нет открытых сборов",
        # --- карточка: поделить сумму ---
        "paid_by": "Оплатил(а): <b>{name}</b> — {amount}",
        "per_person": "Участников: {n} · с каждого: <b>{share}</b>",
        "payer_mark": "платил(а)",
        "collected": "Собрано: {paid}/{n} · {sum} из {total}",
        "closed_all_paid": "🎉 <b>Все оплатили — сбор закрыт</b>",
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
        "pay_cash_hint": "\nОтдали наличными — нажмите «💵 Отдал наличными», чек не нужен.",
        "cash_saved": "✅ Отмечено: вы отдали долю наличными",
        "cash_notice": "💵 <b>{name}</b> отдал(а) наличными за «{title}» — {amount}",
        "btn_cover": "👥 Оплатить и за других",
        "btn_done": "✅ Готово",
        "cover_title": "Отметьте, за кого вы платите вместе со своей долей:",
        "no_one_to_cover": "Больше не за кого платить — остальные уже оплатили или их чеки на проверке",
        "pay_for": "\n👥 Также за: {names} — итого к оплате <b>{total}</b>",
        "receipt_for": " (и за {names})",
        "covered_by": "заплатил(а) {name}",
        "covered_notice": "💸 {payer} оплатил(а) вашу долю в «{title}». Рассчитайтесь с ним(ней) напрямую.",
        "btn_attach": "🔗 Кто за кого заплатил",
        "attach_who": "Чью долю оплатил другой участник?",
        "attach_payer": "Кто заплатил за {name}?",
        "attach_none": "Все уже оплатили или их чеки на проверке",
        "attached": "✅ Отмечено: за {name} заплатил(а) {payer}",
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
        # --- Gap ---
        "btn_gap": "🎯 Gap",
        "btn_gap_new": "➕ Новый Gap",
        "btn_gap_period": "📅 {period}",
        "btn_gap_collector": "🧑‍💼 Сборщик",
        "btn_gap_card": "💳 Карта",
        "btn_gap_add": "➕ Участники",
        "btn_gap_shuffle": "🔀 Перемешать",
        "btn_gap_start": "🚀 Запустить",
        "btn_gap_delete": "🗑 Удалить",
        "btn_gap_mark": "✍️ Отметить оплативших",
        "btn_gap_change_card": "💳 Изменить карту",
        "gap_card_changed": "✅ Карта изменена",
        "gap_card_current": "\n\nСейчас: {card}",
        "btn_gap_next": "➡️ Следующий тур",
        "btn_gap_close_yes": "🔒 Да, закрыть",
        "gap_week": "каждую неделю",
        "gap_month": "каждый месяц",
        "gap_list": "🎯 <b>Gap</b>\n\nВыберите Gap:",
        "gap_list_empty": "🎯 <b>Gap</b>\n\nВы пока не участвуете ни в одном Gap.",
        "gap_list_empty_admin": "🎯 <b>Gap</b>\n\nGap пока нет. Нажмите «➕ Новый Gap».",
        "gap_group_menu": "🎯 <b>Gap</b>\n\nКаждый тур все платят взнос одному участнику — по очереди списка.",
        "gap_ask_amount": (
            "🎯 Новый Gap в «{group}»\n\n"
            "Отправьте взнос одного участника и название:\n"
            "<code>500000 Gap друзей</code> или <code>100$ Gap</code>"
        ),
        "gap_draft": "📝 <b>Gap: {title}</b> (черновик)\nГруппа: {group}",
        "gap_card_title": "🎯 <b>Gap: {title}</b>",
        "gap_card_fee": "💵 Взнос: <b>{fee}</b> · {period}",
        "gap_card_round": "🔄 Тур {round}/{total} — получает {name}: <b>{sum}</b>",
        "gap_card_collector": "🧑‍💼 Сборщик: {name}",
        "gap_finished": "🏁 Gap завершён",
        "gap_receives": " ← получает",
        "gap_received": " · уже получил(а)",
        "gap_paid_count": "Оплатили: {paid}/{total}",
        "gap_order": "Очередь получения:",
        "gap_no_members": "— участников пока нет",
        "gap_pot": "Каждый тур получатель получает: <b>{sum}</b>",
        "gap_draft_hint": "Получают по порядку списка. Удалить участника — нажмите на него.",
        "gap_ask_card": "Отправьте карту, на которую участники будут платить:\n<code>8600 1234 5678 9012 Имя Фамилия</code>",
        "gap_ask_collector": "Выберите сборщика — он будет принимать деньги и подтверждать чеки 👇",
        "gap_ask_members": "Выберите участников 👇 Они встанут в конец очереди в том порядке, в каком вы их выберете.",
        "gap_need_collector": "Сначала выберите сборщика",
        "gap_need_card": "Сначала укажите карту",
        "gap_need_members": "Нужно минимум 2 участника",
        "gap_started": "🚀 Gap запущен",
        "gap_you_collect": "🧑‍💼 Вы — сборщик Gap «{title}» в «{group}». Чеки участников будут приходить сюда.",
        "gap_only_collector": "Это может только сборщик Gap",
        "gap_remind": "🔔 Gap «{title}»: ждём взнос {fee} от {people}",
        "gap_mark_title": "✍️ Тур {round}: нажмите на участника, чтобы отметить или снять оплату",
        "gap_not_all": "Ещё не оплатили: {n}. Отметьте их или дождитесь чеков.",
        "gap_done": "🏁 Это был последний тур — Gap завершён",
        "gap_next_started": "➡️ Начался тур {round}",
        "gap_close_confirm": "Закрыть Gap «{title}» досрочно?",
        "gap_not_member": "Вы не участник этого Gap",
        "gap_you_receive": "🎁 В этом туре получаете вы — платить не нужно",
        "gap_already_paid": "✅ Вы уже оплатили этот тур",
        "gap_pay": (
            "🎯 <b>Gap: {title}</b> — тур {round}, получает {name}\n\n"
            "Переведите <b>{fee}</b> на карту:\n{card}\n\n"
            "📷 Затем отправьте сюда фото чека — его проверит сборщик {collector}.\n"
            "Отдали наличными сборщику — нажмите «💵»."
        ),
        "gap_receipt_caption": "🧾 <b>{name}</b> оплатил(а) Gap «{title}», тур {round} — {amount}",
        "gap_all_paid": "🎉 Gap «{title}»: все оплатили. Передайте деньги {name} и нажмите «➡️ Следующий тур».",
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
        "btn_mine": "📂 Mening yig'imlarim",
        "btn_prepaid": "to'lagan",
        "btn_kind_split": "💰 Summani bo'lish",
        "btn_kind_queue": "🔁 Navbat bilan",
        "btn_confirm": "✅ Tasdiqlash",
        "btn_cash": "💵 Naqd berdim",
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
        "mine_title": "📂 Ochiq yig'imlaringiz — eslatish, tahrirlash yoki yopish uchun tanlang:",
        "reminded": "🔔 Eslatma guruhga yuborildi",
        "nobody_to_remind": "Eslatadigan odam yo'q — hamma to'lagan yoki cheklari tekshirilmoqda",
        "mine_empty": "Sizda ochiq yig'imlar yo'q",
        # --- kartochka: summani bo'lish ---
        "paid_by": "To'lagan: <b>{name}</b> — {amount}",
        "per_person": "Ishtirokchilar: {n} · har biridan: <b>{share}</b>",
        "payer_mark": "to'lagan",
        "collected": "Yig'ildi: {paid}/{n} · {sum} / {total}",
        "closed_all_paid": "🎉 <b>Hamma to'ladi — yig'im yopildi</b>",
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
        "pay_cash_hint": "\nNaqd bergan bo'lsangiz — «💵 Naqd berdim» ni bosing, chek kerak emas.",
        "cash_saved": "✅ Belgilandi: ulushingizni naqd berdingiz",
        "cash_notice": "💵 <b>{name}</b> «{title}» uchun naqd berdi — {amount}",
        "btn_cover": "👥 Boshqalar uchun ham to'lash",
        "btn_done": "✅ Tayyor",
        "cover_title": "O'z ulushingiz bilan birga yana kim uchun to'layotganingizni belgilang:",
        "no_one_to_cover": "To'lanadigan boshqa odam yo'q — qolganlar to'lagan yoki cheklari tekshirilmoqda",
        "pay_for": "\n👥 Yana: {names} uchun — jami <b>{total}</b>",
        "receipt_for": " ({names} uchun ham)",
        "covered_by": "{name} to'ladi",
        "covered_notice": "💸 {payer} «{title}» dagi ulushingizni to'ladi. U bilan o'zingiz hisob-kitob qiling.",
        "btn_attach": "🔗 Kim uchun kim to'ladi",
        "attach_who": "Kimning ulushini boshqa ishtirokchi to'ladi?",
        "attach_payer": "{name} uchun kim to'ladi?",
        "attach_none": "Hamma to'lagan yoki cheklari tekshirilmoqda",
        "attached": "✅ Belgilandi: {name} uchun {payer} to'ladi",
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
        # --- Gap ---
        "btn_gap": "🎯 Gap",
        "btn_gap_new": "➕ Yangi Gap",
        "btn_gap_period": "📅 {period}",
        "btn_gap_collector": "🧑‍💼 Yig'uvchi",
        "btn_gap_card": "💳 Karta",
        "btn_gap_add": "➕ Qatnashchilar",
        "btn_gap_shuffle": "🔀 Aralashtirish",
        "btn_gap_start": "🚀 Boshlash",
        "btn_gap_delete": "🗑 O'chirish",
        "btn_gap_mark": "✍️ To'laganlarni belgilash",
        "btn_gap_change_card": "💳 Kartani o'zgartirish",
        "gap_card_changed": "✅ Karta o'zgartirildi",
        "gap_card_current": "\n\nHozirgi karta: {card}",
        "btn_gap_next": "➡️ Keyingi tur",
        "btn_gap_close_yes": "🔒 Ha, yopish",
        "gap_week": "har hafta",
        "gap_month": "har oy",
        "gap_list": "🎯 <b>Gap</b>\n\nGapni tanlang:",
        "gap_list_empty": "🎯 <b>Gap</b>\n\nSiz hali hech qaysi Gapda qatnashmayapsiz.",
        "gap_list_empty_admin": "🎯 <b>Gap</b>\n\nHali Gap yo'q. «➕ Yangi Gap» ni bosing.",
        "gap_group_menu": "🎯 <b>Gap</b>\n\nHar turda hamma badalni bitta qatnashchiga to'laydi — ro'yxat navbati bo'yicha.",
        "gap_ask_amount": (
            "🎯 «{group}» uchun yangi Gap\n\n"
            "Bitta qatnashchining badali va nomini yuboring:\n"
            "<code>500000 Do'stlar gapi</code> yoki <code>100$ Gap</code>"
        ),
        "gap_draft": "📝 <b>Gap: {title}</b> (qoralama)\nGuruh: {group}",
        "gap_card_title": "🎯 <b>Gap: {title}</b>",
        "gap_card_fee": "💵 Badal: <b>{fee}</b> · {period}",
        "gap_card_round": "🔄 {round}/{total}-tur — oluvchi {name}: <b>{sum}</b>",
        "gap_card_collector": "🧑‍💼 Yig'uvchi: {name}",
        "gap_finished": "🏁 Gap yakunlandi",
        "gap_receives": " ← oladi",
        "gap_received": " · olgan",
        "gap_paid_count": "To'ladi: {paid}/{total}",
        "gap_order": "Olish navbati:",
        "gap_no_members": "— hali qatnashchi yo'q",
        "gap_pot": "Har turda oluvchi oladi: <b>{sum}</b>",
        "gap_draft_hint": "Ro'yxat tartibida oladi. Qatnashchini o'chirish uchun ustiga bosing.",
        "gap_ask_card": "Qatnashchilar to'laydigan kartani yuboring:\n<code>8600 1234 5678 9012 Ism Familiya</code>",
        "gap_ask_collector": "Yig'uvchini tanlang — u pulni qabul qiladi va cheklarni tasdiqlaydi 👇",
        "gap_ask_members": "Qatnashchilarni tanlang 👇 Ular tanlagan tartibingizda navbat oxiriga qo'shiladi.",
        "gap_need_collector": "Avval yig'uvchini tanlang",
        "gap_need_card": "Avval kartani kiriting",
        "gap_need_members": "Kamida 2 ta qatnashchi kerak",
        "gap_started": "🚀 Gap boshlandi",
        "gap_you_collect": "🧑‍💼 Siz «{group}» dagi «{title}» Gapining yig'uvchisisiz. Qatnashchilar cheklari shu yerga keladi.",
        "gap_only_collector": "Buni faqat Gap yig'uvchisi qila oladi",
        "gap_remind": "🔔 «{title}» Gapi: {people} dan {fee} badal kutilmoqda",
        "gap_mark_title": "✍️ {round}-tur: to'lovni belgilash yoki bekor qilish uchun qatnashchini bosing",
        "gap_not_all": "Hali to'lamaganlar: {n}. Ularni belgilang yoki cheklarni kuting.",
        "gap_done": "🏁 Bu oxirgi tur edi — Gap yakunlandi",
        "gap_next_started": "➡️ {round}-tur boshlandi",
        "gap_close_confirm": "«{title}» Gapini muddatidan oldin yopasizmi?",
        "gap_not_member": "Siz bu Gap qatnashchisi emassiz",
        "gap_you_receive": "🎁 Bu turda siz olasiz — to'lash shart emas",
        "gap_already_paid": "✅ Siz bu turni to'lagansiz",
        "gap_pay": (
            "🎯 <b>Gap: {title}</b> — {round}-tur, oluvchi {name}\n\n"
            "<b>{fee}</b> ni kartaga o'tkazing:\n{card}\n\n"
            "📷 So'ng chek rasmini shu yerga yuboring — uni yig'uvchi {collector} tekshiradi.\n"
            "Yig'uvchiga naqd bergan bo'lsangiz — «💵» ni bosing."
        ),
        "gap_receipt_caption": "🧾 <b>{name}</b> «{title}» Gapi uchun to'ladi, {round}-tur — {amount}",
        "gap_all_paid": "🎉 «{title}» Gapi: hamma to'ladi. Pulni {name} ga bering va «➡️ Keyingi tur» ni bosing.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS[DEFAULT_LANG])[key]
    return text.format(**kwargs) if kwargs else text
