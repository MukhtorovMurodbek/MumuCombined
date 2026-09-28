"""Everything the public bots say, in English, Uzbek and Russian.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("text.py is loaded section by section by main.py -- run main.py")


# ─── module: sticker_bot.i18n ────────────────────────────────────────────────
"""Translation strings for StickerBot's end-user-facing text (English, Uzbek, Russian)."""
import asyncio

import db

SUPPORTED_LANGUAGES = ("en", "uz", "ru")
LANGUAGE_LABELS = {"en": "English 🇬🇧", "uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺"}

LANGUAGE_PROMPT = (
    "👋 Welcome! / Xush kelibsiz! / Добро пожаловать!\n\n"
    "Please choose your language / Iltimos, tilni tanlang / "
    "Пожалуйста, выберите язык:"
)

STRINGS = {
    "en": {
        "flood_wait": "You're going faster than I can keep up with — give it about {seconds} second(s) and carry on.",

        "sibling_blurb": "Also part of this bot family, see below \U0001f447",
        "donation_nudge": (
            "💙 If this bot's been useful: hosting/API costs are covered by whoever's "
            "running it, and /donate is a totally optional way to help keep it alive. "
            "No pressure either way!"
        ),
        "donate_unknown_currency": 'Unknown currency "{currency}" — try xtr or usd.',
        "donate_currency_not_configured": "{currency} donations aren't set up on this bot yet — try Stars instead.",
        "donate_invalid_amount": "That's not a valid amount — try e.g. /donate 500 or /donate 5 usd.",
        "donate_prompt": (
            "Thank you for contributing — it goes directly toward this bot's "
            "hosting and API costs. Choose an amount below, or Custom to enter "
            "your own (you can also send /donate <number> [usd] directly)."
        ),
        "donate_custom_button": "✏️ Custom {symbol}",
        "donate_too_many_stars": "That's a lot of stars! Keep it under {max} ⭐ per donation.",
        "donate_out_of_range": "{currency} donations need to be between {lo} and {hi} {symbol}.",
        "donate_invoice_title": "Contribute to hosting",
        "donate_invoice_description": "Goes towards what this bot costs to run, and adds {credited} ⚡ of credit to your balance for conversions in ConvertBot.",
        "donate_invoice_label": "Hosting contribution",
        "donate_invoice_description_fiat": 'A one-time voluntary donation towards hosting costs. Thank you!',
        "donate_prompt_credit": 'Stars you pay become ⚡ credit for conversions in ConvertBot. Your next {left} ⭐ earn {each} ⚡ each ({mult}×): {rate} ⚡ of ordinary credit plus a bonus that expires {days} days after payment. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_prompt_credit_base": 'Stars you pay become ⚡ credit for conversions in ConvertBot, {rate} ⚡ per ⭐. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_invoice_error": "⚠️ Telegram wouldn't create that invoice: {error}",
        "stars_unit": "Stars",
        "donate_custom_ask": "How many {unit} would you like to donate? Reply with a number.",
        "donate_invalid_amount_retry": "That's not a valid amount — send /donate to try again.",
        "donate_thanks": "🙏 Thank you for the {amount} ⭐ — genuinely appreciated!",
        "topup_thanks": "🙏 Thank you for donating {stars} ⭐ — it helps keep the bots running.\n\nAs a thank-you, you've received {total} ⚡ of credit in {convert_bot} to use on file conversions. Your credit there: {balance} ⚡.",
        "topup_thanks_bonus": 'Of that, {bonus} ⚡ is bonus credit and expires on {date}.',
        "credit_cannot_be_withdrawn": '⚡ is credit for conversions in ConvertBot, and can NOT be withdrawn or turned back into Stars. A problem with a payment? /paysupport',
        "paysupport_text": '💳 Help with a payment\n\nPayments are FINAL: Stars are NOT refunded, and ⚡ credit can NOT be withdrawn or turned back into Stars.\n\nIf a payment went wrong — you were charged and no credit arrived, or you were charged twice — write to {contact} with the date, the amount and your Telegram id, {user_id}. It will be checked and put right with credit.\n\n/balance lists every payment and what it added.',
        "report_button": '🐞 Add my details',
        "problem_logged_note": "This is already written down for the bot's owner — the code, the time and the version, and nothing about you.",
        "report_disclaimer": "📨 Add your own details to this problem?\n\nAlready recorded, with you left out of it: the bot's name, the error code {code}, the incident number {incident}, when it happened and the bot's version.\n\nTapping Send adds four things: your Telegram user ID, your @username if you have one, the language you picked, and whether this chat is private or a group. Not what you wrote, and not the file you sent.\n\nIt lets your case be found in the logs, which is usually what makes a rare problem fixable. Entirely your choice.",
        "report_send": '📨 Send my details',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — your details are on incident {incident} now, which is what makes this one findable.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent. The problem itself stays logged.',
        "report_failed": "⚠️ The report couldn't be sent right now. Please try again later.",
        "report_invalid": 'This button no longer works.',
        "crash_notice": "⚠️ Something went wrong on the bot's side while handling that, so it wasn't done. Please try again in a moment.",
        "sandbox_notice": "🧪 Test mode — no real Stars were charged for this.",
        "balance_header": "⚡ Your balance: {balance}",
        "balance_totals": "Paid {paid} ⭐ in total · credited {credited} ⚡ · spent {spent} ⚡",
        "balance_rate": 'Your next {left} ⭐ earn {each} ⚡ each ({mult}×).',
        "balance_rate_base": '1 ⭐ buys {rate} ⚡.',
        "balance_bonus_line": 'Of that, {bonus} ⚡ is bonus credit — {soon} ⚡ of it expires on {date}.',
        "balance_recent": "Recent:",
        "balance_empty_hint": "/donate adds credit whenever you want some.",
        "bot_short_description": (
            "Turns images, GIFs and videos into Telegram sticker packs."
        ),
        "bot_description": (
            "Send a picture, a GIF or a video and this bot builds it into a sticker pack that "
            "belongs to you.\n"
            "\n"
            "Share a pack for someone else to add to, or bulk-import one from another Telegram "
            "pack or a WhatsApp export.\n"
            "\n"
            "English, Uzbek and Russian. /privacy says what it keeps about you."
        ),

        "privacy_heading": "🔒 Privacy",
        "privacy_kept_heading": "What this bot keeps:",
        "privacy_stored": (
            "• your Telegram user id, and the language you chose\n"
            "• the packs you made here: each one's name and title, and the display name and "
            "username you had at the time\n"
            "• who you gave add-access to a pack, and the share links you created\n"
            "• a timestamp each time you use the bot, so its owner can tell whether anyone is "
            "using it\n"
            "• a record of any donation: the amount and Telegram's payment id\n"
            "• whatever the bot is in the middle of doing with you, until it is finished"
        ),
        "privacy_problems_heading": "When something goes wrong:",
        "privacy_problems": (
            "Every error this bot shows anybody is written down by itself: the error code, an "
            "incident number, when it happened and the bot's version. Nothing in that is about "
            "you — not your id, not your name, not what you sent. A fault nobody reports is "
            "still a fault, which is why it does not wait to be asked.\n"
            "\n"
            "\"Add my details\" under an error offers to attach four things to that one "
            "incident: your Telegram user id, your @username if you have one, the language you "
            "picked, and whether the chat is private or a group. All four are named on screen "
            "first, and nothing is sent unless you tap Send. What you wrote and the files you "
            "sent are never part of it.\n"
            "\n"
            "Those four are cleared after 30 days on their own, and /deletemydata clears them "
            "straight away. The record of the error stays — it still happened — it just stops "
            "saying who hit it. The records themselves are deleted after 180 days."
        ),
        "privacy_seen_by_heading": "Who else sees it:",
        "privacy_seen_by": (
            "• Telegram, which carries every message both ways and sets its own terms\n"
            "• the hosting provider this bot runs on, and the database it writes to"
        ),
        "privacy_others": (
            "• and nobody beyond those — stickers are made on the machine the bot runs on, and no outside "
            "service is called"
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
        "terms_specific": (
            "Stickers: upload what is yours to upload. Do not build packs out of someone else's "
            "work without their permission, and do not make packs of anything Telegram's own "
            "terms forbid. A pack lives on Telegram once it exists — this bot can forget one, "
            "but only its owner can delete it, from Telegram."
        ),
        "terms_money": 'Money: /donate is voluntary and goes towards what the bots cost to run. A payment in Stars also adds ⚡ credit for conversions in ConvertBot: 2 ⚡ per ⭐, or 6 for your first 500 Stars ever and 4 for the next 500. The part above 2 is bonus credit and expires 90 days after the payment. Payments are FINAL: Stars are NOT refunded, and credit can NOT be withdrawn or turned back into Stars. Telegram handles every payment and the bot never sees a card number. A payment that went wrong: /paysupport.',
        "terms_no_warranty": (
            "No promises: one person runs this, it is free, and it can be slow, wrong, or off "
            "entirely without warning. Keep your own copy of anything that matters."
        ),
        "policy_full_text": "Full text: {url}",
        "policy_contact": "Questions, complaints or a data request: {contact}",
        "delete_data_confirm": "⚠️ This erases what this bot holds on you. There is no undo.",
        "delete_data_consequences": "The bot forgets the packs you made through it: it stops listing them and can no longer add to them. The packs themselves keep working for everyone who installed them — deleting one for real is done from Telegram, by you. Your language, your share links and anyone's add-access to your packs go as well.\n\nDonation records stay, without your username, because a dispute about a payment is settled against them. Your ⚡ balance stays too, and is still yours if you come back.",
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
        "cancel_button_donation": "💸 Donation amount",
        "cancel_item_donation": "the donation amount I asked you for",
        "cancel_item_stale_prompt": "a leftover prompt that was still waiting on an answer",
        "cancel_item_new_pack": "the new pack you were naming",
        "cancel_button_new_pack": "🆕 Naming a new pack",
        "cancel_item_rename": "renaming \"{title}\"",
        "cancel_button_rename": "✏️ Renaming a pack",
        "cancel_item_editing": "editing \"{title}\"",
        "cancel_button_editing": "📦 Editing a pack",

        "start_intro": (
            "Hey! I turn your images/GIFs/videos/stickers into Telegram sticker "
            "packs, and I can grab videos from Instagram/TikTok links.\n\n"
        ),
        "help_text": "Commands:\n/newpack - start a new sticker pack\n/addsticker - add stickers to an existing pack\n/mypacks - list your packs\n/import <pack link/name> - (while editing) bulk-copy stickers from another Telegram pack, or send a WhatsApp sticker pack .zip/.wastickers file\n/done - finish editing a pack\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/whomade <pack link/name> - see who created a pack (if made through this bot)\n/donate - chip in for hosting costs (totally optional)\n/en, /uz, /rus - switch language (or /language, which asks)\n/balance - your ⚡ credit\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n/convert - converting files lives in ConvertBot now; this points you there\n\nWhile editing a pack: send images, GIFs, videos, or static/video stickers to add them.\nSend emoji after one to tag it with that emoji.\n\nTap a pack from /mypacks to rename it, set up co-editing so someone else can add stickers to it too, or delete it for good (owner-only, asks twice before it actually happens).\n\nWant to grab a video from Instagram/TikTok, or convert a file to another format? Those live in the sibling bots below now.\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n",
        "whomade_usage": "Usage: /whomade <pack name or t.me/addstickers link>",
        "whomade_not_found": (
            "I don't have a record of that pack — either it wasn't created "
            "through this bot, or the name/link isn't right."
        ),
        "whomade_result": "📦 \"{title}\"\nCreated by {creator} on {date} (via this bot).",
        "coedit_link_invalid": "That co-editing link isn't valid — it may have been reset by the pack owner.",
        "coedit_pack_gone": "That pack doesn't seem to exist anymore.",
        "coedit_own_pack": "That's your own pack — use /mypacks to manage it.",
        "coedit_joined_intro": (
            "You've been added as a co-editor on \"{title}\"! Send images, GIFs, "
            "videos, or static/video stickers to add them — default emoji is 😭, "
            "send emoji right after to retag the last one. /done when finished."
        ),
        "btn_new_pack": "➕ New pack",
        "btn_my_packs": "📁 My packs",
        "btn_help": "❓ Help",
        "btn_back": "⬅️ Back",
        "no_packs_yet": "No packs yet — tap New pack or use /newpack.",
        "your_packs": "Your packs:",
        "not_your_pack": "That's not your pack.",
        "pack_detail_title": "📦 {title}",
        "btn_open_pack": "🔗 Open pack",
        "btn_add_stickers": "➕ Add stickers",
        "btn_rename": "✏️ Rename",
        "btn_coedit": "👥 Co-edit",
        "btn_delete_pack": "🗑️ Delete pack",
        "coedit_count_some": "{count} co-editor(s) so far.",
        "coedit_count_none": "No co-editors yet.",
        "coedit_message": (
            "👥 Co-editing \"{title}\"\n\n"
            "Link: {link}\n\n"
            "Share it — anyone who opens it can add stickers to this pack "
            "through the bot (they still get added under your ownership).\n\n"
            "{editors_line}\n\n"
            "Reset the link to stop it from granting access to anyone new."
        ),
        "btn_reset_link": "🔄 Reset link",
        "only_owner_coedit": "Only the pack owner can manage co-editing.",
        "link_reset_confirm": "Link reset — the old one no longer works.",
        "only_owner_rename": "Only the pack owner can rename it.",
        "rename_prompt": "Send the new title for \"{title}\".",
        "rename_broken_state": "Something went wrong — try Rename again from /mypacks.",
        "btn_back_to_pack": "⬅️ Back to pack",
        "renamed_success": "Renamed to \"{title}\".",
        "renamed_failed": "Couldn't rename it: {error}",
        "only_owner_delete": "Only the pack owner can delete it.",
        "btn_delete": "🗑️ Delete",
        "btn_cancel_inline": "⬅️ Cancel",
        "delete_confirm1": (
            "⚠️ Delete \"{title}\"? This removes it from Telegram for everyone who "
            "has it, including any co-editors, and can't be undone."
        ),
        "btn_delete_confirm": "🗑️ Yes, permanently delete it",
        "delete_confirm2": "❗ Last check — permanently delete \"{title}\"? There's no undo after this.",
        "delete_failed": "⚠️ Couldn't delete it: {error}",
        "btn_my_packs_back": "⬅️ My packs",
        "delete_success": "🗑️ \"{title}\" has been permanently deleted.",
        "newpack_title_prompt": "What should the pack title be?",
        "title_empty": "That's empty — send an actual title for the pack.",
        "title_truncated": "Telegram caps pack titles at 64 characters — using \"{title}\".",
        "editing_intro_new": (
            "Send images, GIFs, videos, or static/video stickers — each one "
            "is added with the default 😭 emoji. Send emoji right after to retag "
            "the last one. /done when finished."
        ),
        "no_packs_for_add": "You don't have any packs yet. Use /newpack first.",
        "pick_pack_prompt": "Which pack? Tap it, then \"➕ Add stickers\".",
        "editing_intro_add": (
            "Send images, GIFs, videos, or static/video stickers to add — default "
            "emoji is 😭, send emoji right after to retag the last one. /done when finished.\n\n"
            "Tip: sending a sticker that's already in this pack removes it instead of "
            "adding a duplicate."
        ),
        "status_verb_creating": "Creating",
        "status_verb_editing": "Editing",
        "status_line": "📝 {verb} \"{title}\" — {count} sticker(s) added this session",
        "status_default_title": "this pack",
        "btn_delete_pack_yes": "🗑️ Yes, delete the pack",
        "btn_cancel": "Cancel",
        "remove_last_confirm": (
            "That's the only sticker left in this pack — removing it deletes the "
            "*whole pack* from Telegram, since packs can't be empty. Are you sure?"
        ),
        "remove_failed": "⚠️ Couldn't remove that sticker: {error}",
        "remove_success": "🗑️ That sticker was already in this pack — removed it.",
        "keep_pack": "Okay, kept the pack as-is.",
        "pack_deleted_empty": "🗑️ Pack deleted (it had no stickers left).",
        "pack_deleted_note": "❌ Pack deleted.",
        "image_process_failed": "Couldn't process that image: {error}",
        "added_default_emoji": "Added {emoji} — send an emoji to retag it.",
        "last_attempt_failed": "⚠️ Last attempt failed — send another item to retry, or /cancel.",
        "converting_video": "Converting to a video sticker...",
        "video_convert_failed_redirect": (
            "{error}\n\nCan't turn this into a sticker, but if you just want the "
            "file in a normal format, @ConvertBot can do that — just send the "
            "same file over there 👇"
        ),
        "video_convert_generic_failed": "Couldn't convert that: {error}",
        "added_video_default_emoji": (
            "Added as a video sticker with default {emoji}. Send emoji "
            "now to retag it, another image/GIF/video to keep going, or /done to finish."
        ),
        "animated_not_supported": (
            "Animated (Lottie/.tgs) stickers aren't supported — send a static "
            "image, a GIF/video, or a static/video sticker instead."
        ),
        "import_usage": (
            "Send /import <telegram pack link or name> to copy stickers from "
            "another public Telegram pack into this one — or just send a "
            "WhatsApp sticker pack .zip/.wastickers file directly."
        ),
        "import_invalid_source": "That doesn't look like a valid pack name or t.me/addstickers link.",
        "import_fetching": "Fetching stickers from \"{source}\"...",
        "import_summary_head": "Imported {added} sticker(s) from \"{source}\"",
        "import_summary_skipped": ", skipped {skipped} unsupported (animated/Lottie)",
        "import_summary_failed": ", {failed} failed",
        "import_summary_tail": ". Keep sending more, or /done to finish.",
        "done_standalone_hint": (
            "Nothing to finish — you aren't editing a pack right now. Start one "
            "with /newpack, or tap Add stickers on a pack from /mypacks."
        ),
        "import_standalone_hint": (
            "Start or open a pack first (/newpack, or tap Add stickers on a pack from "
            "/mypacks), then use /import <link> inside that session."
        ),
        "whatsapp_reading": "Reading the WhatsApp sticker pack...",
        "whatsapp_summary_head": "Imported {added} sticker(s) from the WhatsApp pack",
        "not_emoji_message": "Send an image/GIF/video/sticker to add, emoji to retag the last one, or /done.",
        "no_sticker_to_tag": "Add a sticker first, then send emoji to tag it.",
        "retagged_success": "Retagged as {emojis}.",
        "retag_failed": "Couldn't update the emoji: {error}",
        "nothing_added_yet": "You haven't added anything yet. Send an image first.",
        "done_success": (
            "✅ Finished \"{title}\" — {count} sticker(s) added this session.\n\n"
            "All set: https://t.me/addstickers/{pack_name}"
        ),
        "convert_redirect": (
            "File conversion (images/video/audio, not sticker-specific) moved to "
            "@ConvertBot — tap below to open it."
        ),
        "cancelled_status_note": "❌ Cancelled.",
        "unrecognized": "Not sure what that's for — try /newpack, /mypacks, or /help.",
        "unknown_command": "I don't recognize that command. Send /help to see what I can do.",
        "err_invalid_name": (
            "⚠️ Telegram rejected the pack's internal name — this usually happens when the "
            "title starts with a number or symbol. Send /cancel, then /newpack again with a "
            "title that starts with a letter (e.g. \"My 2007\" instead of \"2007\")."
        ),
        "err_name_occupied": (
            "⚠️ That pack's internal name collided with an existing one (rare, just bad luck). "
            "Send /cancel, then /newpack again to get a fresh one."
        ),
        "err_too_many_stickers": "⚠️ This pack is already at Telegram's sticker limit (120) — start a new pack with /newpack instead.",
        "err_bad_format": "⚠️ Telegram didn't accept that file's format for this pack — try a different image.",
        "err_generic": "⚠️ Telegram rejected that: {msg}\n\nYou can try again, or /cancel to stop.",
        "err_timed_out": (
            "⚠️ Telegram didn't confirm in time — it may have gone through anyway, "
            "so check the pack before retrying to avoid a duplicate. You can try "
            "again, or /cancel to stop."
        ),
        "restarting_send_again": "🔄 I'm being updated right now — give me a few seconds and send that again.",
        "update_soon_try_later": "🔧 I'm being updated in a moment, so I can't start anything new right now — please try again in about {minutes} minute(s). I'll message you when I'm back.",
        "update_soon_try_later_soon": "🔧 I'm being updated right now, so I can't start anything new — please try again shortly. I'll message you when I'm back.",
        "update_will_reset": "🔧 Heads up: I'm about to be updated, and what you have going right now will be reset. You'll be able to start it again in a few minutes.",
        "update_done_try_now": '✅ The update is done — go ahead and try again now.',
        "video_convert_ffmpeg_missing": (
            "ffmpeg isn't installed on this host, so GIF/video stickers can't "
            "be converted. Install it with 'apt install ffmpeg' (Linux), "
            "'brew install ffmpeg' (Mac), or add a Windows build to PATH."
        ),
        "video_convert_empty_file": "That file came through empty — try sending it again.",
        "video_convert_too_big": (
            "Couldn't compress this clip under Telegram's 256 KB video-sticker "
            "limit ({note}). Try a shorter or visually simpler clip."
        ),
        "import_pack_not_found": (
            "Couldn't find a sticker pack called \"{source}\" — double-check "
            "the link/name (it must be public)."
        ),
        "import_bad_zip": "That doesn't look like a valid .zip/.wastickers file.",
        "import_zip_no_images": "No usable images found inside that zip.",
    },
    "uz": {
        "flood_wait": 'Juda tez yuboryapsiz — {seconds} soniyacha kutib, keyin davom eting.',
        "sibling_blurb": 'Oilamizdagi boshqa botlar pastda 👇',
        "donation_nudge": "💙 Bot sizga foydali bo'lgan bo'lsa: server va API xarajatlarini botni yuritayotgan odam o'z hisobidan qoplaydi. /donate orqali bunga hissa qo'shishingiz mumkin — bu mutlaqo ixtiyoriy.",
        "donate_unknown_currency": '"{currency}" degan valyuta yo\'q — xtr yoki usd deb yozing.',
        "donate_currency_not_configured": "Bu botda hozircha {currency} bilan xayriya qilib bo'lmaydi — Stars'dan foydalaning.",
        "donate_invalid_amount": "Miqdor noto'g'ri — masalan, /donate 500 yoki /donate 5 usd deb yozing.",
        "donate_prompt": "Hissangiz uchun rahmat — u to'g'ridan-to'g'ri botning server va API xarajatlariga ketadi. Quyidagi miqdorlardan birini tanlang yoki o'zingiz yozish uchun «Boshqa»ni bosing (/donate <son> [usd] deb ham yuborishingiz mumkin).",
        "donate_custom_button": "✏️ Boshqa {symbol}",
        "donate_too_many_stars": "Bu juda ko'p! Bir martalik xayriya {max} ⭐ dan oshmasin.",
        "donate_out_of_range": "{currency} bilan xayriya {lo} dan {hi} {symbol} gacha bo'lishi kerak.",
        "donate_invoice_title": 'Server xarajatlariga hissa',
        "donate_invoice_description": "Botlar xarajatlariga ketadi va ConvertBot'dagi konvertatsiyalar uchun balansingizga {credited} ⚡ kredit qo'shadi.",
        "donate_invoice_label": 'Xayriya',
        "donate_invoice_description_fiat": 'Server xarajatlari uchun bir martalik ixtiyoriy xayriya. Rahmat!',
        "donate_prompt_credit": "To'lagan Stars'ingiz ConvertBot'da konvertatsiyalarga sarflanadigan ⚡ kreditga aylanadi. Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×): {rate} ⚡ oddiy kredit, qolgani esa to'lovdan {days} kun o'tgach muddati tugaydigan bonus. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_prompt_credit_base": "To'lagan har bir ⭐ ConvertBot'da konvertatsiyalarga sarflanadigan {rate} ⚡ kreditga aylanadi. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_invoice_error": "⚠️ Telegram to'lov hisobini yaratmadi: {error}",
        "stars_unit": "Stars (yulduzcha)",
        "donate_custom_ask": 'Qancha {unit} xayriya qilmoqchisiz? Faqat sonni yozib yuboring.',
        "donate_invalid_amount_retry": "Miqdor noto'g'ri — qaytadan urinish uchun /donate yuboring.",
        "donate_thanks": '🙏 {amount} ⭐ uchun katta rahmat!',
        "topup_thanks": "🙏 {stars} ⭐ xayriyangiz uchun rahmat — bu botlarning ishlashiga yordam beradi.\n\nMinnatdorchilik sifatida {convert_bot} botida fayllarni o'girish uchun {total} ⚡ kredit oldingiz. U yerdagi balansingiz: {balance} ⚡.",
        "topup_thanks_bonus": 'Shundan {bonus} ⚡ — bonus kredit, uning muddati {date} kuni tugaydi.',
        "credit_cannot_be_withdrawn": "⚡ — ConvertBot'dagi konvertatsiyalar uchun kredit: uni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. To'lovda muammo bo'lsa: /paysupport",
        "paysupport_text": "💳 To'lov bo'yicha yordam\n\nTo'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.\n\nTo'lovda xatolik bo'lgan bo'lsa — pul yechilgan-u, kredit tushmagan bo'lsa yoki ikki marta yechilgan bo'lsa — {contact} manziliga to'lov sanasi, miqdori va Telegram ID raqamingizni ({user_id}) yozib yuboring. Tekshirilib, kredit bilan to'g'rilab beriladi.\n\n/balance har bir to'lovni va u qancha kredit qo'shganini ko'rsatadi.",
        "report_button": "🐞 Ma'lumotlarimni qo'shish",
        "problem_logged_note": "Bu muammo bot egasi uchun allaqachon yozib olindi — kodi, vaqti va bot versiyasi. Siz haqingizda hech narsa yo'q.",
        "report_disclaimer": "📨 Bu muammoga o'zingiz haqingizdagi ma'lumotni ham qo'shasizmi?\n\nSizsiz yozib olingani: bot nomi, {code} xato kodi, {incident} hodisa raqami, qachon yuz bergani va bot versiyasi.\n\n\"Yuborish\" tugmasi to'rt narsani qo'shadi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. Yozganingiz ham, yuborgan faylingiz ham emas.\n\nShunda sizning holatingizni loglardan topib bo'ladi — kam uchraydigan muammoni odatda shu tuzatib beradi. To'liq o'zingiz hal qilasiz.",
        "report_send": "📨 Ma'lumotlarimni yuborish",
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — ma'lumotlaringiz {incident} hodisasiga biriktirildi, endi uni topish oson.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi. Muammoning o'zi yozib olingan holicha qoladi.",
        "report_failed": "⚠️ Hozir xabarni yuborib bo'lmadi. Keyinroq qayta urinib ko'ring.",
        "report_invalid": 'Bu tugma endi ishlamaydi.',
        "crash_notice": "⚠️ Buni bajarishda bot tomonida xatolik yuz berdi, shuning uchun amal bajarilmadi. Birozdan keyin qayta urinib ko'ring.",
        "sandbox_notice": '🧪 Test rejimi — haqiqiy Stars yechilmadi.',
        "balance_header": "⚡ Balansingiz: {balance}",
        "balance_totals": "Jami {paid} ⭐ to'landi · {credited} ⚡ qo'shildi · {spent} ⚡ sarflandi",
        "balance_rate": 'Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×).',
        "balance_rate_base": '1 ⭐ = {rate} ⚡.',
        "balance_bonus_line": 'Shundan {bonus} ⚡ — bonus kredit; {soon} ⚡ ning muddati {date} kuni tugaydi.',
        "balance_recent": 'Oxirgi amallar:',
        "balance_empty_hint": '/donate orqali istalgan paytda kredit olishingiz mumkin.',
        "bot_short_description": (
            "Rasm, GIF va videolardan Telegram stiker to'plamlarini yasaydi."
        ),
        "bot_description": (
            "Rasm, GIF yoki video yuboring — bot undan o'zingizga tegishli stiker to'plamini "
            "yig'adi.\n"
            "\n"
            "To'plamni boshqa birov ham to'ldira olishi uchun havolasini ulashing yoki boshqa "
            "Telegram to'plamidan hamda WhatsApp arxividan ko'chirib oling.\n"
            "\n"
            "Ingliz, o'zbek va rus tillarida. /privacy nima saqlanishini aytadi."
        ),

        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• shu bot orqali yaratgan to'plamlaringiz: har birining nomi va sarlavhasi, o'sha paytdagi ismingiz va foydalanuvchi nomingiz\n• to'plamlaringizga kimga qo'shish huquqi berganingiz va yaratgan havolalaringiz\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nXato ostidagi \"Ma'lumotlarimni qo'shish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• boshqa hech kim — stikerlar botning o'z serverida tayyorlanadi, tashqi xizmatlarga murojaat qilinmaydi",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
        "privacy_your_choices": "Nima qilishingiz mumkin:\n/deletemydata — bot siz haqingizda saqlagan ma'lumotlarni o'chirish\n/terms — botdan foydalanish shartlari\n\nBotni Telegramda bloklasangiz, u sizga yozmay qo'yadi, lekin hech narsa o'chmaydi. Ikkalasini ham xohlasangiz, avval /deletemydata yuboring.",
        "terms_heading": "📜 Shartlar",
        "terms_use": "Botdan maqsadiga ko'ra, qonun va Telegram qoidalari doirasida foydalaning. Uni boshqalarni bezovta qilish uchun ishlatmang va belgilangan cheklovlardan oshirib yuklamang — aks holda akkaunt bloklanadi.",
        "terms_specific": "Stikerlar haqida: faqat o'zingizga tegishli narsalarni yuklang. Birovning ijodidan ruxsatsiz va Telegram qoidalari taqiqlagan narsalardan to'plam yasamang. Yaratilgan to'plam Telegram'da saqlanadi — bot uni unutishi mumkin, lekin o'chirishni faqat egasi Telegram orqali qila oladi.",
        "terms_money": "Pul haqida: /donate — ixtiyoriy, mablag' botlar xarajatlariga ketadi. Stars'dagi to'lov ConvertBot'da konvertatsiyalar uchun ⚡ kredit ham beradi: har ⭐ uchun 2 ⚡, umumiy hisobda birinchi 500 ta Stars uchun esa 6 ⚡ dan, keyingi 500 tasi uchun 4 ⚡ dan. 2 ⚡ dan ortig'i bonus kredit bo'lib, to'lovdan 90 kun o'tgach muddati tugaydi. To'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Har bir to'lovni Telegram o'tkazadi, bot karta raqamingizni ko'rmaydi. To'lovda muammo bo'lsa: /paysupport.",
        "terms_no_warranty": "Kafolat yo'q: botni bir kishi yuritadi va u oldindan ogohlantirmasdan sekinlashishi, xato qilishi yoki butunlay to'xtab qolishi mumkin. Siz uchun muhim narsalarning nusxasini o'zingizda saqlang.",
        "policy_full_text": "To'liq matn: {url}",
        "policy_contact": "Savol, shikoyat yoki ma'lumot so'rovi uchun: {contact}",
        "delete_data_confirm": "⚠️ Bot siz haqingizda saqlagan ma'lumotlar o'chiriladi. Buni ortga qaytarib bo'lmaydi.",
        "delete_data_consequences": "Bot shu yerda yaratgan to'plamlaringizni unutadi: ular ro'yxatda ko'rinmaydi va ularga stiker qo'shib bo'lmaydi. To'plamlarning o'zi ularni o'rnatganlarda ishlashda davom etadi — butunlay o'chirishni Telegram orqali o'zingiz qilasiz. Til sozlamangiz, havolalaringiz va boshqalarga bergan qo'shish huquqlaringiz ham o'chiriladi.\n\nXayriya yozuvlari foydalanuvchi nomingizsiz saqlanib qoladi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi. ⚡ balansingiz ham saqlanadi — qaytib kelsangiz, u o'z joyida bo'ladi.",
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
        "cancel_button_donation": "💸 Xayriya miqdori",
        "cancel_item_donation": 'kiritilishi kutilayotgan xayriya miqdori',
        "cancel_item_stale_prompt": "javobsiz qolgan eski so'rov",
        "cancel_item_new_pack": "siz nom qo'yayotgan yangi to'plam",
        "cancel_button_new_pack": "🆕 Yangi to'plamga nom berish",
        "cancel_item_rename": "\"{title}\" nomini o'zgartirish",
        "cancel_button_rename": "✏️ To'plam nomini o'zgartirish",
        "cancel_item_editing": "\"{title}\" ni tahrirlash",
        "cancel_button_editing": "📦 To'plamni tahrirlash",
        "start_intro": "Salom! Rasm, GIF, video va stikerlaringizdan Telegram stiker to'plamlari yasayman, Instagram/TikTok havolalaridan video ham olib bera olaman.\n\n",
        "help_text": "Buyruqlar:\n/newpack - yangi stiker to'plami yaratish\n/addsticker - mavjud to'plamga stiker qo'shish\n/mypacks - to'plamlaringizni ko'rish\n/import <to'plam havolasi yoki nomi> - (tahrirlash vaqtida) boshqa Telegram to'plamidagi stikerlarni ko'chirish yoki WhatsApp to'plamining .zip/.wastickers faylini yuklash\n/done - to'plamni tahrirlashni yakunlash\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/whomade <to'plam havolasi yoki nomi> - to'plamni kim yaratganini bilish (shu bot orqali yaratilgan bo'lsa)\n/donate - server xarajatlariga hissa qo'shish (mutlaqo ixtiyoriy)\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/balance - ⚡ kreditingiz\n/paysupport - to'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n/convert - fayllarni o'girish endi ConvertBot'da; bu buyruq sizni o'sha yerga yo'naltiradi\n\nTo'plamni tahrirlash vaqtida rasm, GIF, video yoki statik/video stiker yuborsangiz, u to'plamga qo'shiladi.\nUndan keyin emoji yuborsangiz, o'sha stikerga shu emoji biriktiriladi.\n\n/mypacks'da to'plamni tanlab, nomini o'zgartirishingiz, boshqalar ham stiker qo'sha olishi uchun birgalikda tahrirlashni yoqishingiz yoki uni butunlay o'chirishingiz mumkin (faqat egasi; o'chirishdan oldin ikki marta so'raladi).\n\nInstagram/TikTok'dan video yuklab olish yoki faylni boshqa formatga o'girish kerakmi? Bu endi pastdagi boshqa botlarimizda.\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — /donate orqali to'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO'LMAYDI.\n\n",
        "whomade_usage": "Qanday ishlatiladi: /whomade <to'plam nomi yoki t.me/addstickers havolasi>",
        "whomade_not_found": (
            "Bu to'plam haqida ma'lumotim yo'q — u shu bot orqali yaratilmagan "
            "yoki nom/havola noto'g'ri."
        ),
        "whomade_result": '📦 "{title}"\n{date} kuni {creator} tomonidan shu bot orqali yaratilgan.',
        "coedit_link_invalid": "Bu havola yaroqsiz — ehtimol, to'plam egasi uni yangilagan.",
        "coedit_pack_gone": "Bu to'plam o'chirilganga o'xshaydi.",
        "coedit_own_pack": "Bu o'zingizning to'plamingiz — uni /mypacks orqali boshqaring.",
        "coedit_joined_intro": 'Siz "{title}" to\'plamiga hammuallif bo\'ldingiz! Rasm, GIF, video yoki statik/video stiker yuboring — ular to\'plamga qo\'shiladi (standart emoji: 😭). Oxirgi stikerning emojisini o\'zgartirish uchun darhol emoji yuboring. Tugatgach, /done ni bosing.',
        "btn_new_pack": "➕ Yangi to'plam",
        "btn_my_packs": "📁 Mening to'plamlarim",
        "btn_help": "❓ Yordam",
        "btn_back": "⬅️ Orqaga",
        "no_packs_yet": "Hali to'plamingiz yo'q — «Yangi to'plam» tugmasini bosing yoki /newpack yuboring.",
        "your_packs": "Sizning to'plamlaringiz:",
        "not_your_pack": "Bu sizning to'plamingiz emas.",
        "pack_detail_title": "📦 {title}",
        "btn_open_pack": "🔗 To'plamni ochish",
        "btn_add_stickers": "➕ Stiker qo'shish",
        "btn_rename": "✏️ Nomini o'zgartirish",
        "btn_coedit": '👥 Birgalikda tahrirlash',
        "btn_delete_pack": "🗑️ To'plamni o'chirish",
        "coedit_count_some": "Hozircha {count} ta hammuallif bor.",
        "coedit_count_none": "Hali hammualliflar yo'q.",
        "coedit_message": '👥 "{title}" — birgalikda tahrirlash\n\nHavola: {link}\n\nHavolani ulashing — uni ochgan har kim bot orqali bu to\'plamga stiker qo\'sha oladi (to\'plam baribir sizning nomingizda qoladi).\n\n{editors_line}\n\nYangi odamlar qo\'shilmasligi uchun havolani yangilashingiz mumkin.',
        "btn_reset_link": "🔄 Havolani yangilash",
        "only_owner_coedit": "Birgalikda tahrirlashni faqat to'plam egasi boshqara oladi.",
        "link_reset_confirm": "Havola yangilandi — eskisi endi ishlamaydi.",
        "only_owner_rename": "To'plamni faqat egasi qayta nomlay oladi.",
        "rename_prompt": "\"{title}\" uchun yangi nom yuboring.",
        "rename_broken_state": "Xatolik yuz berdi — /mypacks orqali «Nomini o'zgartirish»ni qaytadan bosing.",
        "btn_back_to_pack": "⬅️ To'plamga qaytish",
        "renamed_success": "\"{title}\" deb qayta nomlandi.",
        "renamed_failed": "Nomini o'zgartirib bo'lmadi: {error}",
        "only_owner_delete": "To'plamni faqat egasi o'chira oladi.",
        "btn_delete": "🗑️ O'chirish",
        "btn_cancel_inline": "⬅️ Bekor qilish",
        "delete_confirm1": '⚠️ "{title}" o\'chirilsinmi? U Telegram\'dan hamma uchun, jumladan hammualliflar uchun ham o\'chib ketadi. Buni ortga qaytarib bo\'lmaydi.',
        "btn_delete_confirm": "🗑️ Ha, butunlay o'chirilsin",
        "delete_confirm2": "❗ Oxirgi tekshiruv — \"{title}\" butunlay o'chirilsinmi? Bundan keyin ortga qaytarib bo'lmaydi.",
        "delete_failed": "⚠️ O'chirib bo'lmadi: {error}",
        "btn_my_packs_back": "⬅️ Mening to'plamlarim",
        "delete_success": "🗑️ \"{title}\" butunlay o'chirildi.",
        "newpack_title_prompt": "To'plamning nomi qanday bo'lsin?",
        "title_empty": "Nom bo'sh bo'lmasin — to'plam uchun nom yuboring.",
        "title_truncated": "Telegram to'plam nomini 64 belgigacha cheklaydi — \"{title}\" ishlatiladi.",
        "editing_intro_new": "Rasm, GIF, video yoki statik/video stiker yuboring — har biri 😭 emojisi bilan qo'shiladi. Oxirgi stikerning emojisini o'zgartirish uchun darhol emoji yuboring. Tugatgach, /done ni bosing.",
        "no_packs_for_add": "Hali to'plamingiz yo'q. Avval /newpack yuboring.",
        "pick_pack_prompt": "Qaysi to'plam? Uni bosing, keyin \"➕ Stiker qo'shish\"ni tanlang.",
        "editing_intro_add": "Qo'shish uchun rasm, GIF, video yoki statik/video stiker yuboring (standart emoji: 😭). Oxirgi stikerning emojisini o'zgartirish uchun darhol emoji yuboring. Tugatgach, /done ni bosing.\n\nMaslahat: to'plamda allaqachon bor stikerni yuborsangiz, u ikkinchi marta qo'shilmaydi — aksincha, to'plamdan olib tashlanadi.",
        "status_verb_creating": "Yaratilmoqda",
        "status_verb_editing": "Tahrirlanmoqda",
        "status_line": "📝 \"{title}\" {verb} — shu seansda {count} ta stiker qo'shildi",
        "status_default_title": "bu to'plam",
        "btn_delete_pack_yes": "🗑️ Ha, to'plam o'chirilsin",
        "btn_cancel": "Bekor qilish",
        "remove_last_confirm": "Bu to'plamdagi oxirgi stiker — uni olib tashlasangiz, *butun to'plam* Telegram'dan o'chadi, chunki to'plam bo'sh bo'lolmaydi. Ishonchingiz komilmi?",
        "remove_failed": "⚠️ Bu stikerni olib tashlab bo'lmadi: {error}",
        "remove_success": "🗑️ Bu stiker to'plamda allaqachon bor edi — uni olib tashladim.",
        "keep_pack": "Yaxshi, to'plam o'zgarishsiz qoldirildi.",
        "pack_deleted_empty": "🗑️ To'plam o'chirildi (unda stiker qolmagan edi).",
        "pack_deleted_note": "❌ To'plam o'chirildi.",
        "image_process_failed": "Rasmni qayta ishlab bo'lmadi: {error}",
        "added_default_emoji": "{emoji} bilan qo'shildi — boshqa emoji kerak bo'lsa, uni yuboring.",
        "last_attempt_failed": "⚠️ Oxirgi urinish muvaffaqiyatsiz tugadi — qayta urinish uchun boshqa narsa yuboring yoki /cancel qiling.",
        "converting_video": "Video stikerga aylantirilmoqda...",
        "video_convert_failed_redirect": "{error}\n\nBundan stiker yasab bo'lmaydi, lekin faylni boshqa formatga o'girish kerak bo'lsa, @ConvertBot yordam beradi — faylni o'sha yerga yuboring 👇",
        "video_convert_generic_failed": "Buni aylantirib bo'lmadi: {error}",
        "added_video_default_emoji": "Video stiker {emoji} emojisi bilan qo'shildi. Emojini o'zgartirish uchun hozir boshqasini yuboring, davom etish uchun yana rasm/GIF/video yuboring yoki tugatish uchun /done ni bosing.",
        "animated_not_supported": (
            "Animatsion (Lottie/.tgs) stikerlar qo'llab-quvvatlanmaydi — buning "
            "o'rniga statik rasm, GIF/video yoki statik/video stiker yuboring."
        ),
        "import_usage": "Boshqa ochiq Telegram to'plamidagi stikerlarni shu to'plamga ko'chirish uchun /import <to'plam havolasi yoki nomi> yuboring — yoki WhatsApp to'plamining .zip/.wastickers faylini to'g'ridan-to'g'ri yuboring.",
        "import_invalid_source": "Bu haqiqiy to'plam nomi yoki t.me/addstickers havolasiga o'xshamayapti.",
        "import_fetching": "\"{source}\" dan stikerlar olinmoqda...",
        "import_summary_head": "\"{source}\" dan {added} ta stiker import qilindi",
        "import_summary_skipped": ", {skipped} ta qo'llab-quvvatlanmaydigani (animatsion/Lottie) o'tkazib yuborildi",
        "import_summary_failed": ", {failed} tasi muvaffaqiyatsiz tugadi",
        "import_summary_tail": '. Yana yuborishingiz mumkin, tugatish uchun esa /done ni bosing.',
        "done_standalone_hint": (
            "Tugatadigan narsa yo'q — hozir hech qanday to'plamni tahrirlamayapsiz. "
            "/newpack bilan yangisini boshlang yoki /mypacks dagi to'plamda "
            "\"Stiker qo'shish\"ni bosing."
        ),
        "import_standalone_hint": (
            "Avval to'plamni boshlang yoki oching (/newpack, yoki /mypacks dan biror "
            "to'plamda \"Stiker qo'shish\"ni bosing), so'ng o'sha seans ichida "
            "/import <havola> dan foydalaning."
        ),
        "whatsapp_reading": "WhatsApp stiker to'plami o'qilmoqda...",
        "whatsapp_summary_head": "WhatsApp to'plamidan {added} ta stiker import qilindi",
        "not_emoji_message": "Qo'shish uchun rasm/GIF/video/stiker yuboring, oxirgisini qayta belgilash uchun emoji yuboring, yoki /done ni bosing.",
        "no_sticker_to_tag": "Avval stiker qo'shing, keyin uni belgilash uchun emoji yuboring.",
        "retagged_success": "Emoji o'zgartirildi: {emojis}",
        "retag_failed": "Emojini yangilab bo'lmadi: {error}",
        "nothing_added_yet": "Siz hali hech narsa qo'shmadingiz. Avval rasm yuboring.",
        "done_success": (
            "✅ \"{title}\" tugallandi — shu seansda {count} ta stiker qo'shildi.\n\n"
            "Tayyor: https://t.me/addstickers/{pack_name}"
        ),
        "convert_redirect": "Fayllarni o'girish (stiker bo'lmagan rasm, video, audio) endi @ConvertBot'da — ochish uchun pastdagi tugmani bosing.",
        "cancelled_status_note": "❌ Bekor qilindi.",
        "unrecognized": "Bu nima uchunligini tushunmadim — /newpack, /mypacks yoki /help ni sinab ko'ring.",
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /help yuboring.",
        "err_invalid_name": (
            "⚠️ Telegram to'plamning ichki nomini rad etdi — bu odatda nom raqam yoki "
            "belgidan boshlanganda yuz beradi. /cancel yuboring, so'ng harfdan "
            "boshlanadigan nom bilan yana /newpack qiling (masalan, \"2007\" o'rniga "
            "\"My 2007\")."
        ),
        "err_name_occupied": (
            "⚠️ Bu to'plamning ichki nomi mavjud nom bilan to'qnashdi (kamdan-kam "
            "uchraydi, shunchaki omadsizlik). /cancel yuboring, so'ng yangisini olish "
            "uchun yana /newpack qiling."
        ),
        "err_too_many_stickers": "⚠️ Bu to'plam Telegram'ning stiker chegarasiga (120) allaqachon yetgan — buning o'rniga /newpack bilan yangi to'plam boshlang.",
        "err_bad_format": "⚠️ Telegram bu fayl formatini shu to'plam uchun qabul qilmadi — boshqa rasmni sinab ko'ring.",
        "err_generic": "⚠️ Telegram buni rad etdi: {msg}\n\nQayta urinib ko'rishingiz mumkin, yoki to'xtatish uchun /cancel qiling.",
        "err_timed_out": (
            "⚠️ Telegram vaqtida tasdiqlamadi — baribir amalga oshgan bo'lishi mumkin, "
            "shuning uchun qayta urinishdan oldin to'plamni tekshiring. Qayta urinib "
            "ko'rishingiz mumkin, yoki to'xtatish uchun /cancel qiling."
        ),
        "restarting_send_again": '🔄 Bot hozir yangilanmoqda — bir necha soniyadan keyin qaytadan yuboring.',
        "update_soon_try_later": "🔧 Bot tez orada yangilanadi, shuning uchun yangi ishni boshlab bo'lmaydi — taxminan {minutes} daqiqadan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_soon_try_later_soon": "🔧 Bot hozir yangilanmoqda, shuning uchun yangi ishni boshlab bo'lmaydi — birozdan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_will_reset": "🔧 Diqqat: bot yangilanadi va hozir bajarilayotgan ishingiz to'xtab qoladi. Bir necha daqiqadan keyin qaytadan boshlashingiz mumkin.",
        "update_done_try_now": "✅ Yangilanish tugadi — endi qaytadan urinib ko'rishingiz mumkin.",
        "video_convert_ffmpeg_missing": (
            "Bu serverda ffmpeg o'rnatilmagan, shuning uchun GIF/video stikerlarni "
            "aylantirib bo'lmaydi. Uni 'apt install ffmpeg' (Linux), 'brew install "
            "ffmpeg' (Mac) orqali o'rnating, yoki Windows uchun build'ni PATH'ga qo'shing."
        ),
        "video_convert_empty_file": "Bu fayl bo'sh holda keldi — uni qayta yuborishga urinib ko'ring.",
        "video_convert_too_big": (
            "Bu klipni Telegram'ning 256 KB video-stiker chegarasidan pastga siqib "
            "bo'lmadi ({note}). Qisqaroq yoki vizual jihatdan soddaroq klipni sinab ko'ring."
        ),
        "import_pack_not_found": (
            "\"{source}\" nomli stiker to'plami topilmadi — havola/nomni qayta "
            "tekshiring (u ochiq bo'lishi kerak)."
        ),
        "import_bad_zip": "Bu haqiqiy .zip/.wastickers fayliga o'xshamayapti.",
        "import_zip_no_images": "Bu zip ichida ishlatsa bo'ladigan rasm topilmadi.",
    },
    "ru": {
        "flood_wait": "Ты отправляешь быстрее, чем я успеваю — подожди примерно {seconds} секунд(ы) и продолжай.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотри ниже \U0001f447",
        "donation_nudge": (
            "💙 Если этот бот оказался полезным: расходы на хостинг/API покрывает тот, "
            "кто его запустил, а /donate — это совершенно необязательный способ помочь "
            "ему остаться на плаву. Никакого давления в любом случае!"
        ),
        "donate_unknown_currency": 'Неизвестная валюта "{currency}" — попробуйте xtr или usd.',
        "donate_currency_not_configured": "Пожертвования в {currency} на этом боте пока не настроены — попробуйте Stars.",
        "donate_invalid_amount": "Это некорректная сумма — попробуйте, например, /donate 500 или /donate 5 usd.",
        "donate_prompt": (
            "Спасибо за вклад — эти средства идут прямо на хостинг и API этого "
            "бота. Выберите сумму ниже или нажмите «Другое», чтобы ввести свою "
            "(также можно сразу отправить /donate <число> [usd])."
        ),
        "donate_custom_button": "✏️ Другое {symbol}",
        "donate_too_many_stars": "Это очень много звёзд! Пусть будет меньше {max} ⭐ за одно пожертвование.",
        "donate_out_of_range": "Пожертвования в {currency} должны быть в диапазоне от {lo} до {hi} {symbol}.",
        "donate_invoice_title": "Поддержать хостинг",
        "donate_invoice_description": "Идёт на расходы по работе бота и добавляет {credited} ⚡ на ваш баланс для конвертаций в ConvertBot.",
        "donate_invoice_label": "Вклад в хостинг",
        "donate_invoice_description_fiat": 'Разовое добровольное пожертвование на хостинг. Спасибо!',
        "donate_prompt_credit": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации в ConvertBot. Следующие {left} ⭐ дают по {each} ⚡ ({mult}×): {rate} ⚡ обычного кредита и бонус, который сгорает через {days} дней после оплаты. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_prompt_credit_base": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации в ConvertBot, {rate} ⚡ за ⭐. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_invoice_error": "⚠️ Telegram не смог создать этот счёт: {error}",
        "stars_unit": "Stars (звёзды)",
        "donate_custom_ask": "Сколько {unit} вы хотите пожертвовать? Ответьте числом.",
        "donate_invalid_amount_retry": "Это некорректная сумма — отправьте /donate, чтобы попробовать снова.",
        "donate_thanks": "🙏 Спасибо за {amount} ⭐ — это по-настоящему ценно!",
        "topup_thanks": '🙏 Спасибо за пожертвование в {stars} ⭐ — это помогает ботам работать.\n\nВ благодарность вы получили {total} ⚡ кредита в {convert_bot} — его можно тратить на конвертацию файлов. Ваш баланс там: {balance} ⚡.',
        "topup_thanks_bonus": 'Из них {bonus} ⚡ — бонусный кредит, он сгорит {date}.',
        "credit_cannot_be_withdrawn": '⚡ — это кредит на конвертации в ConvertBot, его НЕЛЬЗЯ вывести или обменять обратно на Stars. Проблема с платежом? /paysupport',
        "paysupport_text": '💳 Помощь с платежом\n\nПлатежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести или обменять обратно на Stars.\n\nЕсли с платежом что-то пошло не так — деньги списали, а кредит не пришёл, или списали дважды, — напишите на {contact}: дату, сумму и ваш Telegram ID, {user_id}. Это проверят и исправят кредитом.\n\n/balance показывает каждый платёж и что он добавил.',
        "report_button": '🐞 Добавить мои данные',
        "problem_logged_note": 'Эта проблема уже записана для владельца бота — код, время и версия. О вас там ничего нет.',
        "report_disclaimer": '📨 Добавить к этой проблеме ваши данные?\n\nУже записано, без вас: название бота, код ошибки {code}, номер случая {incident}, когда это произошло и версия бота.\n\nКнопка «Отправить» добавит четыре вещи: ваш Telegram ID, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Ни того, что вы написали, ни отправленного файла.\n\nТогда ваш случай можно будет найти в логах — обычно именно это и позволяет починить редкую проблему. Решать только вам.',
        "report_send": '📨 Отправить мои данные',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — ваши данные теперь на случае {incident}, так его легко найти.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено. Сама проблема остаётся записанной.',
        "report_failed": '⚠️ Сейчас не удалось отправить сообщение. Попробуйте позже.',
        "report_invalid": 'Эта кнопка больше не работает.',
        "crash_notice": '⚠️ При обработке произошла ошибка на стороне бота, поэтому ничего не сделано. Попробуйте ещё раз чуть позже.',
        "sandbox_notice": "🧪 Тестовый режим — настоящие Stars не списывались.",
        "balance_header": "⚡ Ваш баланс: {balance}",
        "balance_totals": "Всего оплачено {paid} ⭐ · начислено {credited} ⚡ · потрачено {spent} ⚡",
        "balance_rate": 'Следующие {left} ⭐ дают по {each} ⚡ ({mult}×).',
        "balance_rate_base": '1 ⭐ даёт {rate} ⚡.',
        "balance_bonus_line": 'Из них {bonus} ⚡ — бонусный кредит; {soon} ⚡ сгорит {date}.',
        "balance_recent": "Последние операции:",
        "balance_empty_hint": "/donate добавит кредит в любой момент.",
        "bot_short_description": (
            "Делает стикерпаки из картинок, GIF и видео."
        ),
        "bot_description": (
            "Пришли картинку, GIF или видео — бот соберёт из этого стикерпак, который принадлежит "
            "тебе.\n"
            "\n"
            "Дай ссылку, чтобы паком мог пополнять кто-то ещё, или перенеси стикеры из другого "
            "пака Telegram либо из архива WhatsApp.\n"
            "\n"
            "Английский, узбекский и русский. /privacy — что бот о тебе хранит."
        ),

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": (
            "• твой числовой id в Telegram и выбранный язык\n"
            "• паки, которые ты здесь собрал: имя и название каждого, а также имя и username, "
            "которые были у тебя в тот момент\n"
            "• кому ты дал доступ на добавление в пак и какие ссылки создал\n"
            "• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли "
            "ботом хоть кто-нибудь\n"
            "• запись о пожертвовании: сумму и платёжный id Telegram\n"
            "• то, что бот в этот момент для тебя делает — пока не закончит"
        ),
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nКнопка «Добавить мои данные» под ошибкой предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
        "privacy_seen_by_heading": "Кто ещё это видит:",
        "privacy_seen_by": (
            "• Telegram — он передаёт каждое сообщение в обе стороны и действует по своим "
            "правилам\n"
            "• хостинг, на котором работает бот, и база данных, в которую он пишет"
        ),
        "privacy_others": (
            "• и больше никто, кроме них — стикеры делаются на той же машине, где работает бот, и никакие "
            "внешние сервисы не вызываются"
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
        "terms_specific": (
            "О стикерах: загружай то, что можешь загружать. Не собирай паки из чужих работ без "
            "разрешения и не делай паков из того, что запрещено правилами самого Telegram. "
            "Созданный пак живёт в Telegram — бот может о нём забыть, но удалить его может "
            "только владелец и только через Telegram."
        ),
        "terms_money": 'О деньгах: /donate — дело добровольное, деньги идут на то, во что обходятся боты. Платёж в Stars ещё и добавляет ⚡ кредит на конвертации в ConvertBot: 2 ⚡ за ⭐, а за твои первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держи свою копию всего, что тебе важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о тебе. Отменить будет нельзя.",
        "delete_data_consequences": 'Бот забудет паки, которые ты через него собрал: перестанет их показывать и не сможет в них ничего добавить. Сами паки продолжат работать у всех, кто их установил — по- настоящему удалить пак можно только самому, через Telegram. Язык, твои ссылки и чужой доступ на добавление в твои паки тоже пропадут.\n\nЗаписи о пожертвованиях останутся, без username, потому что по ним разбираются споры о платежах. Баланс ⚡ тоже останется — он твой, если вернёшься.',
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
        "cancel_button_donation": "💸 Сумма пожертвования",
        "cancel_item_donation": "\u0441\u0443\u043c\u043c\u0430 \u043f\u043e\u0436\u0435\u0440\u0442\u0432\u043e\u0432\u0430\u043d\u0438\u044f, \u043a\u043e\u0442\u043e\u0440\u0443\u044e \u044f \u0437\u0430\u043f\u0440\u043e\u0441\u0438\u043b",
        "cancel_item_stale_prompt": "старый запрос, который всё ещё ждал ответа",
        "cancel_item_new_pack": "\u043d\u043e\u0432\u044b\u0439 \u043d\u0430\u0431\u043e\u0440, \u043a\u043e\u0442\u043e\u0440\u043e\u043c\u0443 \u0432\u044b \u0434\u0430\u0432\u0430\u043b\u0438 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
        "cancel_button_new_pack": "🆕 Название нового набора",
        "cancel_item_rename": "\u043f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d\u0438\u0435 \u00ab{title}\u00bb",
        "cancel_button_rename": "✏️ Переименование набора",
        "cancel_item_editing": "\u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u00ab{title}\u00bb",
        "cancel_button_editing": "📦 Редактирование набора",
        "start_intro": (
            "Привет! Я превращаю ваши изображения/GIF/видео/стикеры в наборы "
            "стикеров Telegram, а также могу скачать видео по ссылке из "
            "Instagram/TikTok.\n\n"
        ),
        "help_text": 'Команды:\n/newpack - начать новый набор стикеров\n/addsticker - добавить стикеры в существующий набор\n/mypacks - показать ваши наборы\n/import <ссылка/имя набора> - (во время редактирования) массово скопировать стикеры из другого набора Telegram, или отправить файл экспорта набора стикеров WhatsApp .zip/.wastickers\n/done - закончить редактирование набора\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/whomade <ссылка/имя набора> - узнать, кто создал набор (если он был создан через этого бота)\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/balance - ваш ⚡ кредит\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n/convert - конвертация файлов теперь в ConvertBot; команда подскажет, куда идти\n\nВо время редактирования набора: отправляйте изображения, GIF, видео или статические/видео-стикеры, чтобы добавить их.\nОтправьте эмодзи сразу после стикера, чтобы пометить его этим эмодзи.\n\nНажмите на набор в /mypacks, чтобы переименовать его, настроить совместное редактирование, чтобы кто-то ещё мог добавлять стикеры, или удалить его насовсем (только для владельца, дважды спрашивает перед этим).\n\nХотите скачать видео из Instagram/TikTok или сконвертировать файл в другой формат? Теперь это делают соседние боты ниже.\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
        "whomade_usage": "Использование: /whomade <имя набора или ссылка t.me/addstickers>",
        "whomade_not_found": (
            "У меня нет записи об этом наборе — либо он не был создан через этого "
            "бота, либо имя/ссылка неверны."
        ),
        "whomade_result": "📦 «{title}»\nСоздал(а) {creator} {date} (через этого бота).",
        "coedit_link_invalid": "Эта ссылка для совместного редактирования недействительна — возможно, владелец набора сбросил её.",
        "coedit_pack_gone": "Похоже, этого набора больше не существует.",
        "coedit_own_pack": "Это ваш собственный набор — используйте /mypacks, чтобы им управлять.",
        "coedit_joined_intro": (
            "Вас добавили как соредактора набора «{title}»! Отправляйте изображения, "
            "GIF, видео или статические/видео-стикеры, чтобы добавить их — эмодзи по "
            "умолчанию 😭, отправьте эмодзи сразу после, чтобы переметить последний. "
            "По завершении — /done."
        ),
        "btn_new_pack": "➕ Новый набор",
        "btn_my_packs": "📁 Мои наборы",
        "btn_help": "❓ Помощь",
        "btn_back": "⬅️ Назад",
        "no_packs_yet": "Пока нет наборов — нажмите «Новый набор» или используйте /newpack.",
        "your_packs": "Ваши наборы:",
        "not_your_pack": "Это не ваш набор.",
        "pack_detail_title": "📦 {title}",
        "btn_open_pack": "🔗 Открыть набор",
        "btn_add_stickers": "➕ Добавить стикеры",
        "btn_rename": "✏️ Переименовать",
        "btn_coedit": "👥 Совместное редактирование",
        "btn_delete_pack": "🗑️ Удалить набор",
        "coedit_count_some": "Пока {count} соредактор(ов).",
        "coedit_count_none": "Пока нет соредакторов.",
        "coedit_message": (
            "👥 Совместное редактирование «{title}»\n\n"
            "Ссылка: {link}\n\n"
            "Поделитесь ей — любой, кто её откроет, сможет добавлять стикеры в этот "
            "набор через бота (они всё равно будут добавляться от вашего имени).\n\n"
            "{editors_line}\n\n"
            "Сбросьте ссылку, чтобы она больше не давала доступ новым людям."
        ),
        "btn_reset_link": "🔄 Сбросить ссылку",
        "only_owner_coedit": "Совместным редактированием может управлять только владелец набора.",
        "link_reset_confirm": "Ссылка сброшена — старая больше не работает.",
        "only_owner_rename": "Переименовать набор может только его владелец.",
        "rename_prompt": "Отправьте новое название для «{title}».",
        "rename_broken_state": "Что-то пошло не так — попробуйте снова переименовать через /mypacks.",
        "btn_back_to_pack": "⬅️ Назад к набору",
        "renamed_success": "Переименовано в «{title}».",
        "renamed_failed": "Не удалось переименовать: {error}",
        "only_owner_delete": "Удалить набор может только его владелец.",
        "btn_delete": "🗑️ Удалить",
        "btn_cancel_inline": "⬅️ Отмена",
        "delete_confirm1": (
            "⚠️ Удалить «{title}»? Это удалит набор из Telegram у всех, у кого он "
            "есть, включая соредакторов, и отменить это будет нельзя."
        ),
        "btn_delete_confirm": "🗑️ Да, удалить навсегда",
        "delete_confirm2": "❗ Последняя проверка — удалить «{title}» навсегда? После этого отменить будет нельзя.",
        "delete_failed": "⚠️ Не удалось удалить: {error}",
        "btn_my_packs_back": "⬅️ Мои наборы",
        "delete_success": "🗑️ «{title}» удалён(а) навсегда.",
        "newpack_title_prompt": "Каким будет название набора?",
        "title_empty": "Это пусто — отправьте настоящее название для набора.",
        "title_truncated": "Telegram ограничивает название набора 64 символами — используется «{title}».",
        "editing_intro_new": (
            "Отправляйте изображения, GIF, видео или статические/видео-стикеры — "
            "каждый добавляется с эмодзи по умолчанию 😭. Отправьте эмодзи сразу "
            "после, чтобы переметить последний. По завершении — /done."
        ),
        "no_packs_for_add": "У вас пока нет наборов. Сначала используйте /newpack.",
        "pick_pack_prompt": "Какой набор? Нажмите на него, затем «➕ Добавить стикеры».",
        "editing_intro_add": (
            "Отправляйте изображения, GIF, видео или статические/видео-стикеры, "
            "чтобы добавить их — эмодзи по умолчанию 😭, отправьте эмодзи сразу "
            "после, чтобы переметить последний. По завершении — /done.\n\n"
            "Совет: если отправить стикер, который уже есть в этом наборе, он будет "
            "удалён, а не добавлен повторно."
        ),
        "status_verb_creating": "Создание",
        "status_verb_editing": "Редактирование",
        "status_line": "📝 {verb} «{title}» — за эту сессию добавлено {count} стикер(ов)",
        "status_default_title": "этот набор",
        "btn_delete_pack_yes": "🗑️ Да, удалить набор",
        "btn_cancel": "Отмена",
        "remove_last_confirm": (
            "Это последний стикер, оставшийся в наборе — его удаление удалит *весь "
            "набор* из Telegram, так как наборы не могут быть пустыми. Вы уверены?"
        ),
        "remove_failed": "⚠️ Не удалось удалить этот стикер: {error}",
        "remove_success": "🗑️ Этот стикер уже был в наборе — я его удалил.",
        "keep_pack": "Хорошо, набор оставлен как есть.",
        "pack_deleted_empty": "🗑️ Набор удалён (в нём не осталось стикеров).",
        "pack_deleted_note": "❌ Набор удалён.",
        "image_process_failed": "Не удалось обработать это изображение: {error}",
        "added_default_emoji": "Добавлено {emoji} — отправьте эмодзи, чтобы переметить.",
        "last_attempt_failed": "⚠️ Последняя попытка не удалась — отправьте другой файл, чтобы попробовать снова, или /cancel.",
        "converting_video": "Преобразование в видео-стикер...",
        "video_convert_failed_redirect": (
            "{error}\n\nПревратить это в стикер нельзя, но если вам просто нужен "
            "файл в обычном формате, это может сделать @ConvertBot — просто "
            "отправьте тот же файл туда 👇"
        ),
        "video_convert_generic_failed": "Не удалось это преобразовать: {error}",
        "added_video_default_emoji": (
            "Добавлено как видео-стикер с эмодзи {emoji} по умолчанию. Отправьте "
            "эмодзи сейчас, чтобы переметить, ещё одно изображение/GIF/видео, чтобы "
            "продолжить, или /done, чтобы закончить."
        ),
        "animated_not_supported": (
            "Анимированные (Lottie/.tgs) стикеры не поддерживаются — отправьте "
            "вместо этого статичное изображение, GIF/видео или "
            "статический/видео-стикер."
        ),
        "import_usage": (
            "Отправьте /import <ссылка или имя набора Telegram>, чтобы скопировать "
            "стикеры из другого публичного набора Telegram в этот — или просто "
            "отправьте файл набора стикеров WhatsApp .zip/.wastickers напрямую."
        ),
        "import_invalid_source": "Это не похоже на настоящее имя набора или ссылку t.me/addstickers.",
        "import_fetching": "Загрузка стикеров из «{source}»...",
        "import_summary_head": "Импортировано {added} стикер(ов) из «{source}»",
        "import_summary_skipped": ", пропущено {skipped} неподдерживаемых (анимированные/Lottie)",
        "import_summary_failed": ", {failed} не удалось",
        "import_summary_tail": ". Можете отправлять ещё, или /done, чтобы закончить.",
        "done_standalone_hint": (
            "Нечего завершать — сейчас вы не редактируете набор. "
            "Начните новый через /newpack или нажмите «Добавить стикеры» "
            "на наборе из /mypacks."
        ),
        "import_standalone_hint": (
            "Сначала начните или откройте набор (/newpack, или нажмите «Добавить "
            "стикеры» на наборе из /mypacks), затем используйте /import <ссылка> "
            "внутри этой сессии."
        ),
        "whatsapp_reading": "Чтение набора стикеров WhatsApp...",
        "whatsapp_summary_head": "Импортировано {added} стикер(ов) из набора WhatsApp",
        "not_emoji_message": "Отправьте изображение/GIF/видео/стикер, чтобы добавить, эмодзи, чтобы переметить последний, или /done.",
        "no_sticker_to_tag": "Сначала добавьте стикер, затем отправьте эмодзи, чтобы его пометить.",
        "retagged_success": "Переметено как {emojis}.",
        "retag_failed": "Не удалось обновить эмодзи: {error}",
        "nothing_added_yet": "Вы ещё ничего не добавили. Сначала отправьте изображение.",
        "done_success": (
            "✅ «{title}» завершён — за эту сессию добавлено {count} стикер(ов).\n\n"
            "Готово: https://t.me/addstickers/{pack_name}"
        ),
        "convert_redirect": (
            "Конвертация файлов (изображения/видео/аудио, не только стикеры) теперь "
            "в @ConvertBot — нажмите ниже, чтобы открыть."
        ),
        "cancelled_status_note": "❌ Отменено.",
        "unrecognized": "Не понял, для чего это — попробуйте /newpack, /mypacks или /help.",
        "unknown_command": "Я не знаю такую команду. Отправь /help, чтобы увидеть, что я умею.",
        "err_invalid_name": (
            "⚠️ Telegram отклонил внутреннее имя набора — обычно это происходит, "
            "когда название начинается с цифры или символа. Отправьте /cancel, затем "
            "снова /newpack с названием, начинающимся с буквы (например, «My 2007» "
            "вместо «2007»)."
        ),
        "err_name_occupied": (
            "⚠️ Внутреннее имя набора совпало с уже существующим (редкость, просто "
            "не повезло). Отправьте /cancel, затем снова /newpack, чтобы получить новое."
        ),
        "err_too_many_stickers": "⚠️ Этот набор уже достиг лимита Telegram по стикерам (120) — вместо этого начните новый набор через /newpack.",
        "err_bad_format": "⚠️ Telegram не принял формат этого файла для этого набора — попробуйте другое изображение.",
        "err_generic": "⚠️ Telegram отклонил это: {msg}\n\nВы можете попробовать снова, или /cancel, чтобы остановиться.",
        "err_timed_out": (
            "⚠️ Telegram не подтвердил вовремя — возможно, всё же прошло, поэтому "
            "проверьте набор перед повторной попыткой, чтобы не задвоить. Можете "
            "попробовать снова, или /cancel, чтобы остановиться."
        ),
        "restarting_send_again": "🔄 Сейчас обновляюсь — подождите несколько секунд и отправьте ещё раз.",
        "update_soon_try_later": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова примерно через {minutes} мин. Я напишу, когда вернусь.',
        "update_soon_try_later_soon": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова чуть позже. Я напишу, когда вернусь.',
        "update_will_reset": '🔧 Внимание: меня скоро обновят, и то, что вы сейчас начали, будет сброшено. Через несколько минут сможете начать заново.',
        "update_done_try_now": '✅ Обновление завершено — можете пробовать снова.',
        "video_convert_ffmpeg_missing": (
            "На этом сервере не установлен ffmpeg, поэтому GIF/видео-стикеры нельзя "
            "преобразовать. Установите его через 'apt install ffmpeg' (Linux), "
            "'brew install ffmpeg' (Mac), либо добавьте сборку для Windows в PATH."
        ),
        "video_convert_empty_file": "Этот файл пришёл пустым — попробуйте отправить его ещё раз.",
        "video_convert_too_big": (
            "Не удалось сжать этот клип до лимита Telegram в 256 КБ для "
            "видео-стикера ({note}). Попробуйте более короткий или визуально более "
            "простой клип."
        ),
        "import_pack_not_found": (
            "Не удалось найти набор стикеров с именем «{source}» — перепроверьте "
            "ссылку/имя (он должен быть публичным)."
        ),
        "import_bad_zip": "Это не похоже на настоящий файл .zip/.wastickers.",
        "import_zip_no_images": "Внутри этого zip-файла не найдено пригодных изображений.",
    },
}

import problems

_BOT = "sticker_bot"

def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))

async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler call."""
    cached = context.user_data.get("lang")
    if cached:
        return cached
    lang = await asyncio.to_thread(db.get_user_language, user_id) or "en"
    context.user_data["lang"] = lang
    return lang

COMMAND_MENU = {
    "uz": {
        "start": "Bu bot nima qiladi va qanday boshlash kerak",
        "newpack": "Yangi stiker to'plami yaratish",
        "addsticker": "To'plamingizga stiker qo'shish",
        "mypacks": "To'plamlaringiz",
        "import": "Boshqa to'plamdan stikerlarni ko'chirish",
        "done": "Tahrirlayotgan to'plamni yakunlash",
        "whomade": "To'plamni kim yaratgan — stikerini yuboring",
        "cancel": "Kutayotgan amalimni to'xtatish",
        "help": "Nimalar qila olaman",
        "balance": "⚡ kreditingiz",
        "donate": "Server xarajatlariga hissa qo'shish",
        "paysupport": "To'lov bilan muammo",
        "privacy": "Siz haqingizda nimalarni saqlayman",
        "terms": "Botdan foydalanish shartlari",
        "deletemydata": "Siz haqingizdagi hamma narsani o'chirish",
    },
    "ru": {
        "start": "Что этот бот делает и с чего начать",
        "newpack": "Создать новый стикерпак",
        "addsticker": "Добавить стикеры в ваш пак",
        "mypacks": "Ваши паки",
        "import": "Скопировать стикеры из другого пака",
        "done": "Завершить пак, который вы редактируете",
        "whomade": "Кто сделал пак — пришлите его стикер",
        "cancel": "Остановить то, чего я жду",
        "help": "Что я умею",
        "balance": "Ваш ⚡ кредит",
        "donate": "Помочь с расходами на хостинг",
        "paysupport": "Проблема с оплатой",
        "privacy": "Что я о вас храню",
        "terms": "Для чего можно пользоваться ботом",
        "deletemydata": "Удалить всё, что я о вас храню",
    },
}

# ─── module: convert_bot.i18n ────────────────────────────────────────────────
"""Translation strings for ConvertBot's end-user-facing text (English, Uzbek, Russian)."""
import asyncio

import db

SUPPORTED_LANGUAGES = ("en", "uz", "ru")
LANGUAGE_LABELS = {"en": "English 🇬🇧", "uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺"}

LANGUAGE_PROMPT = (
    "👋 Welcome! / Xush kelibsiz! / Добро пожаловать!\n\n"
    "Please choose your language / Iltimos, tilni tanlang / "
    "Пожалуйста, выберите язык:"
)

STRINGS = {
    "en": {
        "flood_wait": "You're going faster than I can keep up with — give it about {seconds} second(s) and carry on.",

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
        "report_button": '🐞 Add my details',
        "problem_logged_note": "This is already written down for the bot's owner — the code, the time and the version, and nothing about you.",
        "report_disclaimer": "📨 Add your own details to this problem?\n\nAlready recorded, with you left out of it: the bot's name, the error code {code}, the incident number {incident}, when it happened and the bot's version.\n\nTapping Send adds four things: your Telegram user ID, your @username if you have one, the language you picked, and whether this chat is private or a group. Not what you wrote, and not the file you sent.\n\nIt lets your case be found in the logs, which is usually what makes a rare problem fixable. Entirely your choice.",
        "report_send": '📨 Send my details',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — your details are on incident {incident} now, which is what makes this one findable.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent. The problem itself stays logged.',
        "report_failed": "⚠️ The report couldn't be sent right now. Please try again later.",
        "report_invalid": 'This button no longer works.',
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
            "\"Add my details\" under an error offers to attach four things to that one "
            "incident: your Telegram user id, your @username if you have one, the language you "
            "picked, and whether the chat is private or a group. All four are named on screen "
            "first, and nothing is sent unless you tap Send. What you wrote and the files you "
            "sent are never part of it.\n"
            "\n"
            "Those four are cleared after 30 days on their own, and /deletemydata clears them "
            "straight away. The record of the error stays — it still happened — it just stops "
            "saying who hit it. The records themselves are deleted after 180 days."
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

        "start_greeting": "Hey! Send me a file and I'll convert it to another format.\n\n",
        "help_text": "Send me a file and I'll convert it to another format — pictures, video, audio, documents, spreadsheets and subtitles.\n\nCommands:\n/convert - start a conversion (or just send a file directly)\n/formats - every format I read and write\n/balance (or /mystars) - your ⚡ credit and what it was spent on\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/recharge (or /donate) - top up your ⚡ credit\n/en, /uz, /rus - switch language (or /language, which asks)\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n\nPrice in ⚡ credit:\n{pricing}\n\n⚠️ NOTE: Payments are final — Stars are NOT refunded, and ⚡ credit can NOT be withdrawn. A conversion's ⚡ is taken when it STARTS, and goes back to your balance only if the bot fails it.\n\n",
        "convert_start_prompt": (
            "Send me a file to convert, up to {max_mb} MB — a picture, a video, a "
            "sound, a document, a spreadsheet or a subtitle file. Send several "
            "pictures at once and I can bind them into one PDF.\n\n"
            "/formats lists every format I know.\n\n"
            "Price in ⚡ credit:\n{pricing}\n\n/cancel to stop."
        ),
        "cancelled": "Cancelled.",
        "btn_cancel_conversion": "✖️ Cancel",
        "unknown_extension": (
            "Couldn't tell that file's format from its name — try sending it as a "
            "document with a normal extension (e.g. photo.png). /formats lists the "
            "ones I know."
        ),
        "file_too_large_download": "That file is over {max_mb} MB — Telegram bots can't download anything bigger, sorry.",
        "file_too_large_in_group": "Files over {limit} MB only come through in a private chat with me. Send this one to me directly — there it can be up to {max_mb} MB.",
        "big_download_unavailable": "Your file wasn't downloaded: files over {limit} MB reach me through a separate connection to Telegram, and it isn't answering right now. Try again in a few minutes, or send a file under {limit} MB.",
        "card_downloading": "📥 Downloading your file…",
        "card_download_sizes": "{done} of {total}",
        "card_converting": "Converting…",
        "card_sending": "Sending the result…",
        "card_elapsed": "{elapsed} so far",
        "card_left": "about {left} left",
        "card_paid": "{price} ⚡ taken, {balance} ⚡ left.",
        "card_free": "Free conversion.",
        "download_too_slow": "it was still arriving after {minutes} minutes",
        "download_stalled": "it stopped arriving: nothing came through for {seconds} seconds",
        "restarting_send_again": "🔄 I'm being updated right now — give me a few seconds and send that again.",
        "update_soon_try_later": "🔧 I'm being updated in a moment, so I can't start anything new right now — please try again in about {minutes} minute(s). I'll message you when I'm back.",
        "update_soon_try_later_soon": "🔧 I'm being updated right now, so I can't start anything new — please try again shortly. I'll message you when I'm back.",
        "update_will_reset": "🔧 Heads up: I'm about to be updated, and what you have going right now will be reset. You'll be able to start it again in a few minutes.",
        "update_done_try_now": '✅ The update is done — go ahead and try again now.',
        "download_failed": "Couldn't download that file: {error}",
        "unsupported_format": "\".{ext}\" isn't a format I convert — /formats lists the ones I do.",
        "file_too_large_convert": "That file is {size} MB, over the {max_mb} MB limit — can't convert it.",
        "no_target_formats": "No different target format is available for that file.",
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
        "converted_file_caption": "Here's your converted file!",
        "converted_file_caption_free": "Here's your converted file! (free)",
        "conversion_expired": "This conversion session expired — send the file again.",
        "convert_invoice_title": "Convert {src} to {target}",
        "convert_invoice_description": "One-time conversion of your {size_kb} KB file.",
        "convert_invoice_label": "{src}→{target} conversion",
        "topup_needed": 'This one costs {price} ⚡ and you have {balance} ⚡.\n\nInvoice sent for {stars} ⭐, which adds {credited} ⚡ — enough for this conversion, and the rest stays on your balance. /cancel to back out.',
        "credit_policy_note": "⚠️ NOTE: ⚡ is taken when the conversion STARTS. Stop it yourself and it is NOT given back; if it fails on the bot's side, ⚡ goes straight back to your balance. Payments are final — Stars are not refunded.",
        "send_limit_note": "📤 The converted file can be up to {mb} MB. If it comes out bigger, it won't be sent — and its ⚡ goes straight back to your balance.",
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
        "job_reason_too_slow": "This one would take about {minutes} minutes to convert, and a conversion here can run for {limit}, so I stopped it now rather than make you wait for the limit. A shorter clip, or a lower resolution, will fit.",
        "job_reason_crash": 'The conversion failed on my side. The owner has been told.',
        "job_reason_too_large": 'The {target} came out at {mb} MB, more than the {limit} MB I can send back for this conversion — JPG, WEBP or AVIF will be far smaller. The owner has been told.',
        "job_reason_send_failed": 'The file converted, but sending it to you failed. The owner has been told.',
        "job_reason_interrupted": 'I was restarted in the middle of that conversion. Send it again in a minute.',
        "unknown_order": "Unknown order.",
        "unrecognized_message": (
            "That's not a file I can convert — send me one, or /formats to see what "
            "I take. Name a format (\"heic\", \"epub\") and I'll tell you what it "
            "becomes."
        ),
        "unknown_command": "I don't recognize that command. Send /start to see what I can do.",

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

        "price_free": "Free",
        "price_not_supported": "not supported",
        "price_cloud_api_note": "(cloud Bot API's 20 MB download ceiling)",
        "price_from": "from {price} ⚡: most pictures, songs and documents",
        "price_example": "a {mb} MB video to MP4: {price} ⚡",
        "price_at_most": "the biggest file there is, {mb} MB: at most {price} ⚡",
        "price_quoted_first": "The exact price is shown before anything is charged, and it is what you pay.",
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
        "report_button": "🐞 Ma'lumotlarimni qo'shish",
        "problem_logged_note": "Bu muammo bot egasi uchun allaqachon yozib olindi — kodi, vaqti va bot versiyasi. Siz haqingizda hech narsa yo'q.",
        "report_disclaimer": "📨 Bu muammoga o'zingiz haqingizdagi ma'lumotni ham qo'shasizmi?\n\nSizsiz yozib olingani: bot nomi, {code} xato kodi, {incident} hodisa raqami, qachon yuz bergani va bot versiyasi.\n\n\"Yuborish\" tugmasi to'rt narsani qo'shadi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. Yozganingiz ham, yuborgan faylingiz ham emas.\n\nShunda sizning holatingizni loglardan topib bo'ladi — kam uchraydigan muammoni odatda shu tuzatib beradi. To'liq o'zingiz hal qilasiz.",
        "report_send": "📨 Ma'lumotlarimni yuborish",
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — ma'lumotlaringiz {incident} hodisasiga biriktirildi, endi uni topish oson.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi. Muammoning o'zi yozib olingan holicha qoladi.",
        "report_failed": "⚠️ Hozir xabarni yuborib bo'lmadi. Keyinroq qayta urinib ko'ring.",
        "report_invalid": 'Bu tugma endi ishlamaydi.',
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

        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• yuborgan faylingiz — o'girilishi bilanoq o'chiriladi; «faylni saqlash» yoqilgan bo'lsa, boshqa formatlarga ham o'girish uchun har konvertatsiyadan keyin 15 daqiqagacha saqlanadi; nosozlikdan keyin qolib ketgan fayllar muntazam va bot ishga tushganda tozalanadi\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• ⚡ kredit balansingiz va har bir to'ldirish, konvertatsiya uchun yechilgan hamda balansga qaytgan ⚡ yozuvi: miqdori, nima uchunligi va pullik to'lovlarda Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nXato ostidagi \"Ma'lumotlarimni qo'shish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
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
        "help_text": "Menga fayl yuboring — uni boshqa formatga o'girib beraman: rasm, video, audio, hujjat, jadval va subtitrlar.\n\nBuyruqlar:\n/convert - konvertatsiyani boshlash (yoki shunchaki fayl yuboring)\n/formats - qo'llab-quvvatlanadigan barcha formatlar\n/balance (yoki /mystars) - ⚡ kreditingiz va u nimaga sarflangani\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/recharge (yoki /donate) - ⚡ kreditni to'ldirish\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/paysupport - to'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n\nNarxlar ⚡ kreditda:\n{pricing}\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — to'langan Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Konvertatsiya narxi u BOSHLANGANDA yechiladi va faqat bot tomonidagi xatolik tufayli bajarilmasa, ⚡ balansingizga qaytib tushadi.\n\n",
        "convert_start_prompt": "O'girish uchun {max_mb} MB gacha fayl yuboring — rasm, video, audio, hujjat, jadval yoki subtitr. Bir nechta rasmni birga yuborsangiz, ularni bitta PDF qilib beraman.\n\nBarcha formatlar: /formats\n\nNarxlar ⚡ kreditda:\n{pricing}\n\nBekor qilish uchun: /cancel",
        "cancelled": "Bekor qilindi.",
        "btn_cancel_conversion": "✖️ Bekor qilish",
        "unknown_extension": "Fayl nomidan formatini aniqlab bo'lmadi — faylni kengaytmasi bilan (masalan, rasm.png) hujjat sifatida yuboring.",
        "file_too_large_download": 'Afsuski, fayl {max_mb} MB dan katta — Telegram botlarga bundan katta fayllarni yuklab olishga ruxsat bermaydi.',
        "file_too_large_in_group": "{limit} MB dan katta fayllarni faqat shaxsiy chatda qabul qila olaman. Bu faylni menga to'g'ridan-to'g'ri yuboring — u yerda {max_mb} MB gacha bo'lishi mumkin.",
        "big_download_unavailable": "Faylingiz yuklab olinmadi: {limit} MB dan katta fayllar menga Telegram bilan alohida ulanish orqali keladi, u hozir javob bermayapti. Bir necha daqiqadan keyin qayta urinib ko'ring yoki {limit} MB dan kichik fayl yuboring.",
        "card_downloading": "📥 Faylingiz yuklab olinmoqda…",
        "card_download_sizes": "{done} / {total}",
        "card_converting": "O'girilmoqda…",
        "card_sending": "Natija yuborilmoqda…",
        "card_elapsed": "{elapsed} o'tdi",
        "card_left": "taxminan {left} qoldi",
        "card_paid": "{price} ⚡ yechildi, balansda {balance} ⚡ qoldi.",
        "card_free": "Bepul konvertatsiya.",
        "download_too_slow": "{minutes} daqiqadan keyin ham to'liq yetib kelmadi",
        "download_stalled": "u kelishdan to'xtab qoldi: {seconds} soniya davomida hech narsa kelmadi",
        "restarting_send_again": '🔄 Bot hozir yangilanmoqda — bir necha soniyadan keyin qaytadan yuboring.',
        "update_soon_try_later": "🔧 Bot tez orada yangilanadi, shuning uchun yangi ishni boshlab bo'lmaydi — taxminan {minutes} daqiqadan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_soon_try_later_soon": "🔧 Bot hozir yangilanmoqda, shuning uchun yangi ishni boshlab bo'lmaydi — birozdan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_will_reset": "🔧 Diqqat: bot yangilanadi va hozir bajarilayotgan ishingiz to'xtab qoladi. Bir necha daqiqadan keyin qaytadan boshlashingiz mumkin.",
        "update_done_try_now": "✅ Yangilanish tugadi — endi qaytadan urinib ko'rishingiz mumkin.",
        "download_failed": "Faylni yuklab bo'lmadi: {error}",
        "unsupported_format": '".{ext}" formatini o\'gira olmayman. Qo\'llab-quvvatlanadigan formatlar: /formats',
        "file_too_large_convert": "Fayl hajmi {size} MB — bu {max_mb} MB chegarasidan katta, shuning uchun uni o'girib bo'lmaydi.",
        "no_target_formats": "Bu faylni o'girish mumkin bo'lgan boshqa format yo'q.",
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
        "converted_file_caption": 'Mana, faylingiz tayyor!',
        "converted_file_caption_free": 'Mana, faylingiz tayyor! (bepul)',
        "conversion_expired": "Bu konvertatsiyaning vaqti o'tib ketdi — faylni qaytadan yuboring.",
        "convert_invoice_title": '{src} → {target} konvertatsiya',
        "convert_invoice_description": "{size_kb} KB hajmli faylni bir marta o'girish.",
        "convert_invoice_label": "{src}→{target} konvertatsiya",
        "topup_needed": "Bu konvertatsiya {price} ⚡ turadi, balansingizda esa {balance} ⚡.\n\n{stars} ⭐ uchun to'lov hisobi yuborildi: u {credited} ⚡ qo'shadi — bu konvertatsiyaga yetadi, ortgani balansingizda qoladi. Bekor qilish: /cancel",
        "credit_policy_note": "⚠️ DIQQAT: ⚡ konvertatsiya BOSHLANGANDA yechiladi. Uni o'zingiz to'xtatsangiz, ⚡ QAYTARILMAYDI; bot tomonidagi xatolik tufayli bajarilmasa, ⚡ darhol balansingizga qaytib tushadi. To'lovlar qaytarilmaydi — Stars qaytarib berilmaydi.",
        "send_limit_note": "📤 Tayyor fayl {mb} MB gacha bo'lishi mumkin. Bundan katta chiqsa, u yuborilmaydi — bunday holda ⚡ darhol balansingizga qaytib tushadi.",
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
        "job_reason_too_slow": "Bu faylni o'girish taxminan {minutes} daqiqa olardi, bu yerda esa bitta konvertatsiya ko'pi bilan {limit} daqiqa ishlaydi. Shuning uchun chegaragacha kuttirib o'tirmay, hozir to'xtatdim. Qisqaroq video yoki pastroq sifat bemalol sig'adi.",
        "job_reason_crash": 'Konvertatsiya bot tomonidagi xatolik tufayli bajarilmadi. Bot egasiga xabar berildi.',
        "job_reason_too_large": "{target} fayli {mb} MB chiqdi, bu konvertatsiya natijasini esa faqat {limit} MB gacha yubora olaman. JPG, WEBP yoki AVIF ancha kichik bo'ladi. Bot egasiga xabar berildi.",
        "job_reason_send_failed": "Fayl o'girildi, lekin uni sizga yuborib bo'lmadi. Bot egasiga xabar berildi.",
        "job_reason_interrupted": 'Konvertatsiya vaqtida bot qayta ishga tushdi. Bir daqiqadan keyin faylni qaytadan yuboring.',
        "unknown_order": "Noma'lum buyurtma.",
        "unrecognized_message": 'Bu o\'girish mumkin bo\'lgan fayl emas — fayl yuboring yoki qabul qilinadigan formatlarni /formats orqali ko\'ring. Format nomini yozsangiz (masalan, "heic" yoki "epub"), uni nimaga o\'girish mumkinligini aytaman.',
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /start yuboring.",

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
        "price_from": "{price} ⚡ dan: ko'pchilik rasm, qo'shiq va hujjatlar",
        "price_example": "{mb} MB video → MP4: {price} ⚡",
        "price_at_most": "eng katta fayl, {mb} MB: ko'pi bilan {price} ⚡",
        "price_quoted_first": "Aniq narx pul yechilishidan oldin ko'rsatiladi — to'laydiganingiz aynan shu.",
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
        "report_button": '🐞 Добавить мои данные',
        "problem_logged_note": 'Эта проблема уже записана для владельца бота — код, время и версия. О вас там ничего нет.',
        "report_disclaimer": '📨 Добавить к этой проблеме ваши данные?\n\nУже записано, без вас: название бота, код ошибки {code}, номер случая {incident}, когда это произошло и версия бота.\n\nКнопка «Отправить» добавит четыре вещи: ваш Telegram ID, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Ни того, что вы написали, ни отправленного файла.\n\nТогда ваш случай можно будет найти в логах — обычно именно это и позволяет починить редкую проблему. Решать только вам.',
        "report_send": '📨 Отправить мои данные',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — ваши данные теперь на случае {incident}, так его легко найти.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено. Сама проблема остаётся записанной.',
        "report_failed": '⚠️ Сейчас не удалось отправить сообщение. Попробуйте позже.',
        "report_invalid": 'Эта кнопка больше не работает.',
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

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": '• твой числовой id в Telegram и выбранный язык\n• присланный файл — удаляется сразу после конвертации, или хранится до 15 минут после каждой конвертации, если включить «хранить файл», чтобы конвертировать его и в другие форматы; всё, что осталось после сбоя, подчищается по таймеру и при запуске\n• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли ботом хоть кто-нибудь\n• твой баланс ⚡ кредита и запись о каждом пополнении, списании за конвертацию и возврате ⚡ на баланс: сумму, за что и платёжный id Telegram для оплаченного\n• то, что бот в этот момент для тебя делает — пока не закончит',
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nКнопка «Добавить мои данные» под ошибкой предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
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
        "help_text": 'Пришли мне файл, и я преобразую его в другой формат — картинки, видео, аудио, документы, таблицы и субтитры.\n\nКоманды:\n/convert - начать конвертацию (или просто отправь файл напрямую)\n/formats - все форматы, которые я читаю и пишу\n/balance (или /mystars) - ваш ⚡ кредит и на что он потрачен\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/recharge (или /donate) - пополнить ⚡ кредит\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n\nЦена в ⚡ кредите:\n{pricing}\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести. ⚡ за конвертацию списывается при СТАРТЕ и возвращается на баланс, только если сбой по вине бота.\n\n',
        "convert_start_prompt": (
            "Пришли файл для конвертации, до {max_mb} МБ — картинку, видео, звук, "
            "документ, таблицу или файл субтитров. Пришли несколько картинок "
            "сразу — соберу их в один PDF.\n\n"
            "/formats покажет все форматы, которые я знаю.\n\n"
            "Цена в ⚡ кредите:\n{pricing}\n\n"
            "/cancel, чтобы остановиться."
        ),
        "cancelled": "Отменено.",
        "btn_cancel_conversion": "✖️ Отмена",
        "unknown_extension": (
            "Не удалось определить формат файла по названию — попробуй отправить "
            "его как документ с обычным расширением (например, photo.png)."
        ),
        "file_too_large_download": "Этот файл больше {max_mb} МБ — боты Telegram не могут скачать ничего крупнее, увы.",
        "file_too_large_in_group": "Файлы больше {limit} МБ я принимаю только в личном чате. Пришли этот файл мне напрямую — там можно до {max_mb} МБ.",
        "big_download_unavailable": "Файл не скачан: файлы больше {limit} МБ приходят ко мне через отдельное подключение к Telegram, а оно сейчас не отвечает. Попробуй через несколько минут или пришли файл меньше {limit} МБ.",
        "card_downloading": "📥 Скачиваю твой файл…",
        "card_download_sizes": "{done} из {total}",
        "card_converting": "Конвертирую…",
        "card_sending": "Отправляю результат…",
        "card_elapsed": "прошло {elapsed}",
        "card_left": "осталось около {left}",
        "card_paid": "Списано {price} ⚡, на балансе {balance} ⚡.",
        "card_free": "Бесплатная конвертация.",
        "download_too_slow": "он всё ещё не пришёл целиком через {minutes} мин.",
        "download_stalled": "он перестал приходить: {seconds} сек. не пришло ни байта",
        "restarting_send_again": "🔄 Сейчас обновляюсь — подождите несколько секунд и отправьте ещё раз.",
        "update_soon_try_later": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова примерно через {minutes} мин. Я напишу, когда вернусь.',
        "update_soon_try_later_soon": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова чуть позже. Я напишу, когда вернусь.',
        "update_will_reset": '🔧 Внимание: меня скоро обновят, и то, что вы сейчас начали, будет сброшено. Через несколько минут сможете начать заново.',
        "update_done_try_now": '✅ Обновление завершено — можете пробовать снова.',
        "download_failed": "Не удалось скачать этот файл: {error}",
        "unsupported_format": "«.{ext}» — не тот формат, который я конвертирую — /formats покажет те, что умею.",
        "file_too_large_convert": 'Этот файл весит {size} МБ, что больше лимита в {max_mb} МБ — конвертировать его нельзя.',
        "no_target_formats": "Для этого файла нет доступного другого формата.",
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
        "converted_file_caption": "Вот твой сконвертированный файл!",
        "converted_file_caption_free": 'Вот твой сконвертированный файл! (бесплатно)',
        "conversion_expired": "Срок этой сессии конвертации истёк — отправь файл заново.",
        "convert_invoice_title": "Конвертировать {src} в {target}",
        "convert_invoice_description": "Разовая конвертация твоего файла на {size_kb} КБ.",
        "convert_invoice_label": "{src}→{target} конвертация",
        "topup_needed": 'Это стоит {price} ⚡, а у вас {balance} ⚡.\n\nОтправлен счёт на {stars} ⭐ — он добавит {credited} ⚡: хватит на эту конвертацию, остаток останется на балансе. /cancel, чтобы отменить.',
        "credit_policy_note": '⚠️ ВНИМАНИЕ: ⚡ списывается, когда конвертация НАЧИНАЕТСЯ. Остановишь её сам — ⚡ НЕ вернётся; если сбой на стороне бота, ⚡ сразу вернётся на баланс. Платежи окончательные — Stars не возвращаются.',
        "send_limit_note": '📤 Готовый файл может весить до {mb} МБ. Если он получится больше, отправлен он не будет — тогда ⚡ сразу вернётся на баланс.',
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
        "job_reason_too_slow": "На этот файл ушло бы около {minutes} мин., а конвертация здесь может идти не дольше {limit} мин., поэтому я остановил её сразу, а не заставил вас ждать до конца лимита. Подойдёт ролик покороче или в меньшем разрешении.",
        "job_reason_crash": 'Конвертация сломалась на моей стороне. Владелец в курсе.',
        "job_reason_too_large": '{target} получился на {mb} МБ, а по этой конвертации я могу отправить не больше {limit} МБ. JPG, WEBP или AVIF будут намного меньше. Владелец в курсе.',
        "job_reason_send_failed": 'Файл сконвертирован, но отправить его тебе не вышло. Владелец в курсе.',
        "job_reason_interrupted": 'Меня перезапустили посреди конвертации. Пришли файл снова через минуту.',
        "unknown_order": "Неизвестный заказ.",
        "unrecognized_message": (
            "Это не файл, который я могу конвертировать — пришли файл или "
            "/formats, чтобы увидеть, что я принимаю. Назовёшь формат («heic», "
            "«epub») — скажу, во что он превращается."
        ),
        "unknown_command": "Я не знаю такую команду. Отправь /start, чтобы увидеть, что я умею.",

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
        "price_from": "от {price} ⚡: большинство картинок, песен и документов",
        "price_example": "видео {mb} МБ в MP4: {price} ⚡",
        "price_at_most": "самый большой файл, {mb} МБ: не больше {price} ⚡",
        "price_quoted_first": "Точную цену я назову до того, как что-то спишется, — и спишу именно её.",
    },
}

import problems

_BOT = "convert_bot"

def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))

async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler call."""
    cached = context.user_data.get("lang")
    if cached:
        return cached
    lang = await asyncio.to_thread(db.get_user_language, user_id) or "en"
    context.user_data["lang"] = lang
    return lang

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

# ─── module: downloader_bot.i18n ─────────────────────────────────────────────
"""Translation strings for DownloaderBot's end-user-facing text (English, Uzbek, Russian)."""
import asyncio

import db

SUPPORTED_LANGUAGES = ("en", "uz", "ru")
LANGUAGE_LABELS = {"en": "English 🇬🇧", "uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺"}

LANGUAGE_PROMPT = (
    "👋 Welcome! / Xush kelibsiz! / Добро пожаловать!\n\n"
    "Please choose your language / Iltimos, tilni tanlang / "
    "Пожалуйста, выберите язык:"
)

STRINGS = {
    "en": {
        "quota_hour": (
            "You've had {used} downloads in the last hour, which is this bot's limit "
            "({limit}/hour) — it's there so everyone gets a turn on a small server. "
            "The next one frees up in about {minutes} minute(s)."
        ),
        "quota_day": (
            "You've had {used} downloads today, which is this bot's daily limit "
            "({limit}) — it's there so everyone gets a turn on a small server. "
            "It frees up again in about {minutes} minute(s)."
        ),
        "quota_donor_hint": (
            "If you need more: anyone who has ever chipped in via /donate gets a much "
            "higher limit, permanently. One donation of any size is enough."
        ),
        "flood_wait": "You're going faster than I can keep up with — give it about {seconds} second(s) and carry on.",

        "sibling_blurb": "Also part of this bot family, see below \U0001f447",
        "donation_nudge": (
            "💙 If this bot's been useful: hosting/API costs are covered by whoever's "
            "running it, and /donate is a totally optional way to help keep it alive. "
            "No pressure either way!"
        ),
        "donate_unknown_currency": 'Unknown currency "{currency}" — try xtr or usd.',
        "donate_currency_not_configured": "{currency} donations aren't set up on this bot yet — try Stars instead.",
        "donate_invalid_amount": "That's not a valid amount — try e.g. /donate 500 or /donate 5 usd.",
        "donate_prompt": (
            "Thank you for contributing — it goes directly toward this bot's "
            "hosting and API costs. Choose an amount below, or Custom to enter "
            "your own (you can also send /donate <number> [usd] directly)."
        ),
        "donate_custom_button": "✏️ Custom {symbol}",
        "donate_too_many_stars": "That's a lot of stars! Keep it under {max} ⭐ per donation.",
        "donate_out_of_range": "{currency} donations need to be between {lo} and {hi} {symbol}.",
        "donate_invoice_title": "Contribute to hosting",
        "donate_invoice_description": "Goes towards what this bot costs to run, and adds {credited} ⚡ of credit to your balance for conversions in ConvertBot.",
        "donate_invoice_label": "Hosting contribution",
        "donate_invoice_description_fiat": 'A one-time voluntary donation towards hosting costs. Thank you!',
        "donate_prompt_credit": 'Stars you pay become ⚡ credit for conversions in ConvertBot. Your next {left} ⭐ earn {each} ⚡ each ({mult}×): {rate} ⚡ of ordinary credit plus a bonus that expires {days} days after payment. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_prompt_credit_base": 'Stars you pay become ⚡ credit for conversions in ConvertBot, {rate} ⚡ per ⭐. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_invoice_error": "⚠️ Telegram wouldn't create that invoice: {error}",
        "stars_unit": "Stars",
        "donate_custom_ask": "How many {unit} would you like to donate? Reply with a number.",
        "donate_invalid_amount_retry": "That's not a valid amount — send /donate to try again.",
        "donate_thanks": "🙏 Thank you for the {amount} ⭐ — genuinely appreciated!",
        "topup_thanks": "🙏 Thank you for donating {stars} ⭐ — it helps keep the bots running.\n\nAs a thank-you, you've received {total} ⚡ of credit in {convert_bot} to use on file conversions. Your credit there: {balance} ⚡.",
        "topup_thanks_bonus": 'Of that, {bonus} ⚡ is bonus credit and expires on {date}.',
        "credit_cannot_be_withdrawn": '⚡ is credit for conversions in ConvertBot, and can NOT be withdrawn or turned back into Stars. A problem with a payment? /paysupport',
        "paysupport_text": '💳 Help with a payment\n\nPayments are FINAL: Stars are NOT refunded, and ⚡ credit can NOT be withdrawn or turned back into Stars.\n\nIf a payment went wrong — you were charged and no credit arrived, or you were charged twice — write to {contact} with the date, the amount and your Telegram id, {user_id}. It will be checked and put right with credit.\n\n/balance lists every payment and what it added.',
        "report_button": '🐞 Add my details',
        "problem_logged_note": "This is already written down for the bot's owner — the code, the time and the version, and nothing about you.",
        "report_disclaimer": "📨 Add your own details to this problem?\n\nAlready recorded, with you left out of it: the bot's name, the error code {code}, the incident number {incident}, when it happened and the bot's version.\n\nTapping Send adds four things: your Telegram user ID, your @username if you have one, the language you picked, and whether this chat is private or a group. Not what you wrote, and not the file you sent.\n\nIt lets your case be found in the logs, which is usually what makes a rare problem fixable. Entirely your choice.",
        "report_send": '📨 Send my details',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — your details are on incident {incident} now, which is what makes this one findable.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent. The problem itself stays logged.',
        "report_failed": "⚠️ The report couldn't be sent right now. Please try again later.",
        "report_invalid": 'This button no longer works.',
        "crash_notice": "⚠️ Something went wrong on the bot's side while handling that, so it wasn't done. Please try again in a moment.",
        "sandbox_notice": "🧪 Test mode — no real Stars were charged for this.",
        "balance_header": "⚡ Your balance: {balance}",
        "balance_totals": "Paid {paid} ⭐ in total · credited {credited} ⚡ · spent {spent} ⚡",
        "balance_rate": 'Your next {left} ⭐ earn {each} ⚡ each ({mult}×).',
        "balance_rate_base": '1 ⭐ buys {rate} ⚡.',
        "balance_bonus_line": 'Of that, {bonus} ⚡ is bonus credit — {soon} ⚡ of it expires on {date}.',
        "balance_recent": "Recent:",
        "balance_empty_hint": "/donate adds credit whenever you want some.",
        "bot_short_description": (
            "Paste a public Instagram, TikTok, Pinterest, Reddit or X link."
        ),
        "bot_description": (
            "Paste a link to a public post and the media comes back. No command needed.\n"
            "\n"
            "Instagram, TikTok, Pinterest, Reddit and X. Carousels arrive whole, and a text post "
            "comes back as a rendered card.\n"
            "\n"
            "It fetches what is already public — it is not a way around a private account. "
            "English, Uzbek and Russian. /privacy says what it keeps."
        ),

        "privacy_heading": "🔒 Privacy",
        "privacy_kept_heading": "What this bot keeps:",
        "privacy_stored": (
            "• your Telegram user id, your language, and your caption and quality settings\n"
            "• the link you send, for as long as it takes to fetch what is behind it\n"
            "• one row per download — which platform and when, which is what the daily allowance "
            "counts\n"
            "• a timestamp each time you use the bot, so its owner can tell whether anyone is "
            "using it\n"
            "• a record of any donation: the amount and Telegram's payment id\n"
            "• whatever the bot is in the middle of doing with you, until it is finished\n"
            "\n"
            "The media itself is not kept. It is fetched, sent to you, and deleted."
        ),
        "privacy_problems_heading": "When something goes wrong:",
        "privacy_problems": (
            "Every error this bot shows anybody is written down by itself: the error code, an "
            "incident number, when it happened and the bot's version. Nothing in that is about "
            "you — not your id, not your name, not what you sent. A fault nobody reports is "
            "still a fault, which is why it does not wait to be asked.\n"
            "\n"
            "\"Add my details\" under an error offers to attach four things to that one "
            "incident: your Telegram user id, your @username if you have one, the language you "
            "picked, and whether the chat is private or a group. All four are named on screen "
            "first, and nothing is sent unless you tap Send. What you wrote and the files you "
            "sent are never part of it.\n"
            "\n"
            "Those four are cleared after 30 days on their own, and /deletemydata clears them "
            "straight away. The record of the error stays — it still happened — it just stops "
            "saying who hit it. The records themselves are deleted after 180 days."
        ),
        "privacy_seen_by_heading": "Who else sees it:",
        "privacy_seen_by": (
            "• Telegram, which carries every message both ways and sets its own terms\n"
            "• the hosting provider this bot runs on, and the database it writes to"
        ),
        "privacy_others": (
            "• the site you linked to, and the download services this bot falls back on when a "
            "site will not answer it directly. They get the link and see a request from this "
            "bot's server rather than from you; what they log is their business, under their own "
            "policies and not this one."
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
        "terms_specific": (
            "Downloads: this fetches what is already public and hands it to you. It is not a way "
            "around a private account and does not try to be one. What you do afterwards with "
            "someone else's photo, video or post is between you, them and the law — downloading "
            "something does not make it yours. There is a daily allowance per person, so that one "
            "person cannot make the bot unusable for everybody else."
        ),
        "terms_money": 'Money: /donate is voluntary and goes towards what the bots cost to run. A payment in Stars also adds ⚡ credit for conversions in ConvertBot: 2 ⚡ per ⭐, or 6 for your first 500 Stars ever and 4 for the next 500. The part above 2 is bonus credit and expires 90 days after the payment. Payments are FINAL: Stars are NOT refunded, and credit can NOT be withdrawn or turned back into Stars. Telegram handles every payment and the bot never sees a card number. A payment that went wrong: /paysupport.',
        "terms_no_warranty": (
            "No promises: one person runs this, it is free, and it can be slow, wrong, or off "
            "entirely without warning. Keep your own copy of anything that matters."
        ),
        "policy_full_text": "Full text: {url}",
        "policy_contact": "Questions, complaints or a data request: {contact}",
        "delete_data_confirm": "⚠️ This erases what this bot holds on you. There is no undo.",
        "delete_data_consequences": 'Your language, your caption and quality settings, and every record of what you downloaded and when all go. Your daily allowance resets with them. Nothing you downloaded is affected — it was never kept here.\n\nDonation records stay, without your username, because a dispute about a payment is settled against them. Your ⚡ balance stays too, and is still yours if you come back.',
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
        "cancel_button_donation": "💸 Donation amount",
        "cancel_item_donation": "the donation amount I asked you for",
        "cancel_item_stale_prompt": "a leftover prompt that was still waiting on an answer",

        "start_greeting": (
            "Hey! Send me a link (Instagram, TikTok, Pinterest, Reddit, or "
            "Twitter/X) and I'll grab it for you.\n\n"
        ),
        "help_text": 'Paste a link any time and I\'ll grab it — no command needed:\n  - Instagram: reels, photos, whole carousels\n  - TikTok: videos without the watermark, and photo slideshows\n  - Twitter/X: video and photos, or a clean image card for a text post\n  - Pinterest: the pin, at full size\n  - Reddit: the media if it\'s a media post, or a card if it\'s text\n\nCommands:\n/settings - the caption, the file quality, and large files (over 48 MB, for ⚡), on one screen\n/caption on|off - the "via @{username}" credit caption, on its own\n/lossless on|off - get downloads as uncompressed files\n/donate - chip in for hosting costs (totally optional)\n/cancel - stop something I\'m waiting on you for (I\'ll ask which)\n/en, /uz, /rus - switch language (or /language, which asks)\n/balance - your ⚡ credit\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n',
        "caption_state_on": "ON",
        "caption_state_off": "OFF",
        "settings_heading": "⚙️ Your settings. Tap to change any of them.",
        "caption_status": "Caption is currently {state}.",
        "caption_turned": "Download caption turned {state}.",
        "caption_toggle_answer": "Caption turned {state}.",
        "lossless_state_on": "ON",
        "lossless_state_off": "OFF",
        "lossless_status": "Lossless is currently {state}.\n\nON: downloads arrive as files, exactly as the source had them — no Telegram re-compression, but they don't play or preview in the chat until you open them.\nOFF: downloads arrive as photos and videos that play inline, compressed by Telegram.",
        "lossless_turned": "Lossless downloads turned {state}.",
        "lossless_toggle_answer": "Lossless turned {state}.",
        "large_state_on": "ON",
        "large_state_off": "OFF",
        "large_status": "📦 Large files are {state}.\n\nON: a download over {free} MB is still fetched, up to {max} MB, and sent as a file — ⚡{per} up to 100 MB, less for each 100 MB after (⚡{top} for {max} MB), charged only once it has arrived and never if it fails.\nOFF: anything over {free} MB is refused, and nothing is charged.",
        "large_toggle_answer": "Large files: {state}.",
        "large_files_turned_on": "📦 Large files are on. Send the link again and I'll get it — ⚡{per} up to 100 MB, less for each 100 MB after, charged once it has arrived. /settings turns it off again.",
        "large_files_turn_on_button": "📦 Turn on large files",
        "large_files_off": "📦 This one is bigger than {free} MB. I can still get it for you, as a file — ⚡{per} up to 100 MB, less for each 100 MB after — but only once you've switched on large files. Tap below (or /settings), then send the link again.",
        "large_files_private_only": "📦 This one is bigger than {free} MB. Files that big only come in a private chat with me — send me the link there.",
        "large_files_no_credit": "📦 This one is bigger than {free} MB, which costs at least ⚡{per}, and your balance is ⚡{balance}. Top up with /donate, then send the link again.",
        "large_files_fetching": "📦 Bigger than {free} MB — fetching it as a large file. ⚡{per} up to 100 MB, less for each 100 MB after, charged once it has arrived.",
        "large_files_too_big": "📦 This one is bigger than {max} MB, the most Telegram lets me send. Try a shorter clip.",
        "large_files_short": "📦 It came to {mb} MB, which costs ⚡{price}, and your balance is ⚡{balance} — so nothing was charged. Top up with /donate and send the link again.",
        "large_files_sending": "📦 {mb} MB is here. Sending it...",
        "large_files_send_failed": "📦 I got it, but couldn't send it to you. The ⚡{price} is back — your balance is ⚡{balance}.",
        "large_files_charged": "📦 {mb} MB, sent. ⚡{price} for it — your balance is now ⚡{balance}.",
        "download_credit_caption": "⬇️ via @{username}",
        "downloading": "Downloading...",
        "queued": "⏳ Busy with another download — yours starts in a moment.",
        "download_queue_full": 'You already have {count} links on the way. Send more when some of them arrive.',
        "download_short_on_space": "I'm short on temporary space right now — send that link again in a few minutes.",
        "restarting_send_again": "🔄 I'm being updated right now — give me a few seconds and send that again.",
        "update_soon_try_later": "🔧 I'm being updated in a moment, so I can't start anything new right now — please try again in about {minutes} minute(s). I'll message you when I'm back.",
        "update_soon_try_later_soon": "🔧 I'm being updated right now, so I can't start anything new — please try again shortly. I'll message you when I'm back.",
        "update_will_reset": "🔧 Heads up: I'm about to be updated, and what you have going right now will be reset. You'll be able to start it again in a few minutes.",
        "update_done_try_now": '✅ The update is done — go ahead and try again now.',
        "download_failed": "Couldn't download that: {error}",
        "download_blocked": "🚫 I tried every way I have of getting that one and the site turned all of them away. That is about where the request came from, not about your link. Try again in a bit — this usually sorts itself out.",
        "download_missing": "🔍 I couldn't find that post. Usually that means it was deleted, or it is from a private account. Public posts still work.",
        "download_too_big": "📦 That one is bigger than Telegram lets me send. Try a shorter clip.",
        "download_all_routes_failed": "😕 That one didn't work, and I tried every way I know. Give it a minute and send it again — if it keeps failing, it is the site, not the link.",
        "fetching": "Fetching...",
        "reddit_fetch_failed": "Couldn't fetch that Reddit post: {error}",
        "twitter_fetch_failed_link": "Couldn't fetch that post's content right now — here's the link: {url}",
        "unrecognized_message": (
            "That doesn't look like a link I recognize — Instagram, TikTok, "
            "Pinterest, Reddit, or Twitter/X — paste one to download it, or "
            "/help for commands."
        ),
        "redeliver_as_file": "📄 Get it as an uncompressed file",
        "redeliver_as_compressed": "🖼 Get it compressed instead",
        "redeliver_expired": (
            "That one is too old for the button now — send the link again, or use "
            "/lossless to change how everything arrives."
        ),
        "album_delivered": "{count} files above.",
        "unknown_command": "I don't recognize that command. Send /help to see what I can do.",
    },
    "uz": {
        "quota_hour": "So'nggi bir soatda {used} ta fayl yuklab oldingiz — bu soatlik limit ({limit} ta). Kichik serverda hammaga navbat yetishi uchun shunday. Keyingisi taxminan {minutes} daqiqadan keyin mumkin bo'ladi.",
        "quota_day": 'Bugun {used} ta fayl yuklab oldingiz — bu kunlik limit ({limit} ta). Kichik serverda hammaga navbat yetishi uchun shunday. Taxminan {minutes} daqiqadan keyin yana yuklab olishingiz mumkin.',
        "quota_donor_hint": "Ko'proq kerakmi? /donate orqali bir marta bo'lsa ham hissa qo'shganlar uchun limit butunlay ancha yuqori bo'ladi. Miqdori ahamiyatsiz.",
        "flood_wait": 'Juda tez yuboryapsiz — {seconds} soniyacha kutib, keyin davom eting.',
        "sibling_blurb": 'Oilamizdagi boshqa botlar pastda 👇',
        "donation_nudge": "💙 Bot sizga foydali bo'lgan bo'lsa: server va API xarajatlarini botni yuritayotgan odam o'z hisobidan qoplaydi. /donate orqali bunga hissa qo'shishingiz mumkin — bu mutlaqo ixtiyoriy.",
        "donate_unknown_currency": '"{currency}" degan valyuta yo\'q — xtr yoki usd deb yozing.',
        "donate_currency_not_configured": "Bu botda hozircha {currency} bilan xayriya qilib bo'lmaydi — Stars'dan foydalaning.",
        "donate_invalid_amount": "Miqdor noto'g'ri — masalan, /donate 500 yoki /donate 5 usd deb yozing.",
        "donate_prompt": "Hissangiz uchun rahmat — u to'g'ridan-to'g'ri botning server va API xarajatlariga ketadi. Quyidagi miqdorlardan birini tanlang yoki o'zingiz yozish uchun «Boshqa»ni bosing (/donate <son> [usd] deb ham yuborishingiz mumkin).",
        "donate_custom_button": "✏️ Boshqa {symbol}",
        "donate_too_many_stars": "Bu juda ko'p! Bir martalik xayriya {max} ⭐ dan oshmasin.",
        "donate_out_of_range": "{currency} bilan xayriya {lo} dan {hi} {symbol} gacha bo'lishi kerak.",
        "donate_invoice_title": 'Server xarajatlariga hissa',
        "donate_invoice_description": "Botlar xarajatlariga ketadi va ConvertBot'dagi konvertatsiyalar uchun balansingizga {credited} ⚡ kredit qo'shadi.",
        "donate_invoice_label": 'Xayriya',
        "donate_invoice_description_fiat": 'Server xarajatlari uchun bir martalik ixtiyoriy xayriya. Rahmat!',
        "donate_prompt_credit": "To'lagan Stars'ingiz ConvertBot'da konvertatsiyalarga sarflanadigan ⚡ kreditga aylanadi. Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×): {rate} ⚡ oddiy kredit, qolgani esa to'lovdan {days} kun o'tgach muddati tugaydigan bonus. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_prompt_credit_base": "To'lagan har bir ⭐ ConvertBot'da konvertatsiyalarga sarflanadigan {rate} ⚡ kreditga aylanadi. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_invoice_error": "⚠️ Telegram to'lov hisobini yaratmadi: {error}",
        "stars_unit": "Stars (yulduzcha)",
        "donate_custom_ask": 'Qancha {unit} xayriya qilmoqchisiz? Faqat sonni yozib yuboring.',
        "donate_invalid_amount_retry": "Miqdor noto'g'ri — qaytadan urinish uchun /donate yuboring.",
        "donate_thanks": '🙏 {amount} ⭐ uchun katta rahmat!',
        "topup_thanks": "🙏 {stars} ⭐ xayriyangiz uchun rahmat — bu botlarning ishlashiga yordam beradi.\n\nMinnatdorchilik sifatida {convert_bot} botida fayllarni o'girish uchun {total} ⚡ kredit oldingiz. U yerdagi balansingiz: {balance} ⚡.",
        "topup_thanks_bonus": 'Shundan {bonus} ⚡ — bonus kredit, uning muddati {date} kuni tugaydi.',
        "credit_cannot_be_withdrawn": "⚡ — ConvertBot'dagi konvertatsiyalar uchun kredit: uni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. To'lovda muammo bo'lsa: /paysupport",
        "paysupport_text": "💳 To'lov bo'yicha yordam\n\nTo'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.\n\nTo'lovda xatolik bo'lgan bo'lsa — pul yechilgan-u, kredit tushmagan bo'lsa yoki ikki marta yechilgan bo'lsa — {contact} manziliga to'lov sanasi, miqdori va Telegram ID raqamingizni ({user_id}) yozib yuboring. Tekshirilib, kredit bilan to'g'rilab beriladi.\n\n/balance har bir to'lovni va u qancha kredit qo'shganini ko'rsatadi.",
        "report_button": "🐞 Ma'lumotlarimni qo'shish",
        "problem_logged_note": "Bu muammo bot egasi uchun allaqachon yozib olindi — kodi, vaqti va bot versiyasi. Siz haqingizda hech narsa yo'q.",
        "report_disclaimer": "📨 Bu muammoga o'zingiz haqingizdagi ma'lumotni ham qo'shasizmi?\n\nSizsiz yozib olingani: bot nomi, {code} xato kodi, {incident} hodisa raqami, qachon yuz bergani va bot versiyasi.\n\n\"Yuborish\" tugmasi to'rt narsani qo'shadi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. Yozganingiz ham, yuborgan faylingiz ham emas.\n\nShunda sizning holatingizni loglardan topib bo'ladi — kam uchraydigan muammoni odatda shu tuzatib beradi. To'liq o'zingiz hal qilasiz.",
        "report_send": "📨 Ma'lumotlarimni yuborish",
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — ma'lumotlaringiz {incident} hodisasiga biriktirildi, endi uni topish oson.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi. Muammoning o'zi yozib olingan holicha qoladi.",
        "report_failed": "⚠️ Hozir xabarni yuborib bo'lmadi. Keyinroq qayta urinib ko'ring.",
        "report_invalid": 'Bu tugma endi ishlamaydi.',
        "crash_notice": "⚠️ Buni bajarishda bot tomonida xatolik yuz berdi, shuning uchun amal bajarilmadi. Birozdan keyin qayta urinib ko'ring.",
        "sandbox_notice": '🧪 Test rejimi — haqiqiy Stars yechilmadi.',
        "balance_header": "⚡ Balansingiz: {balance}",
        "balance_totals": "Jami {paid} ⭐ to'landi · {credited} ⚡ qo'shildi · {spent} ⚡ sarflandi",
        "balance_rate": 'Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×).',
        "balance_rate_base": '1 ⭐ = {rate} ⚡.',
        "balance_bonus_line": 'Shundan {bonus} ⚡ — bonus kredit; {soon} ⚡ ning muddati {date} kuni tugaydi.',
        "balance_recent": 'Oxirgi amallar:',
        "balance_empty_hint": '/donate orqali istalgan paytda kredit olishingiz mumkin.',
        "bot_short_description": (
            "Instagram, TikTok, Pinterest, Reddit yoki X havolasini tashlang."
        ),
        "bot_description": "Ochiq postning havolasini yuboring — fayl qaytib keladi. Buyruq shart emas.\n\nInstagram, TikTok, Pinterest, Reddit va X. Karusel to'liq keladi, matnli post esa chiroyli kartochka bo'lib qaytadi.\n\nBot faqat ochiq bo'lgan narsani oladi — yopiq akkauntlarni chetlab o'tmaydi. Ingliz, o'zbek va rus tillarida. Nima saqlanishi: /privacy",

        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz, tilingiz, izoh va sifat sozlamalaringiz\n• yuborgan havolangiz — undagi fayl olinguncha\n• har bir yuklab olish uchun bitta yozuv: qaysi platformadan va qachon; kunlik limit shu asosida hisoblanadi\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha\n\nFaylning o'zi saqlanmaydi: u olinadi, sizga yuboriladi va o'chiriladi.",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nXato ostidagi \"Ma'lumotlarimni qo'shish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• siz havolasini yuborgan sayt, hamda sayt to'g'ridan-to'g'ri javob bermaganda bot murojaat qiladigan yuklab olish xizmatlari. Ular havolani oladi va so'rov sizdan emas, bot serveridan kelganini ko'radi; ular nimani qayd etishi o'z qoidalariga bog'liq, bu botning qoidalariga emas.",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
        "privacy_your_choices": "Nima qilishingiz mumkin:\n/deletemydata — bot siz haqingizda saqlagan ma'lumotlarni o'chirish\n/terms — botdan foydalanish shartlari\n\nBotni Telegramda bloklasangiz, u sizga yozmay qo'yadi, lekin hech narsa o'chmaydi. Ikkalasini ham xohlasangiz, avval /deletemydata yuboring.",
        "terms_heading": "📜 Shartlar",
        "terms_use": "Botdan maqsadiga ko'ra, qonun va Telegram qoidalari doirasida foydalaning. Uni boshqalarni bezovta qilish uchun ishlatmang va belgilangan cheklovlardan oshirib yuklamang — aks holda akkaunt bloklanadi.",
        "terms_specific": "Yuklab olish haqida: bot faqat hammaga ochiq bo'lgan narsani olib beradi. Yopiq akkauntlarni chetlab o'tmaydi va bunga urinmaydi ham. Birovning surati, videosi yoki posti bilan keyin nima qilishingiz — siz, o'sha odam va qonun o'rtasidagi masala; yuklab olganingiz uni sizniki qilmaydi. Bitta odam botni boshqalar uchun band qilib qo'ymasligi uchun har bir kishiga kunlik limit bor.",
        "terms_money": "Pul haqida: /donate — ixtiyoriy, mablag' botlar xarajatlariga ketadi. Stars'dagi to'lov ConvertBot'da konvertatsiyalar uchun ⚡ kredit ham beradi: har ⭐ uchun 2 ⚡, umumiy hisobda birinchi 500 ta Stars uchun esa 6 ⚡ dan, keyingi 500 tasi uchun 4 ⚡ dan. 2 ⚡ dan ortig'i bonus kredit bo'lib, to'lovdan 90 kun o'tgach muddati tugaydi. To'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Har bir to'lovni Telegram o'tkazadi, bot karta raqamingizni ko'rmaydi. To'lovda muammo bo'lsa: /paysupport.",
        "terms_no_warranty": "Kafolat yo'q: botni bir kishi yuritadi va u oldindan ogohlantirmasdan sekinlashishi, xato qilishi yoki butunlay to'xtab qolishi mumkin. Siz uchun muhim narsalarning nusxasini o'zingizda saqlang.",
        "policy_full_text": "To'liq matn: {url}",
        "policy_contact": "Savol, shikoyat yoki ma'lumot so'rovi uchun: {contact}",
        "delete_data_confirm": "⚠️ Bot siz haqingizda saqlagan ma'lumotlar o'chiriladi. Buni ortga qaytarib bo'lmaydi.",
        "delete_data_consequences": "Til, izoh va sifat sozlamalaringiz hamda nimani qachon yuklab olganingiz haqidagi qaydlar o'chiriladi. Kunlik limitingiz ham yangilanadi. Yuklab olgan fayllaringizga hech narsa qilmaydi — ular bu yerda umuman saqlanmagan.\n\nXayriya yozuvlari foydalanuvchi nomingizsiz saqlanib qoladi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi. ⚡ balansingiz ham saqlanadi — qaytib kelsangiz, u o'z joyida bo'ladi.",
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
        "cancel_button_donation": "💸 Xayriya miqdori",
        "cancel_item_donation": 'kiritilishi kutilayotgan xayriya miqdori',
        "cancel_item_stale_prompt": "javobsiz qolgan eski so'rov",
        "start_greeting": (
            "Salom! Menga havola yuboring (Instagram, TikTok, Pinterest, Reddit "
            "yoki Twitter/X) va men uni siz uchun yuklab beraman.\n\n"
        ),
        "help_text": 'Havola yuboring — faylni olib beraman, buyruq kerak emas:\n  - Instagram: reels, rasmlar, butun karusel\n  - TikTok: suv belgisiz video va rasm-slaydlar\n  - Twitter/X: video va rasmlar, matnli post uchun esa rasm-kartochka\n  - Pinterest: pin, asl o\'lchamda\n  - Reddit: media post bo\'lsa — media, matnli bo\'lsa — kartochka\n\nBuyruqlar:\n/settings - izoh, fayl sifati va katta fayllar (48 MB dan katta, ⚡ evaziga) — hammasi bitta ekranda\n/caption on|off - fayllar ostidagi "via @{username}" yozuvini yoqish/o\'chirish\n/lossless on|off - fayllarni siqilmagan holda olish\n/donate - server xarajatlariga hissa qo\'shish (ixtiyoriy)\n/cancel - joriy amalni bekor qilish (bir nechta bo\'lsa, qaysi birini so\'rayman)\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/balance - ⚡ kreditingiz\n/paysupport - to\'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o\'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n\n⚠️ DIQQAT: To\'lovlar QAYTARILMAYDI — /donate orqali to\'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO\'LMAYDI.\n\n',
        "caption_state_on": "YONIQ",
        "caption_state_off": "O'CHIQ",
        "settings_heading": "⚙️ Sozlamalaringiz. O'zgartirish uchun bosing.",
        "caption_status": "Izoh hozir {state}.",
        "caption_turned": 'Fayl izohi endi {state}.',
        "caption_toggle_answer": 'Izoh endi {state}.',
        "lossless_state_on": "YONIQ",
        "lossless_state_off": "O'CHIQ",
        "lossless_status": "Siqilmagan rejim hozir {state}.\n\nYONIQ: fayllar asl sifatida, hujjat ko'rinishida keladi — Telegram ularni siqmaydi, lekin ochmaguningizcha chatda ko'rinmaydi va ijro etilmaydi.\nO'CHIQ: fayllar chatda darhol ko'rinadigan rasm va video bo'lib keladi, lekin Telegram ularni siqadi.",
        "lossless_turned": 'Siqilmagan holda yuklash endi {state}.',
        "lossless_toggle_answer": 'Siqilmagan rejim endi {state}.',
        "large_state_on": "YONIQ",
        "large_state_off": "O'CHIQ",
        "large_status": "📦 Katta fayllar hozir {state}.\n\nYONIQ: {free} MB dan katta yuklamani ham {max} MB gacha olib kelaman va fayl sifatida yuboraman — 100 MB gacha ⚡{per}, keyingi har 100 MB undan arzonroq ({max} MB uchun ⚡{top}). Kredit fayl yetib kelgandan keyingina yechiladi, xato bo'lsa umuman yechilmaydi.\nO'CHIQ: {free} MB dan kattasi rad etiladi va hech narsa yechilmaydi.",
        "large_toggle_answer": "Katta fayllar: {state}.",
        "large_files_turned_on": "📦 Katta fayllar yoqildi. Havolani yana yuboring — olib kelaman. 100 MB gacha ⚡{per}, keyingi har 100 MB undan arzonroq; kredit fayl yetib kelgach yechiladi. O'chirish uchun: /settings.",
        "large_files_turn_on_button": "📦 Katta fayllarni yoqish",
        "large_files_off": "📦 Bu fayl {free} MB dan katta. Uni baribir fayl qilib olib bera olaman — 100 MB gacha ⚡{per}, keyingi har 100 MB undan arzonroq, lekin avval katta fayllarni yoqishingiz kerak. Pastdagi tugmani bosing (yoki /settings), keyin havolani yana yuboring.",
        "large_files_private_only": "📦 Bu fayl {free} MB dan katta. Bunday fayllarni faqat men bilan shaxsiy chatda yuboraman — havolani o'sha yerga tashlang.",
        "large_files_no_credit": "📦 Bu fayl {free} MB dan katta, narxi kamida ⚡{per}, balansingizda esa ⚡{balance} bor. /donate orqali to'ldiring, keyin havolani yana yuboring.",
        "large_files_fetching": "📦 {free} MB dan katta — katta fayl sifatida olib kelyapman. 100 MB gacha ⚡{per}, keyingi har 100 MB undan arzonroq; kredit fayl yetib kelgach yechiladi.",
        "large_files_too_big": "📦 Bu fayl {max} MB dan katta — Telegram menga bundan kattasini yuborishga ruxsat bermaydi. Qisqaroq videoni sinab ko'ring.",
        "large_files_short": "📦 Fayl {mb} MB chiqdi, narxi ⚡{price}, balansingizda esa ⚡{balance} — shuning uchun hech narsa yechilmadi. /donate orqali to'ldiring va havolani yana yuboring.",
        "large_files_sending": "📦 {mb} MB tayyor. Yuboryapman...",
        "large_files_send_failed": "📦 Faylni oldim, lekin sizga yubora olmadim. ⚡{price} qaytarildi — balansingiz ⚡{balance}.",
        "large_files_charged": "📦 {mb} MB yuborildi. Buning uchun ⚡{price} yechildi — balansingiz endi ⚡{balance}.",
        "download_credit_caption": "⬇️ @{username} orqali",
        "downloading": "Yuklanmoqda...",
        "queued": '⏳ Boshqa fayl yuklanmoqda — sizniki birozdan keyin boshlanadi.',
        "download_queue_full": 'Sizning {count} ta havolangiz yuklanmoqda. Ulardan biri kelgach, yana yuboring.',
        "download_short_on_space": 'Hozir vaqtinchalik joy yetishmayapti — havolani bir necha daqiqadan keyin qayta yuboring.',
        "restarting_send_again": '🔄 Bot hozir yangilanmoqda — bir necha soniyadan keyin qaytadan yuboring.',
        "update_soon_try_later": "🔧 Bot tez orada yangilanadi, shuning uchun yangi ishni boshlab bo'lmaydi — taxminan {minutes} daqiqadan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_soon_try_later_soon": "🔧 Bot hozir yangilanmoqda, shuning uchun yangi ishni boshlab bo'lmaydi — birozdan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_will_reset": "🔧 Diqqat: bot yangilanadi va hozir bajarilayotgan ishingiz to'xtab qoladi. Bir necha daqiqadan keyin qaytadan boshlashingiz mumkin.",
        "update_done_try_now": "✅ Yangilanish tugadi — endi qaytadan urinib ko'rishingiz mumkin.",
        "download_failed": "Buni yuklab bo'lmadi: {error}",
        "download_blocked": '🚫 Buni olishning barcha yo‘llarini sinab ko‘rdim, sayt hammasini rad etdi. Bu havolangizga emas, so‘rov qayerdan kelganiga bog‘liq. Birozdan so‘ng qayta urinib ko‘ring — odatda o‘zi tuzalib ketadi.',
        "download_missing": '🔍 Bu postni topa olmadim. Odatda bu post o‘chirilgan yoki yopiq akkauntdan ekanini bildiradi. Ochiq postlar ishlayveradi.',
        "download_too_big": '📦 Bu fayl Telegram ruxsat beradigan hajmdan katta. Qisqaroq video sinab ko‘ring.',
        "download_all_routes_failed": '😕 Bu ishlamadi, men bilgan barcha yo‘llarni sinab ko‘rdim. Bir daqiqadan so‘ng yana yuboring — agar takrorlansa, muammo havolada emas, saytda.',
        "fetching": "Olinmoqda...",
        "reddit_fetch_failed": "Bu Reddit postini olib bo'lmadi: {error}",
        "twitter_fetch_failed_link": "Hozircha bu post mazmunini olib bo'lmadi — mana havola: {url}",
        "unrecognized_message": "Bu tanish havolaga o'xshamayapti. Instagram, TikTok, Pinterest, Reddit yoki Twitter/X havolasini yuboring — buyruqlar ro'yxati: /help",
        "redeliver_as_file": "📄 Siqilmagan fayl sifatida olish",
        "redeliver_as_compressed": "🖼 Siqilgan holda olish",
        "redeliver_expired": "Bu tugmaning muddati o'tgan — havolani qaytadan yuboring yoki fayllar qanday kelishini /lossless orqali o'zgartiring.",
        "album_delivered": "Yuqorida {count} ta fayl.",
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /help yuboring.",
    },
    "ru": {
        "quota_hour": (
            "За последний час ты скачал {used} — это предел этого бота ({limit} в час). "
            "Он нужен, чтобы на маленьком сервере хватало всем. Следующая попытка "
            "освободится примерно через {minutes} минут(ы)."
        ),
        "quota_day": (
            "Сегодня ты скачал {used} — это дневной предел бота ({limit}). Он нужен, "
            "чтобы на маленьком сервере хватало всем. Снова откроется примерно через "
            "{minutes} минут(ы)."
        ),
        "quota_donor_hint": (
            "Если нужно больше: у всех, кто хоть раз поддержал бота через /donate, "
            "предел заметно выше и навсегда. Сумма значения не имеет."
        ),
        "flood_wait": "Ты отправляешь быстрее, чем я успеваю — подожди примерно {seconds} секунд(ы) и продолжай.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотри ниже \U0001f447",
        "donation_nudge": (
            "💙 Если этот бот оказался полезным: расходы на хостинг/API покрывает тот, "
            "кто его запустил, а /donate — это совершенно необязательный способ помочь "
            "ему остаться на плаву. Никакого давления в любом случае!"
        ),
        "donate_unknown_currency": 'Неизвестная валюта "{currency}" — попробуйте xtr или usd.',
        "donate_currency_not_configured": "Пожертвования в {currency} на этом боте пока не настроены — попробуйте Stars.",
        "donate_invalid_amount": "Это некорректная сумма — попробуйте, например, /donate 500 или /donate 5 usd.",
        "donate_prompt": (
            "Спасибо за вклад — эти средства идут прямо на хостинг и API этого "
            "бота. Выберите сумму ниже или нажмите «Другое», чтобы ввести свою "
            "(также можно сразу отправить /donate <число> [usd])."
        ),
        "donate_custom_button": "✏️ Другое {symbol}",
        "donate_too_many_stars": "Это очень много звёзд! Пусть будет меньше {max} ⭐ за одно пожертвование.",
        "donate_out_of_range": "Пожертвования в {currency} должны быть в диапазоне от {lo} до {hi} {symbol}.",
        "donate_invoice_title": "Поддержать хостинг",
        "donate_invoice_description": "Идёт на расходы по работе бота и добавляет {credited} ⚡ на ваш баланс для конвертаций в ConvertBot.",
        "donate_invoice_label": "Вклад в хостинг",
        "donate_invoice_description_fiat": 'Разовое добровольное пожертвование на хостинг. Спасибо!',
        "donate_prompt_credit": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации в ConvertBot. Следующие {left} ⭐ дают по {each} ⚡ ({mult}×): {rate} ⚡ обычного кредита и бонус, который сгорает через {days} дней после оплаты. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_prompt_credit_base": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации в ConvertBot, {rate} ⚡ за ⭐. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_invoice_error": "⚠️ Telegram не смог создать этот счёт: {error}",
        "stars_unit": "Stars (звёзды)",
        "donate_custom_ask": "Сколько {unit} вы хотите пожертвовать? Ответьте числом.",
        "donate_invalid_amount_retry": "Это некорректная сумма — отправьте /donate, чтобы попробовать снова.",
        "donate_thanks": "🙏 Спасибо за {amount} ⭐ — это по-настоящему ценно!",
        "topup_thanks": '🙏 Спасибо за пожертвование в {stars} ⭐ — это помогает ботам работать.\n\nВ благодарность вы получили {total} ⚡ кредита в {convert_bot} — его можно тратить на конвертацию файлов. Ваш баланс там: {balance} ⚡.',
        "topup_thanks_bonus": 'Из них {bonus} ⚡ — бонусный кредит, он сгорит {date}.',
        "credit_cannot_be_withdrawn": '⚡ — это кредит на конвертации в ConvertBot, его НЕЛЬЗЯ вывести или обменять обратно на Stars. Проблема с платежом? /paysupport',
        "paysupport_text": '💳 Помощь с платежом\n\nПлатежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести или обменять обратно на Stars.\n\nЕсли с платежом что-то пошло не так — деньги списали, а кредит не пришёл, или списали дважды, — напишите на {contact}: дату, сумму и ваш Telegram ID, {user_id}. Это проверят и исправят кредитом.\n\n/balance показывает каждый платёж и что он добавил.',
        "report_button": '🐞 Добавить мои данные',
        "problem_logged_note": 'Эта проблема уже записана для владельца бота — код, время и версия. О вас там ничего нет.',
        "report_disclaimer": '📨 Добавить к этой проблеме ваши данные?\n\nУже записано, без вас: название бота, код ошибки {code}, номер случая {incident}, когда это произошло и версия бота.\n\nКнопка «Отправить» добавит четыре вещи: ваш Telegram ID, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Ни того, что вы написали, ни отправленного файла.\n\nТогда ваш случай можно будет найти в логах — обычно именно это и позволяет починить редкую проблему. Решать только вам.',
        "report_send": '📨 Отправить мои данные',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — ваши данные теперь на случае {incident}, так его легко найти.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено. Сама проблема остаётся записанной.',
        "report_failed": '⚠️ Сейчас не удалось отправить сообщение. Попробуйте позже.',
        "report_invalid": 'Эта кнопка больше не работает.',
        "crash_notice": '⚠️ При обработке произошла ошибка на стороне бота, поэтому ничего не сделано. Попробуйте ещё раз чуть позже.',
        "sandbox_notice": "🧪 Тестовый режим — настоящие Stars не списывались.",
        "balance_header": "⚡ Ваш баланс: {balance}",
        "balance_totals": "Всего оплачено {paid} ⭐ · начислено {credited} ⚡ · потрачено {spent} ⚡",
        "balance_rate": 'Следующие {left} ⭐ дают по {each} ⚡ ({mult}×).',
        "balance_rate_base": '1 ⭐ даёт {rate} ⚡.',
        "balance_bonus_line": 'Из них {bonus} ⚡ — бонусный кредит; {soon} ⚡ сгорит {date}.',
        "balance_recent": "Последние операции:",
        "balance_empty_hint": "/donate добавит кредит в любой момент.",
        "bot_short_description": (
            "Пришли ссылку на пост в Instagram, TikTok, Pinterest, Reddit или X."
        ),
        "bot_description": (
            "Пришли ссылку на открытый пост — вернётся сам файл. Команда не нужна.\n"
            "\n"
            "Instagram, TikTok, Pinterest, Reddit и X. Карусель приходит целиком, а текстовый "
            "пост возвращается аккуратной карточкой.\n"
            "\n"
            "Бот достаёт то, что и так открыто, — это не обход закрытого аккаунта. Английский, "
            "узбекский и русский. /privacy — что бот хранит."
        ),

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": (
            "• твой числовой id в Telegram, язык и настройки подписи и качества\n"
            "• присланную ссылку — на то время, пока бот достаёт то, что за ней\n"
            "• по одной записи на скачивание: с какой площадки и когда — по ним считается "
            "дневной лимит\n"
            "• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли "
            "ботом хоть кто-нибудь\n"
            "• запись о пожертвовании: сумму и платёжный id Telegram\n"
            "• то, что бот в этот момент для тебя делает — пока не закончит\n"
            "\n"
            "Само видео или фото не хранится: бот его достаёт, отправляет тебе и удаляет."
        ),
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nКнопка «Добавить мои данные» под ошибкой предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
        "privacy_seen_by_heading": "Кто ещё это видит:",
        "privacy_seen_by": (
            "• Telegram — он передаёт каждое сообщение в обе стороны и действует по своим "
            "правилам\n"
            "• хостинг, на котором работает бот, и база данных, в которую он пишет"
        ),
        "privacy_others": (
            "• сайт, на который ведёт ссылка, и сервисы скачивания, к которым бот обращается, "
            "когда сайт не отвечает ему напрямую. Они получают ссылку и видят запрос с сервера "
            "бота, а не от тебя; что они у себя пишут в логи — их дело и их правила, а не эти."
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
        "terms_specific": (
            "О скачивании: бот достаёт то, что и так открыто, и отдаёт тебе. Это не обход "
            "закрытого аккаунта, и он даже не пытается им быть. Что ты потом сделаешь с чужим "
            "фото, видео или постом — это между тобой, автором и законом: скачать не значит "
            "присвоить. На каждого есть дневной лимит, чтобы один человек не сделал бота "
            "бесполезным для всех остальных."
        ),
        "terms_money": 'О деньгах: /donate — дело добровольное, деньги идут на то, во что обходятся боты. Платёж в Stars ещё и добавляет ⚡ кредит на конвертации в ConvertBot: 2 ⚡ за ⭐, а за твои первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держи свою копию всего, что тебе важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о тебе. Отменить будет нельзя.",
        "delete_data_consequences": 'Язык, настройки подписи и качества и все записи о том, что и когда ты скачивал, будут стёрты. Дневной лимит вместе с ними обнулится. На уже скачанное это никак не влияет — здесь оно и не хранилось.\n\nЗаписи о пожертвованиях останутся, без username, потому что по ним разбираются споры о платежах. Баланс ⚡ тоже останется — он твой, если вернёшься.',
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
        "cancel_button_donation": "💸 Сумма пожертвования",
        "cancel_item_donation": "\u0441\u0443\u043c\u043c\u0430 \u043f\u043e\u0436\u0435\u0440\u0442\u0432\u043e\u0432\u0430\u043d\u0438\u044f, \u043a\u043e\u0442\u043e\u0440\u0443\u044e \u044f \u0437\u0430\u043f\u0440\u043e\u0441\u0438\u043b",
        "cancel_item_stale_prompt": "старый запрос, который всё ещё ждал ответа",
        "start_greeting": (
            "Привет! Пришли мне ссылку (Instagram, TikTok, Pinterest, Reddit "
            "или Twitter/X), и я скачаю это для тебя.\n\n"
        ),
        "help_text": 'Просто пришли ссылку в любое время — я её заберу, команда не нужна:\n  - Instagram: reels, фото, карусели целиком\n  - TikTok: видео без водяного знака и фото-слайдшоу\n  - Twitter/X: видео и фото, а для текстового поста — аккуратная карточка\n  - Pinterest: пин в полном размере\n  - Reddit: медиа, если это медиа-пост, или карточка, если это текст\n\nКоманды:\n/settings - подпись, качество файлов и большие файлы (больше 48 МБ, за ⚡), всё на одном экране\n/caption on|off - подпись "via @{username}" на загрузках, отдельно\n/lossless on|off - получать загрузки несжатыми файлами\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/balance - ваш ⚡ кредит\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
        "caption_state_on": "ВКЛ",
        "caption_state_off": "ВЫКЛ",
        "settings_heading": "⚙️ Ваши настройки. Нажмите, чтобы изменить.",
        "caption_status": "Подпись сейчас {state}.",
        "caption_turned": "Подпись к загрузкам теперь {state}.",
        "caption_toggle_answer": "Подпись теперь {state}.",
        "lossless_state_on": "ВКЛ",
        "lossless_state_off": "ВЫКЛ",
        "lossless_status": "Режим без потерь сейчас {state}.\n\nВКЛ: загрузки приходят файлом, ровно такими, какими были в источнике — Telegram их не пережимает, но они не проигрываются в чате, пока вы их не откроете.\nВЫКЛ: загрузки приходят фото и видео, которые играют прямо в чате, со сжатием Telegram.",
        "lossless_turned": "Загрузка без потерь теперь {state}.",
        "lossless_toggle_answer": "Режим без потерь теперь {state}.",
        "large_state_on": "ВКЛ",
        "large_state_off": "ВЫКЛ",
        "large_status": "📦 Большие файлы сейчас {state}.\n\nВКЛ: загрузку больше {free} МБ я всё равно скачаю — до {max} МБ — и пришлю файлом: ⚡{per} до 100 МБ, каждые следующие 100 МБ дешевле ({max} МБ — ⚡{top}). Списываю, только когда файл уже скачан, и ничего — если не получилось.\nВЫКЛ: всё, что больше {free} МБ, отклоняется, и ничего не списывается.",
        "large_toggle_answer": "Большие файлы: {state}.",
        "large_files_turned_on": "📦 Большие файлы включены. Пришлите ссылку ещё раз — я скачаю. ⚡{per} до 100 МБ, каждые следующие 100 МБ дешевле; спишу, когда файл уже будет у меня. Выключить: /settings.",
        "large_files_turn_on_button": "📦 Включить большие файлы",
        "large_files_off": "📦 Этот файл больше {free} МБ. Я всё равно могу прислать его файлом — ⚡{per} до 100 МБ, каждые следующие 100 МБ дешевле, — но только если вы включите большие файлы. Нажмите кнопку ниже (или /settings), потом пришлите ссылку ещё раз.",
        "large_files_private_only": "📦 Этот файл больше {free} МБ. Такие файлы я присылаю только в личном чате — отправьте ссылку туда.",
        "large_files_no_credit": "📦 Этот файл больше {free} МБ, это стоит минимум ⚡{per}, а на балансе ⚡{balance}. Пополните через /donate и пришлите ссылку ещё раз.",
        "large_files_fetching": "📦 Больше {free} МБ — скачиваю как большой файл. ⚡{per} до 100 МБ, каждые следующие 100 МБ дешевле; спишу, когда он будет у меня.",
        "large_files_too_big": "📦 Этот файл больше {max} МБ — больше Telegram мне отправлять не позволяет. Попробуйте ролик покороче.",
        "large_files_short": "📦 Получилось {mb} МБ, это ⚡{price}, а на балансе ⚡{balance} — поэтому ничего не списано. Пополните через /donate и пришлите ссылку ещё раз.",
        "large_files_sending": "📦 {mb} МБ скачано. Отправляю...",
        "large_files_send_failed": "📦 Я скачал файл, но не смог его вам отправить. ⚡{price} вернулись — на балансе ⚡{balance}.",
        "large_files_charged": "📦 {mb} МБ, отправлено. За это ⚡{price} — на балансе теперь ⚡{balance}.",
        "download_credit_caption": "⬇️ через @{username}",
        "downloading": "Скачивание...",
        "queued": "⏳ Занят другой загрузкой — ваша начнётся через мгновение.",
        "download_queue_full": 'У вас уже {count} ссылок в работе. Присылайте ещё, когда какие-то придут.',
        "download_short_on_space": 'Сейчас не хватает временного места — пришлите ссылку снова через пару минут.',
        "restarting_send_again": "🔄 Сейчас обновляюсь — подождите несколько секунд и отправьте ещё раз.",
        "update_soon_try_later": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова примерно через {minutes} мин. Я напишу, когда вернусь.',
        "update_soon_try_later_soon": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова чуть позже. Я напишу, когда вернусь.',
        "update_will_reset": '🔧 Внимание: меня скоро обновят, и то, что вы сейчас начали, будет сброшено. Через несколько минут сможете начать заново.',
        "update_done_try_now": '✅ Обновление завершено — можете пробовать снова.',
        "download_failed": "Не удалось это скачать: {error}",
        "download_blocked": '🚫 Я перебрал все способы достать это, и сайт отказал всем. Дело не в ссылке, а в том, откуда пришёл запрос. Попробуйте через некоторое время — обычно это проходит само.',
        "download_missing": '🔍 Не нашёл этот пост. Обычно это значит, что его удалили или он из закрытого аккаунта. Публичные посты работают.',
        "download_too_big": '📦 Это больше, чем Telegram позволяет мне отправить. Попробуйте ролик покороче.',
        "download_all_routes_failed": '😕 Не получилось, а я пробовал все способы. Подождите минуту и пришлите снова — если повторяется, дело в сайте, а не в ссылке.',
        "fetching": "Загрузка...",
        "reddit_fetch_failed": "Не удалось получить этот пост Reddit: {error}",
        "twitter_fetch_failed_link": "Не удалось получить содержимое поста прямо сейчас — вот ссылка: {url}",
        "unrecognized_message": (
            "Это не похоже на ссылку, которую я узнаю — Instagram, TikTok, "
            "Pinterest, Reddit или Twitter/X — пришли одну из них, чтобы скачать, "
            "или /help для списка команд."
        ),
        "redeliver_as_file": "📄 Получить несжатым файлом",
        "redeliver_as_compressed": "🖼 Получить сжатым",
        "redeliver_expired": (
            "Для кнопки это уже слишком старая загрузка — пришли ссылку заново или "
            "поменяй способ доставки через /lossless."
        ),
        "album_delivered": "Выше {count} файл(ов).",
        "unknown_command": "Я не знаю такую команду. Отправь /help, чтобы увидеть, что я умею.",
    },
}

import problems

_BOT = "downloader_bot"

def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))

async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler call."""
    cached = context.user_data.get("lang")
    if cached:
        return cached
    lang = await asyncio.to_thread(db.get_user_language, user_id) or "en"
    context.user_data["lang"] = lang
    return lang

COMMAND_MENU = {
    "uz": {
        "start": "Bu bot nima qiladi va qanday boshlash kerak",
        "settings": "Izoh va fayl sifati sozlamalari",
        "cancel": "Kutayotgan amalimni to'xtatish",
        "help": "Nimalar qila olaman",
        "balance": "⚡ kreditingiz",
        "donate": "Server xarajatlariga hissa qo'shish",
        "paysupport": "To'lov bilan muammo",
        "privacy": "Siz haqingizda nimalarni saqlayman",
        "terms": "Botdan foydalanish shartlari",
        "deletemydata": "Siz haqingizdagi hamma narsani o'chirish",
    },
    "ru": {
        "start": "Что этот бот делает и с чего начать",
        "settings": "Подпись и качество файлов",
        "cancel": "Остановить то, чего я жду",
        "help": "Что я умею",
        "balance": "Ваш ⚡ кредит",
        "donate": "Помочь с расходами на хостинг",
        "paysupport": "Проблема с оплатой",
        "privacy": "Что я о вас храню",
        "terms": "Для чего можно пользоваться ботом",
        "deletemydata": "Удалить всё, что я о вас храню",
    },
}

# ─── module: anon_bot.i18n ───────────────────────────────────────────────────
"""Translation strings for AnonBot's end-user-facing text (English, Uzbek, Russian)."""
import asyncio

import db

SUPPORTED_LANGUAGES = ("en", "uz", "ru")
LANGUAGE_LABELS = {"en": "English 🇬🇧", "uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺"}

LANGUAGE_PROMPT = (
    "👋 Welcome! / Xush kelibsiz! / Добро пожаловать!\n\n"
    "Please choose your language / Iltimos, tilni tanlang / "
    "Пожалуйста, выберите язык:"
)

STRINGS = {
    "en": {
        "flood_wait": "You're going faster than I can keep up with — give it about {seconds} second(s) and carry on.",

        "sibling_blurb": "Also part of this bot family, see below \U0001f447",
        "donation_nudge": (
            "💙 If this bot's been useful: hosting/API costs are covered by whoever's "
            "running it, and /donate is a totally optional way to help keep it alive. "
            "No pressure either way!"
        ),
        "donate_unknown_currency": 'Unknown currency "{currency}" — try xtr or usd.',
        "donate_currency_not_configured": "{currency} donations aren't set up on this bot yet — try Stars instead.",
        "donate_invalid_amount": "That's not a valid amount — try e.g. /donate 500 or /donate 5 usd.",
        "donate_prompt": (
            "Thank you for contributing — it goes directly toward this bot's "
            "hosting and API costs. Choose an amount below, or Custom to enter "
            "your own (you can also send /donate <number> [usd] directly)."
        ),
        "donate_custom_button": "✏️ Custom {symbol}",
        "donate_too_many_stars": "That's a lot of stars! Keep it under {max} ⭐ per donation.",
        "donate_out_of_range": "{currency} donations need to be between {lo} and {hi} {symbol}.",
        "donate_invoice_title": "Contribute to hosting",
        "donate_invoice_description": "Goes towards what this bot costs to run, and adds {credited} ⚡ of credit to your balance for conversions in ConvertBot.",
        "donate_invoice_label": "Hosting contribution",
        "donate_invoice_description_fiat": 'A one-time voluntary donation towards hosting costs. Thank you!',
        "donate_prompt_credit": 'Stars you pay become ⚡ credit for conversions in ConvertBot. Your next {left} ⭐ earn {each} ⚡ each ({mult}×): {rate} ⚡ of ordinary credit plus a bonus that expires {days} days after payment. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_prompt_credit_base": 'Stars you pay become ⚡ credit for conversions in ConvertBot, {rate} ⚡ per ⭐. ⚡ can NOT be withdrawn or turned back into Stars.',
        "donate_invoice_error": "⚠️ Telegram wouldn't create that invoice: {error}",
        "stars_unit": "Stars",
        "donate_custom_ask": "How many {unit} would you like to donate? Reply with a number.",
        "donate_invalid_amount_retry": "That's not a valid amount — send /donate to try again.",
        "donate_thanks": "🙏 Thank you for the {amount} ⭐ — genuinely appreciated!",
        "topup_thanks": "🙏 Thank you for donating {stars} ⭐ — it helps keep the bots running.\n\nAs a thank-you, you've received {total} ⚡ of credit in {convert_bot} to use on file conversions. Your credit there: {balance} ⚡.",
        "topup_thanks_bonus": 'Of that, {bonus} ⚡ is bonus credit and expires on {date}.',
        "credit_cannot_be_withdrawn": '⚡ is credit for conversions in ConvertBot, and can NOT be withdrawn or turned back into Stars. A problem with a payment? /paysupport',
        "paysupport_text": '💳 Help with a payment\n\nPayments are FINAL: Stars are NOT refunded, and ⚡ credit can NOT be withdrawn or turned back into Stars.\n\nIf a payment went wrong — you were charged and no credit arrived, or you were charged twice — write to {contact} with the date, the amount and your Telegram id, {user_id}. It will be checked and put right with credit.\n\n/balance lists every payment and what it added.',
        "report_button": '🐞 Add my details',
        "problem_logged_note": "This is already written down for the bot's owner — the code, the time and the version, and nothing about you.",
        "report_disclaimer": "📨 Add your own details to this problem?\n\nAlready recorded, with you left out of it: the bot's name, the error code {code}, the incident number {incident}, when it happened and the bot's version.\n\nTapping Send adds four things: your Telegram user ID, your @username if you have one, the language you picked, and whether this chat is private or a group. Not what you wrote, and not the file you sent.\n\nIt lets your case be found in the logs, which is usually what makes a rare problem fixable. Entirely your choice.",
        "report_send": '📨 Send my details',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — your details are on incident {incident} now, which is what makes this one findable.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent. The problem itself stays logged.',
        "report_failed": "⚠️ The report couldn't be sent right now. Please try again later.",
        "report_invalid": 'This button no longer works.',
        "crash_notice": "⚠️ Something went wrong on the bot's side while handling that, so it wasn't done. Please try again in a moment.",
        "sandbox_notice": "🧪 Test mode — no real Stars were charged for this.",
        "balance_header": "⚡ Your balance: {balance}",
        "balance_totals": "Paid {paid} ⭐ in total · credited {credited} ⚡ · spent {spent} ⚡",
        "balance_rate": 'Your next {left} ⭐ earn {each} ⚡ each ({mult}×).',
        "balance_rate_base": '1 ⭐ buys {rate} ⚡.',
        "balance_bonus_line": 'Of that, {bonus} ⚡ is bonus credit — {soon} ⚡ of it expires on {date}.',
        "balance_recent": "Recent:",
        "balance_empty_hint": "/donate adds credit whenever you want some.",
        "bot_short_description": (
            "A permanent link that lets anyone write to you anonymously."
        ),
        "bot_description": (
            "Get a link and post it wherever you like. Anyone who opens it can write to you "
            "without you being shown who they are, and you can answer — as a real threaded "
            "conversation, several at once.\n"
            "\n"
            "They are anonymous to you, not to the bot: it stores which two accounts are talking "
            "so that a reply can reach the right thread, and never stores what either of you "
            "writes. /privacy has the whole of it.\n"
            "\n"
            "English, Uzbek and Russian."
        ),

        "privacy_heading": "🔒 Privacy",
        "privacy_kept_heading": "What this bot keeps:",
        "privacy_stored": (
            "• your Telegram user id, and the language you chose\n"
            "• your inbox link, if you have made one\n"
            "• who is talking to whom: a conversation is stored as the pair of user ids behind it "
            "plus a number, which is what lets a reply reach the right thread\n"
            "• which message belongs to which conversation, by message id, and when each was relayed\n"
            "• who you have blocked\n"
            "• a timestamp each time you use the bot, so its owner can tell whether anyone is "
            "using it\n"
            "• a record of any donation: the amount and Telegram's payment id\n"
            "\n"
            "What is not kept is what anybody writes. Messages pass straight through and are "
            "never stored here: they live in the two Telegram chats, and each side can delete "
            "their own copy. A document made with /export is assembled in memory, sent to you "
            "and dropped; nothing it reads is written down.\n"
            "\n"
            "Anonymous means anonymous to the person you are writing to. They are never shown "
            "your name, your username or your id. It is not anonymity from the bot itself — the "
            "pairing above is what makes a reply possible at all."
        ),
        "privacy_problems_heading": "When something goes wrong:",
        "privacy_problems": (
            "Every error this bot shows anybody is written down by itself: the error code, an "
            "incident number, when it happened and the bot's version. Nothing in that is about "
            "you — not your id, not your name, not what you sent. A fault nobody reports is "
            "still a fault, which is why it does not wait to be asked.\n"
            "\n"
            "\"Add my details\" under an error offers to attach four things to that one "
            "incident: your Telegram user id, your @username if you have one, the language you "
            "picked, and whether the chat is private or a group. All four are named on screen "
            "first, and nothing is sent unless you tap Send. What you wrote and the files you "
            "sent are never part of it.\n"
            "\n"
            "Those four are cleared after 30 days on their own, and /deletemydata clears them "
            "straight away. The record of the error stays — it still happened — it just stops "
            "saying who hit it. The records themselves are deleted after 180 days."
        ),
        "privacy_seen_by_heading": "Who else sees it:",
        "privacy_seen_by": (
            "• Telegram, which carries every message both ways and sets its own terms\n"
            "• the hosting provider this bot runs on, and the database it writes to"
        ),
        "privacy_others": (
            "• and nobody beyond those — messages go through Telegram and no further, and no outside service "
            "is called"
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
        "terms_specific": (
            "Messages: a hidden name is not a licence. Threats, harassment and anything illegal "
            "are all still exactly that when the sender is anonymous, and an inbox owner can "
            "block a sender for good. Anyone running an inbox is responsible for what they invite "
            "people to send them."
        ),
        "terms_money": 'Money: /donate is voluntary and goes towards what the bots cost to run. A payment in Stars also adds ⚡ credit for conversions in ConvertBot: 2 ⚡ per ⭐, or 6 for your first 500 Stars ever and 4 for the next 500. The part above 2 is bonus credit and expires 90 days after the payment. Payments are FINAL: Stars are NOT refunded, and credit can NOT be withdrawn or turned back into Stars. Telegram handles every payment and the bot never sees a card number. A payment that went wrong: /paysupport.',
        "terms_no_warranty": (
            "No promises: one person runs this, it is free, and it can be slow, wrong, or off "
            "entirely without warning. Keep your own copy of anything that matters."
        ),
        "policy_full_text": "Full text: {url}",
        "policy_contact": "Questions, complaints or a data request: {contact}",
        "delete_data_confirm": "⚠️ This erases what this bot holds on you. There is no undo.",
        "delete_data_consequences": 'Your inbox link stops working — every copy of it anybody has posted, permanently. Open conversations stop being routable, so neither side can reply into them any more, and your block list goes with them.\n\nMessages already sent are untouched. They were never stored here; they are in the Telegram chats, and each side deletes their own copy.\n\nDonation records stay, without your username, because a dispute about a payment is settled against them. Your ⚡ balance stays too, and is still yours if you come back.',
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
        "cancel_button_donation": "💸 Donation amount",
        "cancel_item_donation": "the donation amount I asked you for",
        "cancel_item_stale_prompt": "a leftover prompt that was still waiting on an answer",
        "cancel_item_anon_session": "the anonymous chat you had open — tap the link again to start a new one",
        "cancel_button_anon_session": "💬 The anonymous chat you're in",

        "start_greeting": "Hey! This bot runs anonymous-question inboxes.\n\n",
        "help_text": "Two ways to use this bot:\n\nGet your own inbox — /link gives you a permanent link. Post it anywhere public (bio, channel, story, wherever). Anyone who taps it can send you an anonymous message right here in this chat — you won't see who they are.\nAnswer by replying to the message — swipe it, or press and hold it and choose Reply. That is how I know which conversation your answer belongs to, so it is required rather than optional: one public link means several people can be mid-conversation with you at once, and a message that doesn't say which thread it answers could reach the wrong one. Your answer shows up on their end as a real reply too.\n\nGot sent someone else's link? Tap it and write — your first message goes straight through, with your identity hidden. After that, reply to the message you're answering, exactly as the other side does. Tapping the same link again later starts a brand-new conversation, it won't continue the old one.\n\nCommands:\n/link - get your inbox link\n/conversations - your conversations, open and archived\n/which - send it as a reply to any message: which conversation is that?\n/newlink, /pause, /resume - also buttons on the /link screen\n/blocked - review who you've blocked\n/stats - the counts, which are on the /link screen too\n/export - get a conversation back, copied here or as a document\n/donate - chip in for hosting costs (totally optional)\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/en, /uz, /rus - switch language (or /language, which asks)\n/balance - your ⚡ credit\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n/archive - send it as a reply to a message to archive that conversation (every row in /conversations has the button too)\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n",
        "follow_link_invalid": "That link isn't valid — it may have been reset by whoever shared it. Ask them for a fresh one.",
        "follow_link_own": "That's your own inbox link — messaging yourself would just be a note to self! Share it with other people instead: /link",
        "follow_link_blocked": "You're not able to message this person.",
        "follow_link_paused": "This person isn't accepting new anonymous messages right now — try again later.",
        "follow_link_started": (
            "You're messaging someone anonymously — they'll see your message but not who you are\n"
            "\n"
            "Just type your first message below. After that, reply to the message you're "
            "answering — swipe it, or press and hold it and choose Reply — so your words always "
            "land in the right conversation.\n"
            "\n"
            "Tapping this link again later starts a brand-new conversation, separate from this "
            "one — and this one keeps working: reply to any message in it whenever you like."
        ),
        "link_status_paused": "paused — not accepting new conversations",
        "link_status_active": "accepting messages",
        "link_message": (
            "Your anonymous-inbox link ({status}):\n"
            "{url}\n\n"
            "Copy it and post it anywhere — anyone who opens it can message "
            "you here without you seeing who they are."
        ),
        "link_button_pause": "⏸️ Pause",
        "link_button_resume": "▶️ Resume",
        "link_button_newlink": "🔄 New link",
        "anonlink_no_link_yet": "No link yet — send /link first.",
        "anonlink_paused_answer": "Paused.",
        "anonlink_resumed_answer": "Resumed.",
        "anonlink_newlink_answer": "New link generated — the old one no longer starts new conversations.",
        "newlink_message": "New link (the old one no longer starts new conversations):\n{url}",
        "pause_message": (
            "Paused — your link won't start new conversations until /resume. Conversations "
            "already in progress still work normally."
        ),
        "resume_message": "Resumed — your link is accepting new conversations again.",
        "stats_message": "{followers} distinct guest(s) have messaged you, across {conversations} conversation(s) total.",

        "convs_title": "\U0001f4e5 Your inbox",
        "convs_title_archived": "\U0001f5c4 Archived conversations",
        "convs_summary": "{open} open \u00b7 {archived} archived",
        "convs_summary_blocked": "{open} open \u00b7 {archived} archived \u00b7 {blocked} blocked (see /blocked)",
        "convs_empty_open": (
            "Nothing open right now. /link is your inbox link \u2014 anyone who taps it can write to you."
        ),
        "convs_empty_archived": (
            "Nothing archived yet. Archive a conversation from its own card once you are done with it; "
            "it comes back on its own if anything else arrives in it."
        ),
        "convs_row_button": "#{conv_number} \u00b7 {when}",
        "convs_show_archived": "\U0001f5c4 Archived",
        "convs_show_open": "\U0001f4e5 Open",
        "convs_page": "{page}/{pages}",
        "convs_prev": "\u2039",
        "convs_next": "\u203a",
        "conv_card": "Conversation #{conv_number}\n\nOpened {started}\nLast message {when}",
        "conv_card_archived": "Archived {archived}",
        "conv_back_button": "\u2039 Back",
        "conv_jump_button": "\u2934\ufe0f Go to the start",
        "conv_archive_button": "\U0001f5c4 Archive",
        "conv_unarchive_button": "\u21a9\ufe0f Unarchive",
        "conv_archived_answer": "Archived \u2014 out of your open list until something arrives in it.",
        "conv_unarchived_answer": "Back in your open list.",
        "conv_gone": "That conversation is no longer on record.",
        "jump_bookmark": (
            "\U0001f4cd Conversation #{conv_number} starts here. Reply to this message to write in it."
        ),
        "jump_no_anchor": (
            "I can't point at the start of conversation #{conv_number} any more \u2014 a message stops "
            "being kept as a reply anchor after {days} days of silence in its conversation."
        ),

        "which_needs_reply": (
            "Reply to a message with /which and I'll say which conversation it belongs to. Swipe the "
            "message, or press and hold it and choose Reply."
        ),
        "which_unknown": (
            "That message isn't in any conversation open here. It may be one of your own, "
            "or one whose conversation has been archived."
        ),
        "which_owner": "That message is in conversation #{conv_number}.",
        "which_follower": "That message is in the conversation that starts here.",
        "which_follower_no_anchor": "That message is in a conversation you opened {started}.",

        "rel_now": "just now",
        "rel_minutes": "{n} min ago",
        "rel_hours": "{n} h ago",
        "rel_days": "{n} d ago",
        "blocked_none": "You haven't blocked anyone.",
        "blocked_header": "Blocked guests:",
        "blocked_guest_line": "  \U0001f6ab Guest from conversation(s) {conversations}",
        "blocked_guest_line_unknown": "  \U0001f6ab Guest (no conversation on record)",
        "blocked_unblock_button": "↩️ Unblock (conv. {conversations})",
        "blocked_unblock_button_unknown": "↩️ Unblock",
        "reply_button": "↩️ How to reply",
        "block_button": "\U0001f6ab Block",
        "not_your_conversation": "Not your conversation.",
        "blocked_answer": "Blocked.",
        "unblock_button_labelled": "↩️ Unblock conversation #{conv_number}",
        "too_fast": "You're sending those faster than I can pass them on — give it about {seconds} second(s) and try again.",
        "edit_not_relayed": (
            "I'd already passed that message on, so the edit didn't reach them — they "
            "still have what you first wrote. Reply to it again with the correction."
        ),
        "unblocked_answer": "Unblocked.",
        "delivery_blocked": "Your message couldn't be delivered.",
        "inbox_gone": "This inbox no longer exists.",
        "incoming_header": "\U0001f4e9 Conversation #{conv_number}",
        "incoming_header_follower": "\U0001f4ec New message",
        "delivery_forbidden": (
            "Couldn't deliver that — this bot can't message someone who hasn't started "
            "it themselves, and this person hasn't yet. Your message was not sent."
        ),
        "delivery_failed": "Couldn't deliver that message: {error}",
        "sent_confirmation": "Sent ✅",
        "reply_no_match": "Your message was not sent — I couldn't match that reply to a conversation.",
        "must_reply": (
            "Your message was not sent — it didn't say which conversation it answers.\n"
            "\n"
            "Reply to the message quoted above and it goes there. Swipe it, or press and hold it "
            "and choose Reply."
        ),
        "reply_button_hint": (
            "Swipe this message to the right to reply to it — or press and hold it, then choose "
            "Reply. That is how I know which conversation your answer belongs to."
        ),
        "must_reply_opening": (
            "Your message was not sent yet — the conversation you opened hasn't started.\n"
            "\n"
            "Reply to the message quoted above and that becomes your first message to them. Swipe "
            "it, or press and hold it and choose Reply."
        ),
        "must_reply_ambiguous": (
            "Your message was not sent — it didn't say which conversation it answers, and more "
            "than one is open in this chat, so I would have to guess who to send it to.\n"
            "\n"
            "Reply to the message you're answering: swipe it, or press and hold it and choose "
            "Reply."
        ),
        "restarting_send_again": (
            "🔄 I'm being updated right now — give me a few seconds and send that again."
        ),
        "update_soon_try_later": "🔧 I'm being updated in a moment, so I can't start anything new right now — please try again in about {minutes} minute(s). I'll message you when I'm back.",
        "update_soon_try_later_soon": "🔧 I'm being updated right now, so I can't start anything new — please try again shortly. I'll message you when I'm back.",
        "update_will_reset": "🔧 Heads up: I'm about to be updated, and what you have going right now will be reset. You'll be able to start it again in a few minutes.",
        "update_done_try_now": '✅ The update is done — go ahead and try again now.',
        "reply_forbidden": "Couldn't deliver your reply — they may have blocked or left the bot.",
        "reply_failed": "Couldn't deliver your reply: {error}",
        "delivered_confirmation": "Delivered ↩️",
        "reply_stale": (
            "That message isn't in any conversation open here, so your message was not sent.\n"
            "\n"
            "Reply to one of the messages I delivered here instead — swipe it, or press and "
            "hold it and choose Reply."
        ),
        "generic_nudge": "Not sure what this is for — if someone sent you a link, tap that first. Want your own inbox? Send /link.",
        "export_button_cancel": '✖️ Cancel',
        "export_cancelled": 'Export cancelled — nothing was read, copied or kept.',
        "export_failed": "⚠️ The document couldn't be built, so nothing was sent. Nothing was kept either. Send /export to try again.",
        "export_done": '✅ Document sent. Everything the bot read while writing it has been deleted from this chat, and nothing was kept.',
        "export_nothing_to_export": "There is nothing to export yet. Once you have written to somebody through an inbox link, or somebody has written to you, /export can hand that conversation back.",
        "export_pick_intro": "📄 Export a conversation\n\nWhich one? ({count} on record.)",
        "export_pick_numbered": "#{number} · {count} msg",
        "export_pick_yours": "Your conversation · {count} msg",
        "export_pick_all": "📚 All of them · {count} msg",
        "export_gone": "That conversation is no longer on record. Send /export again for the current list.",
        "export_what_numbered": "Conversation #{number}",
        "export_what_yours": "Your conversation",
        "export_what_all": "{conversations} conversations",
        "export_modes": (
            "📄 {what} — {count} messages\n\n"
            "Two ways, and the only difference is whether the bot reads what was said.\n\n"
            "📋 <b>Copy them back here.</b> The bot gives Telegram a list of message "
            "numbers and Telegram makes the copies. It never sees what is in them. "
            "Everything arrives exactly as it was — stickers, photos, voice messages, "
            "files — and you can then select the lot and forward it anywhere. The copies "
            "stay in this chat until you delete them.\n\n"
            "📝 <b>Write them into a document.</b> To put words on a page the bot has to "
            "read them, so it forwards each message to itself, reads it, and deletes what "
            "it read straight away — you will see messages appear and vanish while it "
            "works. The document names media rather than including it ([Photo], [Voice "
            "message]) and nothing is downloaded. It is built in memory, sent to you, and "
            "not kept.\n\n"
            "Either way: no name, no username and no id is in it. The inbox holder is "
            "\"Owner\" and the person writing to them is \"Anon\". The other side is "
            "not told."
        ),
        "export_left_out": "{count} older messages are not included: the bot has no record of which side they were on, or there are more than one export holds.",
        "export_button_copy": "📋 Copy them back here",
        "export_button_doc": "📝 Write a document",
        "export_copy_progress": "📋 Copying… {done} of {total}.",
        "export_copy_header": "— {what}, {count} messages —",
        "export_copy_done": "— end of the copy —\n\n{count} messages were copied back. The bot did not read any of them. Select them and forward them wherever you want them, or delete them when you are done.",
        "export_copy_missing": "{count} could not be copied — most likely you deleted them from this chat.",
        "export_copy_finished": "✅ {count} messages copied back, below. Nothing was read and nothing was kept.",
        "export_doc_progress": "📝 Reading… {done} of {total}. Each one is deleted again straight after.",
        "export_doc_owner": "Owner",
        "export_doc_anon": "Anon",
        "export_doc_unreadable": "{count} could not be read and are missing.",
        "export_caption": '📄 {messages} message(s) in {conversations} conversation(s).',
        "export_doc_title": 'AnonBot transcript',
        "export_doc_generated": 'Made {date}. Times are UTC.',
        "export_doc_started": 'started {date} · {count} message(s)',
        "export_doc_footer": 'Made by reading each message once and deleting the copy straight after. The bot keeps nothing anybody writes, and did not keep this document. No name, username or id appears in it: the inbox holder is Owner and the person writing to them is Anon.',
        "export_kind_photo": 'Photo',
        "export_kind_video": 'Video',
        "export_kind_animation": 'GIF',
        "export_kind_video_note": 'Video message',
        "export_kind_voice": 'Voice message',
        "export_kind_audio": 'Audio',
        "export_kind_sticker": 'Sticker',
        "export_kind_document": 'File',
        "export_kind_location": 'Location',
        "export_kind_contact": 'Contact',
        "export_kind_poll": 'Poll',
        "export_kind_dice": 'Dice',
        "export_kind_other": 'Message',
        "archive_needs_reply": (
            "Reply to a message from the conversation you want to archive and send /archive "
            "again — swipe the message, or press and hold it and choose Reply. Or open "
            "/conversations and pick one from the list."
        ),
        "archive_not_owner": (
            "Archiving is for the person whose inbox this is — it files a conversation out of "
            "their list, and you don't have one."
        ),
        "archive_already": "Conversation #{conv_number} is already archived.",
        "archive_confirm": (
            "Archive conversation #{conv_number}?\n"
            "\n"
            "It moves out of your open list. Nothing is deleted and the other person is never "
            "told, and if they write again the conversation comes straight back."
        ),
        "archive_button_yes": "🗂 Archive #{conv_number}",
        "archive_button_no": "Keep it open",
        "archive_done": "🗂 Conversation #{conv_number} archived. /conversations to see it.",
        "archive_kept": "Left open.",
        "unknown_command": "I don't recognize that command. Send /help to see what I can do.",
    },
    "uz": {
        "flood_wait": 'Juda tez yuboryapsiz — {seconds} soniyacha kutib, keyin davom eting.',
        "sibling_blurb": 'Oilamizdagi boshqa botlar pastda 👇',
        "donation_nudge": "💙 Bot sizga foydali bo'lgan bo'lsa: server va API xarajatlarini botni yuritayotgan odam o'z hisobidan qoplaydi. /donate orqali bunga hissa qo'shishingiz mumkin — bu mutlaqo ixtiyoriy.",
        "donate_unknown_currency": '"{currency}" degan valyuta yo\'q — xtr yoki usd deb yozing.',
        "donate_currency_not_configured": "Bu botda hozircha {currency} bilan xayriya qilib bo'lmaydi — Stars'dan foydalaning.",
        "donate_invalid_amount": "Miqdor noto'g'ri — masalan, /donate 500 yoki /donate 5 usd deb yozing.",
        "donate_prompt": "Hissangiz uchun rahmat — u to'g'ridan-to'g'ri botning server va API xarajatlariga ketadi. Quyidagi miqdorlardan birini tanlang yoki o'zingiz yozish uchun «Boshqa»ni bosing (/donate <son> [usd] deb ham yuborishingiz mumkin).",
        "donate_custom_button": "✏️ Boshqa {symbol}",
        "donate_too_many_stars": "Bu juda ko'p! Bir martalik xayriya {max} ⭐ dan oshmasin.",
        "donate_out_of_range": "{currency} bilan xayriya {lo} dan {hi} {symbol} gacha bo'lishi kerak.",
        "donate_invoice_title": 'Server xarajatlariga hissa',
        "donate_invoice_description": "Botlar xarajatlariga ketadi va ConvertBot'dagi konvertatsiyalar uchun balansingizga {credited} ⚡ kredit qo'shadi.",
        "donate_invoice_label": 'Xayriya',
        "donate_invoice_description_fiat": 'Server xarajatlari uchun bir martalik ixtiyoriy xayriya. Rahmat!',
        "donate_prompt_credit": "To'lagan Stars'ingiz ConvertBot'da konvertatsiyalarga sarflanadigan ⚡ kreditga aylanadi. Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×): {rate} ⚡ oddiy kredit, qolgani esa to'lovdan {days} kun o'tgach muddati tugaydigan bonus. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_prompt_credit_base": "To'lagan har bir ⭐ ConvertBot'da konvertatsiyalarga sarflanadigan {rate} ⚡ kreditga aylanadi. ⚡ ni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.",
        "donate_invoice_error": "⚠️ Telegram to'lov hisobini yaratmadi: {error}",
        "stars_unit": "Stars (yulduzcha)",
        "donate_custom_ask": 'Qancha {unit} xayriya qilmoqchisiz? Faqat sonni yozib yuboring.',
        "donate_invalid_amount_retry": "Miqdor noto'g'ri — qaytadan urinish uchun /donate yuboring.",
        "donate_thanks": '🙏 {amount} ⭐ uchun katta rahmat!',
        "topup_thanks": "🙏 {stars} ⭐ xayriyangiz uchun rahmat — bu botlarning ishlashiga yordam beradi.\n\nMinnatdorchilik sifatida {convert_bot} botida fayllarni o'girish uchun {total} ⚡ kredit oldingiz. U yerdagi balansingiz: {balance} ⚡.",
        "topup_thanks_bonus": 'Shundan {bonus} ⚡ — bonus kredit, uning muddati {date} kuni tugaydi.',
        "credit_cannot_be_withdrawn": "⚡ — ConvertBot'dagi konvertatsiyalar uchun kredit: uni yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. To'lovda muammo bo'lsa: /paysupport",
        "paysupport_text": "💳 To'lov bo'yicha yordam\n\nTo'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI.\n\nTo'lovda xatolik bo'lgan bo'lsa — pul yechilgan-u, kredit tushmagan bo'lsa yoki ikki marta yechilgan bo'lsa — {contact} manziliga to'lov sanasi, miqdori va Telegram ID raqamingizni ({user_id}) yozib yuboring. Tekshirilib, kredit bilan to'g'rilab beriladi.\n\n/balance har bir to'lovni va u qancha kredit qo'shganini ko'rsatadi.",
        "report_button": "🐞 Ma'lumotlarimni qo'shish",
        "problem_logged_note": "Bu muammo bot egasi uchun allaqachon yozib olindi — kodi, vaqti va bot versiyasi. Siz haqingizda hech narsa yo'q.",
        "report_disclaimer": "📨 Bu muammoga o'zingiz haqingizdagi ma'lumotni ham qo'shasizmi?\n\nSizsiz yozib olingani: bot nomi, {code} xato kodi, {incident} hodisa raqami, qachon yuz bergani va bot versiyasi.\n\n\"Yuborish\" tugmasi to'rt narsani qo'shadi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. Yozganingiz ham, yuborgan faylingiz ham emas.\n\nShunda sizning holatingizni loglardan topib bo'ladi — kam uchraydigan muammoni odatda shu tuzatib beradi. To'liq o'zingiz hal qilasiz.",
        "report_send": "📨 Ma'lumotlarimni yuborish",
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — ma'lumotlaringiz {incident} hodisasiga biriktirildi, endi uni topish oson.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi. Muammoning o'zi yozib olingan holicha qoladi.",
        "report_failed": "⚠️ Hozir xabarni yuborib bo'lmadi. Keyinroq qayta urinib ko'ring.",
        "report_invalid": 'Bu tugma endi ishlamaydi.',
        "crash_notice": "⚠️ Buni bajarishda bot tomonida xatolik yuz berdi, shuning uchun amal bajarilmadi. Birozdan keyin qayta urinib ko'ring.",
        "sandbox_notice": '🧪 Test rejimi — haqiqiy Stars yechilmadi.',
        "balance_header": "⚡ Balansingiz: {balance}",
        "balance_totals": "Jami {paid} ⭐ to'landi · {credited} ⚡ qo'shildi · {spent} ⚡ sarflandi",
        "balance_rate": 'Keyingi {left} ⭐ ning har biri {each} ⚡ beradi ({mult}×).',
        "balance_rate_base": '1 ⭐ = {rate} ⚡.',
        "balance_bonus_line": 'Shundan {bonus} ⚡ — bonus kredit; {soon} ⚡ ning muddati {date} kuni tugaydi.',
        "balance_recent": 'Oxirgi amallar:',
        "balance_empty_hint": '/donate orqali istalgan paytda kredit olishingiz mumkin.',
        "bot_short_description": (
            "Sizga anonim yozish imkonini beruvchi doimiy havola."
        ),
        "bot_description": "Havola oling va uni istalgan joyga joylang. Uni ochgan har kim sizga kimligini oshkor qilmay yoza oladi, siz esa javob berasiz — bir vaqtda bir nechta alohida suhbat bo'lib.\n\nYozuvchilar sizga noma'lum, lekin botga emas: javob to'g'ri suhbatga borishi uchun bot qaysi ikki akkaunt yozishayotganini saqlaydi, yozilgan xabarlarni esa hech qachon saqlamaydi. Batafsil: /privacy\n\nIngliz, o'zbek va rus tillarida.",

        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• xabarlar havolangiz, agar yaratgan bo'lsangiz\n• kim kim bilan yozishayotgani: suhbat ikki foydalanuvchi ID raqami va tartib raqami sifatida saqlanadi — javob to'g'ri suhbatga yetib borishi shunga bog'liq\n• qaysi xabar qaysi suhbatga tegishli ekani (xabar raqami bo'yicha) va u qachon yetkazilgani\n• kimlarni bloklaganingiz\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n\nYozilgan xabarlarning o'zi saqlanmaydi. Xabarlar to'g'ridan-to'g'ri yetkaziladi va bu yerda saqlanmaydi: ular ikkala tomonning Telegram chatida turadi va har kim o'z nusxasini o'chira oladi. /export bilan tayyorlangan hujjat faqat xotirada yig'iladi, sizga yuboriladi va keyin yo'q qilinadi; o'qilgan narsalarning hech biri yozib olinmaydi.\n\nAnonimlik — siz yozayotgan odamga nisbatan: unga ismingiz, foydalanuvchi nomingiz yoki ID raqamingiz hech qachon ko'rsatilmaydi. Botning o'zidan esa yashirinib bo'lmaydi: yuqoridagi bog'lanishsiz javob umuman yetib bormasdi.",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nXato ostidagi \"Ma'lumotlarimni qo'shish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• boshqa hech kim — xabarlar faqat Telegram orqali o'tadi, tashqi xizmatlarga murojaat qilinmaydi",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
        "privacy_your_choices": "Nima qilishingiz mumkin:\n/deletemydata — bot siz haqingizda saqlagan ma'lumotlarni o'chirish\n/terms — botdan foydalanish shartlari\n\nBotni Telegramda bloklasangiz, u sizga yozmay qo'yadi, lekin hech narsa o'chmaydi. Ikkalasini ham xohlasangiz, avval /deletemydata yuboring.",
        "terms_heading": "📜 Shartlar",
        "terms_use": "Botdan maqsadiga ko'ra, qonun va Telegram qoidalari doirasida foydalaning. Uni boshqalarni bezovta qilish uchun ishlatmang va belgilangan cheklovlardan oshirib yuklamang — aks holda akkaunt bloklanadi.",
        "terms_specific": "Xabarlar haqida: ismingiz yashirinligi hamma narsaga ruxsat degani emas. Tahdid, ta'qib va qonunga zid har qanday xabar anonim yozilgan bo'lsa ham shundayligicha qoladi, havola egasi esa yuboruvchini butunlay bloklay oladi. Xabarlar qutisini ochgan odam o'zi nimaga taklif qilgani uchun javob beradi.",
        "terms_money": "Pul haqida: /donate — ixtiyoriy, mablag' botlar xarajatlariga ketadi. Stars'dagi to'lov ConvertBot'da konvertatsiyalar uchun ⚡ kredit ham beradi: har ⭐ uchun 2 ⚡, umumiy hisobda birinchi 500 ta Stars uchun esa 6 ⚡ dan, keyingi 500 tasi uchun 4 ⚡ dan. 2 ⚡ dan ortig'i bonus kredit bo'lib, to'lovdan 90 kun o'tgach muddati tugaydi. To'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Har bir to'lovni Telegram o'tkazadi, bot karta raqamingizni ko'rmaydi. To'lovda muammo bo'lsa: /paysupport.",
        "terms_no_warranty": "Kafolat yo'q: botni bir kishi yuritadi va u oldindan ogohlantirmasdan sekinlashishi, xato qilishi yoki butunlay to'xtab qolishi mumkin. Siz uchun muhim narsalarning nusxasini o'zingizda saqlang.",
        "policy_full_text": "To'liq matn: {url}",
        "policy_contact": "Savol, shikoyat yoki ma'lumot so'rovi uchun: {contact}",
        "delete_data_confirm": "⚠️ Bot siz haqingizda saqlagan ma'lumotlar o'chiriladi. Buni ortga qaytarib bo'lmaydi.",
        "delete_data_consequences": "Havolangiz butunlay ishlamay qoladi — qayerga joylangan bo'lsa ham. Ochiq suhbatlarga endi hech bir tomon javob yoza olmaydi, bloklanganlar ro'yxatingiz ham o'chiriladi.\n\nYuborilgan xabarlarga hech narsa qilmaydi: ular bu yerda saqlanmagan, Telegram chatlarida turadi va har kim o'z nusxasini o'zi o'chiradi.\n\nXayriya yozuvlari foydalanuvchi nomingizsiz saqlanib qoladi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi. ⚡ balansingiz ham saqlanadi — qaytib kelsangiz, u o'z joyida bo'ladi.",
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
        "cancel_button_donation": "💸 Xayriya miqdori",
        "cancel_item_donation": 'kiritilishi kutilayotgan xayriya miqdori',
        "cancel_item_stale_prompt": "javobsiz qolgan eski so'rov",
        "cancel_item_anon_session": "ochiq turgan anonim suhbat — yangisini boshlash uchun havolani qayta bosing",
        "cancel_button_anon_session": "💬 Siz turgan anonim suhbat",
        "start_greeting": "Salom! Bu bot anonim savol-javob qutilarini boshqaradi.\n\n",
        "help_text": "Bu botdan ikki xil foydalanish mumkin:\n\nO'z qutingizni oching — /link sizga doimiy havola beradi. Uni istalgan ochiq joyga joylang (bio, kanal, story — qayerda bo'lsa ham). Havolani ochgan har kim sizga shu chatning o'zida anonim xabar yubora oladi — kimligi sizga ko'rinmaydi.\nJavob berish uchun xabarni o'ngga suring yoki uni bosib turib «Javob berish»ni tanlang. Shunda javobingiz qaysi suhbatga tegishli ekanini bilaman, shuning uchun bu shart: havola ochiq joyda turgani uchun bir vaqtda bir nechta odam sizga yozayotgan bo'lishi mumkin, qaysi suhbatga javob ekani ko'rsatilmagan xabar esa boshqa odamga borib qolishi mumkin. Javobingiz ularga ham haqiqiy javob sifatida ko'rinadi.\n\nSizga boshqa birovning havolasini yuborishdimi? Uni bosing va yozing — birinchi xabaringiz kimligingiz yashirilgan holda darhol yetib boradi. Undan keyin xuddi qarshi tomon kabi, javob berayotgan xabaringizga javob tarzida yozing. Keyinroq havolani yana bossangiz, eski suhbat davom etmaydi — yangisi boshlanadi.\n\nBuyruqlar:\n/link - qutingiz havolasini olish\n/conversations - suhbatlaringiz: ochiqlari va arxivdagilari\n/which - istalgan xabarga javob qilib yuboring: u qaysi suhbatdan ekanini aytaman\n/newlink, /pause, /resume - bular /link ekranida tugma sifatida ham bor\n/blocked - bloklanganlar ro'yxati\n/stats - qisqa statistika; u /link ekranida ham bor\n/export - suhbatni qaytarib olish: shu yerga nusxalab yoki hujjat qilib\n/donate - server xarajatlariga hissa qo'shish (ixtiyoriy)\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/balance - ⚡ kreditingiz\n/paysupport - to'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n/archive - xabarga javob qilib yuboring: o'sha suhbat arxivga o'tadi (/conversations ichidagi har bir suhbatda ham shu tugma bor)\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — /donate orqali to'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO'LMAYDI.\n\n",
        "follow_link_invalid": "Bu havola yaroqsiz — uni ulashgan kishi qayta tiklagan bo'lishi mumkin. Ulardan yangisini so'rang.",
        "follow_link_own": "Bu o'zingizning havolangiz — o'zingizga yozsangiz, shunchaki eslatma bo'lib qoladi! Havolani boshqalarga ulashing: /link",
        "follow_link_blocked": 'Bu odamga xabar yubora olmaysiz.',
        "follow_link_paused": "Bu odam hozircha yangi anonim xabarlar qabul qilmayapti — keyinroq urinib ko'ring.",
        "follow_link_started": "Siz anonim yozyapsiz — xabaringizni ko'rishadi, lekin kimligingizni bilishmaydi.\n\nBirinchi xabaringizni pastga yozing. Keyingi xabarlarda esa javob berayotgan xabarni belgilang — uni o'ngga suring yoki bosib turib «Javob berish»ni tanlang — shunda gapingiz doim to'g'ri suhbatga tushadi.\n\nKeyinroq bu havolani yana bossangiz, alohida yangi suhbat boshlanadi, bu suhbat esa ochiqligicha qoladi: undagi istalgan xabarga xohlagan paytda javob berishingiz mumkin.",
        "link_status_paused": "to'xtatilgan — yangi suhbatlar qabul qilinmaydi",
        "link_status_active": 'xabarlar qabul qilinmoqda',
        "link_message": "Anonim qutingiz havolasi ({status}):\n{url}\n\nUni nusxalab, istalgan joyga joylang — havolani ochgan har kim sizga shu yerda kimligini ko'rsatmay xabar yubora oladi.",
        "link_button_pause": "⏸️ To'xtatish",
        "link_button_resume": '▶️ Qayta yoqish',
        "link_button_newlink": "🔄 Yangi havola",
        "anonlink_no_link_yet": "Hali havola yo'q — avval /link yuboring.",
        "anonlink_paused_answer": "To'xtatildi.",
        "anonlink_resumed_answer": 'Qayta yoqildi.',
        "anonlink_newlink_answer": "Yangi havola yaratildi — eski havola endi yangi suhbat boshlamaydi.",
        "newlink_message": "Yangi havola (eskisi endi yangi suhbat boshlamaydi):\n{url}",
        "pause_message": "To'xtatildi — /resume yubormaguningizcha havolangiz orqali yangi suhbat boshlanmaydi. Boshlangan suhbatlar esa odatdagidek davom etadi.",
        "resume_message": 'Qayta yoqildi — havolangiz orqali yana yangi suhbatlar boshlash mumkin.',
        "stats_message": 'Sizga {followers} nafar mehmon yozgan, jami {conversations} ta suhbat.',

        "convs_title": '📥 Qutingiz',
        "convs_title_archived": "\U0001f5c4 Arxivlangan suhbatlar",
        "convs_summary": "{open} ta ochiq \u00b7 {archived} ta arxivda",
        "convs_summary_blocked": "{open} ta ochiq \u00b7 {archived} ta arxivda \u00b7 {blocked} ta bloklangan (/blocked)",
        "convs_empty_open": "Hozircha ochiq suhbat yo'q. Havolangizni /link orqali oling — uni bosgan har kim sizga yoza oladi.",
        "convs_empty_archived": (
            "Arxivda hali hech narsa yo'q. Suhbat tugagach, uni o'z kartasidan arxivga qo'shing; "
            "unga yangi xabar kelsa, o'zi qaytadi."
        ),
        "convs_row_button": "#{conv_number} \u00b7 {when}",
        "convs_show_archived": "\U0001f5c4 Arxiv",
        "convs_show_open": "\U0001f4e5 Ochiq",
        "convs_page": "{page}/{pages}",
        "convs_prev": "\u2039",
        "convs_next": "\u203a",
        "conv_card": "#{conv_number}-suhbat\n\nOchilgan: {started}\nOxirgi xabar: {when}",
        "conv_card_archived": "Arxivlangan: {archived}",
        "conv_back_button": "\u2039 Orqaga",
        "conv_jump_button": "\u2934\ufe0f Boshiga o'tish",
        "conv_archive_button": "\U0001f5c4 Arxivga",
        "conv_unarchive_button": "\u21a9\ufe0f Arxivdan chiqarish",
        "conv_archived_answer": "Arxivga qo'shildi \u2014 yangi xabar kelmaguncha ochiqlar ro'yxatida ko'rinmaydi.",
        "conv_unarchived_answer": "Ochiqlar ro'yxatiga qaytdi.",
        "conv_gone": "Bu suhbat haqida endi ma'lumot yo'q.",
        "jump_bookmark": (
            "\U0001f4cd #{conv_number}-suhbat shu yerdan boshlanadi. Unda yozish uchun shu xabarga javob bering."
        ),
        "jump_no_anchor": "#{conv_number}-suhbatning boshini endi ko'rsata olmayman — {days} kun yozishilmagan suhbatlarning xabarlariga javob berish imkoni saqlanmaydi.",

        "which_needs_reply": (
            "Xabarga javob tarzida /which yuboring \u2014 u qaysi suhbatga tegishli ekanini aytaman. "
            "Xabarni suring yoki bosib turib \u00abJavob berish\u00bb ni tanlang."
        ),
        "which_unknown": (
            "Bu xabar bu yerda ochiq suhbatlarning hech biriga tegishli emas. U sizniki "
            "bo'lishi yoki suhbati arxivlangan bo'lishi mumkin."
        ),
        "which_owner": "Bu xabar #{conv_number}-suhbatga tegishli.",
        "which_follower": "Bu xabar shu yerdan boshlanadigan suhbatga tegishli.",
        "which_follower_no_anchor": "Bu xabar siz {started} ochgan suhbatga tegishli.",

        "rel_now": "hozir",
        "rel_minutes": "{n} daq. oldin",
        "rel_hours": "{n} soat oldin",
        "rel_days": "{n} kun oldin",
        "blocked_none": "Siz hech kimni bloklamagansiz.",
        "blocked_header": "Bloklangan mehmonlar:",
        "blocked_guest_line": "  \U0001f6ab {conversations}-suhbatdagi mehmon",
        "blocked_guest_line_unknown": "  \U0001f6ab Mehmon (suhbat qayd etilmagan)",
        "blocked_unblock_button": "↩️ Blokdan chiqarish ({conversations}-suhbat)",
        "blocked_unblock_button_unknown": "↩️ Blokdan chiqarish",
        "reply_button": '↩️ Qanday javob beraman?',
        "block_button": "\U0001f6ab Bloklash",
        "not_your_conversation": "Bu sizning suhbatingiz emas.",
        "blocked_answer": "Bloklandi.",
        "unblock_button_labelled": "↩️ #{conv_number}-suhbatni blokdan chiqarish",
        "too_fast": "Juda tez yuboryapsiz — {seconds} soniyacha kutib, qayta urinib ko'ring.",
        "edit_not_relayed": "Bu xabar allaqachon yetkazilgan, shuning uchun tahrir qarshi tomonga bormadi — ularda eski matn turibdi. Tuzatilgan matnni o'sha xabarga javob qilib qaytadan yuboring.",
        "unblocked_answer": "Blokdan chiqarildi.",
        "delivery_blocked": "Xabaringiz yetkazilmadi.",
        "inbox_gone": "Bu quti endi mavjud emas.",
        "incoming_header": "\U0001f4e9 #{conv_number}-suhbat",
        "incoming_header_follower": "\U0001f4ec Yangi xabar",
        "delivery_forbidden": "Xabaringiz yuborilmadi — bot faqat o'zini ishga tushirgan odamlarga yoza oladi, bu odam esa botni hali ishga tushirmagan.",
        "delivery_failed": "Bu xabarni yetkazib bo'lmadi: {error}",
        "sent_confirmation": "Yuborildi ✅",
        "reply_no_match": "Xabaringiz yuborilmadi — bu javobni biror suhbatga moslab bo'lmadi.",
        "must_reply": "Xabaringiz yuborilmadi — unda qaysi suhbatga javob ekani ko'rsatilmagan.\n\nYuqoridagi xabarga javob tarzida yozing, shunda u o'sha suhbatga boradi: xabarni o'ngga suring yoki bosib turib «Javob berish»ni tanlang.",
        "reply_button_hint": "Javob berish uchun xabarni o'ngga suring yoki bosib turib «Javob berish»ni tanlang. Shunda javobingiz qaysi suhbatga tegishli ekanini bilaman.",
        "must_reply_opening": "Xabaringiz hali yuborilmadi — siz ochgan suhbat hali boshlanmagan.\n\nYuqoridagi xabarga javob tarzida yozing — bu ularga birinchi xabaringiz bo'ladi. Xabarni o'ngga suring yoki bosib turib «Javob berish»ni tanlang.",
        "must_reply_ambiguous": "Xabaringiz yuborilmadi — unda qaysi suhbatga javob ekani ko'rsatilmagan, bu chatda esa bir nechta suhbat ochiq, kimga yuborishni taxmin qilolmayman.\n\nJavob berayotgan xabarni belgilang: uni o'ngga suring yoki bosib turib «Javob berish»ni tanlang.",
        "restarting_send_again": '🔄 Bot hozir yangilanmoqda — bir necha soniyadan keyin qaytadan yuboring.',
        "update_soon_try_later": "🔧 Bot tez orada yangilanadi, shuning uchun yangi ishni boshlab bo'lmaydi — taxminan {minutes} daqiqadan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_soon_try_later_soon": "🔧 Bot hozir yangilanmoqda, shuning uchun yangi ishni boshlab bo'lmaydi — birozdan keyin qayta urinib ko'ring. Ishga tushgach, o'zim xabar beraman.",
        "update_will_reset": "🔧 Diqqat: bot yangilanadi va hozir bajarilayotgan ishingiz to'xtab qoladi. Bir necha daqiqadan keyin qaytadan boshlashingiz mumkin.",
        "update_done_try_now": "✅ Yangilanish tugadi — endi qaytadan urinib ko'rishingiz mumkin.",
        "reply_forbidden": "Javobingizni yetkazib bo'lmadi — ular sizni bloklagan yoki botni tark etgan bo'lishi mumkin.",
        "reply_failed": "Javobingizni yetkazib bo'lmadi: {error}",
        "delivered_confirmation": "Yetkazildi ↩️",
        "reply_stale": "Xabaringiz yuborilmadi — javob bergan xabaringiz hech bir ochiq suhbatga tegishli emas. Men shu yerga yetkazgan xabarlardan biriga javob tarzida yozing: uni o'ngga suring yoki bosib turib «Javob berish»ni tanlang.",
        "generic_nudge": "Bu nima uchunligini tushunmadim — agar sizga kimdir havola yuborgan bo'lsa, avval o'shani bosing. O'z qutingiz kerakmi? /link yuboring.",
        "export_button_cancel": '✖️ Bekor qilish',
        "export_cancelled": "Eksport bekor qilindi — hech narsa o'qilmadi, nusxalanmadi va saqlanmadi.",
        "export_failed": "⚠️ Hujjatni tayyorlab bo'lmadi, shuning uchun hech narsa yuborilmadi. Hech narsa saqlanmadi ham. Qayta urinish uchun /export yuboring.",
        "export_done": "✅ Hujjat yuborildi. Bot uni yozayotganda o'qigan hamma narsa shu chatdan o'chirildi va hech narsa saqlanmadi.",
        "export_nothing_to_export": "Hozircha eksport qiladigan narsa yo'q. Havola orqali kimgadir yozganingizdan yoki kimdir sizga yozganidan keyin /export o'sha suhbatni qaytarib bera oladi.",
        "export_pick_intro": "📄 Suhbatni eksport qilish\n\nQaysi biri? (Yozuvda {count} ta bor.)",
        "export_pick_numbered": "#{number} · {count} ta",
        "export_pick_yours": "Sizning suhbatingiz · {count} ta",
        "export_pick_all": "📚 Hammasi · {count} ta",
        "export_gone": "Bu suhbat endi yozuvda yo'q. Yangi ro'yxat uchun /export yuboring.",
        "export_what_numbered": "#{number}-suhbat",
        "export_what_yours": "Sizning suhbatingiz",
        "export_what_all": "{conversations} ta suhbat",
        "export_modes": (
            "📄 {what} — {count} ta xabar\n\n"
            "Ikki yo'l bor, farqi bitta: bot yozilganlarni o'qiydimi yoki yo'qmi.\n\n"
            "📋 <b>Shu yerga nusxalab beraman.</b> Bot Telegramga xabar raqamlarini "
            "beradi, nusxalarni Telegram o'zi qiladi. Bot ularning ichida nima borligini "
            "ko'rmaydi. Hammasi asli qanday bo'lsa, shundayligicha keladi — stikerlar, "
            "rasmlar, ovozli xabarlar, fayllar — keyin hammasini belgilab, xohlagan "
            "joyingizga yuborsangiz bo'ladi. Nusxalar o'zingiz o'chirmaguningizcha shu "
            "chatda qoladi.\n\n"
            "📝 <b>Hujjat qilib yozib beraman.</b> Sahifaga so'zlarni yozish uchun bot "
            "ularni o'qishi kerak: har bir xabarni o'ziga forward qiladi, o'qiydi va "
            "o'qiganini shu zahoti o'chiradi — ishlayotganida xabarlar paydo bo'lib, "
            "yo'qolib turganini ko'rasiz. Hujjatda media o'zi emas, nomi bo'ladi "
            "([Rasm], [Ovozli xabar]) va hech narsa yuklab olinmaydi. Hujjat faqat "
            "xotirada tayyorlanadi, sizga yuboriladi va saqlanmaydi.\n\n"
            "Ikkalasida ham: na ism, na foydalanuvchi nomi, na ID bo'ladi. Havola egasi "
            "— \"Owner\", unga yozayotgan odam — \"Anon\". Ikkinchi tomonga hech narsa "
            "aytilmaydi."
        ),
        "export_left_out": "{count} ta eski xabar kirmadi: bot ularning qaysi tomondan ekanini yozib olmagan, yoki bitta eksportga sig'adiganidan ko'p.",
        "export_button_copy": "📋 Shu yerga nusxalab ber",
        "export_button_doc": "📝 Hujjat qilib yoz",
        "export_copy_progress": "📋 Nusxalanmoqda… {total} tadan {done} tasi.",
        "export_copy_header": "— {what}, {count} ta xabar —",
        "export_copy_done": "— nusxa tugadi —\n\n{count} ta xabar qaytarib nusxalandi. Bot ulardan birortasini ham o'qimadi. Belgilab, xohlagan joyingizga yuboring yoki kerak bo'lmasa o'chirib tashlang.",
        "export_copy_missing": "{count} tasini nusxalab bo'lmadi — ehtimol ularni shu chatdan o'chirib yuborgansiz.",
        "export_copy_finished": "✅ {count} ta xabar quyida nusxalandi. Hech narsa o'qilmadi va saqlanmadi.",
        "export_doc_progress": "📝 O'qilmoqda… {total} tadan {done} tasi. Har biri o'qilgach darhol o'chiriladi.",
        "export_doc_owner": "Owner",
        "export_doc_anon": "Anon",
        "export_doc_unreadable": "{count} tasini o'qib bo'lmadi, ular hujjatga kirmadi.",
        "export_caption": '📄 {conversations} ta suhbatda {messages} ta xabar.',
        "export_doc_title": 'AnonBot suhbatlari',
        "export_doc_generated": "Tayyorlangan: {date}. Vaqt UTC bo'yicha.",
        "export_doc_started": 'boshlangan: {date} · {count} ta xabar',
        "export_doc_footer": "Har bir xabar bir marta o'qilib, nusxasi shu zahoti o'chirildi. Bot hech kim yozgan narsani saqlamaydi va bu hujjatni ham saqlamadi. Bu yerda na ism, na foydalanuvchi nomi, na ID bor: havola egasi — Owner, unga yozayotgan odam — Anon.",
        "export_kind_photo": 'Rasm',
        "export_kind_video": 'Video',
        "export_kind_animation": 'GIF',
        "export_kind_video_note": 'Video xabar',
        "export_kind_voice": 'Ovozli xabar',
        "export_kind_audio": 'Audio',
        "export_kind_sticker": 'Stiker',
        "export_kind_document": 'Fayl',
        "export_kind_location": 'Joylashuv',
        "export_kind_contact": 'Kontakt',
        "export_kind_poll": "So'rovnoma",
        "export_kind_dice": 'Zar',
        "export_kind_other": 'Xabar',
        "archive_needs_reply": (
            "Arxivlamoqchi bo'lgan suhbatdagi xabarga javob tarzida /archive yuboring — "
            "xabarni suring yoki bosib turib «Javob berish» ni tanlang. Yoki /conversations "
            "ni ochib ro'yxatdan tanlang."
        ),
        "archive_not_owner": "Suhbatni faqat quti egasi arxivlay oladi — bu uning ro'yxatidan suhbatni olib qo'yadi, sizda esa bunday ro'yxat yo'q.",
        "archive_already": "#{conv_number}-suhbat allaqachon arxivlangan.",
        "archive_confirm": (
            "#{conv_number}-suhbat arxivlansinmi?\n"
            "\n"
            "U ochiq ro'yxatingizdan chiqadi. Hech narsa o'chirilmaydi, suhbatdoshingizga "
            "aytilmaydi, va u yana yozsa suhbat darhol qaytadi."
        ),
        "archive_button_yes": "🗂 #{conv_number} ni arxivlash",
        "archive_button_no": "Ochiq qolsin",
        "archive_done": "🗂 #{conv_number}-suhbat arxivlandi. Ko'rish uchun /conversations.",
        "archive_kept": "Ochiq qoldirildi.",
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /help yuboring.",
    },
    "ru": {
        "flood_wait": "Ты отправляешь быстрее, чем я успеваю — подожди примерно {seconds} секунд(ы) и продолжай.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотри ниже \U0001f447",
        "donation_nudge": (
            "💙 Если этот бот оказался полезным: расходы на хостинг/API покрывает тот, "
            "кто его запустил, а /donate — это совершенно необязательный способ помочь "
            "ему остаться на плаву. Никакого давления в любом случае!"
        ),
        "donate_unknown_currency": 'Неизвестная валюта "{currency}" — попробуйте xtr или usd.',
        "donate_currency_not_configured": "Пожертвования в {currency} на этом боте пока не настроены — попробуйте Stars.",
        "donate_invalid_amount": "Это некорректная сумма — попробуйте, например, /donate 500 или /donate 5 usd.",
        "donate_prompt": (
            "Спасибо за вклад — эти средства идут прямо на хостинг и API этого "
            "бота. Выберите сумму ниже или нажмите «Другое», чтобы ввести свою "
            "(также можно сразу отправить /donate <число> [usd])."
        ),
        "donate_custom_button": "✏️ Другое {symbol}",
        "donate_too_many_stars": "Это очень много звёзд! Пусть будет меньше {max} ⭐ за одно пожертвование.",
        "donate_out_of_range": "Пожертвования в {currency} должны быть в диапазоне от {lo} до {hi} {symbol}.",
        "donate_invoice_title": "Поддержать хостинг",
        "donate_invoice_description": "Идёт на расходы по работе бота и добавляет {credited} ⚡ на ваш баланс для конвертаций в ConvertBot.",
        "donate_invoice_label": "Вклад в хостинг",
        "donate_invoice_description_fiat": 'Разовое добровольное пожертвование на хостинг. Спасибо!',
        "donate_prompt_credit": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации в ConvertBot. Следующие {left} ⭐ дают по {each} ⚡ ({mult}×): {rate} ⚡ обычного кредита и бонус, который сгорает через {days} дней после оплаты. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_prompt_credit_base": 'Оплаченные Stars превращаются в ⚡ кредит на конвертации в ConvertBot, {rate} ⚡ за ⭐. ⚡ НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "donate_invoice_error": "⚠️ Telegram не смог создать этот счёт: {error}",
        "stars_unit": "Stars (звёзды)",
        "donate_custom_ask": "Сколько {unit} вы хотите пожертвовать? Ответьте числом.",
        "donate_invalid_amount_retry": "Это некорректная сумма — отправьте /donate, чтобы попробовать снова.",
        "donate_thanks": "🙏 Спасибо за {amount} ⭐ — это по-настоящему ценно!",
        "topup_thanks": '🙏 Спасибо за пожертвование в {stars} ⭐ — это помогает ботам работать.\n\nВ благодарность вы получили {total} ⚡ кредита в {convert_bot} — его можно тратить на конвертацию файлов. Ваш баланс там: {balance} ⚡.',
        "topup_thanks_bonus": 'Из них {bonus} ⚡ — бонусный кредит, он сгорит {date}.',
        "credit_cannot_be_withdrawn": '⚡ — это кредит на конвертации в ConvertBot, его НЕЛЬЗЯ вывести или обменять обратно на Stars. Проблема с платежом? /paysupport',
        "paysupport_text": '💳 Помощь с платежом\n\nПлатежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести или обменять обратно на Stars.\n\nЕсли с платежом что-то пошло не так — деньги списали, а кредит не пришёл, или списали дважды, — напишите на {contact}: дату, сумму и ваш Telegram ID, {user_id}. Это проверят и исправят кредитом.\n\n/balance показывает каждый платёж и что он добавил.',
        "report_button": '🐞 Добавить мои данные',
        "problem_logged_note": 'Эта проблема уже записана для владельца бота — код, время и версия. О вас там ничего нет.',
        "report_disclaimer": '📨 Добавить к этой проблеме ваши данные?\n\nУже записано, без вас: название бота, код ошибки {code}, номер случая {incident}, когда это произошло и версия бота.\n\nКнопка «Отправить» добавит четыре вещи: ваш Telegram ID, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Ни того, что вы написали, ни отправленного файла.\n\nТогда ваш случай можно будет найти в логах — обычно именно это и позволяет починить редкую проблему. Решать только вам.',
        "report_send": '📨 Отправить мои данные',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — ваши данные теперь на случае {incident}, так его легко найти.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено. Сама проблема остаётся записанной.',
        "report_failed": '⚠️ Сейчас не удалось отправить сообщение. Попробуйте позже.',
        "report_invalid": 'Эта кнопка больше не работает.',
        "crash_notice": '⚠️ При обработке произошла ошибка на стороне бота, поэтому ничего не сделано. Попробуйте ещё раз чуть позже.',
        "sandbox_notice": "🧪 Тестовый режим — настоящие Stars не списывались.",
        "balance_header": "⚡ Ваш баланс: {balance}",
        "balance_totals": "Всего оплачено {paid} ⭐ · начислено {credited} ⚡ · потрачено {spent} ⚡",
        "balance_rate": 'Следующие {left} ⭐ дают по {each} ⚡ ({mult}×).',
        "balance_rate_base": '1 ⭐ даёт {rate} ⚡.',
        "balance_bonus_line": 'Из них {bonus} ⚡ — бонусный кредит; {soon} ⚡ сгорит {date}.',
        "balance_recent": "Последние операции:",
        "balance_empty_hint": "/donate добавит кредит в любой момент.",
        "bot_short_description": (
            "Постоянная ссылка, по которой тебе пишут анонимно."
        ),
        "bot_description": (
            "Получи ссылку и выложи где угодно. Любой, кто её откроет, напишет тебе, не показав, "
            "кто он, а ты сможешь ответить — настоящей веткой, и таких веток может идти сразу "
            "несколько.\n"
            "\n"
            "Они анонимны для тебя, но не для бота: чтобы ответ попал в нужную ветку, бот хранит, "
            "какие два аккаунта переписываются, и никогда не хранит то, что вы пишете. "
            "Подробности — /privacy.\n"
            "\n"
            "Английский, узбекский и русский."
        ),

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": (
            "• твой числовой id в Telegram и выбранный язык\n"
            "• твою ссылку-инбокс, если ты её сделал\n"
            "• кто с кем говорит: разговор хранится как пара id и номер — именно поэтому ответ "
            "попадает в нужную ветку\n"
            "• какое сообщение к какому разговору относится, по id сообщения, и когда оно было доставлено\n"
            "• кого ты заблокировал\n"
            "• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли "
            "ботом хоть кто-нибудь\n"
            "• запись о пожертвовании: сумму и платёжный id Telegram\n"
            "\n"
            "Чего здесь нет — самих сообщений. Они проходят насквозь и тут не сохраняются: они "
            "лежат в двух чатах Telegram, и каждый может удалить свою копию. Документ, собранный через /export, существует только в памяти: он отправляется вам и удаляется, и ничего из прочитанного не записывается.\n"
            "\n"
            "Анонимность — это анонимность от того, кому ты пишешь. Ему никогда не показывают ни "
            "твоё имя, ни username, ни id. От самого бота это не анонимность: без той самой пары "
            "id ответ просто некуда было бы доставить."
        ),
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nКнопка «Добавить мои данные» под ошибкой предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
        "privacy_seen_by_heading": "Кто ещё это видит:",
        "privacy_seen_by": (
            "• Telegram — он передаёт каждое сообщение в обе стороны и действует по своим "
            "правилам\n"
            "• хостинг, на котором работает бот, и база данных, в которую он пишет"
        ),
        "privacy_others": (
            "• и больше никто, кроме них — сообщения идут через Telegram и дальше никуда, никакие внешние "
            "сервисы не вызываются"
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
        "terms_specific": (
            "О сообщениях: скрытое имя — не индульгенция. Угрозы, травля и всё незаконное "
            "остаются ровно тем же самым, когда отправитель анонимен, а владелец инбокса может "
            "заблокировать отправителя навсегда. Кто открыл инбокс, тот и отвечает за то, что он "
            "предлагает ему присылать."
        ),
        "terms_money": 'О деньгах: /donate — дело добровольное, деньги идут на то, во что обходятся боты. Платёж в Stars ещё и добавляет ⚡ кредит на конвертации в ConvertBot: 2 ⚡ за ⭐, а за твои первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держи свою копию всего, что тебе важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о тебе. Отменить будет нельзя.",
        "delete_data_consequences": 'Твоя ссылка перестанет работать — каждая её копия, которую кто-либо выложил, навсегда. Открытые разговоры перестанут маршрутизироваться: ответить в них не сможет ни одна из сторон, и список заблокированных уйдёт вместе с ними.\n\nУже отправленные сообщения это не затронет. Здесь они и не хранились — они в чатах Telegram, и каждый удаляет свою копию сам.\n\nЗаписи о пожертвованиях останутся, без username, потому что по ним разбираются споры о платежах. Баланс ⚡ тоже останется — он твой, если вернёшься.',
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
        "cancel_button_donation": "💸 Сумма пожертвования",
        "cancel_item_donation": "\u0441\u0443\u043c\u043c\u0430 \u043f\u043e\u0436\u0435\u0440\u0442\u0432\u043e\u0432\u0430\u043d\u0438\u044f, \u043a\u043e\u0442\u043e\u0440\u0443\u044e \u044f \u0437\u0430\u043f\u0440\u043e\u0441\u0438\u043b",
        "cancel_item_stale_prompt": "старый запрос, который всё ещё ждал ответа",
        "cancel_item_anon_session": "\u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0439 \u0430\u043d\u043e\u043d\u0438\u043c\u043d\u044b\u0439 \u0447\u0430\u0442 — \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443 \u0441\u043d\u043e\u0432\u0430, \u0447\u0442\u043e\u0431\u044b \u043d\u0430\u0447\u0430\u0442\u044c \u043d\u043e\u0432\u044b\u0439",
        "cancel_button_anon_session": "💬 Анонимный чат, в котором вы",
        "start_greeting": "Привет! Этот бот управляет анонимными почтовыми ящиками для вопросов.\n\n",
        "help_text": 'Есть два способа пользоваться этим ботом:\n\nЗаведите свой ящик — /link даёт вам постоянную ссылку. Разместите её где угодно на виду (в био, канале, истории — где хотите). Любой, кто по ней перейдёт, сможет отправить вам анонимное сообщение прямо в этот чат — вы не увидите, кто это.\nОтвечайте, смахнув сообщение вправо или нажав и удерживая его и выбрав «Ответить» — ваш ответ уйдёт именно этому человеку и появится у него как настоящий ответ, поэтому легко не путать несколько бесед, даже если они приходят в один и тот же чат.\n\nВам прислали чужую ссылку? Перейдите по ней, затем просто напишите — ваше сообщение уйдёт адресату, а личность останется скрытой. Если позже перейти по той же ссылке снова, начнётся новая беседа, а не продолжение старой.\n\nКоманды:\n/link - получить ссылку на свой ящик\n/conversations - ваши разговоры: открытые и в архиве\n/which - отправьте ответом на любое сообщение: скажу, из какого оно разговора\n/newlink, /pause, /resume - они же кнопки на экране /link\n/blocked - посмотреть, кого вы заблокировали\n/stats - краткая статистика, она же на экране /link\n/export - получить разговор обратно: копией сюда или документом\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/balance - ваш ⚡ кредит\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n/archive - отправьте ответом на сообщение, и этот разговор уйдёт в архив (в /conversations такая кнопка есть у каждого разговора)\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
        "follow_link_invalid": "Эта ссылка недействительна — возможно, тот, кто ею поделился, сбросил её. Попросите у него новую.",
        "follow_link_own": "Это ссылка на ваш собственный ящик — писать самому себе было бы просто заметкой для себя! Поделитесь ею с другими: /link",
        "follow_link_blocked": "Вы не можете написать этому человеку.",
        "follow_link_paused": "Этот человек сейчас не принимает новые анонимные сообщения — попробуйте позже.",
        "follow_link_started": (
            "Вы анонимно пишете кому-то — он увидит ваше сообщение, но не узнает, кто вы, если вы "
            "сами не скажете.\n"
            "\n"
            "Напишите первое сообщение ниже. Дальше отвечайте на то сообщение, которому отвечаете "
            "— смахните его или нажмите и удерживайте, затем «Ответить», — чтобы слова всегда "
            "попадали в нужную беседу.\n"
            "\n"
            "Если перейти по этой ссылке снова позже, начнётся отдельная новая беседа — а эта "
            "продолжит работать: отвечайте на любое её сообщение когда угодно."
        ),
        "link_status_paused": "на паузе — новые беседы не принимаются",
        "link_status_active": "принимает сообщения",
        "link_message": (
            "Ссылка на ваш анонимный ящик ({status}):\n"
            "{url}\n\n"
            "Скопируйте её и разместите где угодно — любой, кто её "
            "откроет, сможет написать вам сюда, а вы не увидите, кто это."
        ),
        "link_button_pause": "⏸️ Пауза",
        "link_button_resume": "▶️ Возобновить",
        "link_button_newlink": "🔄 Новая ссылка",
        "anonlink_no_link_yet": "Ссылки пока нет — сначала отправьте /link.",
        "anonlink_paused_answer": "На паузе.",
        "anonlink_resumed_answer": "Возобновлено.",
        "anonlink_newlink_answer": "Создана новая ссылка — старая больше не начинает новые беседы.",
        "newlink_message": "Новая ссылка (старая больше не начинает новые беседы):\n{url}",
        "pause_message": (
            "На паузе — ваша ссылка не будет начинать новые беседы до /resume. "
            "Уже идущие беседы продолжают работать как обычно."
        ),
        "resume_message": "Возобновлено — ваша ссылка снова принимает новые беседы.",
        "stats_message": "Вам писали {followers} разных гостей, всего {conversations} беседы(бесед).",

        "convs_title": "\U0001f4e5 Ваши беседы",
        "convs_title_archived": "\U0001f5c4 Беседы в архиве",
        "convs_summary": "{open} открытых \u00b7 {archived} в архиве",
        "convs_summary_blocked": "{open} открытых \u00b7 {archived} в архиве \u00b7 {blocked} заблокировано (см. /blocked)",
        "convs_empty_open": (
            "Открытых бесед нет. /link \u2014 ваша ссылка; написать вам может любой, кто её откроет."
        ),
        "convs_empty_archived": (
            "В архиве пока пусто. Закончив беседу, отправьте её в архив с её карточки; "
            "она вернётся сама, если в ней что-то появится."
        ),
        "convs_row_button": "#{conv_number} \u00b7 {when}",
        "convs_show_archived": "\U0001f5c4 Архив",
        "convs_show_open": "\U0001f4e5 Открытые",
        "convs_page": "{page}/{pages}",
        "convs_prev": "\u2039",
        "convs_next": "\u203a",
        "conv_card": "Беседа #{conv_number}\n\nНачата: {started}\nПоследнее сообщение: {when}",
        "conv_card_archived": "В архиве с: {archived}",
        "conv_back_button": "\u2039 Назад",
        "conv_jump_button": "\u2934\ufe0f К началу",
        "conv_archive_button": "\U0001f5c4 В архив",
        "conv_unarchive_button": "\u21a9\ufe0f Из архива",
        "conv_archived_answer": "В архиве \u2014 вернётся в список, как только в ней что-то появится.",
        "conv_unarchived_answer": "Снова в списке открытых.",
        "conv_gone": "Такой беседы больше нет в записях.",
        "jump_bookmark": (
            "\U0001f4cd Беседа #{conv_number} начинается здесь. Ответьте на это сообщение, чтобы написать в неё."
        ),
        "jump_no_anchor": (
            "Я больше не могу показать начало беседы #{conv_number} \u2014 сообщения перестают "
            "храниться как якоря для ответа после {days} дней тишины в беседе."
        ),

        "which_needs_reply": (
            "Отправьте /which ответом на сообщение, и я скажу, к какой беседе оно относится. "
            "Проведите по сообщению или нажмите и удерживайте его и выберите \u00abОтветить\u00bb."
        ),
        "which_unknown": (
            "Это сообщение не относится ни к одной открытой здесь беседе. Возможно, оно твоё "
            "собственное или его беседа уже в архиве."
        ),
        "which_owner": "Это сообщение относится к беседе #{conv_number}.",
        "which_follower": "Это сообщение относится к беседе, которая начинается здесь.",
        "which_follower_no_anchor": "Это сообщение относится к беседе, которую вы открыли {started}.",

        "rel_now": "только что",
        "rel_minutes": "{n} мин. назад",
        "rel_hours": "{n} ч. назад",
        "rel_days": "{n} дн. назад",
        "blocked_none": "Вы никого не заблокировали.",
        "blocked_header": "Заблокированные гости:",
        "blocked_guest_line": "  \U0001f6ab Гость из бесед(ы) {conversations}",
        "blocked_guest_line_unknown": "  \U0001f6ab Гость (бесед не найдено)",
        "blocked_unblock_button": "↩️ Разблокировать (беседа {conversations})",
        "blocked_unblock_button_unknown": "↩️ Разблокировать",
        "reply_button": "↩️ Как ответить",
        "block_button": "\U0001f6ab Заблокировать",
        "not_your_conversation": "Это не ваша беседа.",
        "blocked_answer": "Заблокировано.",
        "unblock_button_labelled": "↩️ Разблокировать беседу #{conv_number}",
        "too_fast": "Вы отправляете быстрее, чем я успеваю передавать — подождите около {seconds} сек. и попробуйте снова.",
        "edit_not_relayed": (
            "Это сообщение я уже передал, поэтому правка до собеседника не дошла — "
            "у него прежний текст. Отправьте исправление ещё раз ответом на него."
        ),
        "unblocked_answer": "Разблокирован.",
        "delivery_blocked": "Ваше сообщение не удалось доставить.",
        "inbox_gone": "Этого ящика больше не существует.",
        "incoming_header": "\U0001f4e9 Беседа #{conv_number}",
        "incoming_header_follower": "\U0001f4ec Новое сообщение",
        "delivery_forbidden": (
            "Не удалось доставить — этот бот не может написать тому, кто сам его "
            "не запускал, а этот человек ещё не запускал. Ничего не отправлено."
        ),
        "delivery_failed": "Не удалось доставить это сообщение: {error}",
        "sent_confirmation": "Отправлено ✅",
        "reply_no_match": "Твоё сообщение не отправлено — не удалось сопоставить этот ответ с какой-либо беседой.",
        "must_reply": (
            "Ничего не отправлено — сообщение не сказало, какой беседе оно отвечает.\n"
            "\n"
            "Ответьте на процитированное выше сообщение, и оно уйдёт туда. Смахните его или "
            "нажмите и удерживайте, затем «Ответить»."
        ),
        "reply_button_hint": (
            "Чтобы ответить, смахните это сообщение вправо — или нажмите и удерживайте его и "
            "выберите «Ответить». Так я понимаю, к какой беседе относится ваш ответ."
        ),
        "must_reply_opening": (
            "Пока ничего не отправлено — беседа, которую вы открыли, ещё не начата.\n"
            "\n"
            "Ответьте на процитированное выше сообщение, и это станет вашим первым сообщением им. "
            "Смахните его или нажмите и удерживайте, затем «Ответить»."
        ),
        "must_reply_ambiguous": (
            "Ничего не отправлено — сообщение не сказало, какой беседе оно отвечает, а в этом "
            "чате открыто несколько, так что мне пришлось бы гадать, кому его слать.\n"
            "\n"
            "Ответьте на то сообщение, которому отвечаете: смахните его или нажмите и "
            "удерживайте, затем «Ответить»."
        ),
        "restarting_send_again": (
            "🔄 Сейчас обновляюсь — подождите несколько секунд и отправьте ещё раз."
        ),
        "update_soon_try_later": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова примерно через {minutes} мин. Я напишу, когда вернусь.',
        "update_soon_try_later_soon": '🔧 Сейчас меня обновляют, поэтому я не могу начать ничего нового — попробуйте снова чуть позже. Я напишу, когда вернусь.',
        "update_will_reset": '🔧 Внимание: меня скоро обновят, и то, что вы сейчас начали, будет сброшено. Через несколько минут сможете начать заново.',
        "update_done_try_now": '✅ Обновление завершено — можете пробовать снова.',
        "reply_forbidden": "Не удалось доставить ваш ответ — возможно, вас заблокировали или человек покинул бота.",
        "reply_failed": "Не удалось доставить ваш ответ: {error}",
        "delivered_confirmation": "Доставлено ↩️",
        "reply_stale": (
            "Этого сообщения нет в моих записях, поэтому я не могу понять, какой беседе оно "
            "отвечает. Ничего не отправлено. Ответьте на одно из сообщений, которые я сюда "
            "доставил — смахните его или нажмите и удерживайте, затем «Ответить»."
        ),
        "generic_nudge": "Не совсем понял, для чего это — если кто-то прислал вам ссылку, сначала перейдите по ней. Хотите свой ящик? Отправьте /link.",
        "export_button_cancel": '✖️ Отмена',
        "export_cancelled": 'Выгрузка отменена — ничего не прочитано, не скопировано и не сохранено.',
        "export_failed": '⚠️ Не удалось собрать документ, поэтому ничего не отправлено. И ничего не сохранено. Отправьте /export, чтобы попробовать снова.',
        "export_done": '✅ Документ отправлен. Всё, что бот прочитал, пока его писал, удалено из этого чата, и ничего не сохранено.',
        "export_nothing_to_export": "Экспортировать пока нечего. Как только вы напишете кому-то по ссылке или кто-то напишет вам, /export сможет вернуть этот разговор.",
        "export_pick_intro": "📄 Экспорт разговора\n\nКакой? (В записях их {count}.)",
        "export_pick_numbered": "#{number} · {count} сооб.",
        "export_pick_yours": "Ваш разговор · {count} сооб.",
        "export_pick_all": "📚 Все · {count} сооб.",
        "export_gone": "Этого разговора больше нет в записях. Отправьте /export ещё раз, чтобы увидеть текущий список.",
        "export_what_numbered": "Разговор #{number}",
        "export_what_yours": "Ваш разговор",
        "export_what_all": "{conversations} разговоров",
        "export_modes": (
            "📄 {what} — {count} сообщений\n\n"
            "Два способа, и разница между ними одна: читает ли бот то, что было "
            "написано.\n\n"
            "📋 <b>Скопировать сюда.</b> Бот передаёт Telegram номера сообщений, копии "
            "делает сам Telegram. Что внутри — бот не видит. Всё приходит ровно таким, "
            "каким было: стикеры, фотографии, голосовые, файлы. Потом вы можете выделить "
            "их все и переслать куда угодно. Копии останутся в этом чате, пока вы их не "
            "удалите.\n\n"
            "📝 <b>Собрать документ.</b> Чтобы написать слова на странице, бот должен их "
            "прочитать: он пересылает каждое сообщение себе, читает и тут же удаляет "
            "прочитанное — вы увидите, как сообщения появляются и исчезают. В документе "
            "медиа не вкладывается, а называется ([Фото], [Голосовое сообщение]), и "
            "ничего не скачивается. Документ собирается в памяти, отправляется вам и не "
            "сохраняется.\n\n"
            "В обоих случаях: ни имени, ни username, ни id. Владелец ссылки — "
            "\"Owner\", тот, кто ему пишет, — \"Anon\". Второй стороне ничего не "
            "сообщается."
        ),
        "export_left_out": "{count} старых сообщений не вошли: бот не записал, с какой они стороны, либо их больше, чем помещается в один экспорт.",
        "export_button_copy": "📋 Скопировать сюда",
        "export_button_doc": "📝 Собрать документ",
        "export_copy_progress": "📋 Копирую… {done} из {total}.",
        "export_copy_header": "— {what}, {count} сообщений —",
        "export_copy_done": "— конец копии —\n\nСкопировано {count} сообщений. Бот не прочитал ни одного. Выделите их и перешлите куда нужно — или удалите, когда закончите.",
        "export_copy_missing": "{count} скопировать не удалось — скорее всего, вы удалили их из этого чата.",
        "export_copy_finished": "✅ {count} сообщений скопировано ниже. Ничего не прочитано и ничего не сохранено.",
        "export_doc_progress": "📝 Читаю… {done} из {total}. Каждое сразу же удаляется обратно.",
        "export_doc_owner": "Owner",
        "export_doc_anon": "Anon",
        "export_doc_unreadable": "{count} прочитать не удалось, их в документе нет.",
        "export_caption": '📄 Сообщений: {messages}, разговоров: {conversations}.',
        "export_doc_title": 'Переписка из AnonBot',
        "export_doc_generated": 'Создано {date}. Время — UTC.',
        "export_doc_started": 'начат {date} · сообщений: {count}',
        "export_doc_footer": 'Каждое сообщение прочитано один раз, копия удалена сразу же. Бот не хранит ничего из того, что кто-либо пишет, и не сохранил этот документ. Здесь нет ни имён, ни юзернеймов, ни id: владелец ссылки — Owner, тот, кто ему пишет, — Anon.',
        "export_kind_photo": 'Фото',
        "export_kind_video": 'Видео',
        "export_kind_animation": 'GIF',
        "export_kind_video_note": 'Видеосообщение',
        "export_kind_voice": 'Голосовое сообщение',
        "export_kind_audio": 'Аудио',
        "export_kind_sticker": 'Стикер',
        "export_kind_document": 'Файл',
        "export_kind_location": 'Геопозиция',
        "export_kind_contact": 'Контакт',
        "export_kind_poll": 'Опрос',
        "export_kind_dice": 'Кубик',
        "export_kind_other": 'Сообщение',
        "archive_needs_reply": (
            "Ответь на сообщение из той беседы, которую хочешь убрать в архив, и отправь "
            "/archive ещё раз — смахни сообщение или нажми и удержи его и выбери «Ответить». "
            "Либо открой /conversations и выбери беседу из списка."
        ),
        "archive_not_owner": (
            "Архив — это дело владельца ящика: он убирает беседу из своего списка, а у тебя "
            "такого списка нет."
        ),
        "archive_already": "Беседа #{conv_number} уже в архиве.",
        "archive_confirm": (
            "Убрать беседу #{conv_number} в архив?\n"
            "\n"
            "Она уйдёт из списка открытых. Ничего не удаляется, собеседнику ничего не сообщают, "
            "и если он напишет снова — беседа сразу вернётся."
        ),
        "archive_button_yes": "🗂 В архив #{conv_number}",
        "archive_button_no": "Оставить открытой",
        "archive_done": "🗂 Беседа #{conv_number} в архиве. Посмотреть — /conversations.",
        "archive_kept": "Оставил открытой.",
        "unknown_command": "Я не знаю такую команду. Отправь /help, чтобы увидеть, что я умею.",
    },
}

import problems

_BOT = "anon_bot"

def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))

async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler call."""
    cached = context.user_data.get("lang")
    if cached:
        return cached
    lang = await asyncio.to_thread(db.get_user_language, user_id) or "en"
    context.user_data["lang"] = lang
    return lang

COMMAND_MENU = {
    "uz": {
        "start": "Bu bot nima qiladi va qanday boshlash kerak",
        "link": "Havolangiz va uning sozlamalari",
        "conversations": "Suhbatlaringiz",
        "which": "Bu qaysi suhbat? — xabarga javob qilib yuboring",
        "blocked": "Kimlarni bloklagansiz",
        "export": "Suhbatni qaytarib olish",
        "cancel": "Kutayotgan amalimni to'xtatish",
        "help": "Nimalar qila olaman",
        "balance": "⚡ kreditingiz",
        "donate": "Server xarajatlariga hissa qo'shish",
        "paysupport": "To'lov bilan muammo",
        "privacy": "Siz haqingizda nimalarni saqlayman",
        "terms": "Botdan foydalanish shartlari",
        "deletemydata": "Siz haqingizdagi hamma narsani o'chirish",
    },
    "ru": {
        "start": "Что этот бот делает и с чего начать",
        "link": "Ваша ссылка и её настройки",
        "conversations": "Ваши разговоры",
        "which": "Какой это разговор? — ответьте на сообщение",
        "blocked": "Кого вы заблокировали",
        "export": "Вернуть разговор",
        "cancel": "Остановить то, чего я жду",
        "help": "Что я умею",
        "balance": "Ваш ⚡ кредит",
        "donate": "Помочь с расходами на хостинг",
        "paysupport": "Проблема с оплатой",
        "privacy": "Что я о вас храню",
        "terms": "Для чего можно пользоваться ботом",
        "deletemydata": "Удалить всё, что я о вас храню",
    },
}
