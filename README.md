# birthday bot

discord bot that posts a birthday message in a chosen channel. birthdays are kept in a local sqlite file (`birthdays.db`, not in git).

## commands

| command | who | what |
| --- | --- | --- |
| `/setbirthday 04/12` | anyone | save your birthday |
| `/mybirthday` | anyone | show your saved birthday |
| `/removebirthday` | anyone | delete your birthday |
| `/listbirthdays` | anyone | list everyone's birthdays |
| `/setuserbirthday @member 04/12` | manage server | set someone else's birthday |
| `/setbirthdaychannel #channel` | manage server | pick the announcement channel |

once a minute it checks today's date (`BOT_TIMEZONE`) and announces anyone not announced yet this year, so a message goes out just after midnight.

## install

```
cd /opt/birthday-bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env   # then put the token in .env
cp deploy/birthday-bot.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now birthday-bot
```

the discord bot needs the **server members** intent enabled in the developer portal.

## notes

- `.env` holds the token. never commit it.
- `birthdays.db` holds everyone's birthdays. it is backed up with the container, not in git.
