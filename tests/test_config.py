import unittest
from pathlib import Path

from birthday_bot import config


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = config.load({"DISCORD_BOT_TOKEN": "abc"})
        self.assertEqual(cfg.token, "abc")
        self.assertEqual(str(cfg.timezone), "America/New_York")
        self.assertEqual(cfg.db_path, Path("/var/lib/birthday-bot/birthdays.db"))

    def test_overrides(self):
        cfg = config.load({"DISCORD_BOT_TOKEN": "abc", "BOT_TIMEZONE": "UTC", "BIRTHDAY_DB": "/tmp/x.db"})
        self.assertEqual(str(cfg.timezone), "UTC")
        self.assertEqual(cfg.db_path, Path("/tmp/x.db"))

    def test_missing_token(self):
        for env in ({}, {"DISCORD_BOT_TOKEN": "   "}):
            with self.subTest(env=env), self.assertRaises(config.ConfigError):
                config.load(env)

    def test_bad_timezone(self):
        with self.assertRaises(config.ConfigError):
            config.load({"DISCORD_BOT_TOKEN": "abc", "BOT_TIMEZONE": "Mars/Base"})


if __name__ == "__main__":
    unittest.main()
