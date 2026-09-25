<img src="logo.svg" alt="StickerBot" width="72" align="right">

# StickerBot

A Telegram bot for creating and managing sticker packs. It turns images,
GIFs, videos and existing stickers into a Telegram sticker pack, lets a pack
be co-edited by several people through a share link, and can bulk-import
from another public Telegram pack or from a WhatsApp sticker export.

Runs as its own process, its own repository and its own deployment, and can
be run entirely standalone. It shares a Postgres database with four sibling
bots only in the sense that its tables live in a schema of their own inside
it (`DB_SCHEMA`); no other bot reads or writes them. The one shared area is
`family.*`, where the bot posts a heartbeat and any crash so a monitoring bot
can watch it — `FAMILY_BUS=off` disables that entirely.

---

## Commands

| command | what it does |
|---|---|
| `/newpack` | Start a new sticker pack. |
| `/addsticker` | Add stickers to an existing pack. |
| `/mypacks` | List the user's packs; tapping one offers rename and co-editing. |
| `/import <pack link or name>` | While editing, bulk-copy stickers from another public pack. Also accepts a WhatsApp `.zip` or `.wastickers` export sent as a file. |
| `/done` | Finish editing. |
| `/whomade <pack link or name>` | Who created a pack, if it was made through this bot. |
| `/cancel` | Asks which of the things the bot is waiting on should stop, one button each, and stops nothing until one is chosen. |
| `/donate` | Voluntary contribution towards hosting, paid in Telegram Stars. |
| `/start` | Instructions. The first `/start` from a new user asks which language to use, once. |
| `/language`, `/en`, `/uz`, `/rus` | Switch language. Each reprints the instructions in the language chosen. |
| `/help` | The instructions on their own. |
| `/privacy` | What the bot holds about the person asking, who else sees it, and how long it stays. |
| `/terms` | What the bot may be used for, and where the money stands. |
| `/deletemydata` | Erases what the bot holds about the person asking, after one confirmation. |

Restricted to the account ids in `SBOT_ADMIN_ID`, and answering everyone else
exactly as a misspelt command does, so their existence is not disclosed:
`/whois <user_id>` (a user's name, username and bio, plus any packs of theirs
on record), `/messageas <user_id> <text>`, `/dbdump`, `/status` and
`/crashtest`.

Telegram does not allow a bot to message someone who has never messaged it,
so `/messageas` only reaches people who have used the bot before.

---

## Privacy and terms

The bot holds personal data from the first message it receives: a Telegram
user id is the only thing a bot can address a person by, so there is no
opting out of that one while the bot is in use. `/privacy` says what else is
kept, who else sees it and how long it stays; `/terms` says what the bot may
be used for; `/deletemydata` erases it, immediately and without a form.

All three speak whichever of the three languages the person has chosen.
The long forms are [PRIVACY.md](PRIVACY.md) and [TERMS.md](TERMS.md), which
is also what the privacy-policy link in Telegram's own bot settings points
at.

---

## How it works

**Encoding.** Video stickers have to fit inside Telegram's 256 KB ceiling as
WebM/VP9. The encoder measures rather than laddering blindly: it estimates a
bitrate from the clip's length and dimensions, encodes once, and only retries
if the result missed. Static stickers are resized to Telegram's 512-pixel
box with transparency preserved.

**Co-editing.** A pack has one creator and any number of editors, added by
share link. Editors can add and remove stickers; only the creator can rename
or hand the pack on.

**Importing.** A Telegram pack is copied by file id, so nothing is
re-encoded. A WhatsApp export is a zip of WebP images, which are converted.

**Limits.** A ceiling on updates per minute applies per account, before any
handler runs, so a script cannot hold the process busy. It is configurable;
see `.env.example`.

---

## Running it

In this repository StickerBot runs alongside the other bots from the top-level
`bot.py`, and the [top-level README](../../README.md) covers installing,
configuring and deploying it. Its settings keep the names they have when it
runs alone; one that another bot also reads can be given to StickerBot only by
prefixing it with `SBOT_`.

---

## Licence

AGPL-3.0-or-later — see [LICENSE](../../LICENSE).

This is the licence the AGPL'd PyMuPDF asks for, and §13 of it is the reason:
anybody who interacts with this software over a network must be offered its
source. A Telegram bot is exactly that case, since nobody using it ever holds
a copy. The source is here, which satisfies §13 for this deployment; anybody
running a modified version as a service has to publish their changes too.
