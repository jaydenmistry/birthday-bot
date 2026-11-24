"""Settings, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_DB_PATH = "/var/lib/birthday-bot/birthdays.db"


class ConfigError(RuntimeError):
    """A required setting is missing or invalid."""


@dataclass(frozen=True)
class Config:
    token: str
    timezone: ZoneInfo
    db_path: Path


def load(env: dict[str, str] | None = None) -> Config:
    env = os.environ if env is None else env

    token = env.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError("DISCORD_BOT_TOKEN is not set (see .env.example)")

    tz_name = env.get("BOT_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"BOT_TIMEZONE {tz_name!r} is not a valid timezone") from exc

    db_path = Path(env.get("BIRTHDAY_DB", DEFAULT_DB_PATH).strip() or DEFAULT_DB_PATH)

    return Config(token=token, timezone=timezone, db_path=db_path)
