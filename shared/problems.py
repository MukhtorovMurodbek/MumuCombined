"""Every problem a person can run into in the family's bots, by code.

The owner asked for this in so many words: "Give every possible exception that
the user might trigger a code or a unique identifier", a "report the issue"
button beside it, and "a list or a dictionary that can decode this error
message with as much accuracy as possible." This file is that dictionary.

A CODE names a kind of problem and never changes once shipped, so a report
sent months later still decodes. An INCIDENT names one occurrence: it is made
when the message goes out, carried by the report button, and written to the
log beside what happened, so a report can be matched to its log line.

A code is shown at the end of a message as "🆔 CODE". i18n.t() appends that
line for every key in KEYS; a message assembled from several strings gets it
at its end, where it is assembled (ConvertBot's job endings, StickerBot's
sticker errors and imports, DownloaderBot's allowance message).
shared_features logs every message that ends in one, with its time and incident,
and puts a report button under the ones that are not SIMPLE. Every code also
has a LEVEL -- see the block above `reportable()` -- which decides whether the
owner hears about it now or in the nightly report.

Copied, not imported, into all five bots -- ManagerBot's /decode reads it.
Pure: no Telegram, no database, nothing that can fail at import.
"""
from __future__ import annotations

import re
import secrets
from collections import namedtuple

Problem = namedtuple("Problem", "bot title meaning causes check")

MARK = "🆔 "
CODE_RE = re.compile(r"^[A-Z]{2}(?:-[A-Z0-9]+)+$")
INCIDENT_RE = re.compile(r"^[A-HJ-NP-Z2-9]{6}$")
_INCIDENT_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# At the very end of a message, after a blank line -- possibly inside closing
# HTML tags, for the policy messages that are sent as HTML.
_AT_END = re.compile(r"\n\n🆔 ([A-Z]{2}(?:-[A-Z0-9]+)+)(?:</[a-z]+>)*\s*$")

EVERY_PUBLIC_BOT = "every public bot"

PROBLEMS = {
    # ---- every public bot ----------------------------------------------------
    "FM-CRASH": Problem(
        EVERY_PUBLIC_BOT, "The bot crashed while handling a message",
        "A handler raised an exception nothing caught. The request was not done; the person was told so "
        "and offered a report.",
        "A bug in that handler; the shared database unreachable or timing out; Telegram rejecting a call in "
        "a way the code does not expect (a changed API, editing a message that was deleted).",
        "Search the bot's log for the incident id: the traceback is logged beside it. /events and the crash "
        "alert name the exception type; /status shows whether errors are piling up."),
    "FM-FLOOD": Problem(
        EVERY_PUBLIC_BOT, "Too many updates from one person",
        "One person sent more than FLOOD_UPDATES_PER_MINUTE updates (40 by default) inside a minute; the rest "
        "were ignored until the window cleared.",
        "Tapping buttons very fast, a client resending, forwarding a big selection outside /export, or a script.",
        "Usually nothing. If ordinary use trips it, raise FLOOD_UPDATES_PER_MINUTE on that bot."),
    "FM-DONATE-CURRENCY": Problem(
        EVERY_PUBLIC_BOT, "Unknown currency in /donate or /recharge",
        "The command named a currency the bot does not offer.",
        "A typo, or a currency that was never configured.",
        "Nothing, unless people keep asking for a currency that should be added to FIAT_CURRENCIES."),
    "FM-DONATE-UNAVAILABLE": Problem(
        EVERY_PUBLIC_BOT, "Currency offered but not set up",
        "The currency is known, but its payment provider token is missing, so no invoice can be made.",
        "The provider token environment variable is not set on this bot.",
        "Set that currency's provider token, or stop offering it."),
    "FM-DONATE-AMOUNT": Problem(
        EVERY_PUBLIC_BOT, "Invalid payment amount",
        "The amount was not a positive whole number, or a button carried an amount the bot never offered.",
        "A typo in /donate or /recharge; an old or tampered button.",
        "Nothing, unless it happens with the bot's own buttons -- then the offered amounts and the handler "
        "disagree (DONATE_STAR_OPTIONS)."),
    "FM-DONATE-TOO-MANY": Problem(
        EVERY_PUBLIC_BOT, "Payment above the per-payment limit",
        "The Stars amount was above MAX_DONATION_STARS.",
        "A large custom amount.",
        "Raise MAX_DONATION_STARS if larger single payments are wanted."),
    "FM-DONATE-RANGE": Problem(
        EVERY_PUBLIC_BOT, "Card payment outside the allowed range",
        "A fiat amount was below that currency's minimum or above its maximum.",
        "An amount outside the provider's limits.",
        "Correct the currency's limits in FIAT_CURRENCIES if they are wrong."),
    "FM-INVOICE": Problem(
        EVERY_PUBLIC_BOT, "Telegram refused to create an invoice",
        "send_invoice failed. The payment row was marked failed and nothing was charged.",
        "An amount Telegram rejects, a provider token that stopped working, or Telegram having a problem.",
        "The error Telegram returned is in the message and in the log at that time; check the provider token "
        "and the amount."),
    "FM-ERASE": Problem(
        EVERY_PUBLIC_BOT, "/deletemydata failed",
        "Erasing the person's data raised an error, so nothing was erased and they were asked to try again.",
        "The database unreachable, or a table the erase does not expect.",
        "The traceback is in the log; tests/erase_scenarios.py reproduces erasing against a real database."),
    "FM-UPDATING": Problem(
        EVERY_PUBLIC_BOT, "The bot is paused for an update",
        "New work was refused because an update is about to be deployed (/pause in ManagerBot).",
        "An announced update window, or a pause that was never lifted.",
        "If no update is under way, lift it with /finishupdates in ManagerBot."),
    "FM-UNKNOWN-COMMAND": Problem(
        EVERY_PUBLIC_BOT, "Unknown command",
        "A slash command this bot does not have.",
        "A typo, a command from an older version, or one that belongs to another bot.",
        "Nothing, unless an old command should be kept working as an alias."),

    # ---- ConvertBot --------------------------------------------------------------
    "CV-NO-EXTENSION": Problem(
        "ConvertBot", "File name without a usable extension",
        "The format could not be told from the file's name, so nothing was downloaded or charged.",
        "A file sent without an extension, or with one the bot does not recognise.",
        "Nothing, unless a common extension is missing from formats.ALIASES."),
    "CV-TG-LIMIT": Problem(
        "ConvertBot", "File larger than a bot may download",
        "Telegram declared the file larger than MAX_FILE_MB; the cloud Bot API lets a bot download 20 MB at most.",
        "A large file. Only a local Bot API server (LOCAL_BOT_API_URL) lifts this.",
        "Nothing on the cloud API; the local Bot API server is planned for 1.7.0."),
    "CV-DOWNLOAD": Problem(
        "ConvertBot", "Downloading the file from Telegram failed",
        "get_file or the download raised, so nothing was converted and nothing charged.",
        "A network error, Telegram timing out, or the file no longer being available.",
        "The error text is in the message and the log; repeated failures point at the host's network."),
    "CV-UNSUPPORTED": Problem(
        "ConvertBot", "Format not converted",
        "The source format, or the target that was chosen, is not one this server can convert.",
        "An unsupported file; an old menu offering a format no longer available; a converter missing on this host.",
        "/formats on the bot; the startup log line 'Converters available' lists what was found."),
    "CV-TOO-BIG": Problem(
        "ConvertBot", "File over ConvertBot's size limit",
        "The file is larger than MAX_FILE_MB, so it was refused before anything was charged.",
        "A large file.",
        "CONVERT_MAX_FILE_MB, within what the Bot API allows."),
    "CV-NO-TARGETS": Problem(
        "ConvertBot", "Nothing this file can become",
        "The format is readable, but no target format is available for it on this server.",
        "A converter library or an ffmpeg encoder missing on the host.",
        "The startup log line 'Converters available'; requirements.txt and nixpacks.toml."),
    "CV-NOTHING-SENDABLE": Problem(
        "ConvertBot", "Every result would be too big to send",
        "For a picture this large, every offered format would come out over the 50 MB a bot may send, so "
        "nothing was offered or charged.",
        "A very high-resolution image.",
        "Nothing; a local Bot API server raises the send limit."),
    "CV-MEGAPIXELS": Problem(
        "ConvertBot", "Picture over the megapixel limit",
        "The image is larger than CONVERT_MAX_MEGAPIXELS, above which one decode needs more memory than the "
        "container has. Nothing was charged.",
        "A very high-resolution image.",
        "Raise CONVERT_MAX_MEGAPIXELS only together with the container's memory."),
    "CV-FORMAT-TOO-BIG": Problem(
        "ConvertBot", "That format would be too big to send",
        "A format was tapped whose result is estimated over the send limit, usually from an old menu.",
        "An old menu, or a size estimate that changed.",
        "jobs.unsendable_targets and LOSSLESS_BYTES_PER_PIXEL in jobs.py."),
    "CV-STORAGE-USER": Problem(
        "ConvertBot", "Person over their temporary storage share",
        "Files waiting, or kept for more formats, already use CONVERT_USER_STORAGE_MB for this person.",
        "Several large files kept at once.",
        "Nothing, unless the share is too small for real albums."),
    "CV-STORAGE-FULL": Problem(
        "ConvertBot", "Server short of temporary space",
        "Taking the file would leave less than CONVERT_MIN_FREE_MB free, or push everyone's files over "
        "CONVERT_STORAGE_MB.",
        "Many large conversions at once, or files left behind that the sweep has not removed yet.",
        "Disk use on the container; the sweep lines in the log ('Swept ... abandoned upload(s)')."),
    "CV-QUEUE-FULL": Problem(
        "ConvertBot", "Too many conversions waiting",
        "The person already has CONVERT_MAX_QUEUED_PER_USER conversions queued or running.",
        "Many formats chosen quickly.",
        "Nothing, unless the limit is too low for real use."),
    "CV-EXPIRED": Problem(
        "ConvertBot", "The file is no longer waiting",
        "A format was chosen for a file whose pending state is gone.",
        "More than CONVERT_PENDING_TTL_SECONDS since the file was sent, a restart, or the file already converted.",
        "Nothing, unless it happens within minutes of sending -- then pending state is being lost."),
    "CV-JOB-GONE": Problem(
        "ConvertBot", "That conversion has already finished",
        "Stop was tapped for a conversion that had already ended.",
        "Tapping Stop just as it finished.",
        "Nothing."),
    "CV-NO-CREDIT": Problem(
        "ConvertBot", "Balance did not cover the conversion when it started",
        "When the conversion reached the front of the queue the balance was below its price, so it did not run "
        "and nothing was charged.",
        "Credit spent on another conversion meanwhile, or bonus credit that expired while it waited.",
        "/balance <id> in ManagerBot shows the ledger if the person disputes it."),
    "CV-UNKNOWN-ORDER": Problem(
        "ConvertBot", "Payment for an order the bot does not know",
        "A pre-checkout query carried a payload that is neither a conversion nor a top-up; it was declined "
        "before anything was charged.",
        "A very old invoice, or an invoice made by another deployment of the bot.",
        "The payload is in the log; nothing was charged."),
    "CV-MIXED-BATCH": Problem(
        "ConvertBot", "Album of different formats",
        "Files sent together had different formats, which one conversion cannot take.",
        "A photo and a video in one album.",
        "Nothing."),
    "CV-UNRECOGNIZED": Problem(
        "ConvertBot", "Not something ConvertBot can use",
        "A message that is neither a file nor a format name.",
        "Text, a sticker or other media sent to ConvertBot.",
        "Nothing."),
    "CV-REFUSED": Problem(
        "ConvertBot", "The converter could not convert this file",
        "The worker raised ConversionError: the file could not be read or converted as asked. Its ⚡ went back "
        "to the balance.",
        "A damaged or unusual file, or something the converter does not support (an encrypted PDF, an unusual "
        "codec).",
        "The converter's own message is in the log beside the incident id."),
    "CV-TIMEOUT": Problem(
        "ConvertBot", "Conversion ran past its time limit",
        "The worker was still running at CONVERT_TIME_LIMIT_SECONDS (60 s for a free conversion) and was killed. "
        "Its ⚡ went back to the balance and the owner was alerted.",
        "A very large or complex file (a long video, many pages), a slow encoder such as AVIF, or a host short "
        "of CPU.",
        "The owner alert gives size, formats and run time; compare with /usage for CPU pressure at that time."),
    "CV-CRASH": Problem(
        "ConvertBot", "The conversion worker crashed",
        "The worker process died without a result -- most often killed for memory. Its ⚡ went back to the "
        "balance and the owner was alerted.",
        "An out-of-memory kill on a very large image, or a crash inside a native decoder.",
        "The log line beside the incident id has the exit code (-9 or 137 means killed); /usage shows memory."),
    "CV-OUTPUT-TOO-BIG": Problem(
        "ConvertBot", "The result was over the 50 MB send limit",
        "The conversion finished, but the file is larger than a bot may send. Its ⚡ went back to the balance "
        "and the owner was alerted.",
        "A lossless or high-resolution target (PNG, TIFF, GIF) for a large input.",
        "If one format keeps doing this, add it to the unsendable estimates in jobs.py."),
    "CV-SEND-FAILED": Problem(
        "ConvertBot", "Sending the result failed",
        "The file was converted but uploading it to the person failed. Its ⚡ went back to the balance and the "
        "owner was alerted.",
        "Telegram rejecting the upload, a network error or timeout, or the person having blocked the bot.",
        "The exception type and text are in the owner alert and the log."),
    "CV-RESTARTED": Problem(
        "ConvertBot", "The bot restarted during the conversion",
        "The process stopped while the conversion was running. Its ⚡ went back to the balance.",
        "A redeploy, a manual restart, or the container being killed.",
        "The deploy history at that time, and /events for the restart."),

    # ---- DownloaderBot ------------------------------------------------------------
    "DL-QUOTA-HOUR": Problem(
        "DownloaderBot", "Hourly download limit reached",
        "The person has used their downloads for the last hour.",
        "Heavy use.",
        "The hourly allowance settings; people who have donated get a higher one."),
    "DL-QUOTA-DAY": Problem(
        "DownloaderBot", "Daily download limit reached",
        "The person has used their downloads for the day.",
        "Heavy use.",
        "The daily allowance settings; people who have donated get a higher one."),
    "DL-QUEUE-FULL": Problem(
        "DownloaderBot", "Too many links waiting",
        "The person already has DBOT_MAX_PENDING_PER_USER links in progress.",
        "Many links sent at once.",
        "Nothing, unless the limit is too low."),
    "DL-NO-SPACE": Problem(
        "DownloaderBot", "Server short of temporary space",
        "Free disk was below DBOT_MIN_FREE_MB, so the download did not start.",
        "Several large downloads at once, or files left behind.",
        "Disk use on the container."),
    "DL-DELIVERY": Problem(
        "DownloaderBot", "Sending the downloaded file failed",
        "The media was fetched, but uploading it to Telegram failed.",
        "A file over Telegram's limit after all, a network error, or Telegram rejecting the media.",
        "The provider and exception are in the log ('Delivering ... failed')."),
    "DL-BLOCKED": Problem(
        "DownloaderBot", "The site refused every route",
        "Every provider was refused by the platform: blocked, rate limited, or asked to log in.",
        "The platform limiting the server's IP, expired cookies, or a change on the platform.",
        "/providers and /probe in ManagerBot show which routes are failing."),
    "DL-NOT-FOUND": Problem(
        "DownloaderBot", "Post not found",
        "The platform says the post does not exist or is not public.",
        "A deleted post, a private account, or a mistyped link.",
        "Nothing, unless public posts come back as missing -- then a resolver is misreading the page."),
    "DL-TOO-BIG": Problem(
        "DownloaderBot", "Media over what Telegram allows",
        "The media is larger than a bot may send.",
        "A long, high-quality video.",
        "Nothing on the cloud API."),
    "DL-ALL-ROUTES": Problem(
        "DownloaderBot", "Every download route failed",
        "Every provider in the chain failed, for a reason other than blocked, missing or too big.",
        "Provider outages, a platform change that broke the resolvers, or network trouble.",
        "/providers for failure counts; the per-provider log lines; tests/test_resolvers.py."),
    "DL-REDDIT": Problem(
        "DownloaderBot", "Reddit post could not be fetched",
        "Reading the Reddit post's data failed.",
        "Reddit rate limiting, or a changed response.",
        "The error text in the message and the log."),
    "DL-TWITTER-CARD": Problem(
        "DownloaderBot", "X/Twitter post content unavailable",
        "The post's content could not be fetched, so only the link was sent back.",
        "X blocking the routes, or a changed page.",
        "/providers for the X routes."),
    "DL-UNRECOGNIZED": Problem(
        "DownloaderBot", "Not a supported link",
        "The message was not a link from a supported platform.",
        "Text, or a link from an unsupported platform.",
        "Nothing, unless a supported platform's link format changed (platforms.detect_platform)."),
    "DL-BUTTON-EXPIRED": Problem(
        "DownloaderBot", "Re-send button too old",
        "The compressed/uncompressed button refers to a download that is no longer remembered.",
        "An old message, or a restart.",
        "Nothing."),

    # ---- StickerBot ----------------------------------------------------------------
    "ST-WHOMADE-UNKNOWN": Problem(
        "StickerBot", "Pack not made through this bot",
        "/whomade found no record of the pack.",
        "A pack made elsewhere, or a mistyped name or link.",
        "Nothing."),
    "ST-COEDIT-LINK": Problem(
        "StickerBot", "Co-editing link not valid",
        "The link's token matches no pack.",
        "The owner reset the link, or it was mistyped.",
        "Nothing."),
    "ST-COEDIT-GONE": Problem(
        "StickerBot", "Pack no longer exists",
        "The pack a co-editing link points at has no owner on record.",
        "The pack was deleted.",
        "Nothing."),
    "ST-NOT-YOURS": Problem(
        "StickerBot", "Not the person's pack",
        "A pack button was tapped by someone who does not own the pack.",
        "A forwarded menu, or an old button.",
        "Nothing."),
    "ST-OWNER-ONLY": Problem(
        "StickerBot", "Only the pack's owner can do that",
        "Renaming, co-editing settings and deleting belong to the pack's owner.",
        "A co-editor tapping an owner's button.",
        "Nothing."),
    "ST-RENAME-STATE": Problem(
        "StickerBot", "Rename lost track of the pack",
        "A new name arrived, but the pack it was meant for is no longer known.",
        "A restart, or a long gap between tapping Rename and sending the name.",
        "Nothing, unless it is frequent -- then state is being lost."),
    "ST-RENAME-FAILED": Problem(
        "StickerBot", "Telegram refused the rename",
        "set_sticker_set_title raised.",
        "A title Telegram rejects, the pack deleted meanwhile, or a network error.",
        "The error text is in the message and the log."),
    "ST-DELETE-FAILED": Problem(
        "StickerBot", "Telegram refused to delete the pack",
        "delete_sticker_set raised.",
        "The pack already deleted, or a network error.",
        "The error text is in the message and the log."),
    "ST-TITLE-EMPTY": Problem(
        "StickerBot", "Empty pack name",
        "The name sent was empty once trimmed.",
        "Whitespace, or an empty message.",
        "Nothing."),
    "ST-REMOVE-FAILED": Problem(
        "StickerBot", "Removing a sticker failed",
        "delete_sticker_from_set raised.",
        "The sticker already gone, or a network error.",
        "The error text is in the message and the log."),
    "ST-IMAGE": Problem(
        "StickerBot", "Picture could not be made into a sticker",
        "Processing the image raised.",
        "A damaged or unusual image file.",
        "The error text in the message and the log."),
    "ST-VIDEO-CONVERT": Problem(
        "StickerBot", "Video could not be made into a sticker",
        "The video could not be encoded into a sticker Telegram accepts.",
        "A clip too long or too detailed to fit 256 KB, an empty file, or ffmpeg missing on the host.",
        "The reason is the first line of the message; the startup log says whether ffmpeg was found."),
    "ST-VIDEO-FAILED": Problem(
        "StickerBot", "Video conversion crashed",
        "An unexpected error while converting a video.",
        "A bug, or an unusual file.",
        "The traceback in the log ('Video conversion failed')."),
    "ST-ANIMATED": Problem(
        "StickerBot", "Animated (Lottie) sticker not supported",
        "A .tgs animated sticker was sent, which the bot cannot copy.",
        "An animated sticker.",
        "Nothing."),
    "ST-IMPORT-SOURCE": Problem(
        "StickerBot", "Not a sticker pack name or link",
        "/import was given something that is neither a pack name nor a t.me/addstickers link.",
        "A typo.",
        "Nothing."),
    "ST-IMPORT": Problem(
        "StickerBot", "Import could not read the pack",
        "Importing failed: the Telegram pack was not found, or the WhatsApp archive was not a valid .zip or had "
        "no usable images.",
        "A private or mistyped pack name, or a damaged or unexpected archive.",
        "The message says which; nothing to do unless valid packs fail (import_utils.py)."),
    "ST-TG-TIMEOUT": Problem(
        "StickerBot", "Telegram did not confirm in time",
        "Adding a sticker timed out; it may have been added anyway.",
        "A slow upload, most often a video sticker.",
        "Nothing, unless constant -- then the host's network."),
    "ST-TG-BAD-NAME": Problem(
        "StickerBot", "Telegram rejected the pack's internal name",
        "The generated set name was invalid.",
        "A title starting with a digit or a symbol.",
        "Nothing; the message explains the workaround."),
    "ST-TG-NAME-TAKEN": Problem(
        "StickerBot", "Pack name already taken",
        "The generated set name collided with an existing pack.",
        "Chance.",
        "Nothing."),
    "ST-TG-PACK-FULL": Problem(
        "StickerBot", "Pack is full",
        "The pack reached Telegram's sticker limit (120).",
        "A full pack.",
        "Nothing."),
    "ST-TG-BAD-FORMAT": Problem(
        "StickerBot", "Telegram rejected the sticker file",
        "The prepared file was not accepted for this pack.",
        "A format mismatch, such as a video sticker into an older static pack.",
        "The Telegram error text in the log."),
    "ST-TG-REJECTED": Problem(
        "StickerBot", "Telegram rejected the sticker",
        "Adding a sticker failed with an error the bot has no specific explanation for.",
        "Any other Telegram API error.",
        "The Telegram error text is in the message and the log."),
    "ST-UNRECOGNIZED": Problem(
        "StickerBot", "Message not understood",
        "Something StickerBot has no use for outside a pack session.",
        "Text or media sent without starting a pack.",
        "Nothing."),
    "ST-NOTHING-ADDED": Problem(
        "StickerBot", "/done with nothing added",
        "/done was sent before any sticker was added.",
        "Finishing too early.",
        "Nothing."),
    "ST-NO-STICKER": Problem(
        "StickerBot", "Emoji with no sticker to tag",
        "An emoji arrived before any sticker was added in this session.",
        "Sending the emoji first.",
        "Nothing."),
    "ST-RETAG": Problem(
        "StickerBot", "Changing the emoji failed",
        "set_sticker_emoji_list raised.",
        "The sticker removed meanwhile, or a network error.",
        "The error text is in the message and the log."),

    # ---- AnonBot ---------------------------------------------------------------------
    "AN-LINK-INVALID": Problem(
        "AnonBot", "Inbox link not valid",
        "The link's token matches no inbox.",
        "The owner reset the link, or it was mistyped.",
        "Nothing."),
    "AN-LINK-BLOCKED": Problem(
        "AnonBot", "Blocked by the inbox owner",
        "The person who opened the link is on the owner's block list.",
        "The owner blocked them.",
        "Nothing."),
    "AN-LINK-PAUSED": Problem(
        "AnonBot", "Inbox paused",
        "The owner has paused new conversations.",
        "/pause by the owner.",
        "Nothing."),
    "AN-INBOX-GONE": Problem(
        "AnonBot", "Inbox no longer exists",
        "The owner's inbox is gone, usually through /deletemydata.",
        "The owner erased their data.",
        "Nothing."),
    "AN-SENDER-BLOCKED": Problem(
        "AnonBot", "Message not delivered: blocked",
        "The guest is blocked by the owner, so the message was not relayed.",
        "The owner blocked this guest.",
        "Nothing."),
    "AN-NOT-STARTED": Problem(
        "AnonBot", "Recipient has not started the bot",
        "Telegram refused the delivery (Forbidden).",
        "The recipient never started the bot, or has blocked it.",
        "Nothing."),
    "AN-DELIVERY": Problem(
        "AnonBot", "Relaying the message failed",
        "Telegram rejected the copy for another reason (BadRequest).",
        "An unsupported message type, an oversized caption, or a changed API.",
        "The error text is in the message and the log ('Failed relaying follower message')."),
    "AN-REPLY-NO-MATCH": Problem(
        "AnonBot", "Reply resolved to someone else's conversation",
        "A reply matched a conversation the sender does not own; it was not sent.",
        "Should not happen -- relay rows are written per chat.",
        "The anon_relay rows for that chat; tests/anon_scenarios.py group P checks the pairing."),
    "AN-NEEDS-REPLY": Problem(
        "AnonBot", "Message did not say which conversation",
        "A message that was not a reply arrived while conversations are open.",
        "Typing without swiping to reply.",
        "Nothing."),
    "AN-OPENING-NEEDS-REPLY": Problem(
        "AnonBot", "First message has to answer the opening line",
        "The conversation a link tap opened has not started, and something else arrived in between.",
        "A message from another conversation arriving after the tap.",
        "Nothing."),
    "AN-AMBIGUOUS": Problem(
        "AnonBot", "Several conversations open, none named",
        "A message without a reply while several conversations are open.",
        "Typing without replying.",
        "Nothing."),
    "AN-REPLY-BLOCKED": Problem(
        "AnonBot", "Reply not delivered: guest unavailable",
        "Telegram refused the owner's reply (Forbidden).",
        "The guest blocked the bot or deleted their account.",
        "Nothing."),
    "AN-REPLY-FAILED": Problem(
        "AnonBot", "Relaying the reply failed",
        "Telegram rejected the owner's reply for another reason.",
        "An unsupported message type or an oversized caption.",
        "The error text is in the message and the log ('Failed relaying owner reply')."),
    "AN-REPLY-STALE": Problem(
        "AnonBot", "Reply to a message with no record",
        "The replied-to message is in no tracked conversation.",
        "A reply to the person's own message, to a bot notice, or to a message older than RELAY_RETENTION_DAYS.",
        "Nothing."),
    "AN-TOO-FAST": Problem(
        "AnonBot", "Messages sent too fast",
        "More than ABOT_MSGS_PER_MINUTE messages inside a minute.",
        "Rapid sending, or a script.",
        "Raise ABOT_MSGS_PER_MINUTE if ordinary use trips it."),
    "AN-EDIT-NOT-RELAYED": Problem(
        "AnonBot", "Edits are not relayed",
        "An already relayed message was edited; the other side still has the original.",
        "Editing after sending.",
        "Nothing."),
    "AN-CONV-GONE": Problem(
        "AnonBot", "Conversation no longer on record",
        "A conversation button refers to a conversation that was not found or is not the person's.",
        "An old button, or /deletemydata.",
        "Nothing."),
    "AN-NOT-YOURS": Problem(
        "AnonBot", "Not the person's conversation",
        "A button was tapped for a conversation the tapper is not part of.",
        "A forwarded message with buttons.",
        "Nothing."),
    "AN-NO-ANCHOR": Problem(
        "AnonBot", "Conversation start no longer available",
        "Jumping to the start is impossible because the records of its messages were pruned.",
        "More than RELAY_RETENTION_DAYS of silence in the conversation.",
        "Nothing."),
    "AN-WHICH-UNKNOWN": Problem(
        "AnonBot", "Message belongs to no open conversation",
        "/which or /archive was used on a message with no conversation.",
        "The person's own old message, or an archived conversation.",
        "Nothing."),
    "AN-ARCHIVE-OWNER-ONLY": Problem(
        "AnonBot", "Only the inbox owner archives",
        "A guest tried to archive a conversation.",
        "A guest using the owner's command.",
        "Nothing."),
    "AN-EXPORT-FAILED": Problem(
        "AnonBot", "Building the document failed",
        "Reading the conversation or rendering the page failed; nothing was sent and nothing was kept.",
        "A bug, the database failing during the relay lookup, or Telegram refusing every forward.",
        "The traceback beside 'Could not build a transcript' in the log."),
    "AN-EXPORT-GONE": Problem(
        "AnonBot", "That conversation is no longer on record",
        "A conversation chosen for export had no relay rows left by the time the button was tapped.",
        "prune_old_data clearing a long-silent conversation, or /cancel removing it, between the "
        "menu being drawn and the button being tapped.",
        "Nothing. RELAY_RETENTION_DAYS is what decides how long a conversation stays exportable."),
    "AN-EXPORT-NOTHING": Problem(
        "AnonBot", "Nothing to export",
        "/export was sent by somebody with no conversation on record in this chat.",
        "Never having used an inbox link in either direction, or every conversation being older "
        "than RELAY_RETENTION_DAYS.",
        "Nothing."),
    "AN-UNADDRESSED": Problem(
        "AnonBot", "Message with nowhere to go",
        "A message from somebody with no inbox and no open conversation.",
        "Writing to the bot without having tapped a link.",
        "Nothing."),
}

# i18n key -> code. "shared" applies to every public bot unless the bot's own
# table overrides the key.
KEYS = {
    "shared": {
        "crash_notice": "FM-CRASH",
        "flood_wait": "FM-FLOOD",
        "donate_unknown_currency": "FM-DONATE-CURRENCY",
        "donate_currency_not_configured": "FM-DONATE-UNAVAILABLE",
        "donate_invalid_amount": "FM-DONATE-AMOUNT",
        "donate_invalid_amount_retry": "FM-DONATE-AMOUNT",
        "donate_too_many_stars": "FM-DONATE-TOO-MANY",
        "donate_out_of_range": "FM-DONATE-RANGE",
        "donate_invoice_error": "FM-INVOICE",
        "delete_data_failed": "FM-ERASE",
        "update_soon_try_later": "FM-UPDATING",
        "update_soon_try_later_soon": "FM-UPDATING",
        "unknown_command": "FM-UNKNOWN-COMMAND",
    },
    "convert_bot": {
        "unknown_extension": "CV-NO-EXTENSION",
        "file_too_large_download": "CV-TG-LIMIT",
        "download_failed": "CV-DOWNLOAD",
        "unsupported_format": "CV-UNSUPPORTED",
        "file_too_large_convert": "CV-TOO-BIG",
        "no_target_formats": "CV-NO-TARGETS",
        "nothing_sendable": "CV-NOTHING-SENDABLE",
        "too_many_megapixels": "CV-MEGAPIXELS",
        "too_big_to_send_alert": "CV-FORMAT-TOO-BIG",
        "storage_full_user": "CV-STORAGE-USER",
        "storage_full_global": "CV-STORAGE-FULL",
        "queue_full": "CV-QUEUE-FULL",
        "conversion_expired": "CV-EXPIRED",
        "job_not_running": "CV-JOB-GONE",
        "job_no_credit": "CV-NO-CREDIT",
        "unknown_order": "CV-UNKNOWN-ORDER",
        "batch_mixed_formats": "CV-MIXED-BATCH",
        "unrecognized_message": "CV-UNRECOGNIZED",
    },
    "downloader_bot": {
        "download_queue_full": "DL-QUEUE-FULL",
        "download_short_on_space": "DL-NO-SPACE",
        "download_failed": "DL-DELIVERY",
        "download_blocked": "DL-BLOCKED",
        "download_missing": "DL-NOT-FOUND",
        "download_too_big": "DL-TOO-BIG",
        "download_all_routes_failed": "DL-ALL-ROUTES",
        "reddit_fetch_failed": "DL-REDDIT",
        "twitter_fetch_failed_link": "DL-TWITTER-CARD",
        "unrecognized_message": "DL-UNRECOGNIZED",
        "redeliver_expired": "DL-BUTTON-EXPIRED",
    },
    "sticker_bot": {
        "whomade_not_found": "ST-WHOMADE-UNKNOWN",
        "coedit_link_invalid": "ST-COEDIT-LINK",
        "coedit_pack_gone": "ST-COEDIT-GONE",
        "not_your_pack": "ST-NOT-YOURS",
        "only_owner_coedit": "ST-OWNER-ONLY",
        "only_owner_rename": "ST-OWNER-ONLY",
        "only_owner_delete": "ST-OWNER-ONLY",
        "rename_broken_state": "ST-RENAME-STATE",
        "renamed_failed": "ST-RENAME-FAILED",
        "delete_failed": "ST-DELETE-FAILED",
        "title_empty": "ST-TITLE-EMPTY",
        "remove_failed": "ST-REMOVE-FAILED",
        "image_process_failed": "ST-IMAGE",
        "video_convert_failed_redirect": "ST-VIDEO-CONVERT",
        "video_convert_generic_failed": "ST-VIDEO-FAILED",
        "animated_not_supported": "ST-ANIMATED",
        "import_invalid_source": "ST-IMPORT-SOURCE",
        "unrecognized": "ST-UNRECOGNIZED",
        "nothing_added_yet": "ST-NOTHING-ADDED",
        "no_sticker_to_tag": "ST-NO-STICKER",
        "retag_failed": "ST-RETAG",
    },
    "anon_bot": {
        "follow_link_invalid": "AN-LINK-INVALID",
        "follow_link_blocked": "AN-LINK-BLOCKED",
        "follow_link_paused": "AN-LINK-PAUSED",
        "inbox_gone": "AN-INBOX-GONE",
        "delivery_blocked": "AN-SENDER-BLOCKED",
        "delivery_forbidden": "AN-NOT-STARTED",
        "delivery_failed": "AN-DELIVERY",
        "reply_no_match": "AN-REPLY-NO-MATCH",
        "must_reply": "AN-NEEDS-REPLY",
        "must_reply_opening": "AN-OPENING-NEEDS-REPLY",
        "must_reply_ambiguous": "AN-AMBIGUOUS",
        "reply_forbidden": "AN-REPLY-BLOCKED",
        "reply_failed": "AN-REPLY-FAILED",
        "reply_stale": "AN-REPLY-STALE",
        "too_fast": "AN-TOO-FAST",
        "edit_not_relayed": "AN-EDIT-NOT-RELAYED",
        "conv_gone": "AN-CONV-GONE",
        "not_your_conversation": "AN-NOT-YOURS",
        "jump_no_anchor": "AN-NO-ANCHOR",
        "which_unknown": "AN-WHICH-UNKNOWN",
        "archive_not_owner": "AN-ARCHIVE-OWNER-ONLY",
        "export_failed": "AN-EXPORT-FAILED",
        "export_gone": "AN-EXPORT-GONE",
        "export_nothing_to_export": "AN-EXPORT-NOTHING",
        "generic_nudge": "AN-UNADDRESSED",
    },
}

# Codes a message is given where it is assembled, not by i18n.t().
JOB_ENDINGS = {
    "refused": "CV-REFUSED", "timeout": "CV-TIMEOUT", "crash": "CV-CRASH",
    "too_large": "CV-OUTPUT-TOO-BIG", "send_failed": "CV-SEND-FAILED", "interrupted": "CV-RESTARTED",
}
STICKER_ERRORS = {
    "err_timed_out": "ST-TG-TIMEOUT", "err_invalid_name": "ST-TG-BAD-NAME", "err_name_occupied": "ST-TG-NAME-TAKEN",
    "err_too_many_stickers": "ST-TG-PACK-FULL", "err_bad_format": "ST-TG-BAD-FORMAT", "err_generic": "ST-TG-REJECTED",
}
ASSEMBLED = set(JOB_ENDINGS.values()) | set(STICKER_ERRORS.values()) | {"ST-IMPORT", "DL-QUOTA-HOUR", "DL-QUOTA-DAY"}

# Keys shown in a pop-up rather than a message: they carry the code, cannot
# carry a button, and must stay within Telegram's 200 characters.
ALERT_KEYS = {
    "shared": {"flood_wait", "donate_invalid_amount"},
    "convert_bot": {"unsupported_format", "conversion_expired", "too_big_to_send_alert", "queue_full",
                    "job_not_running", "unknown_order"},
    "downloader_bot": {"redeliver_expired"},
    "sticker_bot": {"not_your_pack", "only_owner_coedit", "only_owner_rename", "only_owner_delete"},
    "anon_bot": {"conv_gone", "not_your_conversation", "export_ended", "export_nothing_yet"},
}


# Problems that get no Report button. The owner, about one under "I don't
# recognize that command": "not every command needs a report button ... this
# one is simple." These are the refusals that explain themselves and that the
# person can act on -- their own typo, a limit they have reached, a button that
# has expired or is somebody else's, the other side's choice -- where nothing
# on the bot's side is wrong. They keep their code, and every one is still
# logged with its time and incident. Everything else gets the button: a crash,
# a failed download, conversion or send, Telegram refusing something the bot
# prepared, or the bot's own configuration. A new code is one or the other on
# purpose; tests/test_problems.py lists both halves so neither grows by default.
SIMPLE = frozenset({
    "FM-FLOOD", "FM-DONATE-CURRENCY", "FM-DONATE-AMOUNT", "FM-DONATE-TOO-MANY", "FM-DONATE-RANGE",
    "FM-UPDATING", "FM-UNKNOWN-COMMAND",
    "CV-NO-EXTENSION", "CV-TG-LIMIT", "CV-UNSUPPORTED", "CV-TOO-BIG", "CV-NOTHING-SENDABLE",
    "CV-MEGAPIXELS", "CV-FORMAT-TOO-BIG", "CV-STORAGE-USER", "CV-QUEUE-FULL", "CV-EXPIRED",
    "CV-JOB-GONE", "CV-NO-CREDIT", "CV-MIXED-BATCH", "CV-UNRECOGNIZED",
    "DL-QUOTA-HOUR", "DL-QUOTA-DAY", "DL-QUEUE-FULL", "DL-TOO-BIG", "DL-UNRECOGNIZED",
    "DL-BUTTON-EXPIRED",
    "ST-WHOMADE-UNKNOWN", "ST-COEDIT-LINK", "ST-COEDIT-GONE", "ST-NOT-YOURS", "ST-OWNER-ONLY",
    "ST-TITLE-EMPTY", "ST-ANIMATED", "ST-IMPORT-SOURCE", "ST-TG-PACK-FULL", "ST-UNRECOGNIZED",
    "ST-NOTHING-ADDED", "ST-NO-STICKER",
    "AN-LINK-INVALID", "AN-LINK-BLOCKED", "AN-LINK-PAUSED", "AN-INBOX-GONE", "AN-SENDER-BLOCKED",
    "AN-NOT-STARTED", "AN-NEEDS-REPLY", "AN-OPENING-NEEDS-REPLY", "AN-AMBIGUOUS", "AN-REPLY-BLOCKED",
    "AN-REPLY-STALE", "AN-TOO-FAST", "AN-EDIT-NOT-RELAYED", "AN-CONV-GONE", "AN-NOT-YOURS",
    "AN-NO-ANCHOR", "AN-WHICH-UNKNOWN", "AN-ARCHIVE-OWNER-ONLY", "AN-EXPORT-GONE",
    "AN-EXPORT-NOTHING", "AN-UNADDRESSED",
})


# ---------------------------------------------------------------------------
# How loudly a problem should be answered
# ---------------------------------------------------------------------------
# The owner, in 1.7.0: "Give priority levels for errors. The highest level
# errors should be sent to me immediately. The most important of those can be
# when a bot crashes entirely. Other errors should be visible in the report
# command."
#
# Three levels, and the line between them is *whose fault it is and how much
# of the bot it takes down*:
#
#   1 URGENT   The bot is broken, or something that had to happen did not:
#              a crash, a disk with no room left, a message that was accepted
#              and then never delivered, money taken with nothing to show for
#              it. One of these is worth a message at three in the morning
#              because waiting until midnight makes it worse.
#
#   2 FAULT    One person asked for something and the bot could not do it,
#              through no fault of theirs -- a download that failed, a
#              conversion that timed out, Telegram refusing a sticker. Worth
#              knowing about, not worth waking up for. Into the daily report.
#
#   3 REFUSED  The bot did exactly the right thing and said no: a file over
#              the limit, a format nobody supports, a quota, an unknown
#              command. Not a fault at all, and the reason SIMPLE exists --
#              these are the problems whose own message explains them. Counted
#              in the daily report, never listed one by one.
#
# A level-2 code can still reach the owner immediately without being promoted:
# see BURST_ESCALATION in shared_features. Fifty of the same failure in an
# hour is not fifty people having bad luck, it is a route that has gone down,
# and that is a level-1 fact assembled out of level-2 parts.

URGENT, FAULT, REFUSED = 1, 2, 3

URGENT_CODES = frozenset({
    # The bot itself fell over.
    "FM-CRASH", "CV-CRASH",
    # Money moved, or should have and did not.
    "FM-INVOICE",
    # A legal obligation the bot failed to honour.
    "FM-ERASE",
    # No room left on the machine -- everybody's next request fails too.
    "CV-STORAGE-FULL", "DL-NO-SPACE",
    # Work accepted and then lost to a restart.
    "CV-RESTARTED",
    # AnonBot took a message and did not deliver it. The whole bot is a
    # promise to carry one message to one person, so this is the only
    # failure it has that is not recoverable by trying again -- the sender
    # believes it arrived.
    "AN-DELIVERY", "AN-REPLY-FAILED",
})


def level(code) -> int:
    """URGENT, FAULT or REFUSED for a code. An unknown code is a FAULT: it
    came from somewhere, and guessing that it is harmless is the wrong way to
    be wrong."""
    if code in URGENT_CODES:
        return URGENT
    if code in SIMPLE:
        return REFUSED
    return FAULT


LEVEL_NAMES = {URGENT: "urgent", FAULT: "fault", REFUSED: "refused"}
LEVEL_ICONS = {URGENT: "🚨", FAULT: "⚠️", REFUSED: "•"}


def urgent(code) -> bool:
    """Whether this one is worth interrupting the owner for."""
    return level(code) == URGENT


def reportable(code) -> bool:
    """Whether a message ending in this code offers a Report button."""
    return is_code(code) and code not in SIMPLE


def code_for(bot: str, key: str) -> "str | None":
    """The code a message key carries in this bot, or None."""
    return KEYS.get(bot, {}).get(key) or KEYS["shared"].get(key)


def code_line(code: "str | None") -> str:
    return f"\n\n{MARK}{code}" if code else ""


def find_code(text: "str | None") -> "str | None":
    """The code a message ends with, if it is a known one."""
    match = _AT_END.search(text or "")
    return match.group(1) if match and match.group(1) in PROBLEMS else None


def strip_code(text: str) -> str:
    """The message without its code line."""
    match = _AT_END.search(text or "")
    return text[:match.start()] if match else text


def new_incident() -> str:
    return "".join(secrets.choice(_INCIDENT_ALPHABET) for _ in range(6))


def is_code(value) -> bool:
    return isinstance(value, str) and value in PROBLEMS


def is_incident(value) -> bool:
    return isinstance(value, str) and bool(INCIDENT_RE.match(value))


def decode(code: str) -> str:
    """Plain-text explanation of a code, for the owner."""
    problem = PROBLEMS.get(code)
    if problem is None:
        return f"{code}: not a known code."
    return (f"{code} — {problem.title} ({problem.bot})\n\n"
            f"What happened: {problem.meaning}\n"
            f"Likely causes: {problem.causes}\n"
            f"What to check: {problem.check}\n"
            f"Report button: {'offered' if reportable(code) else 'not offered, the message explains itself'}")
