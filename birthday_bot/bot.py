"""The Discord client: intents, cogs, and slash command sync."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .config import Config
from .database import Database

log = logging.getLogger(__name__)

EXTENSIONS = (
    "birthday_bot.cogs.birthdays",
    "birthday_bot.cogs.announcer",
)


class BirthdayBot(commands.Bot):
    def __init__(self, config: Config, db: Database) -> None:
        intents = discord.Intents.default()
        intents.members = True  # needed to look up members for announcements and lists
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.config = config
        self.db = db

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        synced = await self.tree.sync()
        log.info("synced %d slash commands", len(synced))

    async def on_ready(self) -> None:
        log.info("logged in as %s (id %s)", self.user, self.user.id if self.user else "?")
