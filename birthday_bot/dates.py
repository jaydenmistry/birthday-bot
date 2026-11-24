"""Pure helpers for parsing birthdays and building messages. No Discord here."""

from __future__ import annotations

from datetime import datetime

DISCORD_MESSAGE_LIMIT = 1900  # under Discord's 2000, leaving room for formatting


def parse_birthday(text: str) -> tuple[int, int]:
    """Parse ``MM/DD`` or ``MM-DD`` into ``(month, day)``.

    Raises ``ValueError`` for anything that is not a real calendar date.
    29 February is accepted.
    """
    parts = text.strip().replace("-", "/").split("/")
    if len(parts) != 2:
        raise ValueError("Use MM/DD format, like 04/12")

    month, day = int(parts[0]), int(parts[1])
    datetime(2000, month, day)  # 2000 is a leap year, so 02/29 is valid
    return month, day


def format_date(month: int, day: int) -> str:
    return f"{month:02d}/{day:02d}"


def join_mentions(mentions: list[str]) -> str:
    """``a``, ``a and b``, or ``a, b, and c``."""
    if len(mentions) == 1:
        return mentions[0]
    if len(mentions) == 2:
        return f"{mentions[0]} and {mentions[1]}"
    return ", ".join(mentions[:-1]) + f", and {mentions[-1]}"


def announcement(mentions: list[str]) -> str:
    people = join_mentions(mentions)
    if len(mentions) == 1:
        return (
            f"Today is {people}'s birthday. "
            "Make sure to wish them a happy birthday on their special day! 🎉🎂"
        )
    return (
        f"Today we are celebrating {people}'s birthdays. "
        "Make sure to wish them a happy birthday on their special day! 🎉🎂"
    )


def chunk_lines(lines: list[str], limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Join lines into messages no longer than ``limit`` characters each."""
    chunks: list[str] = []
    current = ""
    for line in lines:
        if current and len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
