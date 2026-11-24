import os
import sqlite3
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks


TOKEN = os.getenv("DISCORD_BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
BOT_TIMEZONE = os.getenv("BOT_TIMEZONE", "America/New_York")
DB_FILE = os.path.join(os.path.dirname(__file__), "birthdays.db")


# ----------------------------
# Database Functions
# ----------------------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS birthdays (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_log (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            PRIMARY KEY (guild_id, user_id, year)
        )
    """)

    conn.commit()
    conn.close()


def get_birthday_channel(guild_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT channel_id FROM settings WHERE guild_id = ?",
        (guild_id,)
    )
    row = cur.fetchone()
    conn.close()

    return row["channel_id"] if row else None


def set_birthday_channel_db(guild_id: int, channel_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO settings (guild_id, channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            channel_id = excluded.channel_id
    """, (guild_id, channel_id))

    conn.commit()
    conn.close()


def set_birthday_db(guild_id: int, user_id: int, month: int, day: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO birthdays (guild_id, user_id, month, day)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            month = excluded.month,
            day = excluded.day
    """, (guild_id, user_id, month, day))

    conn.commit()
    conn.close()


def remove_birthday_db(guild_id: int, user_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )

    deleted = cur.rowcount
    conn.commit()
    conn.close()

    return deleted > 0


def get_birthdays_for_day(month: int, day: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT guild_id, user_id
        FROM birthdays
        WHERE month = ? AND day = ?
    """, (month, day))

    rows = cur.fetchall()
    conn.close()

    return rows


def get_all_birthdays_for_guild(guild_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, month, day
        FROM birthdays
        WHERE guild_id = ?
        ORDER BY month, day
    """, (guild_id,))

    rows = cur.fetchall()
    conn.close()

    return rows


def already_sent(guild_id: int, user_id: int, year: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM sent_log
        WHERE guild_id = ? AND user_id = ? AND year = ?
    """, (guild_id, user_id, year))

    row = cur.fetchone()
    conn.close()

    return row is not None


def mark_sent(guild_id: int, user_id: int, year: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO sent_log (guild_id, user_id, year)
        VALUES (?, ?, ?)
    """, (guild_id, user_id, year))

    conn.commit()
    conn.close()


# ----------------------------
# Helper Functions
# ----------------------------

def parse_birthday(date_str: str):
    """
    Accepts MM/DD or MM-DD.
    Returns (month, day).
    """
    cleaned = date_str.strip().replace("-", "/")
    parts = cleaned.split("/")

    if len(parts) != 2:
        raise ValueError("Use MM/DD format, like 04/12")

    month = int(parts[0])
    day = int(parts[1])

    # Validate date using a leap-safe year.
    datetime(2000, month, day)

    return month, day


def format_birthday_mentions(members):
    """
    Formats Discord member mentions into a readable list.

    Examples:
    @Neharika K
    @Neharika K and @Ryan Majd
    @Neharika K, @Ryan Majd, and @Alli
    """
    mentions = [member.mention for member in members]

    if len(mentions) == 1:
        return mentions[0]

    if len(mentions) == 2:
        return f"{mentions[0]} and {mentions[1]}"

    return ", ".join(mentions[:-1]) + f", and {mentions[-1]}"


# ----------------------------
# Bot Setup
# ----------------------------

class BirthdayBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await self.tree.sync()
        birthday_check.start()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("Birthday bot is ready.")


bot = BirthdayBot()


# ----------------------------
# User Commands
# ----------------------------

@bot.tree.command(name="setbirthday", description="Save your birthday in MM/DD format.")
@app_commands.describe(date="Your birthday in MM/DD format, for example 04/12")
async def setbirthday(interaction: discord.Interaction, date: str):
    try:
        month, day = parse_birthday(date)
    except (ValueError, TypeError):
        await interaction.response.send_message(
            "Invalid date. Use MM/DD, like `04/12`.",
            ephemeral=True
        )
        return

    set_birthday_db(interaction.guild_id, interaction.user.id, month, day)

    await interaction.response.send_message(
        f"Your birthday has been saved as **{month:02d}/{day:02d}**.",
        ephemeral=True
    )


@bot.tree.command(name="removebirthday", description="Remove your saved birthday.")
async def removebirthday(interaction: discord.Interaction):
    removed = remove_birthday_db(interaction.guild_id, interaction.user.id)

    if removed:
        await interaction.response.send_message(
            "Your birthday was removed.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "You do not have a birthday saved yet.",
            ephemeral=True
        )


@bot.tree.command(name="mybirthday", description="See your saved birthday.")
async def mybirthday(interaction: discord.Interaction):
    rows = get_all_birthdays_for_guild(interaction.guild_id)

    for row in rows:
        if row["user_id"] == interaction.user.id:
            await interaction.response.send_message(
                f"Your saved birthday is **{row['month']:02d}/{row['day']:02d}**.",
                ephemeral=True
            )
            return

    await interaction.response.send_message(
        "You do not have a birthday saved yet.",
        ephemeral=True
    )


@bot.tree.command(name="listbirthdays", description="List all saved birthdays in this server.")
async def listbirthdays(interaction: discord.Interaction):
    rows = get_all_birthdays_for_guild(interaction.guild_id)

    if not rows:
        await interaction.response.send_message(
            "No birthdays have been saved in this server yet.",
            ephemeral=True
        )
        return

    guild = interaction.guild
    lines = []

    for row in rows:
        member = guild.get_member(row["user_id"])
        name = member.display_name if member else f"User ID {row['user_id']}"
        lines.append(f"**{row['month']:02d}/{row['day']:02d}** — {name}")

    message = "\n".join(lines)

    if len(message) <= 1900:
        await interaction.response.send_message(message, ephemeral=True)
        return

    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > 1900:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    await interaction.response.send_message(chunks[0], ephemeral=True)

    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=True)


# ----------------------------
# Admin Commands
# ----------------------------

@bot.tree.command(name="setuserbirthday", description="Admin: set a birthday for another member.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    member="The server member whose birthday you want to set",
    date="Birthday in MM/DD format, for example 04/12"
)
async def setuserbirthday(
    interaction: discord.Interaction,
    member: discord.Member,
    date: str
):
    try:
        month, day = parse_birthday(date)
    except (ValueError, TypeError):
        await interaction.response.send_message(
            "Invalid date. Use MM/DD, like `04/12`.",
            ephemeral=True
        )
        return

    set_birthday_db(interaction.guild_id, member.id, month, day)

    await interaction.response.send_message(
        f"Saved **{member.display_name}**'s birthday as **{month:02d}/{day:02d}**.",
        ephemeral=True
    )


@setuserbirthday.error
async def setuserbirthday_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "You need the **Manage Server** permission to use this command.",
            ephemeral=True
        )
    else:
        if interaction.response.is_done():
            await interaction.followup.send(
                "Something went wrong.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Something went wrong.",
                ephemeral=True
            )


@bot.tree.command(
    name="setbirthdaychannel",
    description="Admin: set the channel where birthday messages are sent."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(channel="The channel where birthday announcements should be posted")
async def setbirthdaychannel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    set_birthday_channel_db(interaction.guild_id, channel.id)

    await interaction.response.send_message(
        f"Birthday messages will be sent in {channel.mention}.",
        ephemeral=True
    )


@setbirthdaychannel.error
async def setbirthdaychannel_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "You need the **Manage Server** permission to use this command.",
            ephemeral=True
        )
    else:
        if interaction.response.is_done():
            await interaction.followup.send(
                "Something went wrong.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Something went wrong.",
                ephemeral=True
            )


# ----------------------------
# Birthday Announcement Task
# ----------------------------

@tasks.loop(minutes=1)
async def birthday_check():
    tz = ZoneInfo(BOT_TIMEZONE)
    now = datetime.now(tz)

    month = now.month
    day = now.day
    year = now.year

    rows = get_birthdays_for_day(month, day)

    # Groups all unsent birthday members by server/channel.
    # This allows multiple birthdays on the same day to be sent in one message.
    birthday_groups = {}

    for row in rows:
        guild_id = row["guild_id"]
        user_id = row["user_id"]

        if already_sent(guild_id, user_id, year):
            continue

        guild = bot.get_guild(guild_id)
        if guild is None:
            continue

        channel_id = get_birthday_channel(guild_id)
        if not channel_id:
            continue

        channel = guild.get_channel(channel_id)
        if channel is None:
            continue

        member = guild.get_member(user_id)

        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                continue
            except discord.HTTPException:
                continue

        group_key = (guild_id, channel_id)

        if group_key not in birthday_groups:
            birthday_groups[group_key] = {
                "guild_id": guild_id,
                "channel": channel,
                "members": []
            }

        birthday_groups[group_key]["members"].append(member)

    for group in birthday_groups.values():
        guild_id = group["guild_id"]
        channel = group["channel"]
        members = group["members"]

        if not members:
            continue

        birthday_people = format_birthday_mentions(members)

        if len(members) == 1:
            message = (
                f"Today is {birthday_people}'s birthday. "
                f"Make sure to wish them a happy birthday on their special day! 🎉🎂"
            )
        else:
            message = (
                f"Today we are celebrating {birthday_people}'s birthdays. "
                f"Make sure to wish them a happy birthday on their special day! 🎉🎂"
            )

        try:
            await channel.send(
                message,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False,
                    users=True,
                    roles=False,
                    replied_user=False
                )
            )

            for member in members:
                mark_sent(guild_id, member.id, year)

            await asyncio.sleep(1)

        except discord.Forbidden:
            print(f"Missing permission to send birthday message in guild {guild_id}.")
        except discord.HTTPException as exc:
            print(f"Failed to send birthday message in guild {guild_id}: {exc}")


@birthday_check.before_loop
async def before_birthday_check():
    await bot.wait_until_ready()


# ----------------------------
# Start Bot
# ----------------------------

def main():
    if TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE" or not TOKEN.strip():
        raise RuntimeError(
            "Set your bot token in DISCORD_BOT_TOKEN before starting the bot."
        )

    init_db()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
