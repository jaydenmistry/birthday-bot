"""Slash commands for saving, viewing, and managing birthdays."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..dates import chunk_lines, format_date, parse_birthday

if TYPE_CHECKING:
    from ..bot import BirthdayBot

log = logging.getLogger(__name__)

INVALID_DATE = "Invalid date. Use MM/DD, like `04/12`."
NO_BIRTHDAY = "You do not have a birthday saved yet."


@app_commands.guild_only()
class Birthdays(commands.Cog):
    def __init__(self, bot: BirthdayBot) -> None:
        self.bot = bot
        self.db = bot.db

    # member commands

    @app_commands.command(name="setbirthday", description="Save your birthday in MM/DD format.")
    @app_commands.describe(date="Your birthday in MM/DD format, for example 04/12")
    async def setbirthday(self, interaction: discord.Interaction, date: str) -> None:
        try:
            month, day = parse_birthday(date)
        except (ValueError, TypeError):
            await interaction.response.send_message(INVALID_DATE, ephemeral=True)
            return

        self.db.set_birthday(interaction.guild_id, interaction.user.id, month, day)
        await interaction.response.send_message(
            f"Your birthday has been saved as **{format_date(month, day)}**.", ephemeral=True
        )

    @app_commands.command(name="removebirthday", description="Remove your saved birthday.")
    async def removebirthday(self, interaction: discord.Interaction) -> None:
        removed = self.db.remove_birthday(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(
            "Your birthday was removed." if removed else NO_BIRTHDAY, ephemeral=True
        )

    @app_commands.command(name="mybirthday", description="See your saved birthday.")
    async def mybirthday(self, interaction: discord.Interaction) -> None:
        saved = self.db.get_birthday(interaction.guild_id, interaction.user.id)
        if saved is None:
            await interaction.response.send_message(NO_BIRTHDAY, ephemeral=True)
            return
        await interaction.response.send_message(
            f"Your saved birthday is **{format_date(*saved)}**.", ephemeral=True
        )

    @app_commands.command(name="listbirthdays", description="List all saved birthdays in this server.")
    async def listbirthdays(self, interaction: discord.Interaction) -> None:
        rows = self.db.birthdays_in_guild(interaction.guild_id)
        if not rows:
            await interaction.response.send_message(
                "No birthdays have been saved in this server yet.", ephemeral=True
            )
            return

        lines = []
        for row in rows:
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else f"User ID {row['user_id']}"
            lines.append(f"**{format_date(row['month'], row['day'])}** — {name}")

        first, *rest = chunk_lines(lines)
        await interaction.response.send_message(first, ephemeral=True)
        for chunk in rest:
            await interaction.followup.send(chunk, ephemeral=True)

    # admin commands (Manage Server)

    @app_commands.command(name="setuserbirthday", description="Admin: set a birthday for another member.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        member="The server member whose birthday you want to set",
        date="Birthday in MM/DD format, for example 04/12",
    )
    async def setuserbirthday(
        self, interaction: discord.Interaction, member: discord.Member, date: str
    ) -> None:
        try:
            month, day = parse_birthday(date)
        except (ValueError, TypeError):
            await interaction.response.send_message(INVALID_DATE, ephemeral=True)
            return

        self.db.set_birthday(interaction.guild_id, member.id, month, day)
        await interaction.response.send_message(
            f"Saved **{member.display_name}**'s birthday as **{format_date(month, day)}**.",
            ephemeral=True,
        )

    @app_commands.command(
        name="setbirthdaychannel", description="Admin: set the channel where birthday messages are sent."
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel where birthday announcements should be posted")
    async def setbirthdaychannel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        self.db.set_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            f"Birthday messages will be sent in {channel.mention}.", ephemeral=True
        )

    # errors

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the **Manage Server** permission to use this command."
        else:
            log.exception("command /%s failed", interaction.command.name if interaction.command else "?",
                          exc_info=error)
            message = "Something went wrong."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: BirthdayBot) -> None:
    await bot.add_cog(Birthdays(bot))
