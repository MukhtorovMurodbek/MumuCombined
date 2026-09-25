"""Translation strings for StickerBot's end-user-facing text (English,
Uzbek, Russian). Deliberately duplicated per bot -- same "no shared files
between bots" independence as shared_features.py -- but the STRINGS content
here is specific to this bot's own commands and flows.

Admin-only output (/whois, /messageas, /dbdump, /status, /crashtest) is
intentionally NOT translated -- only the bot owner ever sees it, same
reasoning as downloader_bot's i18n.py.

The keys below split into two groups:
  - "Shared" keys (donate flow, sibling-bot blurb) exist under the exact
    same names in every bot's i18n.py, since shared_features.py is
    duplicated byte-identical across the family and calls t() with these
    names regardless of which bot it's running in.
  - Bot-specific keys, everything below the shared block, for this bot's
    own bot.py (plus video_sticker.py/import_utils.py error text) strings
    only.
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
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
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
        # ---- stickerbot-specific keys ----
        "start_intro": (
            "Hey! I turn your images/GIFs/videos/stickers into Telegram sticker "
            "packs, and I can grab videos from Instagram/TikTok links.\n\n"
        ),
        "help_text": "Commands:\n/newpack - start a new sticker pack\n/addsticker - add stickers to an existing pack\n/mypacks - list your packs\n/import <pack link/name> - (while editing) bulk-copy stickers from another Telegram pack, or send a WhatsApp sticker pack .zip/.wastickers file\n/done - finish editing a pack\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/whomade <pack link/name> - see who created a pack (if made through this bot)\n/donate - chip in for hosting costs (totally optional)\n/en, /uz, /rus - switch language (or /language, which asks)\n\nWhile editing a pack: send images, GIFs, videos, or static/video stickers to add them.\nSend emoji after one to tag it with that emoji.\n\nTap a pack from /mypacks to rename it, set up co-editing so someone else can add stickers to it too, or delete it for good (owner-only, asks twice before it actually happens).\n\nWant to grab a video from Instagram/TikTok, or convert a file to another format? Those live in the sibling bots below now.\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n",
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
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• shu bot orqali yaratgan to'plamlaringiz: har birining nomi va sarlavhasi, o'sha paytdagi ismingiz va foydalanuvchi nomingiz\n• to'plamlaringizga kimga qo'shish huquqi berganingiz va yaratgan havolalaringiz\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nXato ostidagi \"Xabar berish\" tugmasi xabarda aynan nima bo'lishini ko'rsatadi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Unda faqat shu xatoga aloqador narsalar, bot siz bilan gaplashadigan til, suhbat shaxsiymi yoki guruhmi va, yozsangiz, izohingiz bo'ladi. Ismingiz va @username'ingiz hech qachon. Telegram ID raqamingiz faqat \"Bot egasi menga javob yozsin\"ni yoqsangiz — aks holda xabar sizga bog'lanmaydi.\n\nXabardagi narsalar 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa ID raqamingiz bor xabarlarni darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
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
        "help_text": "Buyruqlar:\n/newpack - yangi stiker to'plami yaratish\n/addsticker - mavjud to'plamga stiker qo'shish\n/mypacks - to'plamlaringizni ko'rish\n/import <to'plam havolasi yoki nomi> - (tahrirlash vaqtida) boshqa Telegram to'plamidagi stikerlarni ko'chirish yoki WhatsApp to'plamining .zip/.wastickers faylini yuklash\n/done - to'plamni tahrirlashni yakunlash\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/whomade <to'plam havolasi yoki nomi> - to'plamni kim yaratganini bilish (shu bot orqali yaratilgan bo'lsa)\n/donate - server xarajatlariga hissa qo'shish (mutlaqo ixtiyoriy)\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n\nTo'plamni tahrirlash vaqtida rasm, GIF, video yoki statik/video stiker yuborsangiz, u to'plamga qo'shiladi.\nUndan keyin emoji yuborsangiz, o'sha stikerga shu emoji biriktiriladi.\n\n/mypacks'da to'plamni tanlab, nomini o'zgartirishingiz, boshqalar ham stiker qo'sha olishi uchun birgalikda tahrirlashni yoqishingiz yoki uni butunlay o'chirishingiz mumkin (faqat egasi; o'chirishdan oldin ikki marta so'raladi).\n\nInstagram/TikTok'dan video yuklab olish yoki faylni boshqa formatga o'girish kerakmi? Bu endi pastdagi boshqa botlarimizda.\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — /donate orqali to'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO'LMAYDI.\n\n",
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
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
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
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nКнопка «Сообщить» под ошибкой показывает, что именно будет в сообщении, и ничего не отправляется, пока вы не нажмёте «Отправить». В нём только то, что относится к этой ошибке, плюс язык, на котором бот с вами говорит, личный это чат или группа, и комментарий, если вы его напишете. Никогда — ваше имя или @username. Ваш Telegram id — только если вы включите «Пусть владелец мне ответит», иначе сообщение с вами не связано.\n\nВсё, что было в сообщении, стирается само через 30 дней, а /deletemydata сразу стирает сообщения с вашим id. Запись об ошибке остаётся — она действительно произошла. Сами записи удаляются через 180 дней.",
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
        "help_text": 'Команды:\n/newpack - начать новый набор стикеров\n/addsticker - добавить стикеры в существующий набор\n/mypacks - показать ваши наборы\n/import <ссылка/имя набора> - (во время редактирования) массово скопировать стикеры из другого набора Telegram, или отправить файл экспорта набора стикеров WhatsApp .zip/.wastickers\n/done - закончить редактирование набора\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/whomade <ссылка/имя набора> - узнать, кто создал набор (если он был создан через этого бота)\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n\nВо время редактирования набора: отправляйте изображения, GIF, видео или статические/видео-стикеры, чтобы добавить их.\nОтправьте эмодзи сразу после стикера, чтобы пометить его этим эмодзи.\n\nНажмите на набор в /mypacks, чтобы переименовать его, настроить совместное редактирование, чтобы кто-то ещё мог добавлять стикеры, или удалить его насовсем (только для владельца, дважды спрашивает перед этим).\n\nХотите скачать видео из Instagram/TikTok или сконвертировать файл в другой формат? Теперь это делают соседние боты ниже.\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
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


# Every problem a person can run into ends with its code, and the code is what
# puts a "Report the issue" button under it -- see problems.py. Imported here,
# below the tables, because it is pure data and nothing above needs it.
import problems  # noqa: E402

_BOT = "sticker_bot"


def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))


async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler
    call. Falls back to "en" for a user who hasn't chosen a language yet
    (only reachable outside /start's first-run gate, e.g. someone who sends
    a sticker before ever running /start)."""
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
