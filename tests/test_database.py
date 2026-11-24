import sqlite3
import tempfile
import unittest
from pathlib import Path

from birthday_bot.database import Database

GUILD, OTHER_GUILD, USER, OTHER_USER = 1, 2, 10, 20


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "birthdays.db")
        self.db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_set_get_and_update_birthday(self):
        self.assertIsNone(self.db.get_birthday(GUILD, USER))
        self.db.set_birthday(GUILD, USER, 4, 12)
        self.assertEqual(self.db.get_birthday(GUILD, USER), (4, 12))
        self.db.set_birthday(GUILD, USER, 5, 1)
        self.assertEqual(self.db.get_birthday(GUILD, USER), (5, 1))

    def test_birthdays_are_per_server(self):
        self.db.set_birthday(GUILD, USER, 4, 12)
        self.assertIsNone(self.db.get_birthday(OTHER_GUILD, USER))

    def test_remove_birthday(self):
        self.assertFalse(self.db.remove_birthday(GUILD, USER))
        self.db.set_birthday(GUILD, USER, 4, 12)
        self.assertTrue(self.db.remove_birthday(GUILD, USER))
        self.assertIsNone(self.db.get_birthday(GUILD, USER))

    def test_lists_are_sorted_by_date(self):
        self.db.set_birthday(GUILD, USER, 12, 1)
        self.db.set_birthday(GUILD, OTHER_USER, 1, 5)
        rows = self.db.birthdays_in_guild(GUILD)
        self.assertEqual([(r["month"], r["day"]) for r in rows], [(1, 5), (12, 1)])

    def test_birthdays_on_a_day(self):
        self.db.set_birthday(GUILD, USER, 4, 12)
        self.db.set_birthday(OTHER_GUILD, OTHER_USER, 4, 12)
        self.db.set_birthday(GUILD, OTHER_USER, 4, 13)
        rows = self.db.birthdays_on(4, 12)
        self.assertEqual(sorted((r["guild_id"], r["user_id"]) for r in rows), [(GUILD, USER), (OTHER_GUILD, OTHER_USER)])

    def test_channel_setting(self):
        self.assertIsNone(self.db.get_channel(GUILD))
        self.db.set_channel(GUILD, 555)
        self.db.set_channel(GUILD, 556)
        self.assertEqual(self.db.get_channel(GUILD), 556)

    def test_sent_log_is_per_year(self):
        self.assertFalse(self.db.already_sent(GUILD, USER, 2026))
        self.db.mark_sent(GUILD, USER, 2026)
        self.db.mark_sent(GUILD, USER, 2026)  # twice is harmless
        self.assertTrue(self.db.already_sent(GUILD, USER, 2026))
        self.assertFalse(self.db.already_sent(GUILD, USER, 2027))

    def test_existing_database_with_extra_tables_still_works(self):
        # the live database also has a portal_import table; init must leave it alone
        path = Path(self.tmp.name) / "old.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE portal_import (guild_id INTEGER, user_id INTEGER)")
        conn.execute("INSERT INTO portal_import VALUES (1, 2)")
        conn.commit()
        conn.close()

        db = Database(path)
        db.init_schema()
        db.init_schema()
        conn = sqlite3.connect(path)
        self.assertEqual(conn.execute("SELECT count(*) FROM portal_import").fetchone()[0], 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
