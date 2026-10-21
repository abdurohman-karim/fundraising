"""Локальная SQLite база."""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Set, Tuple

import aiosqlite

DRAFT, OPEN, CLOSED = "draft", "open", "closed"
SPLIT, QUEUE = "split", "queue"
PENDING, CONFIRMED, REJECTED = "pending", "confirmed", "rejected"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS groups (
    chat_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS members (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    name    TEXT    NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS cards (
    user_id INTEGER PRIMARY KEY,
    number  TEXT NOT NULL,
    holder  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS collections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id      INTEGER NOT NULL,
    chat_title   TEXT    NOT NULL DEFAULT '',
    creator_id   INTEGER NOT NULL,
    creator_name TEXT    NOT NULL,
    kind         TEXT    NOT NULL DEFAULT 'split',
    title        TEXT    NOT NULL,
    amount       INTEGER NOT NULL,   -- split: вся сумма; queue: платёж за один раз
    currency     TEXT    NOT NULL,
    share        INTEGER NOT NULL DEFAULT 0,
    message_id   INTEGER,            -- черновик: в личке автора; потом: в группе
    status       TEXT    NOT NULL DEFAULT 'draft',
    pointer      INTEGER NOT NULL DEFAULT 0,  -- queue: чья очередь (индекс по pos)
    round        INTEGER NOT NULL DEFAULT 1,  -- queue: номер круга
    created_at   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS shares (
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL,
    name          TEXT    NOT NULL,
    paid          INTEGER NOT NULL DEFAULT 0,  -- split: доля оплачена
    pos           INTEGER NOT NULL DEFAULT 0,  -- queue: место в очереди
    owed          INTEGER NOT NULL DEFAULT 0,  -- queue: сколько раз должен заплатить в этом круге
    PRIMARY KEY (collection_id, user_id)
);

CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL,
    name          TEXT    NOT NULL,
    file_id       TEXT    NOT NULL,
    file_type     TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending',
    created_at    INTEGER NOT NULL
);
"""

# Колонки, которых не было в прошлых версиях базы.
MIGRATIONS = [
    ("collections", "status", "TEXT NOT NULL DEFAULT 'open'"),
    ("collections", "chat_title", "TEXT NOT NULL DEFAULT ''"),
    ("collections", "kind", "TEXT NOT NULL DEFAULT 'split'"),
    ("collections", "pointer", "INTEGER NOT NULL DEFAULT 0"),
    ("collections", "round", "INTEGER NOT NULL DEFAULT 1"),
    ("shares", "pos", "INTEGER NOT NULL DEFAULT 0"),
    ("shares", "owed", "INTEGER NOT NULL DEFAULT 0"),
]


def next_turn(order: List[int], owed: Dict[int, int], pointer: int, rnd: int) -> Tuple[int, int]:
    """Первый, кто ещё должен в этом круге, начиная с pointer.
    Если таких нет — новый круг: каждому ещё по одному разу, долги и переплаты сохраняются."""
    while True:
        while pointer < len(order) and owed[order[pointer]] <= 0:
            pointer += 1
        if pointer < len(order):
            return pointer, rnd
        rnd += 1
        pointer = 0
        for u in order:
            owed[u] += 1


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None
        self._lang: Optional[str] = None

    async def connect(self) -> None:
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.executescript(SCHEMA)
        await self._migrate()
        await self.conn.commit()

    async def _migrate(self) -> None:
        for table, column, ddl in MIGRATIONS:
            cur = await self.conn.execute(f"PRAGMA table_info({table})")
            if column not in {row["name"] for row in await cur.fetchall()}:
                await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                if column == "status":  # первая версия хранила is_open
                    await self.conn.execute("UPDATE collections SET status = 'closed' WHERE is_open = 0")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # --- язык (один на весь бот) ---

    async def get_lang(self) -> Optional[str]:
        if self._lang is None:
            cur = await self.conn.execute("SELECT value FROM settings WHERE key = 'lang'")
            row = await cur.fetchone()
            self._lang = row["value"] if row else ""
        return self._lang or None

    async def set_lang(self, lang: str) -> None:
        await self.conn.execute(
            "INSERT INTO settings (key, value) VALUES ('lang', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (lang,),
        )
        await self.conn.commit()
        self._lang = lang

    # --- группы, где есть бот ---

    async def remember_group(self, chat_id: int) -> None:
        await self.conn.execute("INSERT OR IGNORE INTO groups (chat_id) VALUES (?)", (chat_id,))
        await self.conn.commit()

    async def known_groups(self) -> List[int]:
        cur = await self.conn.execute(
            "SELECT chat_id FROM groups UNION SELECT chat_id FROM members ORDER BY chat_id"
        )
        return [row["chat_id"] for row in await cur.fetchall()]

    # --- жильцы чата ---

    async def add_member(self, chat_id: int, user_id: int, name: str) -> bool:
        """True, если человек добавлен впервые."""
        cur = await self.conn.execute(
            "SELECT 1 FROM members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
        )
        existed = await cur.fetchone() is not None
        await self.conn.execute(
            "INSERT INTO members (chat_id, user_id, name) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET name = excluded.name",
            (chat_id, user_id, name),
        )
        await self.conn.commit()
        return not existed

    async def remove_member(self, chat_id: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def get_members(self, chat_id: int) -> List[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT user_id, name FROM members WHERE chat_id = ? ORDER BY name", (chat_id,)
        )
        return list(await cur.fetchall())

    # --- карты ---

    async def set_card(self, user_id: int, number: str, holder: str) -> None:
        await self.conn.execute(
            "INSERT INTO cards (user_id, number, holder) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET number = excluded.number, holder = excluded.holder",
            (user_id, number, holder),
        )
        await self.conn.commit()

    async def delete_card(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM cards WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def get_card(self, user_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT number, holder FROM cards WHERE user_id = ?", (user_id,))
        return await cur.fetchone()

    # --- сборы ---

    async def create_draft(
        self, chat_id: int, chat_title: str, creator_id: int, creator_name: str,
        kind: str, title: str, amount: int, currency: str,
    ) -> int:
        """Черновик сбора; участники — все жильцы чата."""
        # share указываем явно: в базе первой версии у колонки нет значения по умолчанию.
        cur = await self.conn.execute(
            "INSERT INTO collections (chat_id, chat_title, creator_id, creator_name, kind, title, amount, currency, "
            "share, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (chat_id, chat_title, creator_id, creator_name, kind, title, amount, currency, DRAFT, int(time.time())),
        )
        cid = cur.lastrowid
        members = await self.get_members(chat_id)
        await self.conn.executemany(
            "INSERT INTO shares (collection_id, user_id, name, pos) VALUES (?, ?, ?, ?)",
            [(cid, m["user_id"], m["name"], i) for i, m in enumerate(members)],
        )
        await self.conn.commit()
        return cid

    async def set_message_id(self, cid: int, message_id: int) -> None:
        await self.conn.execute("UPDATE collections SET message_id = ? WHERE id = ?", (message_id, cid))
        await self.conn.commit()

    async def get_collection(self, cid: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM collections WHERE id = ?", (cid,))
        return await cur.fetchone()

    async def get_shares(self, cid: int) -> List[aiosqlite.Row]:
        """Для очереди — по порядку очереди, для сбора — оплатившие сверху."""
        cur = await self.conn.execute(
            "SELECT s.user_id, s.name, s.paid, s.pos, s.owed FROM shares s "
            "JOIN collections c ON c.id = s.collection_id WHERE s.collection_id = ? "
            "ORDER BY CASE c.kind WHEN 'queue' THEN s.pos ELSE -s.paid END, s.name",
            (cid,),
        )
        return list(await cur.fetchall())

    async def add_share(self, cid: int, user_id: int, name: str) -> None:
        """Добавляет участника в конец списка (для очереди — в конец очереди)."""
        await self.conn.execute(
            "INSERT OR IGNORE INTO shares (collection_id, user_id, name, pos) "
            "VALUES (?, ?, ?, (SELECT COALESCE(MAX(pos), -1) + 1 FROM shares WHERE collection_id = ?))",
            (cid, user_id, name, cid),
        )
        await self.conn.commit()

    async def remove_share(self, cid: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM shares WHERE collection_id = ? AND user_id = ?", (cid, user_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def clear_shares(self, cid: int) -> None:
        await self.conn.execute("DELETE FROM shares WHERE collection_id = ?", (cid,))
        await self.conn.commit()

    async def set_amount(self, cid: int, amount: int, currency: str) -> None:
        await self.conn.execute(
            "UPDATE collections SET amount = ?, currency = ? WHERE id = ?", (amount, currency, cid)
        )
        await self.conn.commit()

    async def open_draft(self, cid: int, share: int) -> None:
        c = await self.get_collection(cid)
        await self.conn.execute("UPDATE collections SET status = ?, share = ? WHERE id = ?", (OPEN, share, cid))
        if c["kind"] == QUEUE:
            # Нумеруем очередь подряд с нуля. В первом круге каждый должен один раз,
            # кроме отмеченных «уже оплатил» в черновике (paid = 1).
            rows = await self.get_shares(cid)
            order = [s["user_id"] for s in rows]
            owed = {s["user_id"]: 0 if s["paid"] else 1 for s in rows}
            pointer, rnd = next_turn(order, owed, 0, 1)
            await self.conn.executemany(
                "UPDATE shares SET pos = ?, owed = ?, paid = 0 WHERE collection_id = ? AND user_id = ?",
                [(i, owed[u], cid, u) for i, u in enumerate(order)],
            )
            await self.conn.execute(
                "UPDATE collections SET pointer = ?, round = ? WHERE id = ?", (pointer, rnd, cid)
            )
        else:
            await self.conn.execute(
                "UPDATE shares SET paid = 1 WHERE collection_id = ? AND user_id = ?", (cid, c["creator_id"])
            )
        await self.conn.commit()

    async def delete_collection(self, cid: int) -> None:
        await self.conn.execute("DELETE FROM collections WHERE id = ?", (cid,))
        await self.conn.commit()

    async def set_paid(self, cid: int, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE shares SET paid = 1 WHERE collection_id = ? AND user_id = ?", (cid, user_id)
        )
        await self.conn.commit()

    async def toggle_paid(self, cid: int, user_id: int) -> None:
        """В черновике: «уже оплатил» (сбор — уже отдал долю, очередь — уже платил в этом круге)."""
        await self.conn.execute(
            "UPDATE shares SET paid = 1 - paid WHERE collection_id = ? AND user_id = ?", (cid, user_id)
        )
        await self.conn.commit()

    async def queue_pay(self, cid: int, user_id: int) -> None:
        """Один платёж в очереди закрывает текущий ход.

        Платит тот, чья очередь — очередь идёт дальше (или остаётся у него, если он должен ещё).
        Платит другой — ход закрыт, а тот, чья была очередь, пропущен: его неоплаченный
        раз переносится в следующий круг, и там он должен заплатить два раза."""
        c = await self.get_collection(cid)
        rows = await self.get_shares(cid)
        order = [r["user_id"] for r in rows]
        owed = {r["user_id"]: r["owed"] for r in rows}
        pointer, rnd = c["pointer"], c["round"]
        current = order[pointer]

        owed[user_id] -= 1
        if user_id != current or owed[current] <= 0:
            pointer, rnd = next_turn(order, owed, pointer + 1, rnd)

        await self.conn.executemany(
            "UPDATE shares SET owed = ? WHERE collection_id = ? AND user_id = ?",
            [(v, cid, u) for u, v in owed.items()],
        )
        await self.conn.execute("UPDATE collections SET pointer = ?, round = ? WHERE id = ?", (pointer, rnd, cid))
        await self.conn.commit()

    async def set_status(self, cid: int, status: str) -> None:
        await self.conn.execute("UPDATE collections SET status = ? WHERE id = ?", (status, cid))
        await self.conn.commit()

    async def chat_collections(self, chat_id: int, status: str) -> List[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT c.*, "
            "(SELECT COUNT(*) FROM shares s WHERE s.collection_id = c.id) AS total, "
            "(SELECT COUNT(*) FROM shares s WHERE s.collection_id = c.id AND s.paid = 1) AS paid_count "
            "FROM collections c WHERE c.chat_id = ? AND c.status = ? ORDER BY c.id",
            (chat_id, status),
        )
        return list(await cur.fetchall())

    async def creator_active(self, user_id: int) -> List[aiosqlite.Row]:
        """Черновики и открытые сборы этого автора."""
        cur = await self.conn.execute(
            "SELECT id FROM collections WHERE creator_id = ? AND status IN (?, ?)", (user_id, DRAFT, OPEN)
        )
        return list(await cur.fetchall())

    async def user_open(self, user_id: int) -> List[aiosqlite.Row]:
        """Открытые сборы, где человек участвует, вместе с его строкой."""
        cur = await self.conn.execute(
            "SELECT c.*, s.paid, s.pos, s.owed FROM collections c JOIN shares s ON s.collection_id = c.id "
            "WHERE s.user_id = ? AND c.status = ? ORDER BY c.id",
            (user_id, OPEN),
        )
        return list(await cur.fetchall())

    # --- чеки ---

    async def add_payment(self, cid: int, user_id: int, name: str, file_id: str, file_type: str, status: str) -> int:
        cur = await self.conn.execute(
            "INSERT INTO payments (collection_id, user_id, name, file_id, file_type, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, user_id, name, file_id, file_type, status, int(time.time())),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_payment(self, pid: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM payments WHERE id = ?", (pid,))
        return await cur.fetchone()

    async def set_payment_status(self, pid: int, status: str) -> None:
        await self.conn.execute("UPDATE payments SET status = ? WHERE id = ?", (status, pid))
        await self.conn.commit()

    async def pending_users(self, cid: int) -> Set[int]:
        cur = await self.conn.execute(
            "SELECT user_id FROM payments WHERE collection_id = ? AND status = ?", (cid, PENDING)
        )
        return {row["user_id"] for row in await cur.fetchall()}
