"""Translation strings for ConvertBot's end-user-facing text (English,
Uzbek, Russian). Deliberately duplicated per bot -- same "no shared files
between bots" independence as shared_features.py -- but the STRINGS content
here is specific to this bot's own commands and flows.

Admin-only output (/stars, /dbdump, /status) is intentionally NOT
translated -- only the bot owner reads it, same reasoning as
downloader_bot's i18n.py.

The keys below split into two groups:
  - "Shared" keys (donate flow, sibling-bot blurb) exist under the exact
    same names in every bot's i18n.py, since shared_features.py is
    duplicated byte-identical across the family and calls t() with these
    names regardless of which bot it's running in.
  - Bot-specific keys, everything below the shared block, for this bot's
    own bot.py/convert_utils.py strings only.
"""
import asyncio

import db

SUPPORTED_LANGUAGES = ("en", "uz", "ru")
LANGUAGE_LABELS = {"en": "English 🇬🇧", "uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺"}

# What every /start shows, whether or not the user already has a language.
# Deliberately not part of STRINGS: it is trilingual on purpose, so there
# is no single `lang` to look it up under.
LANGUAGE_PROMPT = (
    "👋 Welcome! / Xush kelibsiz! / Добро пожаловать!\n\n"
    "Please choose your language / Iltimos, tilni tanlang / "
    "Пожалуйста, выберите язык:"
)

STRINGS = {
    "en": {
        "flood_wait": "You're going faster than I can keep up with — give it about {seconds} second(s) and carry on.",
        # ---- shared keys (same name in every bot's i18n.py) ----
        "sibling_blurb": "Also part of this bot family, see below \U0001f447",
        "donation_nudge": '⚡ Converting bigger files often? /recharge tops up your credit ahead of time.',
        "donate_unknown_currency": 'Unknown currency "{currency}" — try xtr or usd.',
        "donate_currency_not_configured": "{currency} payments aren't set up on this bot yet — use Stars instead.",
        "donate_invalid_amount": "That's not a valid amount — try e.g. /recharge 500.",
        "donate_prompt": 'Top up your ⚡ credit for conversions. Choose an amount below, or Custom to enter your own (you can also send /recharge <number> directly).',
        "donate_custom_button": "✏️ Custom {symbol}",
        "donate_too_many_stars": "That's a lot of Stars! Keep it under {max} ⭐ per top-up.",
        "donate_out_of_range": "{currency} donations need to be between {lo} and {hi} {symbol}.",
        "donate_invoice_title": 'Top up ⚡ credit',
        "donate_invoice_description": 'Adds {credited} ⚡ of credit to your balance for conversions.',
        "donate_invoice_label": '⚡ credit top-up',
        "donate_invoice_description_fiat": 'A one-time voluntary donation towards hosting costs. Thank you!',
        "donate_prompt_credit": 'Each ⭐ you pay becomes ⚡ credit for conversions. Your next {left} ⭐ earn {each} ⚡ each ({mult}×): {rate} ⚡ of ordinary credit plus a bonus that expires {days} days after payment. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_prompt_credit_base": 'Each ⭐ you pay becomes {rate} ⚡ of credit for conversions. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_invoice_error": "⚠️ Telegram wouldn't create that invoice: {error}",
        "stars_unit": "Stars",
        "donate_custom_ask": 'How many {unit} would you like to top up with? Reply with a number.',
        "donate_invalid_amount_retry": "That's not a valid amount — send /recharge to try again.",
        "donate_thanks": "🙏 Thank you for the {amount} ⭐ — genuinely appreciated!",
        "topup_thanks": '⚡ Recharged — {stars} ⭐ received. Thank you!\n\nAdded to your balance: +{credited} ⚡\nYour balance now: {balance} ⚡',
        "topup_thanks_bonus": '🎁 Plus {bonus} ⚡ bonus credit — it expires on {date}.',
        "credit_cannot_be_withdrawn": '⚡ is credit for conversions in ConvertBot, and can NOT be withdrawn or turned back into Stars. A problem with a payment? /paysupport',
        "paysupport_text": '💳 Help with a payment\n\nPayments are FINAL: Stars are NOT refunded, and ⚡ credit can NOT be withdrawn or turned back into Stars.\n\nIf a payment went wrong — you were charged and no credit arrived, or you were charged twice — write to {contact} with the date, the amount and your Telegram id, {user_id}. It will be checked and put right with credit.\n\n/balance lists every payment and what it added.',
        "report_button": "🐞 Report this",
        "problem_logged_note": "This is already written down for the bot's owner — the code, the time and the version, and nothing about you.",
        "report_disclaimer": "📨 Report this problem?\n\nAlready recorded, without you: the error code {code}, the incident number {incident}, when it happened and the bot's version.\n\nSend adds only what is related to this problem:",
        "report_send": "📨 Send",
        "report_cancel": "✖️ Cancel",
        "report_sent": "✅ Sent — thank you. It's on incident {incident} now.",
        "report_already": "A report is already on incident {incident}. Nothing more was sent.",
        "report_cancelled": "Cancelled — nothing was sent. The problem itself stays logged, without you.",
        "report_failed": "⚠️ The report couldn't be sent right now. Please try again later.",
        "report_invalid": 'This button no longer works.',
        "report_field_link": "the link you sent: {value}",
        "report_field_site": "which site it was: {value}",
        "report_field_routes": "which download routes were tried and what each one answered (technical, nothing about you)",
        "report_field_lang": "the language the bot speaks to you in ({value})",
        "report_field_chat_private": "that this is a private chat",
        "report_field_chat_group": "that this is a group chat",
        "report_field_comment": "your comment: “{value}”",
        "report_field_contact": "your Telegram user ID, so the owner can write back to you",
        "report_leaves_out": "Left out: your name, your @username and everything else you sent. Your user ID goes only if you turn on the reply switch below — otherwise the report isn't linked to your account. Whatever you send is cleared after 30 days.",
        "report_comment_add": "💬 Add a comment",
        "report_comment_edit": "💬 Change the comment",
        "report_contact_off": "☐ Let the owner reply to me",
        "report_contact_on": "☑️ Let the owner reply to me",
        "report_comment_ask": "💬 Write your comment as a reply to this message — what you were trying to do, or what you expected to happen. One message, up to {limit} characters. /cancel to skip it.",
        "cancel_item_report_comment": "the comment for your problem report",
        "cancel_button_report_comment": "💬 Report comment",
        "crash_notice": "⚠️ Something went wrong on the bot's side while handling that, so it wasn't done. Please try again in a moment.",
        "sandbox_notice": "🧪 Test mode — no real Stars were charged for this.",
        "balance_header": "⚡ Your balance: {balance}",
        "balance_totals": "Paid {paid} ⭐ in total · credited {credited} ⚡ · spent {spent} ⚡",
        "balance_rate": 'Your next {left} ⭐ earn {each} ⚡ each ({mult}×).',
        "balance_rate_base": '1 ⭐ buys {rate} ⚡.',
        "balance_bonus_line": 'Of that, {bonus} ⚡ is bonus credit — {soon} ⚡ of it expires on {date}.',
        "balance_recent": "Recent:",
        "balance_empty_hint": '/recharge adds credit whenever you want some.',
        "bot_short_description": (
            "Converts pictures, video, audio, documents, spreadsheets and subtitles "
            "between about 75 formats."
        ),
        "bot_description": 'Send a file and pick what to turn it into. Pictures, video, audio, documents, spreadsheets, subtitles — 75 formats in, 40 out.\n\nA HEIC from an iPhone becomes a JPG. Several pictures become one PDF. A PDF becomes pictures or text. /formats has the rest.\n\nAnything under 3 MB is free. Above that it is priced by size in ⚡ credit, bought with Stars and shown before you choose. A conversion the bot fails gives its credit back.\n\nEnglish, Uzbek and Russian. /privacy says what it keeps about you.',
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
        "privacy_heading": "🔒 Privacy",
        "privacy_kept_heading": "What this bot keeps:",
        "privacy_stored": '• your Telegram user id, and the language you chose\n• the file you send — deleted as soon as it has been converted, or kept for up to 15 minutes after each conversion if you turn on "keep file" to convert it to more formats; anything a crash leaves behind is swept up on a timer and at startup\n• a timestamp each time you use the bot, so its owner can tell whether anyone is using it\n• your ⚡ credit balance, and a record of every top-up, conversion charge and ⚡ returned to your balance: the amount, what it was for, and Telegram\'s payment id for anything paid\n• whatever the bot is in the middle of doing with you, until it is finished',
        "privacy_problems_heading": "When something goes wrong:",
        "privacy_problems": (
            "Every error this bot shows anybody is written down by itself: the error code, an "
            "incident number, when it happened and the bot's version. Nothing in that is about "
            "you — not your id, not your name, not what you sent. A fault nobody reports is "
            "still a fault, which is why it does not wait to be asked.\n"
            "\n"
            "\"Report this\" under an error shows exactly what a report would carry, and "
            "nothing is sent unless you tap Send. It carries only what is related to that error, "
            "plus the language the bot speaks to you in, whether the chat is private or a group, "
            "and a comment if you write one. Never your name or @username. Your Telegram user id "
            "only if you turn on \"Let the owner reply to me\" — without it, the report is not "
            "linked to you.\n"
            "\n"
            "Whatever a report carries is cleared after 30 days on its own, and /deletemydata "
            "clears straight away any report with your id on it. The record of the error stays — "
            "it still happened. The records themselves are deleted after 180 days."
        ),
        "privacy_seen_by_heading": "Who else sees it:",
        "privacy_seen_by": (
            "• Telegram, which carries every message both ways and sets its own terms\n"
            "• the hosting provider this bot runs on, and the database it writes to"
        ),
        "privacy_others": (
            "• and nobody beyond those — files are converted on the machine the bot runs on and are never "
            "handed to an outside service"
        ),
        "privacy_kept_for_heading": "How long it stays:",
        "privacy_kept_for": 'Settings and anything the bot is holding for you stay until you erase them or stop using it. Counted use is dropped after about three months. Payment records and your ⚡ balance are kept longer, because a dispute about a payment is settled against them.\n\nNothing here is sold, rented or used for advertising, and nothing goes to anyone not named above.',
        "privacy_your_choices": (
            "What you can do:\n"
            "/deletemydata — erase what this bot holds on you\n"
            "/terms — what the bot may be used for\n"
            "\n"
            "Blocking the bot in Telegram stops it talking to you but erases nothing, so send "
            "/deletemydata first if you want both."
        ),
        "terms_heading": "📜 Terms",
        "terms_use": (
            "Use it for what it is for, within the law and within Telegram's own terms. Do not "
            "use it to harass anyone, and do not drive it past the limits it sets — an account "
            "doing either is blocked."
        ),
        "terms_specific": "Files and payment: convert what you have the right to convert. Anything under 3 MB is free; above that the price is in ⚡ credit, bought with Telegram Stars, and is shown before you choose a format. ⚡ is taken when a conversion STARTS. If you stop a running conversion yourself, it is NOT given back; if it fails on the bot's side, ⚡ goes back to your balance automatically. Payments are FINAL: Stars are NOT refunded, and credit can NOT be withdrawn or turned back into Stars.",
        "terms_money": 'Money: /recharge buys ⚡ credit for conversions: 2 ⚡ per ⭐, or 6 for your first 500 Stars ever and 4 for the next 500. The part above 2 is bonus credit and expires 90 days after the payment. Payments are FINAL: Stars are NOT refunded, and credit can NOT be withdrawn or turned back into Stars. Telegram handles every payment and the bot never sees a card number. A payment that went wrong: /paysupport.',
        "terms_no_warranty": (
            "No promises: one person runs this, it is free, and it can be slow, wrong, or off "
            "entirely without warning. Keep your own copy of anything that matters."
        ),
        "policy_full_text": "Full text: {url}",
        "policy_contact": "Questions, complaints or a data request: {contact}",
        "delete_data_confirm": "⚠️ This erases what this bot holds on you. There is no undo.",
        "delete_data_consequences": 'Your language, your position in the top-up reminder and every record of when you used the bot all go. Files are not involved: whatever you converted was deleted when the conversion finished.\n\nWhat you paid stays, without your username, because a dispute about a payment is settled against it — and so does your ⚡ balance, which /balance will still show.',
        "delete_data_button_yes": "🗑 Erase it",
        "delete_data_button_no": "↩️ Keep my data",
        "delete_data_kept": "Nothing was erased.",
        "delete_data_done": (
            "🗑 Done — {rows} record(s) erased.\n"
            "\n"
            "Send /start whenever you like; the bot will treat you as new."
        ),
        "delete_data_failed": (
            "Couldn't erase that just now — something went wrong at my end. Please try again in "
            "a few minutes."
        ),
        "language_set_confirmation": "✅ Language set to English.",
        "cancel_header": "\u274c Cancelled:",
        "cancel_nothing": "Nothing to cancel — I wasn't waiting on anything from you.",
        "cancel_ask": "What should I stop? Here's what I'm waiting on:",
        "cancel_kept": "Alright — nothing cancelled.",
        "cancel_reply_box_freed": "Your reply box is free again.",
        "cancel_button_all": "❌ All of it",
        "cancel_button_none": "↩️ Nothing, keep going",
        "cancel_button_donation": '💸 Top-up amount',
        "cancel_item_donation": 'the top-up amount I asked you for',
        "cancel_item_stale_prompt": "a leftover prompt that was still waiting on an answer",
        "cancel_item_conversion": "the .{ext} file you were converting",
        "cancel_button_conversion": "🔄 The file waiting to convert",
        # ---- convert_bot-specific keys ----
        "start_greeting": "Hey! Send me a file and I'll convert it to another format.\n\n",
        "help_text": "Send me a file and I'll convert it to another format — pictures, video, audio, documents, spreadsheets and subtitles.\n\nCommands:\n/convert - start a conversion (or just send a file directly)\n/formats - every format I read and write\n/balance - your ⚡ credit and what it was spent on\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/recharge - top up your ⚡ credit\n/en, /uz, /rus - switch language (or /language, which asks)\n\nPrice in ⚡ credit, by file size:\n{pricing}\n\n⚠️ NOTE: Payments are final — Stars are NOT refunded, and ⚡ credit can NOT be withdrawn. A conversion's ⚡ is taken when it STARTS, and goes back to your balance only if the bot fails it.\n\n",
        "convert_start_prompt": (
            "Send me a file to convert, up to {max_mb} MB — a picture, a video, a "
            "sound, a document, a spreadsheet or a subtitle file. Send several "
            "pictures at once and I can bind them into one PDF.\n\n"
            "/formats lists every format I know.\n\n"
            "Price in ⚡ credit, by file size:\n{pricing}\n\n/cancel to stop."
        ),
        "cancelled": "Cancelled.",
        "btn_cancel_conversion": "✖️ Cancel",
        "unknown_extension": (
            "Couldn't tell that file's format from its name — try sending it as a "
            "document with a normal extension (e.g. photo.png). /formats lists the "
            "ones I know."
        ),
        "file_too_large_download": "That file is over {max_mb} MB — Telegram bots can't download anything bigger, sorry.",
        "downloading": "Downloading...",
        "restarting_send_again": "🔄 I'm being updated right now — give me a few seconds and send that again.",
        "update_soon_try_later": "🔧 I'm being updated in a moment, so I can't start anything new right now — please try again in about {minutes} minute(s). I'll message you when I'm back.",
        "update_soon_try_later_soon": "🔧 I'm being updated right now, so I can't start anything new — please try again shortly. I'll message you when I'm back.",
        "update_will_reset": "🔧 Heads up: I'm about to be updated, and what you have going right now will be reset. You'll be able to start it again in a few minutes.",
        "update_done_try_now": '✅ The update is done — go ahead and try again now.',
        "download_failed": "Couldn't download that file: {error}",
        "unsupported_format": "\".{ext}\" isn't a format I convert — /formats lists the ones I do.",
        "file_too_large_convert": "That file is {size} MB, over the {max_mb} MB limit — can't convert it. A bigger maximum file size is coming soon.",
        "no_target_formats": "No different target format is available for that file.",
        "price_free_under": 'Free (under {mb} MB)',
        "category_image": "image",
        "category_video": "video",
        "category_audio": "audio",
        "convert_options_prompt": "Got it — {size} {category} file. Convert to:\n\n{price_line}",
        "price_after_format": "What it costs depends on what comes out as well as what went in, so pick a format and I will quote it before anything is charged.",
        "quote_line_sizes": "{in_size} in · about {out_size} out",
        "quote_free": "Free — the whole job stays under {mb} MB.",
        "quote_cost": "Cost: {price} ⚡",
        "quote_fixed": "That price is fixed now. If the result comes out bigger than the estimate, you are not charged more.",
        "quote_balance": "You have {balance} ⚡.",
        "btn_quote_go": "✅ Convert · {price} ⚡",
        "btn_quote_free": "✅ Convert",
        "btn_quote_back": "↩️ Another format",
        "conversion_failed": "Conversion failed: {error}",
        "conversion_crashed": "Something went wrong converting that file: {error}",
        "converted_file_caption": "Here's your converted file!",
        "converted_file_caption_free": "Here's your converted file! (free)",
        "conversion_expired": "This conversion session expired — send the file again.",
        "converting_free": 'Converting (free)...',
        "convert_invoice_title": "Convert {src} to {target}",
        "convert_invoice_description": "One-time conversion of your {size_kb} KB file.",
        "convert_invoice_label": "{src}→{target} conversion",
        "invoice_sent": "Invoice sent for {price} ⭐ — pay it to get your converted file. /cancel to back out.",
        "paid_from_balance": "Converting… {price} ⚡ spent, {balance} ⚡ left on your balance.",
        "topup_needed": 'This one costs {price} ⚡ and you have {balance} ⚡.\n\nInvoice sent for {stars} ⭐, which adds {credited} ⚡ — enough for this conversion, and the rest stays on your balance. /cancel to back out.',
        "credit_refunded": "{credits} ⚡ went back onto your balance — you have {balance} ⚡.",
        "credit_policy_note": "⚠️ NOTE: ⚡ is taken when the conversion STARTS. Stop it yourself and it is NOT given back; if it fails on the bot's side, ⚡ goes straight back to your balance. Payments are final — Stars are not refunded.",
        "send_limit_note": "📤 A bot can send files of up to {mb} MB. If the converted file comes out bigger, it can't be sent — and its ⚡ goes straight back to your balance.",
        "too_many_megapixels": 'That picture is {mp} megapixels — over the {max} MP I can convert safely. Nothing was charged.',
        "too_big_to_send_note": "📐 {formats} aren't offered: at {mp} MP they would come out over the {limit} MB a bot can send. JPG, WEBP or AVIF keep it sendable.",
        "nothing_sendable": 'Every format I could offer would come out over the {limit} MB a bot can send for a picture this size. Nothing was charged.',
        "too_big_to_send_alert": 'That format would come out over the {limit} MB a bot can send for this picture.',
        "keep_toggle_off": '📌 Keep file for more formats: off',
        "keep_toggle_on": '📌 Keep file for more formats: on',
        "keep_explained_on": "I'll keep your file for {minutes} minutes after each conversion, so you can convert it to other formats too. /cancel deletes it sooner.",
        "keep_explained_off": 'Your file will be deleted as soon as it has been converted.',
        "storage_full_user": 'You already have {used} MB of files with me, and I hold up to {limit} MB per person. Let a conversion finish or /cancel one, then send it again.',
        "storage_full_global": "I'm short on temporary space right now — send that again in a few minutes.",
        "cancel_item_job_running": 'the {target} conversion of your {size} MB {src} — running',
        "cancel_item_job_queued": 'the {target} conversion of your {size} MB {src} — queued, nothing charged yet',
        "cancel_button_job": '⏹ {target} conversion',
        "queue_full": 'You already have {count} conversions queued or running. Send more when some of them finish.',
        "job_queued": '⏳ {src} → {target} is queued, {ahead} ahead of it. Nothing is taken until it starts.',
        "job_starting": '⏳ {src} → {target}: starting…',
        "job_not_running": 'That conversion has already finished.',
        "payment_kept_as_credit": 'Payment received — +{credited} ⚡, your balance is {balance} ⚡. The file had already expired, so nothing was converted; send it again and it will be paid from your balance.',
        "job_started": '🔄 Converting {src} → {target}… {price} ⚡ taken, {balance} ⚡ left.',
        "job_started_free": '🔄 Converting {src} → {target} (free)…',
        "job_progress": "⏳ Still converting — {elapsed} min so far. I'll write again in {next} min, and in {last} min at the latest you'll hear how it ended.",
        "job_progress_last": '⏳ Still converting — {elapsed} min so far. The last update comes in {last} min: by then it will be done, or stopped with its ⚡ back on your balance.',
        "job_stop_button": '⏹ Stop',
        "job_stop_button_queued": '✖ Remove from queue',
        "job_done": '✅ {src} → {target} done.',
        "balance_left_line": '{balance} ⚡ left on your balance.',
        "job_user_stopped": '⏹ Stopped — the {price} ⚡ it started with stays spent.',
        "job_user_stopped_free": '⏹ Stopped.',
        "job_removed_from_queue": '✖ Removed from the queue — nothing was charged.',
        "job_no_credit": "That conversion couldn't start: it costs {price} ⚡ and your balance is {balance} ⚡. Nothing was charged — /recharge tops it up.",
        "job_refunded_line": 'The {price} ⚡ went back to your balance — you have {balance} ⚡.',
        "job_reason_refused": "I couldn't convert that file: {detail}",
        "job_reason_timeout": 'That conversion ran past its {minutes}-minute limit, so I stopped it. The owner has been told.',
        "job_reason_crash": 'The conversion failed on my side. The owner has been told.',
        "job_reason_too_large": 'The {target} came out at {mb} MB, over the {limit} MB a bot can send — JPG, WEBP or AVIF will be far smaller. The owner has been told.',
        "job_reason_send_failed": 'The file converted, but sending it to you failed. The owner has been told.',
        "job_reason_interrupted": 'I was restarted in the middle of that conversion. Send it again in a minute.',
        "unknown_order": "Unknown order.",
        "payment_received_converting": "Payment received — converting now...",
        "mystars_empty": "You haven't used the converter yet.",
        "mystars_total": "Total spent: {total} ⭐ (Stars only — see below for any fiat donations)\n\nRecent:",
        "unrecognized_message": (
            "That's not a file I can convert — send me one, or /formats to see what "
            "I take. Name a format (\"heic\", \"epub\") and I'll tell you what it "
            "becomes."
        ),
        "unknown_command": "I don't recognize that command. Send /start to see what I can do.",
        # ---- /formats, and the two-level format menu ----
        "category_document": "document",
        "category_data": "data",
        "category_subtitle": "subtitle",
        "formats_title": "📁 What I convert",
        "formats_intro": (
            "{sources} formats in, {targets} out — {pairs} combinations in all. "
            "Send me a file and I'll show you what that one can become; tap a "
            "category below for the whole list."
        ),
        "formats_highlights": (
            "Some of the less obvious ones:\n"
            "• iPhone photo (HEIC) → JPG or PNG\n"
            "• Any picture — or a whole album at once — into one PDF\n"
            "• PDF or EPUB → PNG, JPG or plain text\n"
            "• Word document → PDF, HTML or Markdown\n"
            "• CSV, JSON or XML → an XLSX spreadsheet\n"
            "• Subtitles: SRT, VTT and ASS between each other, or just the transcript"
        ),
        "formats_reads": "Reads",
        "formats_writes": "Writes",
        "formats_category_title": "📁 {category} files",
        "formats_lookup": ".{ext} is in the {category} category. I convert it to: {targets}",
        "formats_lookup_none": (
            "I can read .{ext}, but there is nothing this host can turn it into."
        ),
        "formats_lookup_unknown": (
            "I don't know a \".{ext}\" — /formats lists every format I do."
        ),
        "formats_hint": "/formats - every format I read and write",
        "btn_more_formats": "⋯ More formats",
        "btn_fewer_formats": "‹ Fewer",
        "btn_what_formats": "📁 What can you convert?",
        "btn_formats_back": "‹ All categories",
        "convert_options_prompt_batch": (
            "Got it — {count} files, {size} in all. Convert to:\n\n{price_line}"
        ),
        "converted_file_caption_zip": "Here you go — {items} files, in a zip.",
        "converted_file_caption_pdf": "Here you go — {items} pictures, one per page.",
        "converted_file_caption_pages": "Here you go — {items} pages, in a zip.",
        "converted_docx_note": (
            "The text is real text you can edit, with headings where the PDF "
            "set a line larger than the rest, bold where it said bold, and the "
            "pictures in the order they appeared. The page layout is not "
            "carried over: columns come out one after another, a table comes "
            "out as its text, and the page breaks are the PDF's."
        ),
        "converted_layout_note": (
            "The headings, emphasis, lists and tables are all there. The page "
            "layout is re-flowed rather than copied exactly — this host has no "
            "Word to ask."
        ),
        "batch_mixed_formats": (
            "Those files aren't all the same format, so send them one at a time "
            "— or a set of pictures, which I can bind into a single PDF."
        ),
        # ---- convert_utils.py pricing-table strings ----
        "price_free": "Free",
        "price_not_supported": "not supported",
        "price_cloud_api_note": "(cloud Bot API's 20 MB download ceiling)",
        "price_extra_per_100mb": "{stars} ⚡ + {extra} ⚡ per extra 100 MB",
        "price_coming_soon": '🔜 Coming soon: better prices and a bigger maximum file size.',
    },
    "uz": {
        "flood_wait": 'Juda tez yuboryapsiz — {seconds} soniyacha kutib, keyin davom eting.',
        "sibling_blurb": 'Oilamizdagi boshqa botlar pastda 👇',
        "donation_nudge": "⚡ Kattaroq fayllarni tez-tez o'girasizmi? /recharge orqali kreditni oldindan to'ldirib qo'yishingiz mumkin.",
        "donate_unknown_currency": '"{currency}" degan valyuta yo\'q — xtr yoki usd deb yozing.',
        "donate_currency_not_configured": "Bu botda hozircha {currency} bilan to'lab bo'lmaydi — Stars'dan foydalaning.",
        "donate_invalid_amount": "Miqdor noto'g'ri — masalan, /recharge 500 deb yozing.",
        "donate_prompt": "Konvertatsiyalar uchun ⚡ kreditingizni to'ldiring. Quyidagi miqdorlardan birini tanlang yoki o'zingiz yozish uchun «Boshqa»ni bosing (/recharge <son> deb ham yuborishingiz mumkin).",
        "donate_custom_button": "✏️ Boshqa {symbol}",
        "donate_too_many_stars": "Bu juda ko'p! Bir martalik to'ldirish {max} ⭐ dan oshmasin.",
        "donate_out_of_range": "{currency} bilan xayriya {lo} dan {hi} {symbol} gacha bo'lishi kerak.",
        "donate_invoice_title": "⚡ kreditni to'ldirish",
        "donate_invoice_description": "Konvertatsiyalar uchun balansingizga {credited} ⚡ kredit qo'shadi.",
        "donate_invoice_label": '⚡ kredit',
        "donate_invoice_description_fiat": 'Server xarajatlari uchun bir martalik ixtiyoriy xayriya. Rahmat!',
        "donate_prompt_credit": "To'lagan har bir ⭐ konvertatsiyalarga sarflanadigan ⚡ kreditga aylanadi. Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×): {rate} ⚡ oddiy kredit, qolgani esa to'lovdan {days} kun o'tgach muddati tugaydigan bonus. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_prompt_credit_base": "To'lagan har bir ⭐ konvertatsiyalarga sarflanadigan {rate} ⚡ kreditga aylanadi. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_invoice_error": "⚠️ Telegram to'lov hisobini yaratmadi: {error}",
        "stars_unit": "Stars (yulduzcha)",
        "donate_custom_ask": "Balansni qancha {unit} ga to'ldirmoqchisiz? Faqat sonni yozib yuboring.",
        "donate_invalid_amount_retry": "Miqdor noto'g'ri — qaytadan urinish uchun /recharge yuboring.",
        "donate_thanks": '🙏 {amount} ⭐ uchun katta rahmat!',
        "topup_thanks": "⚡ Balans to'ldirildi — {stars} ⭐ qabul qilindi. Rahmat!\n\nBalansingizga qo'shildi: +{credited} ⚡\nHozirgi balans: {balance} ⚡",
        "topup_thanks_bonus": '🎁 Ustiga {bonus} ⚡ bonus kredit — muddati {date} kuni tugaydi.',
        "credit_cannot_be_withdrawn": "⚡ — ConvertBot'dagi konvertatsiyalar uchun kredit: uni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. To'lovda muammo bo'lsa: /paysupport",
        "paysupport_text": "💳 To'lov bo'yicha yordam\n\nTo'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.\n\nTo'lovda xatolik bo'lgan bo'lsa — pul yechilgan-u, kredit tushmagan bo'lsa yoki ikki marta yechilgan bo'lsa — {contact} manziliga to'lov sanasi, miqdori va Telegram ID raqamingizni ({user_id}) yozib yuboring. Tekshirilib, kredit bilan to'g'rilab beriladi.\n\n/balance har bir to'lovni va u qancha kredit qo'shganini ko'rsatadi.",
        "report_button": "🐞 Xabar berish",
        "problem_logged_note": "Bu muammo bot egasi uchun allaqachon yozib olindi — kodi, vaqti va bot versiyasi. Siz haqingizda hech narsa yo'q.",
        "report_disclaimer": "📨 Bu muammo haqida xabar berasizmi?\n\nSizsiz allaqachon yozib olingan: {code} xato kodi, {incident} hodisa raqami, qachon yuz bergani va bot versiyasi.\n\n\"Yuborish\" faqat shu muammoga aloqador narsalarni qo'shadi:",
        "report_send": "📨 Yuborish",
        "report_cancel": "✖️ Bekor qilish",
        "report_sent": "✅ Yuborildi — rahmat. Endi u {incident} hodisasida.",
        "report_already": "{incident} hodisasi haqida allaqachon xabar berilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — hech narsa yuborilmadi. Muammoning o'zi sizsiz yozib olingan holicha qoladi.",
        "report_failed": "⚠️ Hozir xabarni yuborib bo'lmadi. Keyinroq qayta urinib ko'ring.",
        "report_invalid": 'Bu tugma endi ishlamaydi.',
        "report_field_link": "siz yuborgan havola: {value}",
        "report_field_site": "qaysi sayt ekani: {value}",
        "report_field_routes": "qaysi yuklab olish yo'llari sinab ko'rilgani va har biri nima javob bergani (texnik ma'lumot, siz haqingizda emas)",
        "report_field_lang": "bot siz bilan gaplashadigan til ({value})",
        "report_field_chat_private": "bu shaxsiy suhbat ekani",
        "report_field_chat_group": "bu guruh suhbati ekani",
        "report_field_comment": "izohingiz: “{value}”",
        "report_field_contact": "Telegram ID raqamingiz — bot egasi sizga javob yozishi uchun",
        "report_leaves_out": "Qo'shilmaydi: ismingiz, @username'ingiz va yuborgan boshqa hamma narsa. ID raqamingiz faqat pastdagi javob tugmasini yoqsangiz yuboriladi — aks holda xabar hisobingizga bog'lanmaydi. Yuborilgan narsa 30 kundan keyin o'chiriladi.",
        "report_comment_add": "💬 Izoh qo'shish",
        "report_comment_edit": "💬 Izohni o'zgartirish",
        "report_contact_off": "☐ Bot egasi menga javob yozsin",
        "report_contact_on": "☑️ Bot egasi menga javob yozsin",
        "report_comment_ask": "💬 Izohingizni shu xabarga javob qilib yozing — nima qilmoqchi edingiz yoki nima bo'lishini kutgandingiz. Bitta xabar, {limit} belgigacha. O'tkazib yuborish uchun /cancel.",
        "cancel_item_report_comment": "muammo haqidagi xabaringiz uchun izoh",
        "cancel_button_report_comment": "💬 Xabar izohi",
        "crash_notice": "⚠️ Buni bajarishda bot tomonida xatolik yuz berdi, shuning uchun amal bajarilmadi. Birozdan keyin qayta urinib ko'ring.",
        "sandbox_notice": '🧪 Test rejimi — haqiqiy Stars yechilmadi.',
        "balance_header": "⚡ Balansingiz: {balance}",
        "balance_totals": "Jami {paid} ⭐ to'landi · {credited} ⚡ qo'shildi · {spent} ⚡ sarflandi",
        "balance_rate": 'Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×).',
        "balance_rate_base": '1 ⭐ = {rate} ⚡.',
        "balance_bonus_line": 'Shundan {bonus} ⚡ — bonus kredit; {soon} ⚡ ning muddati {date} kuni tugaydi.',
        "balance_recent": 'Oxirgi amallar:',
        "balance_empty_hint": "/recharge orqali istalgan paytda balansni to'ldirishingiz mumkin.",
        "bot_short_description": (
            "Rasm, video, audio, hujjat, jadval va subtitrlarni 75 ga yaqin format "
            "orasida o'giradi."
        ),
        "bot_description": "Fayl yuboring va qaysi formatga o'girishni tanlang. Rasm, video, audio, hujjat, jadval, subtitr — 75 formatdan 40 formatga.\n\niPhone'dagi HEIC rasm — JPG ga. Bir nechta rasm — bitta PDF ga. PDF — rasm yoki matnga. Hammasi: /formats\n\n3 MB gacha bepul. Kattaroq fayl hajmiga qarab Stars bilan sotib olinadigan ⚡ kreditda to'lanadi, narx oldindan ko'rsatiladi. Bot xato qilsa, ⚡ balansga qaytadi.\n\nIngliz, o'zbek va rus tillarida. Nima saqlanishi: /privacy",
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• yuborgan faylingiz — o'girilishi bilanoq o'chiriladi; «faylni saqlash» yoqilgan bo'lsa, boshqa formatlarga ham o'girish uchun har konvertatsiyadan keyin 15 daqiqagacha saqlanadi; nosozlikdan keyin qolib ketgan fayllar muntazam va bot ishga tushganda tozalanadi\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• ⚡ kredit balansingiz va har bir to'ldirish, konvertatsiya uchun yechilgan hamda balansga qaytgan ⚡ yozuvi: miqdori, nima uchunligi va pullik to'lovlarda Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nXato ostidagi \"Xabar berish\" tugmasi xabarda aynan nima bo'lishini ko'rsatadi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Unda faqat shu xatoga aloqador narsalar, bot siz bilan gaplashadigan til, suhbat shaxsiymi yoki guruhmi va, yozsangiz, izohingiz bo'ladi. Ismingiz va @username'ingiz hech qachon. Telegram ID raqamingiz faqat \"Bot egasi menga javob yozsin\"ni yoqsangiz — aks holda xabar sizga bog'lanmaydi.\n\nXabardagi narsalar 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa ID raqamingiz bor xabarlarni darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• boshqa hech kim — fayllar botning o'z serverida o'giriladi va hech qanday tashqi xizmatga yuborilmaydi",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
        "privacy_your_choices": "Nima qilishingiz mumkin:\n/deletemydata — bot siz haqingizda saqlagan ma'lumotlarni o'chirish\n/terms — botdan foydalanish shartlari\n\nBotni Telegramda bloklasangiz, u sizga yozmay qo'yadi, lekin hech narsa o'chmaydi. Ikkalasini ham xohlasangiz, avval /deletemydata yuboring.",
        "terms_heading": "📜 Shartlar",
        "terms_use": "Botdan maqsadiga ko'ra, qonun va Telegram qoidalari doirasida foydalaning. Uni boshqalarni bezovta qilish uchun ishlatmang va belgilangan cheklovlardan oshirib yuklamang — aks holda akkaunt bloklanadi.",
        "terms_specific": "Fayllar va to'lov: faqat o'girishga huquqingiz bor fayllarni o'giring. 3 MB gacha bepul; kattarog'ining narxi Telegram Stars bilan sotib olinadigan ⚡ kreditda bo'lib, format tanlashdan oldin ko'rsatiladi. ⚡ konvertatsiya BOSHLANGANDA yechiladi. Ishlayotgan konvertatsiyani o'zingiz to'xtatsangiz, ⚡ QAYTARILMAYDI; bot tomonidagi xatolik tufayli bajarilmasa, ⚡ avtomatik ravishda balansingizga qaytib tushadi. To'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "terms_money": "Pul haqida: /recharge orqali konvertatsiyalar uchun ⚡ kredit sotib olasiz: har ⭐ uchun 2 ⚡, umumiy hisobda birinchi 500 ta Stars uchun esa 6 ⚡ dan, keyingi 500 tasi uchun 4 ⚡ dan. 2 ⚡ dan ortig'i bonus kredit bo'lib, to'lovdan 90 kun o'tgach muddati tugaydi. To'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Har bir to'lovni Telegram o'tkazadi, bot karta raqamingizni ko'rmaydi. To'lovda muammo bo'lsa: /paysupport.",
        "terms_no_warranty": "Kafolat yo'q: botni bir kishi yuritadi va u oldindan ogohlantirmasdan sekinlashishi, xato qilishi yoki butunlay to'xtab qolishi mumkin. Siz uchun muhim narsalarning nusxasini o'zingizda saqlang.",
        "policy_full_text": "To'liq matn: {url}",
        "policy_contact": "Savol, shikoyat yoki ma'lumot so'rovi uchun: {contact}",
        "delete_data_confirm": "⚠️ Bot siz haqingizda saqlagan ma'lumotlar o'chiriladi. Buni ortga qaytarib bo'lmaydi.",
        "delete_data_consequences": "Til sozlamangiz, eslatmalar hisobi va botdan qachon foydalanganingiz haqidagi qaydlar o'chiriladi. Fayllarga bu taalluqli emas: o'girilgan fayllar konvertatsiya tugashi bilanoq o'chirilgan.\n\nTo'lovlaringiz foydalanuvchi nomingizsiz saqlanib qoladi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi. ⚡ balansingiz ham saqlanadi va /balance uni ko'rsatishda davom etadi.",
        "delete_data_button_yes": "🗑 O'chirilsin",
        "delete_data_button_no": "↩️ Ma'lumotlarim qolsin",
        "delete_data_kept": "Hech narsa o'chirilmadi.",
        "delete_data_done": "🗑 Bajarildi — {rows} ta yozuv o'chirildi.\n\nIstalgan payt /start yuborsangiz, bot sizni yangi foydalanuvchi sifatida kutib oladi.",
        "delete_data_failed": "Hozir o'chirib bo'lmadi — bot tomonida xatolik yuz berdi. Bir necha daqiqadan keyin qayta urinib ko'ring.",
        "language_set_confirmation": "✅ Til o'zbekchaga o'zgartirildi.",
        "cancel_header": "\u274c Bekor qilindi:",
        "cancel_nothing": "Bekor qilinadigan amal yo'q — hozir hech narsa kutilmayapti.",
        "cancel_ask": 'Qaysi birini bekor qilay? Hozir quyidagilar kutilmoqda:',
        "cancel_kept": "Yaxshi — hech narsa bekor qilinmadi.",
        "cancel_reply_box_freed": "Xabar yozish maydoni endi bo'sh.",
        "cancel_button_all": "❌ Hammasini",
        "cancel_button_none": '↩️ Hech birini, davom etamiz',
        "cancel_button_donation": "💸 To'ldirish miqdori",
        "cancel_item_donation": "kiritilishi kutilayotgan to'ldirish miqdori",
        "cancel_item_stale_prompt": "javobsiz qolgan eski so'rov",
        "cancel_item_conversion": "o'girilishi kutilayotgan .{ext} fayli",
        "cancel_button_conversion": "🔄 Konvertatsiyani kutayotgan fayl",
        "start_greeting": "Salom! Menga faylni yuboring va men uni boshqa formatga o'giraman.\n\n",
        "help_text": "Menga fayl yuboring — uni boshqa formatga o'girib beraman: rasm, video, audio, hujjat, jadval va subtitrlar.\n\nBuyruqlar:\n/convert - konvertatsiyani boshlash (yoki shunchaki fayl yuboring)\n/formats - qo'llab-quvvatlanadigan barcha formatlar\n/balance - ⚡ kreditingiz va u nimaga sarflangani\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/recharge - ⚡ kreditni to'ldirish\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n\nNarxlar ⚡ kreditda, fayl hajmiga qarab:\n{pricing}\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — to'langan Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Konvertatsiya narxi u BOSHLANGANDA yechiladi va faqat bot tomonidagi xatolik tufayli bajarilmasa, ⚡ balansingizga qaytib tushadi.\n\n",
        "convert_start_prompt": "O'girish uchun {max_mb} MB gacha fayl yuboring — rasm, video, audio, hujjat, jadval yoki subtitr. Bir nechta rasmni birga yuborsangiz, ularni bitta PDF qilib beraman.\n\nBarcha formatlar: /formats\n\nNarxlar ⚡ kreditda, fayl hajmiga qarab:\n{pricing}\n\nBekor qilish uchun: /cancel",
        "cancelled": "Bekor qilindi.",
        "btn_cancel_conversion": "✖️ Bekor qilish",
        "unknown_extension": "Fayl nomidan formatini aniqlab bo'lmadi — faylni kengaytmasi bilan (masalan, rasm.png) hujjat sifatida yuboring.",
        "file_too_large_download": 'Afsuski, fayl {max_mb} MB dan katta — Telegram botlarga bundan katta fayllarni yuklab olishga ruxsat bermaydi.',
        "downloading": "Yuklanmoqda...",
        "restarting_send_again": '🔄 Bot hozir yangilanmoqda — bir necha soniyadan keyin qaytadan yuboring.',
        "update_soon_try_later": "🔧 Bot tez orada yangilanadi, shuning uchun yangi ishni boshlab bo'lmaydi — taxminan {minutes} daqiqadan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_soon_try_later_soon": "🔧 Bot hozir yangilanmoqda, shuning uchun yangi ishni boshlab bo'lmaydi — birozdan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_will_reset": "🔧 Diqqat: bot yangilanadi va hozir bajarilayotgan ishingiz to'xtab qoladi. Bir necha daqiqadan keyin qaytadan boshlashingiz mumkin.",
        "update_done_try_now": "✅ Yangilanish tugadi — endi qaytadan urinib ko'rishingiz mumkin.",
        "download_failed": "Faylni yuklab bo'lmadi: {error}",
        "unsupported_format": '".{ext}" formatini o\'gira olmayman. Qo\'llab-quvvatlanadigan formatlar: /formats',
        "file_too_large_convert": "Fayl hajmi {size} MB — bu {max_mb} MB chegarasidan katta, shuning uchun uni o'girib bo'lmaydi. Tez orada kattaroq fayllar ham qabul qilinadi.",
        "no_target_formats": "Bu faylni o'girish mumkin bo'lgan boshqa format yo'q.",
        "price_free_under": 'Bepul ({mb} MB gacha)',
        "category_image": "rasm",
        "category_video": "video",
        "category_audio": "audio",
        "convert_options_prompt": "Qabul qilindi — {size} hajmli {category} fayli. Qaysi formatga o'giray?\n\n{price_line}",
        "price_after_format": "Narx faqat yuborgan faylingizga emas, natijada chiqadigan faylga ham bog'liq. Shuning uchun formatni tanlang — pul yechilishidan oldin narxini aytaman.",
        "quote_line_sizes": "kirish {in_size} · chiqish taxminan {out_size}",
        "quote_free": "Bepul — butun ish {mb} MB dan oshmaydi.",
        "quote_cost": "Narxi: {price} ⚡",
        "quote_fixed": "Bu narx endi o'zgarmaydi. Natija taxmindan kattaroq chiqsa ham, ustiga qo'shimcha olinmaydi.",
        "quote_balance": "Hisobingizda {balance} ⚡ bor.",
        "btn_quote_go": "✅ O'girish · {price} ⚡",
        "btn_quote_free": "✅ O'girish",
        "btn_quote_back": "↩️ Boshqa format",
        "conversion_failed": 'Konvertatsiya bajarilmadi: {error}',
        "conversion_crashed": "Faylni o'girishda xatolik yuz berdi: {error}",
        "converted_file_caption": 'Mana, faylingiz tayyor!',
        "converted_file_caption_free": 'Mana, faylingiz tayyor! (bepul)',
        "conversion_expired": "Bu konvertatsiyaning vaqti o'tib ketdi — faylni qaytadan yuboring.",
        "converting_free": "O'girilmoqda (bepul)...",
        "convert_invoice_title": '{src} → {target} konvertatsiya',
        "convert_invoice_description": "{size_kb} KB hajmli faylni bir marta o'girish.",
        "convert_invoice_label": "{src}→{target} konvertatsiya",
        "invoice_sent": "{price} ⭐ uchun to'lov hisobi yuborildi — tayyor faylni olish uchun to'lang. Bekor qilish: /cancel",
        "paid_from_balance": "O'girilmoqda… {price} ⚡ yechildi, balansda {balance} ⚡ qoldi.",
        "topup_needed": "Bu konvertatsiya {price} ⚡ turadi, balansingizda esa {balance} ⚡.\n\n{stars} ⭐ uchun to'lov hisobi yuborildi: u {credited} ⚡ qo'shadi — bu konvertatsiyaga yetadi, ortgani balansingizda qoladi. Bekor qilish: /cancel",
        "credit_refunded": '{credits} ⚡ balansingizga qaytib tushdi — hozir {balance} ⚡.',
        "credit_policy_note": "⚠️ DIQQAT: ⚡ konvertatsiya BOSHLANGANDA yechiladi. Uni o'zingiz to'xtatsangiz, ⚡ QAYTARILMAYDI; bot tomonidagi xatolik tufayli bajarilmasa, ⚡ darhol balansingizga qaytib tushadi. To'lovlar qaytarilmaydi — Stars qaytarib berilmaydi.",
        "send_limit_note": "📤 Bot {mb} MB gacha bo'lgan faylni yubora oladi. Tayyor fayl bundan katta chiqsa, uni yuborib bo'lmaydi — bunday holda ⚡ darhol balansingizga qaytib tushadi.",
        "too_many_megapixels": "Bu rasm {mp} megapiksel — xavfsiz o'girish chegarasi {max} MP. Balansdan hech narsa yechilmadi.",
        "too_big_to_send_note": "📐 {formats} formatlari ko'rsatilmadi: {mp} MP rasmda ular bot yubora oladigan {limit} MB dan katta chiqadi. JPG, WEBP yoki AVIF esa yuborsa bo'ladigan hajmda bo'ladi.",
        "nothing_sendable": "Bu o'lchamdagi rasm istalgan formatda bot yubora oladigan {limit} MB dan katta chiqadi. Balansdan hech narsa yechilmadi.",
        "too_big_to_send_alert": 'Bu rasm shu formatda bot yubora oladigan {limit} MB dan katta chiqadi.',
        "keep_toggle_off": "📌 Faylni boshqa formatlar uchun saqlash: o'chirilgan",
        "keep_toggle_on": '📌 Faylni boshqa formatlar uchun saqlash: yoqilgan',
        "keep_explained_on": "Har bir konvertatsiyadan keyin faylingizni {minutes} daqiqa saqlab turaman — uni boshqa formatlarga ham o'girishingiz mumkin. Ertaroq o'chirish uchun: /cancel",
        "keep_explained_off": "Faylingiz o'girilishi bilanoq o'chiriladi.",
        "storage_full_user": "Fayllaringiz {used} MB joy egallagan, bir kishiga esa {limit} MB gacha ajratiladi. Biror konvertatsiya tugashini kuting yoki /cancel qiling, so'ng qaytadan yuboring.",
        "storage_full_global": 'Hozir vaqtinchalik joy yetishmayapti — bir necha daqiqadan keyin qaytadan yuboring.',
        "cancel_item_job_running": "{size} MB li {src} faylingizni {target} ga o'girish — bajarilmoqda",
        "cancel_item_job_queued": "{size} MB li {src} faylingizni {target} ga o'girish — navbatda, hali hech narsa yechilmagan",
        "cancel_button_job": "⏹ {target} ga o'girish",
        "queue_full": 'Sizda {count} ta konvertatsiya navbatda yoki bajarilmoqda. Ulardan biri tugagach, yana yuboring.',
        "job_queued": '⏳ {src} → {target} navbatda, oldinda {ahead} ta. Boshlanmaguncha hech narsa yechilmaydi.',
        "job_starting": '⏳ {src} → {target}: boshlanmoqda…',
        "job_not_running": 'Bu konvertatsiya allaqachon tugagan.',
        "payment_kept_as_credit": "To'lov qabul qilindi — +{credited} ⚡, balansingiz {balance} ⚡. Lekin faylning saqlanish muddati o'tib ketgani uchun u o'girilmadi: faylni qaytadan yuboring — narxi balansdan yechiladi.",
        "job_started": "🔄 {src} → {target} o'girilmoqda… {price} ⚡ yechildi, {balance} ⚡ qoldi.",
        "job_started_free": "🔄 {src} → {target} o'girilmoqda (bepul)…",
        "job_progress": "⏳ Konvertatsiya davom etmoqda — {elapsed} daqiqa o'tdi. {next} daqiqadan keyin yana xabar beraman, ko'pi bilan {last} daqiqada esa natijasini bilasiz.",
        "job_progress_last": "⏳ Konvertatsiya hali davom etmoqda — {elapsed} daqiqa o'tdi. Oxirgi xabar {last} daqiqadan keyin keladi: unda konvertatsiya yo tugagan, yo to'xtatilib, ⚡ balansingizga qaytgan bo'ladi.",
        "job_stop_button": "⏹ To'xtatish",
        "job_stop_button_queued": '✖ Navbatdan olib tashlash',
        "job_done": '✅ {src} → {target} tayyor.',
        "balance_left_line": 'Balansingizda {balance} ⚡ qoldi.',
        "job_user_stopped": "⏹ To'xtatildi — boshlanishida yechilgan {price} ⚡ qaytarilmaydi.",
        "job_user_stopped_free": "⏹ To'xtatildi.",
        "job_removed_from_queue": '✖ Navbatdan olib tashlandi — hech narsa yechilmadi.',
        "job_no_credit": "Konvertatsiya boshlanmadi: narxi {price} ⚡, balansingizda esa {balance} ⚡. Hech narsa yechilmadi — balansni /recharge orqali to'ldiring.",
        "job_refunded_line": '{price} ⚡ balansingizga qaytib tushdi — hozir {balance} ⚡.',
        "job_reason_refused": "Faylni o'girib bo'lmadi: {detail}",
        "job_reason_timeout": "Konvertatsiya {minutes} daqiqalik vaqt chegarasidan oshib ketgani uchun to'xtatildi. Bot egasiga xabar berildi.",
        "job_reason_crash": 'Konvertatsiya bot tomonidagi xatolik tufayli bajarilmadi. Bot egasiga xabar berildi.',
        "job_reason_too_large": "{target} fayli {mb} MB chiqdi — bu bot yubora oladigan {limit} MB dan katta. JPG, WEBP yoki AVIF ancha kichik bo'ladi. Bot egasiga xabar berildi.",
        "job_reason_send_failed": "Fayl o'girildi, lekin uni sizga yuborib bo'lmadi. Bot egasiga xabar berildi.",
        "job_reason_interrupted": 'Konvertatsiya vaqtida bot qayta ishga tushdi. Bir daqiqadan keyin faylni qaytadan yuboring.',
        "unknown_order": "Noma'lum buyurtma.",
        "payment_received_converting": "To'lov qabul qilindi — hozir o'girilmoqda...",
        "mystars_empty": "Siz hali konvertordan foydalanmagansiz.",
        "mystars_total": 'Jami sarflangan: {total} ⭐ (faqat Stars — boshqa valyutadagi xayriyalar pastda)\n\nOxirgilari:',
        "unrecognized_message": 'Bu o\'girish mumkin bo\'lgan fayl emas — fayl yuboring yoki qabul qilinadigan formatlarni /formats orqali ko\'ring. Format nomini yozsangiz (masalan, "heic" yoki "epub"), uni nimaga o\'girish mumkinligini aytaman.',
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /start yuboring.",
        # ---- /formats ----
        "category_document": "hujjat",
        "category_data": "ma'lumot",
        "category_subtitle": "subtitr",
        "formats_title": "📁 Qaysi formatlarni o'giraman",
        "formats_intro": "{sources} ta formatdan {targets} ta formatga — jami {pairs} xil yo'nalish. Fayl yuborsangiz, uni nimaga o'girish mumkinligini ko'rsataman; to'liq ro'yxat uchun quyidan turkumni tanlang.",
        "formats_highlights": "Ko'pchilik bilmaydigan imkoniyatlar:\n• iPhone rasmi (HEIC) → JPG yoki PNG\n• Istalgan rasm — yoki butun albom — bitta PDF\n• PDF yoki EPUB → PNG, JPG yoki oddiy matn\n• Word hujjati → PDF, HTML yoki Markdown\n• CSV, JSON yoki XML → XLSX jadval\n• Subtitrlar: SRT, VTT va ASS bir-biriga, yoki faqat matn",
        "formats_reads": "O'qiydi",
        "formats_writes": "Yozadi",
        "formats_category_title": "📁 {category} fayllari",
        "formats_lookup": ".{ext} — {category} fayli. Uni quyidagi formatlarga o'girish mumkin: {targets}",
        "formats_lookup_none": ".{ext} faylini o'qiy olaman, lekin bu serverda uni boshqa formatga o'girib bo'lmaydi.",
        "formats_lookup_unknown": '".{ext}" formati notanish — barcha formatlar: /formats',
        "formats_hint": "/formats - qo'llab-quvvatlanadigan barcha formatlar",
        "btn_more_formats": "⋯ Yana formatlar",
        "btn_fewer_formats": "‹ Kamroq",
        "btn_what_formats": '📁 Qaysi formatlar bor?',
        "btn_formats_back": "‹ Barcha turkumlar",
        "convert_options_prompt_batch": "Qabul qilindi — {count} ta fayl, jami {size}. Qaysi formatga o'giray?\n\n{price_line}",
        "converted_file_caption_zip": "Mana — {items} ta fayl, zip ichida.",
        "converted_file_caption_pdf": "Mana — {items} ta rasm, har biri alohida sahifada.",
        "converted_file_caption_pages": "Mana — {items} ta sahifa, zip ichida.",
        "converted_docx_note": "Matn haqiqiy matn — tahrirlash mumkin. PDF'da boshqalardan kattaroq yozilgan qatorlar sarlavha bo'ldi, qalin yozilgani qalinligicha qoldi, rasmlar esa o'z tartibida turibdi. Sahifa ko'rinishi ko'chirilmadi: ustunlar ketma-ket chiqadi, jadval o'z matniga aylanadi, sahifa chegaralari esa PDF'dagicha qoladi.",
        "converted_layout_note": "Sarlavhalar, ajratilgan matn, ro'yxat va jadvallar saqlandi. Sahifa ko'rinishi asl nusxadagidek emas, qaytadan joylashtirilgan — bu serverda Word yo'q.",
        "batch_mixed_formats": 'Fayllarning formati har xil, shuning uchun ularni birma-bir yuboring — yoki faqat rasmlar yuboring, ularni bitta PDF qilib beraman.',
        "price_free": "Bepul",
        "price_not_supported": "qo'llab-quvvatlanmaydi",
        "price_cloud_api_note": '(Telegram botlar uchun 20 MB yuklab olish chegarasi)',
        "price_extra_per_100mb": "{stars} ⚡ + har qo'shimcha 100 MB uchun {extra} ⚡",
        "price_coming_soon": '🔜 Tez orada: qulayroq narxlar va kattaroq fayllar.',
    },
    "ru": {
        "flood_wait": "Ты отправляешь быстрее, чем я успеваю — подожди примерно {seconds} секунд(ы) и продолжай.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотри ниже \U0001f447",
        "donation_nudge": '⚡ Часто конвертируете большие файлы? /recharge пополнит кредит заранее.',
        "donate_unknown_currency": 'Неизвестная валюта "{currency}" — попробуйте xtr или usd.',
        "donate_currency_not_configured": 'Оплата в {currency} на этом боте пока не настроена — используйте Stars.',
        "donate_invalid_amount": 'Это некорректная сумма — попробуйте, например, /recharge 500.',
        "donate_prompt": 'Пополните ⚡ кредит для конвертаций. Выберите сумму ниже или нажмите «Другое», чтобы ввести свою (можно и сразу отправить /recharge <число>).',
        "donate_custom_button": "✏️ Другое {symbol}",
        "donate_too_many_stars": 'Это очень много звёзд! Пусть будет меньше {max} ⭐ за одно пополнение.',
        "donate_out_of_range": "Пожертвования в {currency} должны быть в диапазоне от {lo} до {hi} {symbol}.",
        "donate_invoice_title": 'Пополнение ⚡ кредита',
        "donate_invoice_description": 'Добавляет {credited} ⚡ на ваш баланс для конвертаций.',
        "donate_invoice_label": 'Пополнение ⚡ кредита',
        "donate_invoice_description_fiat": 'Разовое добровольное пожертвование на хостинг. Спасибо!',
        "donate_prompt_credit": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации. Следующие {left} ⭐ дают по {each} ⚡ ({mult}×): {rate} ⚡ обычного кредита и бонус, который сгорает через {days} дней после оплаты. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_prompt_credit_base": 'Каждая оплаченная ⭐ превращается в {rate} ⚡ кредита на конвертации. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_invoice_error": "⚠️ Telegram не смог создать этот счёт: {error}",
        "stars_unit": "Stars (звёзды)",
        "donate_custom_ask": 'На сколько {unit} хотите пополнить? Ответьте числом.',
        "donate_invalid_amount_retry": 'Это некорректная сумма — отправьте /recharge, чтобы попробовать снова.',
        "donate_thanks": "🙏 Спасибо за {amount} ⭐ — это по-настоящему ценно!",
        "topup_thanks": '⚡ Баланс пополнен — {stars} ⭐ получено. Спасибо!\n\nНачислено на баланс: +{credited} ⚡\nВаш баланс: {balance} ⚡',
        "topup_thanks_bonus": '🎁 И ещё {bonus} ⚡ бонусного кредита — он сгорит {date}.',
        "credit_cannot_be_withdrawn": '⚡ — это кредит на конвертации в ConvertBot, его НЕЛЬЗЯ вывести или обменять обратно на Stars. Проблема с платежом? /paysupport',
        "paysupport_text": '💳 Помощь с платежом\n\nПлатежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести или обменять обратно на Stars.\n\nЕсли с платежом что-то пошло не так — деньги списали, а кредит не пришёл, или списали дважды, — напишите на {contact}: дату, сумму и ваш Telegram ID, {user_id}. Это проверят и исправят кредитом.\n\n/balance показывает каждый платёж и что он добавил.',
        "report_button": "🐞 Сообщить",
        "problem_logged_note": 'Эта проблема уже записана для владельца бота — код, время и версия. О вас там ничего нет.',
        "report_disclaimer": "📨 Сообщить об этой проблеме?\n\nУже записано, без вас: код ошибки {code}, номер случая {incident}, когда это произошло и версия бота.\n\n«Отправить» добавит только то, что относится к этой проблеме:",
        "report_send": "📨 Отправить",
        "report_cancel": "✖️ Отмена",
        "report_sent": "✅ Отправлено — спасибо. Теперь это на случае {incident}.",
        "report_already": "По случаю {incident} уже есть сообщение. Больше ничего не отправлено.",
        "report_cancelled": "Отменено — ничего не отправлено. Сама проблема остаётся записанной, без вас.",
        "report_failed": '⚠️ Сейчас не удалось отправить сообщение. Попробуйте позже.',
        "report_invalid": 'Эта кнопка больше не работает.',
        "report_field_link": "ссылку, которую вы отправили: {value}",
        "report_field_site": "какой это сайт: {value}",
        "report_field_routes": "какие способы загрузки были испробованы и что ответил каждый (техническое, не о вас)",
        "report_field_lang": "язык, на котором бот с вами говорит ({value})",
        "report_field_chat_private": "что это личный чат",
        "report_field_chat_group": "что это групповой чат",
        "report_field_comment": "ваш комментарий: «{value}»",
        "report_field_contact": "ваш Telegram ID — чтобы владелец мог вам ответить",
        "report_leaves_out": "Не отправляется: ваше имя, ваш @username и всё остальное, что вы присылали. ID — только если вы включите переключатель ответа ниже, иначе сообщение не связано с вашим аккаунтом. Всё отправленное удаляется через 30 дней.",
        "report_comment_add": "💬 Добавить комментарий",
        "report_comment_edit": "💬 Изменить комментарий",
        "report_contact_off": "☐ Пусть владелец мне ответит",
        "report_contact_on": "☑️ Пусть владелец мне ответит",
        "report_comment_ask": "💬 Напишите комментарий ответом на это сообщение — что вы пытались сделать или чего ожидали. Одно сообщение, до {limit} символов. /cancel — пропустить.",
        "cancel_item_report_comment": "комментарий к сообщению о проблеме",
        "cancel_button_report_comment": "💬 Комментарий",
        "crash_notice": '⚠️ При обработке произошла ошибка на стороне бота, поэтому ничего не сделано. Попробуйте ещё раз чуть позже.',
        "sandbox_notice": "🧪 Тестовый режим — настоящие Stars не списывались.",
        "balance_header": "⚡ Ваш баланс: {balance}",
        "balance_totals": "Всего оплачено {paid} ⭐ · начислено {credited} ⚡ · потрачено {spent} ⚡",
        "balance_rate": 'Следующие {left} ⭐ дают по {each} ⚡ ({mult}×).',
        "balance_rate_base": '1 ⭐ даёт {rate} ⚡.',
        "balance_bonus_line": 'Из них {bonus} ⚡ — бонусный кредит; {soon} ⚡ сгорит {date}.',
        "balance_recent": "Последние операции:",
        "balance_empty_hint": '/recharge пополнит кредит в любой момент.',
        "bot_short_description": (
            "Конвертирует картинки, видео, аудио, документы, таблицы и субтитры "
            "— около 75 форматов."
        ),
        "bot_description": 'Пришли файл и выбери, во что его превратить. Картинки, видео, аудио, документы, таблицы и субтитры — около 75 форматов на вход, 40 на выход.\n\nHEIC с iPhone становится JPG. Набор картинок — одним PDF. PDF — картинками или текстом. Весь список — /formats\n\nВсё меньше 3 МБ — бесплатно. Дороже — цена по размеру файла в ⚡ кредите, купленном за Stars, и видна до выбора. Если конвертация сорвётся по вине бота, кредит вернётся.\n\nАнглийский, узбекский и русский. /privacy — что бот о тебе хранит.',
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": '• твой числовой id в Telegram и выбранный язык\n• присланный файл — удаляется сразу после конвертации, или хранится до 15 минут после каждой конвертации, если включить «хранить файл», чтобы конвертировать его и в другие форматы; всё, что осталось после сбоя, подчищается по таймеру и при запуске\n• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли ботом хоть кто-нибудь\n• твой баланс ⚡ кредита и запись о каждом пополнении, списании за конвертацию и возврате ⚡ на баланс: сумму, за что и платёжный id Telegram для оплаченного\n• то, что бот в этот момент для тебя делает — пока не закончит',
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nКнопка «Сообщить» под ошибкой показывает, что именно будет в сообщении, и ничего не отправляется, пока вы не нажмёте «Отправить». В нём только то, что относится к этой ошибке, плюс язык, на котором бот с вами говорит, личный это чат или группа, и комментарий, если вы его напишете. Никогда — ваше имя или @username. Ваш Telegram id — только если вы включите «Пусть владелец мне ответит», иначе сообщение с вами не связано.\n\nВсё, что было в сообщении, стирается само через 30 дней, а /deletemydata сразу стирает сообщения с вашим id. Запись об ошибке остаётся — она действительно произошла. Сами записи удаляются через 180 дней.",
        "privacy_seen_by_heading": "Кто ещё это видит:",
        "privacy_seen_by": (
            "• Telegram — он передаёт каждое сообщение в обе стороны и действует по своим "
            "правилам\n"
            "• хостинг, на котором работает бот, и база данных, в которую он пишет"
        ),
        "privacy_others": (
            "• и больше никто, кроме них — файлы конвертируются на той же машине, где работает бот, и никуда "
            "наружу не передаются"
        ),
        "privacy_kept_for_heading": "Сколько это хранится:",
        "privacy_kept_for": 'Настройки и всё, что бот держит для тебя, остаются, пока ты их не сотрёшь или не перестанешь пользоваться ботом. Отметки об использовании удаляются примерно через три месяца. Записи о платежах и баланс ⚡ хранятся дольше — по ним разбираются споры о платежах.\n\nНичего из этого не продаётся, не сдаётся в аренду и не используется для рекламы, и никому кроме перечисленных выше не передаётся.',
        "privacy_your_choices": (
            "Что можно сделать:\n"
            "/deletemydata — стереть всё, что бот хранит о тебе\n"
            "/terms — для чего ботом можно пользоваться\n"
            "\n"
            "Блокировка бота в Telegram остановит его сообщения, но ничего не сотрёт — если "
            "нужно и то и другое, сначала отправь /deletemydata."
        ),
        "terms_heading": "📜 Условия",
        "terms_use": (
            "Пользуйся ботом по назначению, в рамках закона и правил самого Telegram. Не "
            "используй его, чтобы кого-то донимать, и не нагружай сверх заданных лимитов — за то "
            "и другое аккаунт блокируется."
        ),
        "terms_specific": 'Файлы и оплата: конвертируй то, что имеешь право конвертировать. Всё меньше 3 МБ бесплатно; дороже — цена в ⚡ кредите, который покупается за Telegram Stars, и показывается до выбора формата. ⚡ списывается, когда конвертация НАЧИНАЕТСЯ. Если остановишь идущую конвертацию сам, ⚡ НЕ вернётся; если сбой на стороне бота — ⚡ автоматически вернётся на баланс. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "terms_money": 'О деньгах: /recharge покупает ⚡ кредит на конвертации: 2 ⚡ за ⭐, а за твои первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держи свою копию всего, что тебе важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о тебе. Отменить будет нельзя.",
        "delete_data_consequences": 'Язык, место в напоминании о пополнении и все отметки о том, когда ты пользовался ботом, будут стёрты. Файлы тут ни при чём: то, что ты конвертировал, удалилось сразу после конвертации.\n\nОплаты останутся, без username, потому что по ним разбираются споры о платежах, — и баланс ⚡ тоже: /balance по-прежнему его покажет.',
        "delete_data_button_yes": "🗑 Стереть",
        "delete_data_button_no": "↩️ Оставить мои данные",
        "delete_data_kept": "Ничего не стёрто.",
        "delete_data_done": (
            "🗑 Готово — стёрто записей: {rows}.\n"
            "\n"
            "Отправь /start когда захочешь; бот примет тебя как нового."
        ),
        "delete_data_failed": (
            "Сейчас стереть не получилось — что-то сломалось на моей стороне. Попробуй ещё раз "
            "через несколько минут."
        ),
        "language_set_confirmation": "✅ Язык изменён на русский.",
        "cancel_header": "\u274c \u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e:",
        "cancel_nothing": "\u041e\u0442\u043c\u0435\u043d\u044f\u0442\u044c \u043d\u0435\u0447\u0435\u0433\u043e — \u044f \u043d\u0438\u0447\u0435\u0433\u043e \u043e\u0442 \u0432\u0430\u0441 \u043d\u0435 \u0436\u0434\u0430\u043b.",
        "cancel_ask": "Что остановить? Вот что я жду:",
        "cancel_kept": "Хорошо — ничего не отменено.",
        "cancel_reply_box_freed": "Поле ответа снова свободно.",
        "cancel_button_all": "❌ Всё",
        "cancel_button_none": "↩️ Ничего, продолжаем",
        "cancel_button_donation": '💸 Сумма пополнения',
        "cancel_item_donation": 'сумма пополнения, которую я запросил',
        "cancel_item_stale_prompt": "старый запрос, который всё ещё ждал ответа",
        "cancel_item_conversion": "\u0444\u0430\u0439\u043b .{ext}, \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0432\u044b \u043a\u043e\u043d\u0432\u0435\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u043b\u0438",
        "cancel_button_conversion": "🔄 Файл, ждущий конвертации",
        "start_greeting": "Привет! Пришли мне файл, и я преобразую его в другой формат.\n\n",
        "help_text": 'Пришли мне файл, и я преобразую его в другой формат — картинки, видео, аудио, документы, таблицы и субтитры.\n\nКоманды:\n/convert - начать конвертацию (или просто отправь файл напрямую)\n/formats - все форматы, которые я читаю и пишу\n/balance - твой ⚡ кредит и на что он потрачен\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/recharge - пополнить ⚡ кредит\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n\nЦена в ⚡ кредите, по размеру файла:\n{pricing}\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести. ⚡ за конвертацию списывается при СТАРТЕ и возвращается на баланс, только если сбой по вине бота.\n\n',
        "convert_start_prompt": (
            "Пришли файл для конвертации, до {max_mb} МБ — картинку, видео, звук, "
            "документ, таблицу или файл субтитров. Пришли несколько картинок "
            "сразу — соберу их в один PDF.\n\n"
            "/formats покажет все форматы, которые я знаю.\n\n"
            "Цена в ⚡ кредите, по размеру файла:\n{pricing}\n\n"
            "/cancel, чтобы остановиться."
        ),
        "cancelled": "Отменено.",
        "btn_cancel_conversion": "✖️ Отмена",
        "unknown_extension": (
            "Не удалось определить формат файла по названию — попробуй отправить "
            "его как документ с обычным расширением (например, photo.png)."
        ),
        "file_too_large_download": "Этот файл больше {max_mb} МБ — боты Telegram не могут скачать ничего крупнее, увы.",
        "downloading": "Скачивание...",
        "restarting_send_again": "🔄 Сейчас обновляюсь — подождите несколько секунд и отправьте ещё раз.",
        "update_soon_try_later": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова примерно через {minutes} мин. Я напишу, когда вернусь.',
        "update_soon_try_later_soon": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова чуть позже. Я напишу, когда вернусь.',
        "update_will_reset": '🔧 Внимание: меня скоро обновят, и то, что вы сейчас начали, будет сброшено. Через несколько минут сможете начать заново.',
        "update_done_try_now": '✅ Обновление завершено — можете пробовать снова.',
        "download_failed": "Не удалось скачать этот файл: {error}",
        "unsupported_format": "«.{ext}» — не тот формат, который я конвертирую — /formats покажет те, что умею.",
        "file_too_large_convert": 'Этот файл весит {size} МБ, что больше лимита в {max_mb} МБ — конвертировать его нельзя. Скоро максимальный размер файла станет больше.',
        "no_target_formats": "Для этого файла нет доступного другого формата.",
        "price_free_under": 'Бесплатно (меньше {mb} МБ)',
        "category_image": "изображение",
        "category_video": "видео",
        "category_audio": "аудио",
        "convert_options_prompt": "Принято — файл {category} на {size}. Во что конвертировать:\n\n{price_line}",
        "price_after_format": "Цена зависит не только от того, что вы прислали, но и от того, что получится. Выберите формат — я назову цену до того, как что-то спишется.",
        "quote_line_sizes": "на входе {in_size} · на выходе примерно {out_size}",
        "quote_free": "Бесплатно — вся работа укладывается в {mb} МБ.",
        "quote_cost": "Стоимость: {price} ⚡",
        "quote_fixed": "Эта цена уже зафиксирована. Если результат окажется больше оценки, доплачивать не придётся.",
        "quote_balance": "У вас {balance} ⚡.",
        "btn_quote_go": "✅ Конвертировать · {price} ⚡",
        "btn_quote_free": "✅ Конвертировать",
        "btn_quote_back": "↩️ Другой формат",
        "conversion_failed": "Конвертация не удалась: {error}",
        "conversion_crashed": "Что-то пошло не так при конвертации этого файла: {error}",
        "converted_file_caption": "Вот твой сконвертированный файл!",
        "converted_file_caption_free": 'Вот твой сконвертированный файл! (бесплатно)',
        "conversion_expired": "Срок этой сессии конвертации истёк — отправь файл заново.",
        "converting_free": 'Конвертация (бесплатно)...',
        "convert_invoice_title": "Конвертировать {src} в {target}",
        "convert_invoice_description": "Разовая конвертация твоего файла на {size_kb} КБ.",
        "convert_invoice_label": "{src}→{target} конвертация",
        "invoice_sent": "Счёт на {price} ⭐ отправлен — оплати его, чтобы получить сконвертированный файл. /cancel, чтобы отменить.",
        "paid_from_balance": "Конвертирую… списано {price} ⚡, на балансе осталось {balance} ⚡.",
        "topup_needed": 'Это стоит {price} ⚡, а у вас {balance} ⚡.\n\nОтправлен счёт на {stars} ⭐ — он добавит {credited} ⚡: хватит на эту конвертацию, остаток останется на балансе. /cancel, чтобы отменить.',
        "credit_refunded": "{credits} ⚡ вернулись на ваш баланс — теперь {balance} ⚡.",
        "credit_policy_note": '⚠️ ВНИМАНИЕ: ⚡ списывается, когда конвертация НАЧИНАЕТСЯ. Остановишь её сам — ⚡ НЕ вернётся; если сбой на стороне бота, ⚡ сразу вернётся на баланс. Платежи окончательные — Stars не возвращаются.',
        "send_limit_note": '📤 Бот может отправить файл размером до {mb} МБ. Если готовый файл получится больше, отправить его не выйдет — тогда ⚡ сразу вернётся на баланс.',
        "too_many_megapixels": 'В этой картинке {mp} мегапикселей — больше {max} МП, которые я могу безопасно конвертировать. Ничего не списано.',
        "too_big_to_send_note": '📐 {formats} не предлагаются: при {mp} МП они выйдут больше {limit} МБ, которые бот может отправить. JPG, WEBP или AVIF поместятся.',
        "nothing_sendable": 'Любой формат, который я могу предложить, для картинки такого размера выйдет больше {limit} МБ, которые бот может отправить. Ничего не списано.',
        "too_big_to_send_alert": 'Этот формат для такой картинки выйдет больше {limit} МБ, которые бот может отправить.',
        "keep_toggle_off": '📌 Хранить файл для других форматов: выкл',
        "keep_toggle_on": '📌 Хранить файл для других форматов: вкл',
        "keep_explained_on": 'После каждой конвертации я буду хранить файл {minutes} минут, чтобы ты мог конвертировать его и в другие форматы. /cancel удалит его раньше.',
        "keep_explained_off": 'Файл удалится сразу после конвертации.',
        "storage_full_user": 'У меня уже {used} МБ твоих файлов, а на одного человека я храню до {limit} МБ. Дождись окончания конвертации или отмени её через /cancel и пришли снова.',
        "storage_full_global": 'Сейчас не хватает временного места — пришли это снова через пару минут.',
        "cancel_item_job_running": 'конвертацию {size} МБ {src} в {target} — идёт',
        "cancel_item_job_queued": 'конвертацию {size} МБ {src} в {target} — в очереди, пока ничего не списано',
        "cancel_button_job": '⏹ Конвертация в {target}',
        "queue_full": 'У тебя уже {count} конвертаций в очереди или в работе. Пришли ещё, когда какие-то закончатся.',
        "job_queued": '⏳ {src} → {target} в очереди, перед ней {ahead}. Ничего не списывается, пока она не начнётся.',
        "job_starting": '⏳ {src} → {target}: начинаю…',
        "job_not_running": 'Эта конвертация уже закончилась.',
        "payment_kept_as_credit": 'Оплата получена — +{credited} ⚡, на балансе {balance} ⚡. Файл уже устарел, поэтому ничего не конвертировано; пришли его снова — оплата пойдёт с баланса.',
        "job_started": '🔄 Конвертирую {src} → {target}… списано {price} ⚡, осталось {balance} ⚡.',
        "job_started_free": '🔄 Конвертирую {src} → {target} (бесплатно)…',
        "job_progress": '⏳ Конвертация ещё идёт — прошло {elapsed} мин. Напишу снова через {next} мин., а не позже чем через {last} мин. сообщу, чем всё закончилось.',
        "job_progress_last": '⏳ Конвертация всё ещё идёт — прошло {elapsed} мин. Последнее сообщение — через {last} мин.: к тому времени она закончится или будет остановлена, а ⚡ вернётся на баланс.',
        "job_stop_button": '⏹ Остановить',
        "job_stop_button_queued": '✖ Убрать из очереди',
        "job_done": '✅ {src} → {target} готово.',
        "balance_left_line": 'На балансе осталось {balance} ⚡.',
        "job_user_stopped": '⏹ Остановлено — списанные при старте {price} ⚡ остаются потраченными.',
        "job_user_stopped_free": '⏹ Остановлено.',
        "job_removed_from_queue": '✖ Убрано из очереди — ничего не списано.',
        "job_no_credit": 'Конвертация не началась: она стоит {price} ⚡, а на балансе {balance} ⚡. Ничего не списано — /recharge пополнит баланс.',
        "job_refunded_line": '{price} ⚡ вернулись на баланс — теперь {balance} ⚡.',
        "job_reason_refused": 'Не получилось конвертировать этот файл: {detail}',
        "job_reason_timeout": 'Конвертация не уложилась в {minutes} мин., и я её остановил. Владелец в курсе.',
        "job_reason_crash": 'Конвертация сломалась на моей стороне. Владелец в курсе.',
        "job_reason_too_large": '{target} получился на {mb} МБ — больше {limit} МБ, которые бот может отправить; JPG, WEBP или AVIF будут намного меньше. Владелец в курсе.',
        "job_reason_send_failed": 'Файл сконвертирован, но отправить его тебе не вышло. Владелец в курсе.',
        "job_reason_interrupted": 'Меня перезапустили посреди конвертации. Пришли файл снова через минуту.',
        "unknown_order": "Неизвестный заказ.",
        "payment_received_converting": "Платёж получен — конвертирую...",
        "mystars_empty": "Ты ещё не пользовался конвертером.",
        "mystars_total": "Всего потрачено: {total} ⭐ (только Stars — по фиатным пожертвованиям смотри ниже)\n\nПоследние:",
        "unrecognized_message": (
            "Это не файл, который я могу конвертировать — пришли файл или "
            "/formats, чтобы увидеть, что я принимаю. Назовёшь формат («heic», "
            "«epub») — скажу, во что он превращается."
        ),
        "unknown_command": "Я не знаю такую команду. Отправь /start, чтобы увидеть, что я умею.",
        # ---- /formats ----
        "category_document": "документ",
        "category_data": "данные",
        "category_subtitle": "субтитры",
        "formats_title": "📁 Что я конвертирую",
        "formats_intro": (
            "{sources} форматов на вход, {targets} на выход — всего {pairs} "
            "комбинаций. Пришли файл, и я покажу, во что его можно превратить; "
            "нажми на категорию ниже, чтобы увидеть весь список."
        ),
        "formats_highlights": (
            "Из менее очевидного:\n"
            "• Фото с iPhone (HEIC) → JPG или PNG\n"
            "• Любая картинка — или целый альбом сразу — в один PDF\n"
            "• PDF или EPUB → PNG, JPG или обычный текст\n"
            "• Документ Word → PDF, HTML или Markdown\n"
            "• CSV, JSON или XML → таблица XLSX\n"
            "• Субтитры: SRT, VTT и ASS между собой или просто их текст"
        ),
        "formats_reads": "Читает",
        "formats_writes": "Пишет",
        "formats_category_title": "📁 Файлы: {category}",
        "formats_lookup": ".{ext} — это файл категории «{category}». Я преобразую его в: {targets}",
        "formats_lookup_none": (
            "Я умею читать .{ext}, но на этом сервере не во что его превратить."
        ),
        "formats_lookup_unknown": (
            "Я не знаю «.{ext}» — /formats покажет все форматы, которые я умею."
        ),
        "formats_hint": "/formats - все форматы, которые я читаю и пишу",
        "btn_more_formats": "⋯ Ещё форматы",
        "btn_fewer_formats": "‹ Меньше",
        "btn_what_formats": "📁 Что ты умеешь конвертировать?",
        "btn_formats_back": "‹ Все категории",
        "convert_options_prompt_batch": (
            "Принято — {count} файлов, всего {size}. Во что конвертировать:"
            "\n\n{price_line}"
        ),
        "converted_file_caption_zip": "Готово — {items} файлов, в zip-архиве.",
        "converted_file_caption_pdf": "Готово — {items} картинок, по одной на страницу.",
        "converted_file_caption_pages": "Готово — {items} страниц, в zip-архиве.",
        "converted_docx_note": (
            "Текст — настоящий текст, его можно править: заголовки там, где в "
            "PDF строка была крупнее остальных, полужирный там, где он был, и "
            "картинки в том же порядке. Вёрстка страницы не переносится: "
            "колонки идут одна за другой, таблица превращается в свой текст, а "
            "разбивка на страницы остаётся такой, какой была в PDF."
        ),
        "converted_layout_note": (
            "Заголовки, выделения, списки и таблицы на месте. Вёрстка страницы "
            "не копируется точь-в-точь, а пересобирается заново — Word на этом "
            "сервере нет."
        ),
        "batch_mixed_formats": (
            "Эти файлы разных форматов, так что отправляй их по одному — или "
            "набор картинок, который я соберу в один PDF."
        ),
        "price_free": "Бесплатно",
        "price_not_supported": "не поддерживается",
        "price_cloud_api_note": "(ограничение облачного Bot API в 20 МБ на скачивание)",
        "price_extra_per_100mb": "{stars} ⚡ + {extra} ⚡ за каждые дополнительные 100 МБ",
        "price_coming_soon": '🔜 Скоро: более выгодные цены и больший максимальный размер файла.',
    },
}


# Every problem a person can run into ends with its code, and the code is what
# puts a "Report the issue" button under it -- see problems.py. Imported here,
# below the tables, because it is pure data and nothing above needs it.
import problems  # noqa: E402

_BOT = "convert_bot"


def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))


async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler
    call. Falls back to "en" for a user who hasn't chosen a language yet
    (only reachable outside /start's first-run gate, e.g. someone who sends
    a file before ever running /start)."""
    cached = context.user_data.get("lang")
    if cached:
        return cached
    lang = await asyncio.to_thread(db.get_user_language, user_id) or "en"
    context.user_data["lang"] = lang
    return lang


# ---------------------------------------------------------------------------
# The slash menu, in the other two languages
# ---------------------------------------------------------------------------
# English lives in BOT_COMMANDS in bot.py, where the menu can be read by
# reading the file. These are the same commands for a client whose language is
# Uzbek or Russian; shared_features.publish_commands() sends one list per
# language and Telegram picks the matching one.
#
# Deliberately absent: /language, /en, /uz and /rus. Each of the three is
# written in the language it switches TO, and /language is written in all
# three at once, because they are the way back for somebody who chose the
# wrong one. Translating them would make the menu of a Russian client offer
# three lines of Russian, one of which is the only route out.
#
# A command missing from here keeps its English description rather than
# vanishing from that language's menu -- a half-translated menu is a menu
# with commands missing, and a missing command reads as a bot that cannot do
# the thing. Kept honest by tests/test_menu.py, which fails on a command that
# has no entry here and on an entry naming a command that no longer exists.

COMMAND_MENU = {
    "uz": {
        "start": "Bu bot nima qiladi va qanday boshlash kerak",
        "convert": "Faylni o'girish — yoki shunchaki menga yuboring",
        "formats": "Men o'qiydigan va yozadigan barcha formatlar",
        "cancel": "Kutayotgan amalimni to'xtatish",
        "help": "Nimalar qila olaman",
        "balance": "⚡ kreditingiz va u qayerga sarflangani",
        "recharge": "⚡ kredit to'ldirish",
        "paysupport": "To'lov bilan muammo",
        "privacy": "Siz haqingizda nimalarni saqlayman",
        "terms": "Botdan foydalanish shartlari",
        "deletemydata": "Siz haqingizdagi hamma narsani o'chirish",
    },
    "ru": {
        "start": "Что этот бот делает и с чего начать",
        "convert": "Конвертировать файл — или просто пришлите его",
        "formats": "Все форматы, которые я читаю и пишу",
        "cancel": "Остановить то, чего я жду",
        "help": "Что я умею",
        "balance": "Ваш ⚡ кредит и куда он ушёл",
        "recharge": "Пополнить ⚡ кредит",
        "paysupport": "Проблема с оплатой",
        "privacy": "Что я о вас храню",
        "terms": "Для чего можно пользоваться ботом",
        "deletemydata": "Удалить всё, что я о вас храню",
    },
}
