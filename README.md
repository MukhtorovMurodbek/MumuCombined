# MumuCombined

Five Telegram bots in one process.

| bot | what it does |
|---|---|
| **StickerBot** | Turns images, GIFs, videos and stickers into Telegram sticker packs, with co-editing by share link and bulk import from another pack or a WhatsApp export. |
| **ConvertBot** | Converts files between about 75 formats: pictures, video, audio, documents, e-books, spreadsheets and subtitles, up to 2000 MB. |
| **DownloaderBot** | Returns the media behind an Instagram, TikTok, Pinterest, Reddit or X link -- over 50 MB too, for ⚡ credit, for somebody who switched that on. |
| **AnonBot** | A permanent personal link for receiving anonymous messages, with two-way replies threaded per conversation. |
| **ManagerBot** | Private. Watches the other four, forwards their crashes and payments, and runs their owner-only commands from one chat. |

All five share one interpreter, one event loop and one container, and one
Postgres database with a schema per bot. Privacy and terms for the four
public bots are in [LEGAL.md](LEGAL.md).

This is the long-term edition: every feature of the separately deployed bots,
released less often and arranged by what the code does rather than by bot.

---

## Why one process

Memory. Most of what an idle bot holds is the interpreter and its libraries —
Python, python-telegram-bot, httpx, psycopg, Pillow — and five processes hold
five copies of them. Measured idle after startup:

| | resident memory |
|---|---|
| five processes, one bot each | 302 MB |
| **one process, all five bots** | **77 MB** |

Each bot costs about 4 MB of its own on top of the shared part.

What sharing a process gives up: an out-of-memory kill or anything else that
ends the process stops all five at once; one deploy restarts every bot; and
all five always run the same version. What it keeps: an error in one bot's
handler is caught for that bot alone, a bot that cannot start is logged and
left out while the others run, and each bot keeps its own schema, settings
and log.

---

## The bots

Every public bot answers `/start` (asking for a language once, on first use),
`/help`, `/language` with `/en`, `/uz` and `/rus`, `/cancel` (which asks what
to stop, one button each, and stops nothing until one is chosen), `/balance`,
`/paysupport`, `/privacy`, `/terms` and `/deletemydata`, in English, Uzbek and
Russian. Owner-only commands answer anybody else exactly as a misspelt command
does, so their existence is not disclosed.

### StickerBot

| command | |
|---|---|
| `/newpack` | Start a pack from images, GIFs, videos or stickers. |
| `/addsticker` | Add to an existing pack. |
| `/mypacks` | The person's packs; each offers renaming and co-editing. |
| `/import <pack>` | While editing, copy stickers from another public pack, or send a WhatsApp `.zip` / `.wastickers` export. |
| `/done` | Finish editing. |
| `/whomade <pack>` | Who created a pack made through the bot. |
| `/donate` | A voluntary payment in Stars. |

Owner-only: `/whois`, `/messageas`, `/dbdump`, `/status`, `/crashtest`.

Video stickers must fit Telegram's 256 KB as WebM/VP9; the encoder estimates a
bitrate from the clip, encodes once, and retries only when it missed. Static
stickers are fitted to 512 pixels with transparency kept. A pack has one
creator and any number of editors added by share link. Telegram packs are
imported by file id, without re-encoding.

### ConvertBot

| command | |
|---|---|
| *(send a file)* | Offers what it can become, as buttons. `/convert` does the same. |
| `/formats` | Every format read and written; `/formats heic` answers for one. |
| `/recharge` | Buys ⚡ credit with Stars (`/donate` also works). |

Owner-only: `/stars`, `/messageas`, `/dbdump`, `/status`.

| | reads | writes |
|---|---|---|
| **Pictures** | PNG, JPEG, WEBP, BMP, TIFF, ICO, HEIC/HEIF, AVIF, JPEG 2000, PSD, TGA, PCX, DDS, PPM, SGI, XBM, XPM, ICNS, QOI, BLP, SVG | PNG, JPEG, WEBP, PDF, ICO, TIFF, BMP, GIF, AVIF, HEIC, JPEG 2000, TGA, PPM, QOI, ICNS |
| **Video** | MP4, MOV, M4V, AVI, WEBM, MKV, FLV, WMV, TS, M2TS, MPEG, 3GP, OGV, ASF, GIF, APNG | MP4, WEBM, MKV, MOV, AVI, GIF, animated WEBP, APNG, and the audio on its own |
| **Audio** | MP3, WAV, OGG, Opus, M4A, AAC, FLAC, AIFF, WMA, AMR, AC3, MP2, AU, CAF, W64, VOC | MP3, M4A, AAC, OGG, Opus, WAV, FLAC, AIFF, WMA, AC3 |
| **Documents** | PDF, DOCX, EPUB, MOBI, FB2, CBZ, XPS, Markdown, HTML, plain text | PDF, DOCX, PNG, JPEG, WEBP, TIFF, SVG, plain text, HTML, Markdown |
| **Data** | CSV, TSV, JSON, YAML, XLSX, XML | JSON, CSV, TSV, YAML, XLSX, Markdown table, HTML table, PDF |
| **Subtitles** | SRT, VTT, ASS/SSA | SRT, VTT, ASS, or the transcript without timings |

An album of pictures becomes one PDF; a many-page document becomes a zip of
pages; a format whose library is missing on the host is left off the menu.
Conversions under 3 MB are free. A larger one is quoted in ⚡ credit once the
format is chosen — priced on the file and on what it is estimated to become —
and the credit is taken when the conversion starts. From ⚡6; a 100 MB video to
MP4 is ⚡22, and nothing costs more than ⚡84. A price is the job's cost plus a
markup that is the cost itself while it is small and grows more slowly after,
so a bigger file costs less per megabyte; the cost is the most the job is
allowed to use at the host's rates, so no price is below what its job can cost
(`core/pricing.py`). A conversion that fails
for the bot's reasons gives its credit back. One runs at a time, in a child
process with a time limit, with updates at two and five minutes.

**Files over 20 MB.** Telegram's Bot API lets a bot download 20 MB and send 50.
With `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` set (from
[my.telegram.org](https://my.telegram.org), *API development tools*; ConvertBot's
own `CBOT_API_ID` / `CBOT_API_HASH` win), larger files move over MTProto
instead — Telegram's own protocol, logged in as the same bot, each transfer in
a short-lived process of its own so the bot never carries the library — in
private chats, up to 2000 MB, Telegram's own limit for a bot
(`CONVERT_MAX_FILE_MB` lowers it). Four 512 KB parts are in flight at once, a
transfer that stops moving for 90 seconds is given up, and a conversion on
course to miss its ten minutes is stopped within its first minute and its ⚡
given back. A result may be sent back at up to twice the size it was priced
on. Without the two settings the limit is 20 MB.

**HDR video.** A phone video shot in HDR10 or HLG is tone-mapped to ordinary
BT.709 colour on its way to any target that is not HDR, instead of coming out
grey and flat.

### DownloaderBot

Pasting a supported link is the whole interface.

| platform | returns |
|---|---|
| Instagram | Reels, photo posts and carousels |
| TikTok | Videos without the watermark, and photo slideshows |
| Twitter / X | Video and photos; a text post as an image card |
| Pinterest | The pin at full resolution, or its video; idea pins page by page; any country domain and `pin.it` links |
| Reddit | Media posts directly; text and link posts as an image card |

| command | |
|---|---|
| `/settings` | The caption, the file quality and large files on one screen. |
| `/lossless on\|off` | Downloads as files rather than as re-encoded photos and videos. A button under each download gets that one file the other way. |
| `/caption on\|off` | The credit caption. |
| `/donate` | A voluntary payment in Stars; it also raises the download allowance. |

**Large files, over 48 MB.** The Bot API sends 50 MB at most, so downloads
stop at 48. With the API id and hash above, a file past that is fetched anyway
and sent over MTProto, up to 2000 MB, **for ⚡7 up to 100 MB and less for each
100 MB after (⚡76 for 2000 MB)** -- and only
for somebody who switched large files on in `/settings`, which is off until
they do. Off, the bot answers with the price and a button that switches it
on, and nothing past 48 MB is fetched or charged. On, it says before it
starts that this one costs credit, and charges once the file is here: a
balance that does not cover it is charged nothing, and a send that fails gives
the credit back. `DBOT_LARGE_MAX_MB` lowers the ceiling; the price follows
the same rule as a conversion's.

Owner-only: `/providers`, `/messageas`, `/dbdump`, `/status`, and `/probe`
through ManagerBot.

Sites decide what to serve partly by where a request comes from, and cloud
addresses are often served a login page. So each platform has a chain of
independent providers, tried in order; a failing provider moves to the back
and rests, with the delay growing, and requests from the container's own
address are tried last. `/providers` shows what the chain believes, `/probe`
tries every route against known-good posts. Two downloads run at a time, one
per person, within an hourly and daily allowance counted in the database.
`DBOT_IG_COOKIES_FILE` and `DBOT_IG_PROXY` improve Instagram from a
datacenter.

### AnonBot

| command | |
|---|---|
| `/link` | The person's permanent inbox link, with Pause, Resume and New-link buttons (`/pause`, `/resume`, `/newlink`). |
| `/conversations` | Open threads, one card each, with buttons to jump to a conversation's start or archive it. |
| `/which` | As a reply: which conversation a message belongs to. |
| `/archive` | As a reply: file that conversation away, after one confirmation. |
| `/blocked` | Blocked senders, each with an Undo button. |
| `/export` | A conversation, or all of them, copied back into the chat or written into a document. |
| `/stats` | How many people have written, and how many conversations. |

Owner-only: `/dbdump`, `/messageas`, `/status`.

One inbox link is often posted publicly, so one chat holds many conversations
at once. Every message is therefore a Telegram reply, and the bot maps each
delivered message to its conversation and to its counterpart in the other
chat; a reply is routed through that map, never by guessing. The one message
that needs no reply is the one that opens a conversation. A message that names
no conversation is refused, not sent and not stored. No message content is
stored at all — only which accounts are talking and which message belongs to
which conversation.

### ManagerBot

Answers only `ADMIN_ID`; without it, it does not start.

- **On its own:** checks every bot's heartbeat once a minute and reports when
  one goes down or comes back, telling a redeploy from a crash; forwards
  crashes with the end of the traceback, and payments; says when its own
  database connection fails; sends one roll-call after it starts.
- **Watching:** `/status`, `/events`, `/problems`, `/report`, `/errors`,
  `/usage`, `/idle`, `/users`, `/alerts on|off`.
- **Reaching into a bot:** `/run <bot> <command>`, `/ping [bot]` (the round
  trip leg by leg, timed on the database's clock), `/logs <bot>`, `/restart`,
  `/whois`, `/say`, `/dbdump`.
- **Releases:** `/pause`, `/warn`, `/resume`, `/broadcast`.
- **The family:** `/balance`, `/addcredit`, `/donations`, `/backup` (the whole
  database as CSVs), `/sql <SELECT …>` (read-only), `/decode <code>`.

Any unambiguous prefix or the bot's username names a bot: `/logs stick`,
`/run conv status`, `/logs @mumu_chat_bot`.

---

## Running it

### Docker, on any host

```bash
docker build -t botfamily .
docker run --env-file .env botfamily
```

The image installs ffmpeg, compiles the bytecode, then runs
`python main.py --check`: every bot is loaded once and one real conversion is
run through ConvertBot's worker, so an image in which a bot cannot even be
imported fails to build rather than failing to start.

### Railway

A service created from this repository builds with the Dockerfile
(`railway.json` selects it) and takes its variables from `.env.example`. A bot
token can be polled by one process at a time; while another process still polls
a bot, that bot waits up to four minutes and the others start without waiting.

### Without Docker

Python 3.11 or later, Postgres 16 or later, and `ffmpeg` on `PATH`:

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`python main.py sticker anon` (or `BOTS=sticker,anon`) runs a subset;
`--list` says which bots have a token; `--check` loads everything without
starting any bot.

---

## Configuration

`.env.example` lists every setting, each marked required, required for one
bot, or optional with its default. Twelve lines run all five: `DATABASE_URL`,
`ADMIN_ID`, and a token and username per bot — `SBOT_` StickerBot, `CBOT_`
ConvertBot, `DBOT_` DownloaderBot, `ABOT_` AnonBot, `MBOT_` ManagerBot.

- **`DATABASE_URL`** — one Postgres for all five; each bot's tables live in a
  schema named after it, set automatically.
- **`ADMIN_ID`** — the owner's Telegram id, once, for all five.
- **A bot without a token is not started.**
- **Derived rather than repeated:** the sibling bots each public bot points
  to come from their usernames, and every bot's policy links point to its own
  sections of `LEGAL.md` (`LEGAL_URL` moves them).

A setting under its own name applies to every bot; with a bot's prefix, to
that bot only (`POLL_TIMEOUT=30`, `DBOT_POLL_TIMEOUT=50`). Settings that can
only mean one bot — its schema, its policy links, a payment provider's token —
are accepted only with a prefix. An empty value counts as not set.

Before any bot loads, the settings everything depends on are checked and the
database is tried once; a problem stops the start with one line,
`Not starting: …`. Every log line names the bot it came from, a status line
reports which bots are polling and what the process holds every 30 minutes
(`UNIFIED_STATUS_MINUTES`), and ManagerBot's `/usage` counts the process's
memory once. On a stop signal every bot tells anyone whose work was
interrupted, saves its open conversations, releases its poll lease and closes
its connections.

---

## Layout

Nine files of code, one for each thing it does, the way a single bot's would
be:

```
main.py        starts all five bots in one process; --check, --list
core.py        what every bot shares: the family bus and the ⚡ wallet (family_link),
               surviving a redeploy (lifecycle), messages that update in place
               (live_message), error codes (problems), payments, policies, flood control
               and logging (shared_features), files past the Bot API's limits (big_files),
               and prices (pricing)
bots.py        each bot's commands and conversations, and ManagerBot's monitoring
storage.py     each bot's database schema and queries; ManagerBot's family-wide reads
text.py        each public bot's English, Uzbek and Russian
stickers.py    resizing, WebM encoding, emoji, pack imports
convert.py     formats, the converters, the worker process, the queue
download.py    the provider chains, platform parsing, video muxing, image cards, the probe
anon.py        routing and the /export transcript
data/          created at run time: each bot's logs
LEGAL.md       privacy and terms for the four public bots
```

**A file is made of sections.** Each begins with a line like
`# ─── module: convert_bot.jobs`, and is a module of its own: ConvertBot's
`jobs`. A section named without a bot -- `# ─── module: family_link` -- is one
every bot has. `main.py` reads the sections, loads each bot's as a package of
its own -- `sticker_bot.db`, `anon_bot.db` -- and gives each bot's modules an
import and an environment of their own, so a bare `import db` inside StickerBot
means StickerBot's and a prefixed setting reaches only its bot. A shared
section is stored once and loaded once per bot. Tracebacks name the file and
the line, as for any other module. A file is never imported whole (the first
thing in each says so); the two programs the bots start -- ConvertBot's
conversion worker and the big-file transfer -- are started as
`python main.py --module convert_bot.convert_worker` and
`python main.py --module big_files`.

Every section is the base edition's module of the same name
(`MukhtorovMurodbek/MumuBots`), comments out and docstrings shortened, and
proven the same program by its syntax tree -- apart from a handful of edits
this edition needs, listed in `CHANGES_v<version>C.md`.

---

## Security

Do not open a public issue for a vulnerability. Use GitHub's private reporting
(**Security → Report a vulnerability**) or message the operator through a bot,
with what happens, the steps, and roughly when. In scope: anything that lets
somebody reach another user's files, messages or account id, act as another
user or reach an owner-only command, extract database contents, tokens or
environment variables, or make a bot fetch or run something it was not asked
to. Not in scope: deliberate rate limits, a bot refusing or failing on a
malformed file, and Telegram or third-party services themselves.

## Contributing

Issues and pull requests are welcome. A change should keep every bot working in
all three languages, keep `python main.py --check` passing, and say in its
description what it changes for the people using the bots.

## Licence

AGPL-3.0-or-later — see [LICENSE](LICENSE). Anybody who runs a modified
version as a network service has to offer its source to the people using it.
