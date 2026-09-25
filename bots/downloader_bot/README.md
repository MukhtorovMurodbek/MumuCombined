<img src="logo.svg" alt="DownloaderBot" width="72" align="right">

# DownloaderBot

A Telegram bot that downloads media from a pasted link and sends it back. No
command is needed — pasting a supported link is the whole interface.

| platform | what it returns |
|---|---|
| Instagram | Reels, photo posts and carousels |
| TikTok | Videos without the watermark, and photo slideshows |
| Twitter / X | Video and photos; a text-only post is rendered as an image card |
| Pinterest | The pin's image at full resolution, or its video. Video pins and idea pins both work, and an idea pin of several pages arrives as several files. Any country domain (`co.`, `in.`, `br.` …) and `pin.it` shortlinks are recognised. |
| Reddit | Media posts directly; text and link posts as an image card |

Runs as its own process, its own repository and its own deployment, and can
be run entirely standalone. It shares a Postgres database with four sibling
bots only in the sense that its tables live in a schema of their own inside
it (`DB_SCHEMA`); no other bot reads or writes them. The one shared area is
`family.*`, where the bot posts a heartbeat and any crash so a monitoring bot
can watch it — `FAMILY_BUS=off` disables that entirely.

---

## Where a download actually comes from

This is the part of the bot worth understanding before reading any of it.

Several of these sites decide what to serve partly from **where the request
comes from**. Every cloud host's addresses sit in published datacenter
ranges, and those ranges are served a login page where a residential
connection is served the post. A downloader that makes its requests from
inside its own container therefore works on a laptop and fails in
production, for reasons that look like bugs and are not.

So the bot does not have one way to fetch a link. Each platform has a
**chain of independent providers**, tried in order, and the chain remembers
what it learns:

- A provider that fails does not end the attempt; the next one is tried.
- Repeated failures move a provider to the back of its chain and rest it for
  a while, with the delay growing each time — rather than removing it, since
  most of these outages are temporary.
- A chain whose every member is resting still tries every member. "The site
  is slow today" and "the bot is broken" are different answers and only one
  of them is worth showing.
- Requests that go out from the container's own address are tried **last**,
  because that is the address these sites treat differently.

`/providers` prints what the chain currently believes, per platform, with
each provider's success and failure counts and its last error. `/probe`
actively tries every route against known-good sample posts and reports what
happened, which answers "is it broken, or was that one post private".

---

## Commands

| command | what it does |
|---|---|
| *(paste a link)* | Downloads it and sends it back |
| `/lossless on\|off` | Send downloads as files rather than as photos and videos. Telegram re-encodes anything sent as media — that compression is what makes it play inline, and there is no way to have both — so with this on the bytes arrive exactly as the source had them, at the cost of a tap to open. Off by default, remembered per user. A button under every finished download gets that one file the other way round without changing the setting. |
| `/caption on\|off` | Toggle the credit caption. |
| `/cancel` | Asks which of the things the bot is waiting on should stop, one button each. |
| `/donate` | Voluntary contribution towards hosting, paid in Telegram Stars. |
| `/start` | Instructions. The first `/start` from a new user asks which language to use, once. |
| `/language`, `/en`, `/uz`, `/rus` | Switch language. Each reprints the instructions in the language chosen. |
| `/help` | The instructions on their own. |
| `/privacy` | What the bot holds about the person asking, who else sees it, and how long it stays. |
| `/terms` | What the bot may be used for, and where the money stands. |
| `/deletemydata` | Erases what the bot holds about the person asking, after one confirmation. |

Restricted to the account ids in `DBOT_ADMIN_ID`, and answering everyone else
exactly as a misspelt command does: `/providers`, `/probe`,
`/messageas <user_id> <text>`, `/dbdump` and `/status`.

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

## Limits

This is the bot in its family with real resource spikes — a fetch, an
`ffmpeg` mux and an upload, all at once — so it is bounded on three axes:

- **Two downloads at a time** across the whole process, which is what stops
  ten links pasted in one minute from becoming ten simultaneous downloads.
- **One of those slots per person**, so nobody can hold both and leave
  everyone else queueing behind a stranger.
- **A rolling hourly and daily allowance per person**, counted in the
  database so a redeploy does not reset it. Anyone who has contributed
  through `/donate` gets a larger allowance, permanently and for any amount.

All three are configurable; see `.env.example`. Size and duration ceilings
stop a mis-pasted link to a three-hour stream before the first byte is
fetched.

---

## Running it

In this repository DownloaderBot runs alongside the other bots from the top-level
`bot.py`, and the [top-level README](../../README.md) covers installing,
configuring and deploying it. Its settings keep the names they have when it
runs alone; one that another bot also reads can be given to DownloaderBot only by
prefixing it with `DBOT_`.

---

## A note on scope

This bot downloads publicly accessible posts on behalf of the person asking
for them. It is not a way around a private account, and it does not attempt
to be. Whoever runs it is responsible for how it is used where they run it.

## Licence

AGPL-3.0-or-later — see [LICENSE](../../LICENSE).

This is the licence the AGPL'd PyMuPDF asks for, and §13 of it is the reason:
anybody who interacts with this software over a network must be offered its
source. A Telegram bot is exactly that case, since nobody using it ever holds
a copy. The source is here, which satisfies §13 for this deployment; anybody
running a modified version as a service has to publish their changes too.
