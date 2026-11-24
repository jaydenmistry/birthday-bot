"""SQLite storage for birthdays, the announcement channel, and what was sent."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS birthdays (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    month    INTEGER NOT NULL,
    day      INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id   INTEGER PRIMARY KEY,
    channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS sent_log (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    year     INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id, year)
);
"""


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # settings

    def get_channel(self, guild_id: int) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT channel_id FROM settings WHERE guild_id = ?", (guild_id,)
            ).fetchone()
        return row["channel_id"] if row else None

    def set_channel(self, guild_id: int, channel_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (guild_id, channel_id) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
                """,
                (guild_id, channel_id),
            )

    # birthdays

    def set_birthday(self, guild_id: int, user_id: int, month: int, day: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO birthdays (guild_id, user_id, month, day) VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    month = excluded.month, day = excluded.day
                """,
                (guild_id, user_id, month, day),
            )

    def remove_birthday(self, guild_id: int, user_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
        return cur.rowcount > 0

    def get_birthday(self, guild_id: int, user_id: int) -> tuple[int, int] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT month, day FROM birthdays WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ).fetchone()
        return (row["month"], row["day"]) if row else None

    def birthdays_in_guild(self, guild_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT user_id, month, day FROM birthdays WHERE guild_id = ? ORDER BY month, day",
                (guild_id,),
            ).fetchall()

    def birthdays_on(self, month: int, day: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT guild_id, user_id FROM birthdays WHERE month = ? AND day = ?",
                (month, day),
            ).fetchall()

    # announcements

    def already_sent(self, guild_id: int, user_id: int, year: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM sent_log WHERE guild_id = ? AND user_id = ? AND year = ?",
                (guild_id, user_id, year),
            ).fetchone()
        return row is not None

    def mark_sent(self, guild_id: int, user_id: int, year: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sent_log (guild_id, user_id, year) VALUES (?, ?, ?)",
                (guild_id, user_id, year),
            )
