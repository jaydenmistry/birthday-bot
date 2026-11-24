"""Posts the daily birthday announcement.

Checks once a minute, so the message goes out just after midnight in
``BOT_TIMEZONE``. If the bot is offline at midnight it still announces when it
comes back, as long as that is the same day. Each person is announced at most
once per year (``sent_log``).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from ..dates import announcement

if TYPE_CHECKING:
    from ..bot import BirthdayBot

log = logging.getLogger(__name__)

MENTION_USERS_ONLY = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False)


class Announcer(commands.Cog):
    def __init__(self, bot: BirthdayBot) -> None:
        self.bot = bot
        self.db = bot.db

    async def cog_load(self) -> None:
        self.check_birthdays.start()

    async def cog_unload(self) -> None:
        self.check_birthdays.cancel()

    @tasks.loop(minutes=1)
    async def check_birthdays(self) -> None:
        # an uncaught error would stop the loop for good, so one bad minute
        # (a locked database, a Discord outage) is logged and the next minute retries
        try:
            await self._announce_today()
        except Exception:
            log.exception("birthday check failed")

    async def _announce_today(self) -> None:
        now = datetime.now(self.bot.config.timezone)

        # (guild, channel) -> members, so people sharing a birthday get one message
        groups: dict[tuple[int, int], tuple[discord.TextChannel, list[discord.Member]]] = {}

        for row in self.db.birthdays_on(now.month, now.day):
            guild_id, user_id = row["guild_id"], row["user_id"]
            if self.db.already_sent(guild_id, user_id, now.year):
                continue

            guild = self.bot.get_guild(guild_id)
            channel_id = self.db.get_channel(guild_id) if guild else None
            channel = guild.get_channel(channel_id) if guild and channel_id else None
            if channel is None:
                continue

            member = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except discord.HTTPException:  # left the server, or Discord hiccup
                    continue

            groups.setdefault((guild_id, channel.id), (channel, []))[1].append(member)

        for (guild_id, _), (channel, members) in groups.items():
            try:
                await channel.send(
                    announcement([m.mention for m in members]), allowed_mentions=MENTION_USERS_ONLY
                )
            except discord.Forbidden:
                log.warning("missing permission to post in guild %s", guild_id)
                continue
            except discord.HTTPException as exc:
                log.warning("could not post birthday message in guild %s: %s", guild_id, exc)
                continue

            for member in members:
                self.db.mark_sent(guild_id, member.id, now.year)
            await asyncio.sleep(1)

    @check_birthdays.before_loop
    async def before_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: BirthdayBot) -> None:
    await bot.add_cog(Announcer(bot))
