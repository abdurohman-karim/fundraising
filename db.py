"""Локальная SQLite база."""
from __future__ import annotations

import os
import time
from typing import List, Optional

import aiosqlite

DRAFT, OPEN, CLOSED = "draft", "open", "closed"

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    lang    TEXT NOT NULL
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
    creator_id   INTEGER NOT NULL,
    creator_name TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    amount       INTEGER NOT NULL,
    currency     TEXT    NOT NULL,
    share        INTEGER NOT NULL DEFAULT 0,
    message_id   INTEGER,
    status       TEXT    NOT NULL DEFAULT 'draft',
    created_at   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS shares (
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL,
    name          TEXT    NOT NULL,
    paid          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (collection_id, user_id)
);
"""


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None

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
        # Первая версия хранила is_open вместо status.
        cur = await self.conn.execute("PRAGMA table_info(collections)")
        columns = {row["name"] for row in await cur.fetchall()}
        if "status" not in columns:
            await self.conn.execute("ALTER TABLE collections ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
            await self.conn.execute("UPDATE collections SET status = 'closed' WHERE is_open = 0")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # --- язык чата ---

    async def get_lang(self, chat_id: int) -> Optional[str]:
        cur = await self.conn.execute("SELECT lang FROM chats WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        return row["lang"] if row else None

    async def set_lang(self, chat_id: int, lang: str) -> None:
        await self.conn.execute(
            "INSERT INTO chats (chat_id, lang) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET lang = excluded.lang",
            (chat_id, lang),
        )
        await self.conn.commit()

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
        self, chat_id: int, creator_id: int, creator_name: str, title: str, amount: int, currency: str
    ) -> int:
        """Черновик сбора; участники — все жильцы чата."""
        cur = await self.conn.execute(
            "INSERT INTO collections (chat_id, creator_id, creator_name, title, amount, currency, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, creator_id, creator_name, title, amount, currency, DRAFT, int(time.time())),
        )
        cid = cur.lastrowid
        await self.conn.execute(
            "INSERT INTO shares (collection_id, user_id, name) SELECT ?, user_id, name FROM members WHERE chat_id = ?",
            (cid, chat_id),
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
        cur = await self.conn.execute(
            "SELECT user_id, name, paid FROM shares WHERE collection_id = ? ORDER BY paid DESC, name",
            (cid,),
        )
        return list(await cur.fetchall())

    async def add_share(self, cid: int, user_id: int, name: str) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO shares (collection_id, user_id, name) VALUES (?, ?, ?)", (cid, user_id, name)
        )
        await self.conn.commit()

    async def remove_share(self, cid: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM shares WHERE collection_id = ? AND user_id = ?", (cid, user_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def set_amount(self, cid: int, amount: int, currency: str) -> None:
        await self.conn.execute(
            "UPDATE collections SET amount = ?, currency = ? WHERE id = ?", (amount, currency, cid)
        )
        await self.conn.commit()

    async def open_draft(self, cid: int, share: int) -> None:
        await self.conn.execute(
            "UPDATE collections SET status = ?, share = ? WHERE id = ?", (OPEN, share, cid)
        )
        await self.conn.execute(
            "UPDATE shares SET paid = 1 WHERE collection_id = ? "
            "AND user_id = (SELECT creator_id FROM collections WHERE id = ?)",
            (cid, cid),
        )
        await self.conn.commit()

    async def delete_collection(self, cid: int) -> None:
        await self.conn.execute("DELETE FROM collections WHERE id = ?", (cid,))
        await self.conn.commit()

    async def toggle_paid(self, cid: int, user_id: int) -> Optional[bool]:
        """Переключает отметку об оплате. None — человек не участвует в сборе."""
        cur = await self.conn.execute(
            "UPDATE shares SET paid = 1 - paid WHERE collection_id = ? AND user_id = ?", (cid, user_id)
        )
        await self.conn.commit()
        if cur.rowcount == 0:
            return None
        cur = await self.conn.execute(
            "SELECT paid FROM shares WHERE collection_id = ? AND user_id = ?", (cid, user_id)
        )
        return bool((await cur.fetchone())["paid"])

    async def close_collection(self, cid: int) -> None:
        await self.conn.execute("UPDATE collections SET status = ? WHERE id = ?", (CLOSED, cid))
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
        """Черновики и открытые сборы, где человек — получатель денег."""
        cur = await self.conn.execute(
            "SELECT id FROM collections WHERE creator_id = ? AND status IN (?, ?)", (user_id, DRAFT, OPEN)
        )
        return list(await cur.fetchall())

    async def user_debts(self, user_id: int, chat_id: Optional[int] = None) -> List[aiosqlite.Row]:
        sql = (
            "SELECT c.* FROM collections c JOIN shares s ON s.collection_id = c.id "
            "WHERE s.user_id = ? AND s.paid = 0 AND c.status = ?"
        )
        params: tuple = (user_id, OPEN)
        if chat_id is not None:
            sql += " AND c.chat_id = ?"
            params += (chat_id,)
        cur = await self.conn.execute(sql + " ORDER BY c.id", params)
        return list(await cur.fetchall())
