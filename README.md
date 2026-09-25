# BotFamily

Five Telegram bots, packaged to run as a single process.

| | bot | what it does |
|---|---|---|
| <img src="bots/sticker_bot/logo.svg" width="28"> | [**StickerBot**](bots/sticker_bot/) | Turns images, GIFs, videos and stickers into Telegram sticker packs, with co-editing by share link and bulk import from another pack or a WhatsApp export. |
| <img src="bots/convert_bot/logo.svg" width="28"> | [**ConvertBot**](bots/convert_bot/) | Converts files between about 75 formats: pictures, video, audio, documents, e-books, spreadsheets and subtitles. |
| <img src="bots/downloader_bot/logo.svg" width="28"> | [**DownloaderBot**](bots/downloader_bot/) | Returns the media behind an Instagram, TikTok, Pinterest, Reddit or X link. |
| <img src="bots/anon_bot/logo.svg" width="28"> | [**AnonBot**](bots/anon_bot/) | A permanent personal link for receiving anonymous messages, with two-way replies threaded per conversation. |
| <img src="bots/manager_bot/logo.svg" width="28"> | [**ManagerBot**](bots/manager_bot/) | Private. Watches the other four, forwards their crashes and donations, and runs their owner-only commands remotely. |

Each bot is also published as a repository of its own and normally deployed
as a service of its own. This repository holds the same code arranged to run
together: one interpreter, one event loop, one container. Each bot's folder
has its own README describing its commands.

---

## Why one process

Memory. Most of what an idle bot holds is the interpreter and its libraries —
Python, python-telegram-bot, httpx, psycopg, Pillow — and five processes hold
five copies of them. Measured on the same image, idle after startup:

| | resident memory | container memory |
|---|---|---|
| five processes, one bot each | 302 MB (57–62 MB each) | 225 MB |
| **one process, all five bots** | **77 MB** | **60 MB** |
| one process, two bots | 64 MB | — |

Each bot added to the shared process costs about 4 MB of its own.

What sharing a process gives up:

- **One failure reaches every bot.** An out-of-memory kill, or anything else
  that ends the process, stops all five at once.
- **One deploy restarts every bot**, and so does ManagerBot's
  `/run <bot> restart`, which works by ending the process.
- **Bots cannot be released separately.** All five always run the same
  version.

What it does not give up: an error in one bot's handler is caught for that
bot, as before; a bot that cannot start is logged and left out while the
others run; and each bot keeps its own database schema, its own settings and
its own log.

---

## Running it

### Docker, on any host

```bash
docker build -t botfamily .
docker run --env-file .env botfamily
```

The image installs ffmpeg, compiles the bytecode and then loads every bot
once (`python bot.py --check`), so an image in which any bot cannot even be
imported fails to build rather than failing to start.

### Railway

A service created from this repository builds with the Dockerfile
(`railway.json` selects it) and takes its variables from `.env.example`.

A bot token can only be polled by one process at a time. While another
process is still polling a bot — the same bot's own service, or the previous
deployment of this one — that bot waits up to four minutes for it to stop,
and the other bots start without waiting. Stopping the per-bot services
before starting this one avoids the wait.

### Without Docker

Python 3.11 or later, Postgres 16 or later, and `ffmpeg` on `PATH`:

```bash
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

---

## Configuration

`.env.example` is every setting any of the five bots reads, each marked
**required**, **required for** one bot, or **optional** with its default. Only
twelve lines are needed to run all five: `DATABASE_URL`, `ADMIN_ID`, and a
token and username for each bot — `SBOT_` StickerBot, `CBOT_` ConvertBot,
`DBOT_` DownloaderBot, `ABOT_` AnonBot, `MBOT_` ManagerBot:

```
SBOT_TOKEN=123456:ABC...
SBOT_USERNAME=my_sticker_bot
```

- **`DATABASE_URL`** — one Postgres for all five. Each bot keeps its tables
  in a schema named after its folder (`sticker_bot`, `convert_bot`, …); that
  is set automatically.
- **`ADMIN_ID`** — the owner's Telegram id, once, for all five bots.
- **A bot without a token is not started**, so any subset runs. `BOTS`
  picks a subset explicitly: `BOTS=sticker,anon`, or
  `python bot.py sticker anon`.
- **Derived rather than repeated:** the list of sibling bots each public bot
  shows is written from their usernames, and `POLICY_BASE_URL` gives every
  bot the links to its own `PRIVACY.md` and `TERMS.md`.

Every other setting has a working default. A setting given under its own name
applies to every bot; the same setting with a bot's prefix applies to that
bot only, whenever the bot reads it:

```
POLL_TIMEOUT=30          every bot
DBOT_POLL_TIMEOUT=50     DownloaderBot only
```

A few settings only ever describe one bot — its database schema, its policy
links, a payment provider's token — and are accepted only with a prefix; a
process-wide value is ignored, with a warning in the log. An empty value
counts as not set.

---

## Watching it

Every line of the log names the bot it came from, including the lines
written by python-telegram-bot and psycopg on a bot's behalf:

```
09:06:16,068 StickerBot    INFO    family: Polling as @...
09:06:16,086 family        INFO    family: 5/5 polling · 76 MB resident (peak 76 MB), 26 threads
09:07:51,266 AnonBot       INFO    lifecycle: Got SIGTERM -- draining. Finishing what's in flight, then stopping.
```

- **A status line** — which bots are polling, and what the process holds —
  is written once every bot has started and every 30 minutes after that
  (`UNIFIED_STATUS_MINUTES`; 0 turns it off).
- **`/status`** in any bot shows that bot, with the memory figure of the
  whole process. **ManagerBot** shows all five, and its `/logs <bot>`
  returns only that bot's lines.
- **ManagerBot's `/usage`** records the process's memory under one bot only,
  so its total counts the process once.
- **`python bot.py --list`** says which bots have a token;
  **`python bot.py --check`** loads every bot without starting any and
  confirms each got its own modules.

On a stop signal every bot tells anyone whose work was interrupted, saves
its open conversations, releases its poll lease and closes its database
connections; the process then exits.

---

## Layout

```
bot.py            runs the bots in one process
bots/<bot>/       each bot's own code, README, PRIVACY.md and TERMS.md
bots/bots.json    which shared modules each bot uses
shared/           the modules every bot uses, stored once
requirements.txt  every bot's requirements, merged
Dockerfile        the image, with ffmpeg
railway.json      Railway's build and deploy settings
.env.example      every variable, with its meaning
```

## How the bots are kept apart

Each bot is written as a program of its own: `import db` means its own
database module, `import i18n` its own translations, and the shared modules
keep per-bot state in module globals. `bot.py` loads each bot as a package —
`sticker_bot.db`, `anon_bot.db` — and gives each bot's modules an import of
their own, so a bare `import db` inside StickerBot still means StickerBot's.
A module in `shared/` is stored once and loaded once per bot that uses it,
and settings that share a name between bots are applied only while that bot
loads. Nothing outside the bots' own modules is changed. The full account is
at the top of `bot.py`.

## Licence

AGPL-3.0-or-later — see [LICENSE](LICENSE). Security reports:
[SECURITY.md](SECURITY.md).
