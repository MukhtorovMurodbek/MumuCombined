<img src="logo.svg" alt="ConvertBot" width="72" align="right">

# ConvertBot

A Telegram bot that converts files between formats: pictures, video, audio,
documents, e-books, spreadsheets and subtitles — around seventy-five formats
in, forty out, and some eight hundred combinations. Small files are free;
larger ones are priced in Telegram Stars, paid in the chat.

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
| `/convert` | Convert a file. Sending a file directly does the same thing; the command exists for people who look for one. |
| `/formats` | Every format the bot reads and writes, a category at a time. `/formats heic` answers for one format directly. |
| `/mystars` | That user's own Stars spending history with this bot. |
| `/cancel` | Asks which of the things the bot is waiting on should stop, one button each, and stops nothing until one is chosen. |
| `/donate` | Voluntary contribution towards hosting, paid in Telegram Stars. |
| `/start` | Instructions. The first `/start` from a new user asks which language to use, once. |
| `/language`, `/en`, `/uz`, `/rus` | Switch language. Each reprints the instructions in the language chosen. |
| `/help` | The instructions on their own. |
| `/privacy` | What the bot holds about the person asking, who else sees it, and how long it stays. |
| `/terms` | What the bot may be used for, and where the money stands. |
| `/deletemydata` | Erases what the bot holds about the person asking, after one confirmation. |

Restricted to the account ids in `CBOT_ADMIN_ID`, and answering everyone else
exactly as a misspelt command does: `/stars` (the whole Stars ledger — paid,
free and refunded), `/messageas <user_id> <text>`, `/dbdump` and `/status`.

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

## What it converts

| | reads | writes |
|---|---|---|
| **Pictures** | PNG, JPEG, WEBP, BMP, TIFF, ICO, HEIC/HEIF, AVIF, JPEG 2000, PSD, TGA, PCX, DDS, PPM, SGI, XBM, XPM, ICNS, QOI, BLP, SVG | PNG, JPEG, WEBP, **PDF**, ICO, TIFF, BMP, GIF, AVIF, HEIC, JPEG 2000, TGA, PPM, QOI, ICNS |
| **Video** | MP4, MOV, M4V, AVI, WEBM, MKV, FLV, WMV, TS, M2TS, MPEG, 3GP, OGV, ASF, GIF, APNG | MP4, WEBM, MKV, MOV, AVI, GIF, animated WEBP, APNG — and the audio on its own, in any audio format below |
| **Audio** | MP3, WAV, OGG, Opus, M4A, AAC, FLAC, AIFF, WMA, AMR, AC3, MP2, AU, CAF, W64, VOC | MP3, M4A, AAC, OGG, Opus, WAV, FLAC, AIFF, WMA, AC3 |
| **Documents** | PDF, DOCX, EPUB, MOBI, FB2, CBZ, XPS, Markdown, HTML, plain text | PDF, PNG, JPEG, WEBP, TIFF, SVG, plain text, HTML, Markdown |
| **Data** | CSV, TSV, JSON, YAML, XLSX, XML | JSON, CSV, TSV, YAML, XLSX, Markdown table, HTML table, PDF |
| **Subtitles** | SRT, VTT, ASS/SSA | SRT, VTT, ASS — or the transcript with the timings removed |

`/formats` says the same thing inside the chat, and answers for one format at
a time. What is offered is what the running host can actually do: the
document, e-book, spreadsheet and HEIC backends are optional dependencies,
and a format whose library is absent is left off the menu rather than failing
when somebody picks it.

Some combinations worth knowing about:

- An **iPhone photo** (HEIC) becomes a JPEG or a PNG.
- **Several pictures at once** become a single PDF, one to a page. Sending
  them as one album is enough; the bot collects the album and offers PDF for
  the set.
- A **PDF or an e-book** becomes pictures — one page as an image, several
  pages as a zip of them — or plain text.
- A **Word document** becomes a PDF, HTML or Markdown. The headings,
  emphasis, lists and tables carry; the page layout is re-flowed rather than
  copied exactly, and the bot says so on the file it sends back.
- A **CSV, JSON or XML export** becomes an XLSX spreadsheet, and a workbook
  becomes a CSV per sheet.
- **Subtitles** convert between SRT, VTT and ASS, or reduce to the transcript.

---

## How it works

**The flow.** A file arrives; the bot offers the formats it can be converted
to as buttons; one tap starts the conversion. Long lists open on the six most
asked-for and expand on request. Files under the free threshold convert
immediately. Above it, an invoice is sent first and the conversion starts once
it is paid.

**More than one file at a time.** A Telegram album arrives as separate
messages a fraction of a second apart. The bot waits for the rest of the album
before drawing a menu, so a set of pictures is one conversion — into a single
PDF, or into a zip of individually converted files — rather than one prompt
per picture.

**More than one file back.** A forty-page PDF converted to PNG is forty
files, and a Telegram message carries one document. The result is a zip in
that case, and the caption says how many are inside.

**Payment.** Telegram Stars, which need no payment provider and no merchant
account. Every invoice, payment and refund is recorded in a ledger, so
`/mystars` and `/stars` are reads rather than reconstructions. A conversion
that fails after payment is refunded automatically.

**Conversion.** Pillow for still pictures, `ffmpeg` for video, audio and
subtitles, PyMuPDF for documents and e-books, and the standard library with
`openpyxl` for structured data. Everything runs under a timeout, so a
pathological input cannot occupy the process indefinitely. The staged upload
is deleted whether the conversion succeeded or not.

**Limits.** The price is calculated from the file size, which is a poor proxy
for how much work a conversion is: a small PDF can be hundreds of pages and a
small GIF thousands of frames. So there are ceilings on the work itself —
pages rendered, frames encoded, spreadsheet rows and cells, files in one batch
— and a job over one of them is refused before an invoice is sent, not after.
A ceiling on updates per minute applies per account, before any handler runs,
so a script cannot hold the process busy. All configurable; see
`.env.example`.

**Untrusted files.** Every backend here parses a file a stranger chose. XML is
read with `defusedxml`, which refuses the entity expansion that turns a
fourteen-line upload into gigabytes of memory or a read of a local file; YAML
is read with `safe_load`, never `load`, which would construct arbitrary Python
objects named in the document; and images are decoded under a pixel ceiling
that turns a decompression bomb into a caught error rather than an
out-of-memory kill.

---

## Running it

In this repository ConvertBot runs alongside the other bots from the top-level
`bot.py`, and the [top-level README](../../README.md) covers installing,
configuring and deploying it. Its settings keep the names they have when it
runs alone; one that another bot also reads can be given to ConvertBot only by
prefixing it with `CBOT_`.

---

## Licence

AGPL-3.0-or-later — see [LICENSE](../../LICENSE).

This is the licence the AGPL'd PyMuPDF asks for, and §13 of it is the reason:
anybody who interacts with this software over a network must be offered its
source. A Telegram bot is exactly that case, since nobody using it ever holds
a copy. The source is here, which satisfies §13 for this deployment; anybody
running a modified version as a service has to publish their changes too.
