"""Entry point: ``python -m birthday_bot``."""

from __future__ import annotations

import logging
import sys

import discord

from . import config as config_module
from .bot import BirthdayBot
from .database import Database


def main() -> int:
    discord.utils.setup_logging(level=logging.INFO)

    try:
        config = config_module.load()
    except config_module.ConfigError as exc:
        logging.getLogger("birthday_bot").error("%s", exc)
        return 2

    db = Database(config.db_path)
    db.init_schema()

    bot = BirthdayBot(config, db)
    bot.run(config.token, log_handler=None)  # logging is already set up above
    return 0


if __name__ == "__main__":
    sys.exit(main())
