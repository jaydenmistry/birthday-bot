# Birthday Bot

A Discord bot that remembers members' birthdays and posts a message in a chosen channel on the day.

## Features

- Members save their own birthday with a slash command. Only the month and day are stored, never the year.
- Admins can set birthdays for others and choose the announcement channel.
- People who share a birthday are announced together in one message.
- Each person is announced at most once per year, even if the bot restarts.
- If the bot is offline at midnight, it catches up as long as it is back the same day.

## Commands

| Command | Who | What it does |
| --- | --- | --- |
| `/setbirthday 04/12` | everyone | Save or change your birthday (`MM/DD` or `MM-DD`) |
| `/mybirthday` | everyone | Show your saved birthday |
| `/removebirthday` | everyone | Delete your saved birthday |
| `/listbirthdays` | everyone | List all birthdays in the server |
| `/setuserbirthday @member 04/12` | Manage Server | Set another member's birthday |
| `/setbirthdaychannel #channel` | Manage Server | Choose where announcements are posted |

All replies are only visible to the person who ran the command. The announcement itself mentions the birthday person but never `@everyone` or roles.

## How it works

Once a minute the bot checks the date in `BOT_TIMEZONE`. For every birthday today that has not been announced yet this year, it posts in the server's announcement channel and records it in `sent_log`. In practice the message goes out just after midnight.

Birthdays on 29 February are only announced in leap years.

## Project layout

```
birthday_bot/
  __main__.py        entry point (python -m birthday_bot)
  bot.py             Discord client, intents, command sync
  config.py          settings from environment variables
  database.py        SQLite storage
  dates.py           date parsing and message text (no Discord code)
  cogs/
    birthdays.py     slash commands
    announcer.py     daily announcement loop
tests/               unit tests (python -m unittest)
deploy/              systemd unit
```

## Configuration

Settings come from environment variables. See [`.env.example`](.env.example).

| Variable | Required | Default |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | yes | |
| `BOT_TIMEZONE` | no | `America/New_York` |
| `BIRTHDAY_DB` | no | `/var/lib/birthday-bot/birthdays.db` |

In the Discord Developer Portal, the bot needs the **Server Members Intent** enabled. In the server it needs **View Channel** and **Send Messages** in the announcement channel.

## Installation (Debian / Ubuntu)

```sh
# 1. a system user with no login and no home directory
sudo useradd --system --no-create-home --shell /usr/sbin/nologin birthday-bot

# 2. the code, owned by root so the bot cannot modify itself
sudo git clone https://github.com/jaydenmistry/birthday-bot.git /opt/birthday-bot
sudo python3 -m venv /opt/birthday-bot/venv
sudo /opt/birthday-bot/venv/bin/pip install -r /opt/birthday-bot/requirements.txt

# 3. the token, readable only by root (systemd reads it before starting the bot)
sudo install -d -m 700 /etc/birthday-bot
sudo install -m 600 /opt/birthday-bot/.env.example /etc/birthday-bot/birthday-bot.env
sudo nano /etc/birthday-bot/birthday-bot.env

# 4. the service
sudo cp /opt/birthday-bot/deploy/birthday-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now birthday-bot
journalctl -u birthday-bot -f
```

The database is created automatically in `/var/lib/birthday-bot/`.

### Updating

```sh
cd /opt/birthday-bot
sudo git pull
sudo venv/bin/pip install -r requirements.txt
sudo systemctl restart birthday-bot
```

## Security

- The bot runs as its own unprivileged user inside a systemd sandbox: read-only access to the system, no access to home directories, write access only to its data folder, network only.
- The token lives in `/etc/birthday-bot/birthday-bot.env` (mode `600`, root only), never in the repository or the unit file.
- The database is kept outside the code folder and out of git. Back it up with the server.

## Development

```sh
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python -m unittest discover -s tests -t . -v

# run locally against a test server
DISCORD_BOT_TOKEN=... BIRTHDAY_DB=./birthdays.db venv/bin/python -m birthday_bot
```
