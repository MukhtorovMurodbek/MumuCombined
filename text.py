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
        "report_button": '🐞 Send more details',
        "problem_logged_note": "Anonymous technical report saved.",
        "problem_logged_note_optin": "Anonymous technical report saved. You can opt in to send more details.",
        "report_disclaimer": "📨 Send more details with incident {incident}?\n\nSaved already, nothing about you: the bot, code {code}, the time, the version.\n\nSend adds:\n• your Telegram ID\n• your @username, if you have one\n• your language\n• private chat or group\n\nNever your messages or files. Cleared after 30 days, or now with /deletemydata.",
        "report_send": '📨 Send',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — added to incident {incident}.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent.',
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
            "• how many times each button is tapped, counted per day for the whole bot, with nothing about who tapped it\n• how much was done — links per site, conversions, stickers, relayed messages — counted per day for the whole bot, with nothing about who\n"
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
            "Under a crash, a failed /deletemydata or /feedback, or an error that keeps "
            "happening to you, \"Send more details\" offers to attach four things to that one "
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
        "privacy_kept_for": 'Settings and anything the bot is holding for you stay until you erase them or stop using it. Counted use is dropped after about three months; the daily counts of what was done, which say nothing about who, after 400 days. Payment records and your ⚡ balance are kept longer, because a dispute about a payment is settled against them.\n\nNothing here is sold, rented or used for advertising, and nothing goes to anyone not named above.',
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
        "feedback_ask": (
            "💬 What would you like to tell the person who runs these bots? A suggestion, a "
            "problem, anything — write it in one message, as a reply to this one.\n"
            "\n"
            "Only they read it, and they can't write back: it is sent without your name or id. "
            "/cancel to stop."
        ),
        "feedback_placeholder": "Your feedback",
        "feedback_text_only": "That one has to be in words — write your feedback as a text reply to this message, or send /cancel.",
        "feedback_thanks": "✅ Thank you — sent. Only the person who runs these bots reads it, and they can't reply: nothing in it says who you are.",
        "feedback_limit": "You've sent {per_day} messages with /feedback today, which is as many as I take in a day. Thank you — write again tomorrow.",
        "feedback_failed": "Your feedback wasn't sent — something went wrong on my side. Please try again in a few minutes.",
        "cancel_button_feedback": "💬 Feedback",
        "cancel_item_feedback": "the feedback I asked you for",
        "help_brief": "How it works:\n\n• /newpack makes a sticker pack: name it, then send pictures, GIFs, videos or stickers — each goes in as it arrives.\n• The buttons under the message box: ✏️ to add to a pack, 👁 to open it. To change a sticker's emoji, reply to its ✅ message with emoji.\n• /mypacks lists your packs, with buttons to rename, share or delete one. /import copies stickers in from another Telegram pack or a WhatsApp export.\n• Ideas or problems: /feedback — only the person who runs these bots reads it, and they can't reply.\n\nMain commands: /newpack · /addsticker · /mypacks · /cancel\nEvery command: the full guide, below or /fullhelp.\n\n",
        "help_full_button": "📖 Full guide",
        "help_brief_button": "↩️ Short version",
        "help_page_everything": "The full guide: /fullhelp",
        "help_page_gone": "That help page no longer exists. Send /help to see the current ones.",
        "helppage_newpack": "🆕 /newpack — a new sticker pack\n\n1. Send /newpack (or tap ➕ New pack), then the pack's title as a message (up to {title_max} characters; longer is cut). If Telegram refuses the title, start it with a letter.\n2. Send what should become stickers, one per message: photos or image files, GIFs, videos, or stickers. The pack is made with the first one — no sticker, no pack. Each one gets a ✅ reply once it's in.\n3. Each sticker gets {emoji}. To change it, reply to its ✅ message (or to what you sent) with emoji — up to {emoji_max}.\n4. That's all: there is nothing to finish. The pack's buttons stay under the message box; /cancel stops.\n\nHow each kind turns out:\n• A photo, an image file or a static sticker becomes a static sticker, {side} px on its longer side.\n• A GIF, a video or a video sticker becomes a video sticker: {side} px, up to {seconds} seconds, {fps} frames a second, no sound, under {kb} KB. A longer clip gets speed choices (or trim it yourself); one too heavy gets lower resolution or frame rate to choose from.\n• Animated (.tgs) stickers can't be added.\n• Many at once: a WhatsApp sticker pack (.zip or .wastickers), or /import from a Telegram pack.\n\nExample: /newpack, then \"Cat faces\", then three photos of your cat, then reply 😺 to one of the ✅ messages.",
        "helppage_addsticker": "➕ /addsticker — more stickers in a pack you have\n\n1. Tap ✏️ on the pack under the message box (or /addsticker, tap the pack, then \"➕ Add stickers\").\n2. Send photos, GIFs, videos or stickers, just as for a new pack. Each gets {emoji}; reply to its ✅ message with emoji to change it.\n• Sending a sticker that is already in the pack takes it out. If it's the last one, I ask first, because that deletes the whole pack.\n• Sent something with no pack open? I keep it for 10 minutes and ask which pack it goes to.\n• Only packs made with this bot that are yours are listed. None yet? /newpack.\n• /mypacks shows the same list. Each pack's menu can also rename it, let someone else edit it with you, or delete it.\n\nExample: tap ✏️ Edit Cat faces, then send a new photo.",
        "helppage_import": (
            "📥 /import — many stickers at once, from another pack\n"
            "\n"
            "It works while you are filling a pack: after /newpack and its title, or after \"➕ Add stickers\".\n"
            "• /import followed by a public Telegram pack's link (t.me/addstickers/…) or its name copies its stickers into your pack, with their emoji. Up to {max} each time.\n"
            "• Animated (.tgs) stickers are skipped, and I say how many.\n"
            "• From WhatsApp: send the sticker pack's .zip or .wastickers file instead.\n"
            "• Then keep sending more.\n"
            "\n"
            "Example: /newpack, then \"Favourites\", then /import t.me/addstickers/SomePack"
        ),
        "privacy_feedback_heading": "If you send /feedback:",
        "privacy_feedback": (
            "What you write reaches the person who runs these bots as a Telegram message, with "
            "which bot it came from and your language — not your name, your username or your id. "
            "Only they read it, and they cannot reply to it. A copy is kept in the bots' "
            "database for 30 days and then deleted."
        ),
        "cancel_item_new_pack": "the new pack you were naming",
        "cancel_button_new_pack": "🆕 Naming a new pack",
        "cancel_item_rename": "renaming \"{title}\"",
        "cancel_button_rename": "✏️ Renaming a pack",
        "cancel_item_editing": "editing \"{title}\"",
        "cancel_button_editing": "📦 Editing a pack",

        "start_intro": (
            "Hey! I turn your images, GIFs, videos and stickers into Telegram sticker "
            "packs.\n\n"
        ),
        "help_text": "Commands:\n/newpack - start a new sticker pack\n/addsticker - add stickers to an existing pack\n/mypacks - list your packs\n/import <pack link/name> - (while editing) bulk-copy stickers from another Telegram pack, or send a WhatsApp sticker pack .zip/.wastickers file\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/feedback - suggest something or report a problem; only whoever runs these bots reads it, and they cannot reply\n/whomade <pack link/name> - see who created a pack (if made through this bot)\n/donate - chip in for hosting costs (totally optional)\n/en, /uz, /rus - switch language (or /language, which asks)\n/balance - your ⚡ credit\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n/fullhelp - this full guide (/help - the short one)\n/convert - converting files lives in ConvertBot now; this points you there\n\nWhile editing a pack: send images, GIFs, videos, or static/video stickers to add them.\nSend emoji after one to tag it with that emoji.\n\nTap a pack from /mypacks to rename it, set up co-editing so someone else can add stickers to it too, or delete it for good (owner-only, asks twice before it actually happens).\n\nWant to grab a video from Instagram/TikTok, or convert a file to another format? Those live in the sibling bots below now.\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n",
        "whomade_usage": "Usage: /whomade <pack name or t.me/addstickers link>",
        "whomade_not_found": (
            "I don't have a record of that pack — either it wasn't created "
            "through this bot, or the name/link isn't right."
        ),
        "whomade_result": "📦 \"{title}\"\nCreated by {creator} on {date} (via this bot).",
        "coedit_link_invalid": "That co-editing link isn't valid — it may have been reset by the pack owner.",
        "coedit_pack_gone": "That pack doesn't seem to exist anymore.",
        "coedit_own_pack": "That's your own pack — use /mypacks to manage it.",
        "coedit_joined_intro": "You're a co-editor of “{title}” now. Send pictures, GIFs, videos or stickers to add.",
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
        "session_lost": "That pack session closed after a long pause. Start again: /newpack or /addsticker.",
        "held_full": "I'm already holding {n} for a pack — pick one for them first, then send this again.",
        "held_already_in_pack": "That sticker is already in “{title}” — left as it is.",
        "btn_kb_edit": "✏️ Edit {title}",
        "btn_kb_view": "👁 View {title}",
        "pack_view": "👁 “{title}”",
        "item_added": "✅ Added to “{title}” with {emoji}. Reply to this message with emoji to change it.",
        "item_added_video": "✅ Added to “{title}” as a video sticker with {emoji}. Reply to this message with emoji to change it.",
        "item_added_fit": "✅ Added to “{title}” ({how}) with {emoji}. Reply to this message with emoji to change it.",
        "retag_unknown": "I don't know which sticker that message was for any more.",
        "packs_keyboard_note": "📦 Your packs are on the buttons below — tap one to add stickers to it.",
        "pack_button_gone": "I can't find that pack — it may have been deleted. Here are your packs as they are now.",
        "held_offer": "Which pack should {n} item(s) go to? They wait {minutes} minutes.",
        "btn_held_discard": "✖️ Don't add",
        "held_expired": "This waited too long — send it again.",
        "held_discarded": "Not added.",
        "video_too_long": "This clip is {seconds} s; a video sticker can be {limit} s at most. Pick a speed, or trim it to {limit} s yourself and send it again.",
        "video_too_long_no_speed": "This clip is {seconds} s; a video sticker can be {limit} s at most, and it would take more than {speed}× to fit. Trim it to {limit} s (or to {longest} s, then speed it up) and send it again.",
        "video_too_heavy": "This clip doesn't fit Telegram's {kb} KB for a video sticker. Make it lighter:",
        "video_too_heavy_last": "Even so it doesn't fit Telegram's {kb} KB. Trim it shorter and send it again.",
        "btn_speed_fit": "⏩ {speed}× — fits exactly",
        "btn_speed": "⏩ {speed}×",
        "btn_lower_res": "🔽 Lower resolution (recommended)",
        "btn_lower_fps": "🎞 Lower frame rate ({fps} fps)",
        "btn_skip_clip": "✖️ Skip this clip",
        "video_fit_expired": "That choice has expired — send the clip again.",
        "video_fit_skipped": "Skipped — that clip was not added.",
        "video_fit_added": "✅ Added ({how}).",
        "fit_lower_res": "lower resolution",
        "fit_lower_fps": "{fps} fps",
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
        "editing_intro_new": "Send pictures, GIFs, videos or stickers to add.",
        "no_packs_for_add": "You don't have any packs yet. Use /newpack first.",
        "pick_pack_prompt": "Which pack? Tap it, then \"➕ Add stickers\".",
        "editing_intro_add": "Send pictures, GIFs, videos or stickers to add.",
        "status_verb_creating": "Creating",
        "status_verb_editing": "Editing",
        "status_line": "✏️ {verb} “{title}”",
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
        "batch_not_added": "⚠️ {done}/{total} — {failed} not added",
        "last_attempt_failed": "⚠️ Not added — send it again to retry.",
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
        "import_summary_tail": ".",
        "done_standalone_hint": "Nothing to finish — stickers go in as you send them. Tap ✏️ on a pack below to add to it.",
        "import_standalone_hint": (
            "Start or open a pack first (/newpack, or tap Add stickers on a pack from "
            "/mypacks), then use /import <link> inside that session."
        ),
        "whatsapp_reading": "Reading the WhatsApp sticker pack...",
        "whatsapp_summary_head": "Imported {added} sticker(s) from the WhatsApp pack",
        "not_emoji_message": "Send pictures, GIFs, videos or stickers to add. To change a sticker's emoji, reply to its ✅ message with emoji.",
        "no_sticker_to_tag": "To change a sticker's emoji, reply to its ✅ message with emoji.",
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
        "gift_granted": "🎁 We have passed 100 users, thank you! You get {amount} ⚡ of free credit, good until {date}. It pays for about {conversions} paid conversions in {convert} or big-file downloads in {download}. Your balance: /balance",
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
        "report_button": "🐞 Qo'shimcha ma'lumot yuborish",
        "problem_logged_note": "Anonim texnik hisobot saqlandi.",
        "problem_logged_note_optin": "Anonim texnik hisobot saqlandi. Xohlasangiz, qo'shimcha ma'lumot yuborishingiz mumkin.",
        "report_disclaimer": "📨 {incident} hodisasiga qo'shimcha ma'lumot yuborasizmi?\n\nAllaqachon saqlangan, siz haqingizda hech narsa yo'q: bot, {code} kodi, vaqt, versiya.\n\n\"Yuborish\" qo'shadi:\n• Telegram ID raqamingiz\n• bo'lsa, @username'ingiz\n• tilingiz\n• shaxsiy suhbatmi yoki guruh\n\nXabarlaringiz va fayllaringiz hech qachon kirmaydi. 30 kundan keyin o'chiriladi, /deletemydata bilan esa darhol.",
        "report_send": '📨 Yuborish',
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — {incident} hodisasiga qo'shildi.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi.",
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
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• shu bot orqali yaratgan to'plamlaringiz: har birining nomi va sarlavhasi, o'sha paytdagi ismingiz va foydalanuvchi nomingiz\n• to'plamlaringizga kimga qo'shish huquqi berganingiz va yaratgan havolalaringiz\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• har bir tugma necha marta bosilgani — butun bot bo'yicha kunlik umumiy hisob, kim bosgani haqida hech qanday ma'lumotsiz\n• qancha ish qilingani — sayt bo'yicha havolalar, konvertatsiyalar, stikerlar, yuborilgan xabarlar — butun bot bo'yicha kunlik hisob, kim ekani haqida ma'lumotsiz\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nIshdan chiqish, bajarilmagan /deletemydata yoki /feedback, yoki sizda takror-takror yuz berayotgan xato ostidagi \"Qo'shimcha ma'lumot yuborish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• boshqa hech kim — stikerlar botning o'z serverida tayyorlanadi, tashqi xizmatlarga murojaat qilinmaydi",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi; qancha ish qilinganining kunlik hisobi esa — unda kimligi yo'q — 400 kundan keyin. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
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
        "feedback_ask": (
            "💬 Bu botlarni yuritayotgan odamga nima demoqchisiz? Taklif, muammo — nima bo'lsa "
            "ham, bitta xabarda, shu xabarga javob qilib yozing.\n"
            "\n"
            "Uni faqat o'sha odam o'qiydi va sizga javob yoza olmaydi: xabar ismingiz va ID "
            "raqamingizsiz yuboriladi. To'xtatish: /cancel"
        ),
        "feedback_placeholder": "Fikringiz",
        "feedback_text_only": "Bu yerga faqat matn qabul qilinadi — fikringizni shu xabarga javob qilib so'z bilan yozing yoki /cancel yuboring.",
        "feedback_thanks": "✅ Rahmat — yuborildi. Uni faqat bu botlarni yuritayotgan odam o'qiydi va javob yoza olmaydi: xabarda kimligingiz ko'rsatilmagan.",
        "feedback_limit": "Bugun /feedback orqali {per_day} ta xabar yubordingiz — bir kunda shuncha qabul qilaman. Rahmat, ertaga yana yozishingiz mumkin.",
        "feedback_failed": "Fikringiz yuborilmadi — bot tomonida nimadir buzildi. Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring.",
        "cancel_button_feedback": "💬 Fikr-mulohaza",
        "cancel_item_feedback": "men so'ragan fikr-mulohaza",
        "help_brief": "Bot qanday ishlaydi:\n\n• /newpack stiker to'plami yaratadi: nom bering, so'ng rasm, GIF, video yoki stiker yuboring — har biri kelishi bilan qo'shiladi.\n• Xabar maydoni ostidagi tugmalar: ✏️ — to'plamga qo'shish, 👁 — uni ochish. Stiker emojisini o'zgartirish uchun uning ✅ xabariga emoji bilan javob bering.\n• /mypacks to'plamlaringiz ro'yxati — nomini o'zgartirish, ulashish yoki o'chirish tugmalari bilan. /import boshqa Telegram to'plamidan yoki WhatsApp eksportidan stikerlarni ko'chiradi.\n• Taklif yoki muammo: /feedback — uni faqat bu botlarni yuritayotgan odam o'qiydi, javob qaytmaydi.\n\nAsosiy buyruqlar: /newpack · /addsticker · /mypacks · /cancel\nBarcha buyruqlar: to'liq qo'llanmada — pastdagi tugma yoki /fullhelp.\n\n",
        "help_full_button": "📖 To'liq qo'llanma",
        "help_brief_button": "↩️ Qisqa variant",
        "help_page_everything": "To'liq qo'llanma: /fullhelp",
        "help_page_gone": "Bu yordam sahifasi endi yo'q. Hozirgilarini ko'rish uchun /help yuboring.",
        "helppage_newpack": "🆕 /newpack — yangi stiker to'plami\n\n1. /newpack yuboring (yoki ➕ Yangi to'plam tugmasini bosing), keyin to'plamning nomini xabar qilib ({title_max} belgigacha; uzunrog'i qisqartiriladi). Telegram nomni qabul qilmasa, uni harf bilan boshlang.\n2. Stikerga aylanadigan narsalarni har birini alohida xabarda yuboring: rasm yoki rasm-fayl, GIF, video yoki stiker. To'plam birinchisi bilan yaratiladi — stiker bo'lmasa, to'plam ham bo'lmaydi. Qo'shilgan har biriga ✅ bilan javob beraman.\n3. Har bir stikerga {emoji} beriladi. O'zgartirish uchun uning ✅ xabariga (yoki o'zingiz yuborganiga) emoji bilan javob bering — {emoji_max} tagacha.\n4. Tamom: yakunlash shart emas. To'plam tugmalari xabar maydoni ostida qoladi; /cancel to'xtatadi.\n\nHar biri nimaga aylanadi:\n• Rasm, rasm-fayl yoki oddiy stiker oddiy stikerga aylanadi, uzun tomoni {side} px.\n• GIF, video yoki video-stiker video-stikerga aylanadi: {side} px, {seconds} soniyagacha, soniyasiga {fps} kadr, ovozsiz, {kb} KB dan kichik. Uzunroq klip uchun tezlik tanlovlarini beraman (yoki o'zingiz qisqartiring); juda og'ir bo'lsa — pastroq sifat yoki kamroq kadr.\n• Animatsiyali (.tgs) stikerlarni qo'shib bo'lmaydi.\n• Ko'pini birdan: WhatsApp stiker to'plami (.zip yoki .wastickers) yoki Telegram to'plamidan /import.\n\nMisol: /newpack, keyin \"Mushuk yuzlari\", keyin mushugingizning uchta rasmi, keyin ✅ xabarlardan biriga 😺 bilan javob.",
        "helppage_addsticker": "➕ /addsticker — mavjud to'plamingizga yangi stikerlar\n\n1. Xabar maydoni ostidagi to'plamning ✏️ tugmasini bosing (yoki /addsticker, to'plamni bosing, keyin \"➕ Stiker qo'shish\").\n2. Rasm, GIF, video yoki stikerlarni yangi to'plamdagidek yuboring. Har biriga {emoji} beriladi; o'zgartirish uchun uning ✅ xabariga emoji bilan javob bering.\n• To'plamda allaqachon bor stikerni yuborsangiz, u to'plamdan olib tashlanadi. Agar u oxirgisi bo'lsa, avval so'rayman, chunki bu butun to'plamni o'chiradi.\n• To'plam ochilmaganda nimadir yubordingizmi? Uni 10 daqiqa saqlab, qaysi to'plamga qo'shishni so'rayman.\n• Faqat shu bot orqali yaratilgan va sizniki bo'lgan to'plamlar ko'rsatiladi. Hali yo'qmi? /newpack.\n• /mypacks ham shu ro'yxatni ko'rsatadi. Har bir to'plam menyusida uni qayta nomlash, boshqa birov bilan birga tahrirlash yoki o'chirish ham mumkin.\n\nMisol: \"✏️ Tahrirlash: Mushuk yuzlari\" ni bosing, keyin yangi rasm yuboring.",
        "helppage_import": (
            "📥 /import — boshqa to'plamdan ko'p stikerni birdan\n"
            "\n"
            "To'plamni to'ldirayotganingizda ishlaydi: /newpack va nomidan keyin yoki \"➕ Stiker qo'shish\" dan keyin.\n"
            "• /import va ochiq Telegram to'plamining havolasi (t.me/addstickers/…) yoki nomi uning stikerlarini emojilari bilan birga to'plamingizga ko'chiradi. Har safar {max} tagacha.\n"
            "• Animatsiyali (.tgs) stikerlar o'tkazib yuboriladi va nechtasi ekanini aytaman.\n"
            "• WhatsApp'dan: buning o'rniga stiker to'plamining .zip yoki .wastickers faylini yuboring.\n"
            "• Keyin yana yuborishda davom eting.\n"
            "\n"
            "Misol: /newpack, keyin \"Sevimlilar\", keyin /import t.me/addstickers/SomePack"
        ),
        "privacy_feedback_heading": "/feedback yuborsangiz:",
        "privacy_feedback": (
            "Yozganingiz bu botlarni yuritayotgan odamga Telegram xabari sifatida yetib boradi — "
            "qaysi botdan kelgani va tilingiz bilan birga, lekin ismingiz, foydalanuvchi nomingiz "
            "va ID raqamingizsiz. Uni faqat o'sha odam o'qiydi va unga javob yoza olmaydi. "
            "Nusxasi botlar bazasida 30 kun saqlanadi, keyin o'chiriladi."
        ),
        "cancel_item_new_pack": "siz nom qo'yayotgan yangi to'plam",
        "cancel_button_new_pack": "🆕 Yangi to'plamga nom berish",
        "cancel_item_rename": "\"{title}\" nomini o'zgartirish",
        "cancel_button_rename": "✏️ To'plam nomini o'zgartirish",
        "cancel_item_editing": "\"{title}\" ni tahrirlash",
        "cancel_button_editing": "📦 To'plamni tahrirlash",
        "start_intro": "Salom! Rasm, GIF, video va stikerlaringizdan Telegram stiker to'plamlari yasayman.\n\n",
        "help_text": "Buyruqlar:\n/newpack - yangi stiker to'plami yaratish\n/addsticker - mavjud to'plamga stiker qo'shish\n/mypacks - to'plamlaringizni ko'rish\n/import <to'plam havolasi yoki nomi> - (tahrirlash vaqtida) boshqa Telegram to'plamidagi stikerlarni ko'chirish yoki WhatsApp to'plamining .zip/.wastickers faylini yuklash\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/feedback - taklif yozish yoki muammo haqida xabar berish; uni faqat botlarni yuritayotgan odam o'qiydi, javob qaytmaydi\n/whomade <to'plam havolasi yoki nomi> - to'plamni kim yaratganini bilish (shu bot orqali yaratilgan bo'lsa)\n/donate - server xarajatlariga hissa qo'shish (mutlaqo ixtiyoriy)\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/balance - ⚡ kreditingiz\n/paysupport - to'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n/fullhelp - shu to'liq qo'llanma (/help - qisqasi)\n/convert - fayllarni o'girish endi ConvertBot'da; bu buyruq sizni o'sha yerga yo'naltiradi\n\nTo'plamni tahrirlash vaqtida rasm, GIF, video yoki statik/video stiker yuborsangiz, u to'plamga qo'shiladi.\nUndan keyin emoji yuborsangiz, o'sha stikerga shu emoji biriktiriladi.\n\n/mypacks'da to'plamni tanlab, nomini o'zgartirishingiz, boshqalar ham stiker qo'sha olishi uchun birgalikda tahrirlashni yoqishingiz yoki uni butunlay o'chirishingiz mumkin (faqat egasi; o'chirishdan oldin ikki marta so'raladi).\n\nInstagram/TikTok'dan video yuklab olish yoki faylni boshqa formatga o'girish kerakmi? Bu endi pastdagi boshqa botlarimizda.\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — /donate orqali to'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO'LMAYDI.\n\n",
        "whomade_usage": "Qanday ishlatiladi: /whomade <to'plam nomi yoki t.me/addstickers havolasi>",
        "whomade_not_found": (
            "Bu to'plam haqida ma'lumotim yo'q — u shu bot orqali yaratilmagan "
            "yoki nom/havola noto'g'ri."
        ),
        "whomade_result": '📦 "{title}"\n{date} kuni {creator} tomonidan shu bot orqali yaratilgan.',
        "coedit_link_invalid": "Bu havola yaroqsiz — ehtimol, to'plam egasi uni yangilagan.",
        "coedit_pack_gone": "Bu to'plam o'chirilganga o'xshaydi.",
        "coedit_own_pack": "Bu o'zingizning to'plamingiz — uni /mypacks orqali boshqaring.",
        "coedit_joined_intro": "Endi siz “{title}” to'plamining hammuallifisiz. Qo'shish uchun rasm, GIF, video yoki stiker yuboring.",
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
        "session_lost": "Uzoq tanaffusdan keyin to'plam bilan ishlash yopildi. Qaytadan boshlang: /newpack yoki /addsticker.",
        "held_full": "To'plam uchun {n} tasini allaqachon saqlab turibman — avval ular uchun to'plam tanlang, keyin buni qayta yuboring.",
        "held_already_in_pack": "Bu stiker “{title}” to'plamida allaqachon bor — o'zgarishsiz qoldirildi.",
        "btn_kb_edit": "✏️ Tahrirlash: {title}",
        "btn_kb_view": "👁 Ko'rish: {title}",
        "pack_view": "👁 “{title}”",
        "item_added": "✅ “{title}” to'plamiga {emoji} bilan qo'shildi. Emojini o'zgartirish uchun bu xabarga emoji bilan javob bering.",
        "item_added_video": "✅ “{title}” to'plamiga video stiker sifatida {emoji} bilan qo'shildi. Emojini o'zgartirish uchun bu xabarga emoji bilan javob bering.",
        "item_added_fit": "✅ “{title}” to'plamiga ({how}) {emoji} bilan qo'shildi. Emojini o'zgartirish uchun bu xabarga emoji bilan javob bering.",
        "retag_unknown": "Bu xabar qaysi stiker uchun ekanini endi bilmayman.",
        "packs_keyboard_note": "📦 To'plamlaringiz pastdagi tugmalarda — stiker qo'shish uchun birini bosing.",
        "pack_button_gone": "Bu to'plamni topa olmadim — o'chirilgan bo'lishi mumkin. Mana to'plamlaringiz hozirgi holida.",
        "held_offer": "{n} ta narsa qaysi to'plamga qo'shilsin? Ular {minutes} daqiqa kutadi.",
        "btn_held_discard": "✖️ Qo'shmaslik",
        "held_expired": "Bu juda uzoq kutdi — qayta yuboring.",
        "held_discarded": "Qo'shilmadi.",
        "video_too_long": "Bu klip {seconds} soniya; video stiker ko'pi bilan {limit} soniya bo'ladi. Tezlikni tanlang yoki uni o'zingiz {limit} soniyaga qisqartirib, qayta yuboring.",
        "video_too_long_no_speed": "Bu klip {seconds} soniya; video stiker ko'pi bilan {limit} soniya bo'ladi, sig'ishi uchun {speed}× dan ortiq tezlashtirish kerak. Uni {limit} soniyaga (yoki {longest} soniyaga, keyin tezlashtirib) qisqartiring va qayta yuboring.",
        "video_too_heavy": "Bu klip video stiker uchun Telegramning {kb} KB chegarasiga sig'madi. Yengilroq qiling:",
        "video_too_heavy_last": "Shunda ham Telegramning {kb} KB chegarasiga sig'madi. Qisqaroq qilib qayta yuboring.",
        "btn_speed_fit": "⏩ {speed}× — aynan sig'adi",
        "btn_speed": "⏩ {speed}×",
        "btn_lower_res": "🔽 Pastroq sifat (tavsiya etiladi)",
        "btn_lower_fps": "🎞 Kamroq kadr ({fps} fps)",
        "btn_skip_clip": "✖️ Bu klipni o'tkazib yuborish",
        "video_fit_expired": "Bu tanlov eskirgan — klipni qayta yuboring.",
        "video_fit_skipped": "O'tkazib yuborildi — bu klip qo'shilmadi.",
        "video_fit_added": "✅ Qo'shildi ({how}).",
        "fit_lower_res": "pastroq sifat",
        "fit_lower_fps": "{fps} fps",
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
        "editing_intro_new": "Qo'shish uchun rasm, GIF, video yoki stiker yuboring.",
        "no_packs_for_add": "Hali to'plamingiz yo'q. Avval /newpack yuboring.",
        "pick_pack_prompt": "Qaysi to'plam? Uni bosing, keyin \"➕ Stiker qo'shish\"ni tanlang.",
        "editing_intro_add": "Qo'shish uchun rasm, GIF, video yoki stiker yuboring.",
        "status_verb_creating": "Yaratilmoqda",
        "status_verb_editing": "Tahrirlanmoqda",
        "status_line": "✏️ “{title}” — {verb}",
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
        "batch_not_added": "⚠️ {done}/{total} — {failed} tasi qo'shilmadi",
        "last_attempt_failed": "⚠️ Qo'shilmadi — qayta urinish uchun yana yuboring.",
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
        "import_summary_tail": ".",
        "done_standalone_hint": "Yakunlaydigan narsa yo'q — stikerlar yuborishingiz bilan qo'shiladi. Qo'shish uchun pastdagi to'plamning ✏️ tugmasini bosing.",
        "import_standalone_hint": (
            "Avval to'plamni boshlang yoki oching (/newpack, yoki /mypacks dan biror "
            "to'plamda \"Stiker qo'shish\"ni bosing), so'ng o'sha seans ichida "
            "/import <havola> dan foydalaning."
        ),
        "whatsapp_reading": "WhatsApp stiker to'plami o'qilmoqda...",
        "whatsapp_summary_head": "WhatsApp to'plamidan {added} ta stiker import qilindi",
        "not_emoji_message": "Qo'shish uchun rasm, GIF, video yoki stiker yuboring. Stiker emojisini o'zgartirish uchun uning ✅ xabariga emoji bilan javob bering.",
        "no_sticker_to_tag": "Stiker emojisini o'zgartirish uchun uning ✅ xabariga emoji bilan javob bering.",
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
        "gift_granted": "🎁 Bizda 100 dan ortiq foydalanuvchi bo'ldi, rahmat! Sizga {amount} ⚡ bepul kredit berildi, u {date} gacha amal qiladi. Bu {convert} orqali taxminan {conversions} ta pullik konvertatsiya yoki {download} orqali katta fayllarni yuklab olish uchun yetadi. Balansingiz: /balance",
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
        "flood_wait": "Вы отправляете быстрее, чем я успеваю — подождите примерно {seconds} секунд(ы) и продолжайте.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотрите ниже \U0001f447",
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
        "report_button": '🐞 Отправить подробности',
        "problem_logged_note": 'Анонимный технический отчёт сохранён.',
        "problem_logged_note_optin": 'Анонимный технический отчёт сохранён. По желанию можно отправить подробности.',
        "report_disclaimer": "📨 Отправить подробности к случаю {incident}?\n\nУже сохранено, без ничего о вас: бот, код {code}, время, версия.\n\n«Отправить» добавит:\n• ваш Telegram ID\n• ваш @username, если есть\n• ваш язык\n• личный чат или группа\n\nВаши сообщения и файлы — никогда. Стирается через 30 дней или сразу через /deletemydata.",
        "report_send": '📨 Отправить',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — добавлено к случаю {incident}.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено.',
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
            "Пришлите картинку, GIF или видео — бот соберёт из этого стикерпак, который принадлежит "
            "вам.\n"
            "\n"
            "Дайте ссылку, чтобы паком мог пополнять кто-то ещё, или перенесите стикеры из другого "
            "пака Telegram либо из архива WhatsApp.\n"
            "\n"
            "Английский, узбекский и русский. /privacy — что бот о вас хранит."
        ),

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": (
            "• ваш числовой id в Telegram и выбранный язык\n"
            "• паки, которые вы здесь собрали: имя и название каждого, а также имя и username, "
            "которые были у вас в тот момент\n"
            "• кому вы дали доступ на добавление в пак и какие ссылки создали\n"
            "• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли "
            "ботом хоть кто-нибудь\n"
            "• сколько раз нажимают каждую кнопку — общий счёт за день по всему боту, без сведений о том, кто нажимал\n• сколько всего сделано — ссылки по сайтам, конвертации, стикеры, пересланные сообщения — общий счёт за день по всему боту, без сведений о том, кто\n"
            "• запись о пожертвовании: сумму и платёжный id Telegram\n"
            "• то, что бот в этот момент для вас делает — пока не закончит"
        ),
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nПод сбоем, неудавшимся /deletemydata или /feedback, или ошибкой, которая повторяется у вас снова и снова, кнопка «Отправить подробности» предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
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
        "privacy_kept_for": 'Настройки и всё, что бот держит для вас, остаются, пока вы их не сотрёте или не перестанете пользоваться ботом. Отметки об использовании удаляются примерно через три месяца, а дневные счётчики сделанного — в них нет ничего о том, кто, — через 400 дней. Записи о платежах и баланс ⚡ хранятся дольше — по ним разбираются споры о платежах.\n\nНичего из этого не продаётся, не сдаётся в аренду и не используется для рекламы, и никому кроме перечисленных выше не передаётся.',
        "privacy_your_choices": (
            "Что можно сделать:\n"
            "/deletemydata — стереть всё, что бот хранит о вас\n"
            "/terms — для чего ботом можно пользоваться\n"
            "\n"
            "Блокировка бота в Telegram остановит его сообщения, но ничего не сотрёт — если "
            "нужно и то и другое, сначала отправьте /deletemydata."
        ),
        "terms_heading": "📜 Условия",
        "terms_use": (
            "Пользуйтесь ботом по назначению, в рамках закона и правил самого Telegram. Не "
            "используйте его, чтобы кого-то донимать, и не нагружайте сверх заданных лимитов — за то "
            "и другое аккаунт блокируется."
        ),
        "terms_specific": (
            "О стикерах: загружайте то, что можете загружать. Не собирайте паки из чужих работ без "
            "разрешения и не делайте паков из того, что запрещено правилами самого Telegram. "
            "Созданный пак живёт в Telegram — бот может о нём забыть, но удалить его может "
            "только владелец и только через Telegram."
        ),
        "terms_money": 'О деньгах: /donate — дело добровольное, деньги идут на то, во что обходятся боты. Платёж в Stars ещё и добавляет ⚡ кредит на конвертации в ConvertBot: 2 ⚡ за ⭐, а за ваши первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держите свою копию всего, что вам важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о вас. Отменить будет нельзя.",
        "delete_data_consequences": 'Бот забудет паки, которые вы через него собрали: перестанет их показывать и не сможет в них ничего добавить. Сами паки продолжат работать у всех, кто их установил — по- настоящему удалить пак можно только самому, через Telegram. Язык, ваши ссылки и чужой доступ на добавление в ваши паки тоже пропадут.\n\nЗаписи о пожертвованиях останутся, без username, потому что по ним разбираются споры о платежах. Баланс ⚡ тоже останется — он ваш, если вернётесь.',
        "delete_data_button_yes": "🗑 Стереть",
        "delete_data_button_no": "↩️ Оставить мои данные",
        "delete_data_kept": "Ничего не стёрто.",
        "delete_data_done": (
            "🗑 Готово — стёрто записей: {rows}.\n"
            "\n"
            "Отправьте /start, когда захотите; бот примет вас как нового."
        ),
        "delete_data_failed": (
            "Сейчас стереть не получилось — что-то сломалось на моей стороне. Попробуйте ещё раз "
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
        "feedback_ask": (
            "💬 Что вы хотите сказать тому, кто ведёт этих ботов? Идея, проблема, что угодно — "
            "напишите одним сообщением в ответ на это.\n"
            "\n"
            "Его прочитает только он, и ответить вам он не сможет: сообщение уходит без вашего "
            "имени и id. Остановить: /cancel"
        ),
        "feedback_placeholder": "Ваш отзыв",
        "feedback_text_only": "Сюда нужен текст — напишите отзыв словами в ответ на это сообщение или отправьте /cancel.",
        "feedback_thanks": "✅ Спасибо — отправлено. Это прочитает только тот, кто ведёт этих ботов, и ответить он не сможет: в сообщении нет ничего о том, кто вы.",
        "feedback_limit": "Через /feedback сегодня пришло уже {per_day} ваших сообщений — больше за день я не принимаю. Спасибо, напишите завтра.",
        "feedback_failed": "Отзыв не отправлен — что-то сломалось на моей стороне. Попробуйте ещё раз через несколько минут.",
        "cancel_button_feedback": "💬 Отзыв",
        "cancel_item_feedback": "отзыв, который я просил написать",
        "help_brief": "Как это устроено:\n\n• /newpack создаёт набор стикеров: дайте название, потом присылайте картинки, GIF, видео или стикеры — каждый добавляется сразу.\n• Кнопки под полем ввода: ✏️ — добавлять в набор, 👁 — открыть его. Чтобы сменить эмодзи стикера, ответьте эмодзи на его сообщение с ✅.\n• /mypacks — список наборов с кнопками: переименовать, поделиться, удалить. /import копирует стикеры из другого набора Telegram или из экспорта WhatsApp.\n• Идеи или проблемы: /feedback — это прочитает только тот, кто ведёт этих ботов, ответа не будет.\n\nОсновные команды: /newpack · /addsticker · /mypacks · /cancel\nВсе команды — в полном руководстве: кнопка ниже или /fullhelp.\n\n",
        "help_full_button": "📖 Полное руководство",
        "help_brief_button": "↩️ Кратко",
        "help_page_everything": "Полное руководство: /fullhelp",
        "help_page_gone": "Этой страницы справки больше нет. Отправьте /help, чтобы увидеть актуальные.",
        "helppage_newpack": "🆕 /newpack — новый набор стикеров\n\n1. Отправьте /newpack (или нажмите ➕ Новый набор), затем название набора сообщением (до {title_max} символов; длиннее — обрежу). Если Telegram не примет название, начните его с буквы.\n2. Присылайте то, что станет стикерами, по одному в сообщении: фото или картинки файлом, GIF, видео или стикеры. Набор создаётся с первым стикером — нет стикера, нет набора. На каждый добавленный я отвечаю ✅.\n3. Каждый стикер получает {emoji}. Чтобы сменить, ответьте эмодзи на его сообщение с ✅ (или на то, что вы прислали) — до {emoji_max}.\n4. И всё: завершать ничего не нужно. Кнопки наборов остаются под полем ввода; /cancel — прервать.\n\nВо что что превращается:\n• Фото, картинка файлом или обычный стикер — обычный стикер, {side} px по длинной стороне.\n• GIF, видео или видеостикер — видеостикер: {side} px, до {seconds} с, {fps} кадров в секунду, без звука, меньше {kb} КБ. Для клипа длиннее предложу ускорение (или обрежьте сами); для слишком тяжёлого — ниже разрешение или меньше кадров.\n• Анимированные стикеры (.tgs) добавить нельзя.\n• Много сразу: набор стикеров WhatsApp (.zip или .wastickers) или /import из набора Telegram.\n\nПример: /newpack, потом «Кошачьи морды», потом три фото вашей кошки, потом ответьте 😺 на одно из сообщений с ✅.",
        "helppage_addsticker": "➕ /addsticker — добавить стикеры в ваш набор\n\n1. Нажмите ✏️ у нужного набора под полем ввода (или /addsticker, нажмите набор, затем «➕ Добавить стикеры»).\n2. Присылайте фото, GIF, видео или стикеры — так же, как для нового набора. Каждый получает {emoji}; чтобы сменить, ответьте эмодзи на его сообщение с ✅.\n• Если прислать стикер, который уже есть в наборе, он из набора уберётся. Если он последний, я сначала спрошу — это удалит весь набор.\n• Прислали что-то, не открыв набор? Я подержу это 10 минут и спрошу, в какой набор добавить.\n• В списке только ваши наборы, созданные через этого бота. Ещё нет? /newpack.\n• /mypacks показывает тот же список. В меню набора его можно ещё переименовать, дать кому-то редактировать вместе с вами или удалить.\n\nПример: нажмите ✏️ у «Кошачьи морды», потом пришлите новое фото.",
        "helppage_import": (
            "📥 /import — много стикеров сразу из другого набора\n"
            "\n"
            "Работает, пока вы наполняете набор: после /newpack и названия или после «➕ Добавить стикеры».\n"
            "• /import и ссылка на открытый набор Telegram (t.me/addstickers/…) или его имя копирует его стикеры в ваш набор вместе с эмодзи. До {max} за раз.\n"
            "• Анимированные стикеры (.tgs) пропускаются, и я скажу, сколько.\n"
            "• Из WhatsApp: вместо этого пришлите файл набора .zip или .wastickers.\n"
            "• Дальше присылайте ещё.\n"
            "\n"
            "Пример: /newpack, потом «Избранное», потом /import t.me/addstickers/SomePack"
        ),
        "privacy_feedback_heading": "Если вы отправляете /feedback:",
        "privacy_feedback": (
            "Написанное уходит тому, кто ведёт этих ботов, сообщением в Telegram — вместе с "
            "названием бота и вашим языком, но без имени, username и id. Копия хранится в базе "
            "ботов 30 дней, потом удаляется. Читает его только он, и ответить на него он не может."
        ),
        "cancel_item_new_pack": "\u043d\u043e\u0432\u044b\u0439 \u043d\u0430\u0431\u043e\u0440, \u043a\u043e\u0442\u043e\u0440\u043e\u043c\u0443 \u0432\u044b \u0434\u0430\u0432\u0430\u043b\u0438 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
        "cancel_button_new_pack": "🆕 Название нового набора",
        "cancel_item_rename": "\u043f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d\u0438\u0435 \u00ab{title}\u00bb",
        "cancel_button_rename": "✏️ Переименование набора",
        "cancel_item_editing": "\u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u00ab{title}\u00bb",
        "cancel_button_editing": "📦 Редактирование набора",
        "start_intro": (
            "Здравствуйте! Я превращаю ваши изображения, GIF, видео и стикеры в наборы "
            "стикеров Telegram.\n\n"
        ),
        "help_text": 'Команды:\n/newpack - начать новый набор стикеров\n/addsticker - добавить стикеры в существующий набор\n/mypacks - показать ваши наборы\n/import <ссылка/имя набора> - (во время редактирования) массово скопировать стикеры из другого набора Telegram, или отправить файл экспорта набора стикеров WhatsApp .zip/.wastickers\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/feedback - предложить идею или сообщить о проблеме; это прочитает только тот, кто ведёт этих ботов, ответа не будет\n/whomade <ссылка/имя набора> - узнать, кто создал набор (если он был создан через этого бота)\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/balance - ваш ⚡ кредит\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n/fullhelp - это полное руководство (/help - краткое)\n/convert - конвертация файлов теперь в ConvertBot; команда подскажет, куда идти\n\nВо время редактирования набора: отправляйте изображения, GIF, видео или статические/видео-стикеры, чтобы добавить их.\nОтправьте эмодзи сразу после стикера, чтобы пометить его этим эмодзи.\n\nНажмите на набор в /mypacks, чтобы переименовать его, настроить совместное редактирование, чтобы кто-то ещё мог добавлять стикеры, или удалить его насовсем (только для владельца, дважды спрашивает перед этим).\n\nХотите скачать видео из Instagram/TikTok или сконвертировать файл в другой формат? Теперь это делают соседние боты ниже.\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
        "whomade_usage": "Использование: /whomade <имя набора или ссылка t.me/addstickers>",
        "whomade_not_found": (
            "У меня нет записи об этом наборе — либо он не был создан через этого "
            "бота, либо имя/ссылка неверны."
        ),
        "whomade_result": "📦 «{title}»\nСоздал(а) {creator} {date} (через этого бота).",
        "coedit_link_invalid": "Эта ссылка для совместного редактирования недействительна — возможно, владелец набора сбросил её.",
        "coedit_pack_gone": "Похоже, этого набора больше не существует.",
        "coedit_own_pack": "Это ваш собственный набор — используйте /mypacks, чтобы им управлять.",
        "coedit_joined_intro": "Теперь вы соавтор «{title}». Отправляйте картинки, GIF, видео или стикеры, чтобы добавить.",
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
        "session_lost": "Работа с набором закрылась после долгой паузы. Начните заново: /newpack или /addsticker.",
        "held_full": "Я уже держу {n} шт. — сначала выберите для них набор, потом пришлите это снова.",
        "held_already_in_pack": "Этот стикер уже есть в «{title}» — оставлен как есть.",
        "btn_kb_edit": "✏️ Изменить «{title}»",
        "btn_kb_view": "👁 Открыть «{title}»",
        "pack_view": "👁 «{title}»",
        "item_added": "✅ Добавлено в «{title}» с {emoji}. Ответьте на это сообщение эмодзи, чтобы сменить.",
        "item_added_video": "✅ Добавлено в «{title}» как видео-стикер с {emoji}. Ответьте на это сообщение эмодзи, чтобы сменить.",
        "item_added_fit": "✅ Добавлено в «{title}» ({how}) с {emoji}. Ответьте на это сообщение эмодзи, чтобы сменить.",
        "retag_unknown": "Я уже не знаю, к какому стикеру относилось то сообщение.",
        "packs_keyboard_note": "📦 Ваши наборы — на кнопках внизу: нажмите на набор, чтобы добавлять в него стикеры.",
        "pack_button_gone": "Не нахожу этот набор — возможно, его удалили. Вот ваши наборы сейчас.",
        "held_offer": "В какой набор добавить {n} шт.? Они ждут {minutes} мин.",
        "btn_held_discard": "✖️ Не добавлять",
        "held_expired": "Это ждало слишком долго — отправьте снова.",
        "held_discarded": "Не добавлено.",
        "video_too_long": "Этот клип длится {seconds} с; видео-стикер — не больше {limit} с. Выберите скорость или обрежьте его до {limit} с сами и пришлите снова.",
        "video_too_long_no_speed": "Этот клип длится {seconds} с; видео-стикер — не больше {limit} с, а чтобы уместить его, нужно ускорение больше {speed}×. Обрежьте его до {limit} с (или до {longest} с, а потом ускорьте) и пришлите снова.",
        "video_too_heavy": "Этот клип не помещается в {kb} КБ, которые Telegram даёт видео-стикеру. Сделайте его легче:",
        "video_too_heavy_last": "Всё равно не помещается в {kb} КБ. Обрежьте его короче и пришлите снова.",
        "btn_speed_fit": "⏩ {speed}× — ровно впритык",
        "btn_speed": "⏩ {speed}×",
        "btn_lower_res": "🔽 Ниже разрешение (рекомендуется)",
        "btn_lower_fps": "🎞 Меньше кадров ({fps} fps)",
        "btn_skip_clip": "✖️ Пропустить этот клип",
        "video_fit_expired": "Этот выбор устарел — пришлите клип снова.",
        "video_fit_skipped": "Пропущено — этот клип не добавлен.",
        "video_fit_added": "✅ Добавлено ({how}).",
        "fit_lower_res": "ниже разрешение",
        "fit_lower_fps": "{fps} fps",
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
        "editing_intro_new": "Отправляйте картинки, GIF, видео или стикеры, чтобы добавить.",
        "no_packs_for_add": "У вас пока нет наборов. Сначала используйте /newpack.",
        "pick_pack_prompt": "Какой набор? Нажмите на него, затем «➕ Добавить стикеры».",
        "editing_intro_add": "Отправляйте картинки, GIF, видео или стикеры, чтобы добавить.",
        "status_verb_creating": "Создание",
        "status_verb_editing": "Редактирование",
        "status_line": "✏️ {verb} «{title}»",
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
        "batch_not_added": "⚠️ {done}/{total} — не добавлено: {failed}",
        "last_attempt_failed": "⚠️ Не добавлено — отправьте ещё раз, чтобы повторить.",
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
        "import_summary_tail": ".",
        "done_standalone_hint": "Завершать нечего — стикеры добавляются, как только вы их присылаете. Чтобы добавить в набор, нажмите ✏️ у него внизу.",
        "import_standalone_hint": (
            "Сначала начните или откройте набор (/newpack, или нажмите «Добавить "
            "стикеры» на наборе из /mypacks), затем используйте /import <ссылка> "
            "внутри этой сессии."
        ),
        "whatsapp_reading": "Чтение набора стикеров WhatsApp...",
        "whatsapp_summary_head": "Импортировано {added} стикер(ов) из набора WhatsApp",
        "not_emoji_message": "Отправляйте картинки, GIF, видео или стикеры, чтобы добавить. Чтобы сменить эмодзи стикера, ответьте эмодзи на его сообщение с ✅.",
        "no_sticker_to_tag": "Чтобы сменить эмодзи стикера, ответьте эмодзи на его сообщение с ✅.",
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
        "unknown_command": "Я не знаю такую команду. Отправьте /help, чтобы увидеть, что я умею.",
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
        "gift_granted": "🎁 Нас уже больше 100 — спасибо! Вам начислено {amount} ⚡ бесплатного кредита, он действует до {date}. Этого хватит примерно на {conversions} платных конвертаций в {convert} или на скачивание больших файлов в {download}. Ваш баланс: /balance",
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
        "whomade": "To'plamni kim yaratgan — stikerini yuboring",
        "cancel": "Kutayotgan amalimni to'xtatish",
        "help": "Nimalar qila olaman",
        "feedback": "Taklif yoki muammo haqida yozish",
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
        "whomade": "Кто сделал пак — пришлите его стикер",
        "cancel": "Остановить то, чего я жду",
        "help": "Что я умею",
        "feedback": "Предложить идею или сообщить о проблеме",
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
        "report_button": '🐞 Send more details',
        "problem_logged_note": "Anonymous technical report saved.",
        "problem_logged_note_optin": "Anonymous technical report saved. You can opt in to send more details.",
        "report_disclaimer": "📨 Send more details with incident {incident}?\n\nSaved already, nothing about you: the bot, code {code}, the time, the version.\n\nSend adds:\n• your Telegram ID\n• your @username, if you have one\n• your language\n• private chat or group\n\nNever your messages or files. Cleared after 30 days, or now with /deletemydata.",
        "report_send": '📨 Send',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — added to incident {incident}.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent.',
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
            "Converts pictures, raw photos, video, audio, documents, presentations, spreadsheets, subtitles and archives "
            "— about 100 formats."
        ),
        "bot_description": 'Send a file and pick what to turn it into. Pictures, raw, video, audio, documents, slides, spreadsheets, subtitles, archives — about 100 formats in, 60 out.\n\nA HEIC from an iPhone becomes a JPG. Several pictures become one PDF. A PDF becomes pictures or text. /formats has the rest.\n\nAnything under 3 MB is free. Above that it is priced by size in ⚡ credit, bought with Stars and shown before you choose. A conversion the bot fails gives its credit back.\n\nEnglish, Uzbek and Russian. /privacy says what it keeps about you.',

        "privacy_heading": "🔒 Privacy",
        "privacy_kept_heading": "What this bot keeps:",
        "privacy_stored": '• your Telegram user id, and the language you chose\n• the file you send — deleted as soon as it has been converted, or kept for up to 15 minutes after each conversion if you turn on "keep file" to convert it to more formats; anything a crash leaves behind is swept up on a timer and at startup\n• a timestamp each time you use the bot, so its owner can tell whether anyone is using it\n• how many times each button is tapped, counted per day for the whole bot, with nothing about who tapped it\n• how much was done — links per site, conversions, stickers, relayed messages — counted per day for the whole bot, with nothing about who\n• your ⚡ credit balance, and a record of every top-up, conversion charge and ⚡ returned to your balance: the amount, what it was for, and Telegram\'s payment id for anything paid\n• whatever the bot is in the middle of doing with you, until it is finished',
        "privacy_problems_heading": "When something goes wrong:",
        "privacy_problems": (
            "Every error this bot shows anybody is written down by itself: the error code, an "
            "incident number, when it happened and the bot's version. Nothing in that is about "
            "you — not your id, not your name, not what you sent. A fault nobody reports is "
            "still a fault, which is why it does not wait to be asked.\n"
            "\n"
            "Under a crash, a failed /deletemydata or /feedback, or an error that keeps "
            "happening to you, \"Send more details\" offers to attach four things to that one "
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
        "privacy_kept_for": 'Settings and anything the bot is holding for you stay until you erase them or stop using it. Counted use is dropped after about three months; the daily counts of what was done, which say nothing about who, after 400 days. Payment records and your ⚡ balance are kept longer, because a dispute about a payment is settled against them.\n\nNothing here is sold, rented or used for advertising, and nothing goes to anyone not named above.',
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
        "feedback_ask": (
            "💬 What would you like to tell the person who runs these bots? A suggestion, a "
            "problem, anything — write it in one message, as a reply to this one.\n"
            "\n"
            "Only they read it, and they can't write back: it is sent without your name or id. "
            "/cancel to stop."
        ),
        "feedback_placeholder": "Your feedback",
        "feedback_text_only": "That one has to be in words — write your feedback as a text reply to this message, or send /cancel.",
        "feedback_thanks": "✅ Thank you — sent. Only the person who runs these bots reads it, and they can't reply: nothing in it says who you are.",
        "feedback_limit": "You've sent {per_day} messages with /feedback today, which is as many as I take in a day. Thank you — write again tomorrow.",
        "feedback_failed": "Your feedback wasn't sent — something went wrong on my side. Please try again in a few minutes.",
        "cancel_button_feedback": "💬 Feedback",
        "cancel_item_feedback": "the feedback I asked you for",
        "help_brief": (
            "How it works:\n"
            "\n"
            "• Send me a file — a picture, camera raw photo, video, audio, document, presentation, spreadsheet, subtitles or archive — and choose what it should become. /formats lists everything.\n"
            "• 📝 Text from a photo or a scanned PDF: send it and choose TXT or Searchable PDF.\n"
            "• A conversion costs ⚡ credit, and its price is shown before anything is taken. /recharge tops it up; /balance shows what you have and where it went.\n"
            "• Ideas or problems: /feedback — only the person who runs these bots reads it, and they can't reply.\n"
            "\n"
            "Main commands: /convert · /formats · /balance · /recharge · /cancel\n"
            "Every command, and the prices: the full guide, below or /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 Full guide",
        "help_brief_button": "↩️ Short version",
        "help_page_everything": "The full guide: /fullhelp",
        "help_page_gone": "That help page no longer exists. Send /help to see the current ones.",
        "price_free_upto": "0–{mb} MB: ",
        "price_over": "over {mb} MB: ",
        "helppage_convert": (
            "🔄 /convert — turning a file into another format\n"
            "\n"
            "1. Send me the file — or send /convert first, then the file. Up to {max_mb} MB.\n"
            "2. I list the formats it can become. Tap one; \"⋯ More formats\" shows the rest.\n"
            "3. A free conversion starts at once. Otherwise you first see the price, and only \"✅ Convert\" starts it — nothing is taken before that.\n"
            "\n"
            "Price in ⚡ credit:\n"
            "{pricing}\n"
            "\n"
            "• Free: the file you send and the file you get back come to less than {free_mb} MB together.\n"
            "• The ⚡ is taken when the conversion starts, not while it waits its turn. If I fail it (I refuse the file, it runs out of time, or the result can't be sent), the ⚡ goes back to your balance. If you stop it yourself, it doesn't.\n"
            "• The price screen says how big the result may be. If it comes out bigger, it isn't sent, and the ⚡ goes back.\n"
            "• An album of pictures gets one menu for all of them (up to {batch} files). PDF puts one picture on each page; the other formats come back as a ZIP.\n"
            "• 📝 Text from a photo or a scanned PDF: choose TXT (just the text) or Searchable PDF (the same pages, with text you can select and search). For a picture, both are under \"⋯ More formats\". A Searchable PDF can be made from up to {ocr_pages} scanned pages. \"🔤 Text language\" switches between English, Russian and Uzbek. Up to {ocr_free_pages} page(s), with the files under {free_mb} MB, reading the text is free.\n"
            "• \"📌 Keep file for more formats\" keeps your file {minutes} minutes after each conversion, so you can convert it again without sending it again. It is off at first: the file is deleted straight after.\n"
            "• I wait {minutes} minutes for you to choose a format.\n"
            "\n"
            "Example: send report.docx and tap PDF. A small document converts at once, for free. A bigger one first shows its price — {least} ⚡ or more — and \"✅ Convert\" starts it."
        ),
        "helppage_recharge": (
            "⭐ /recharge — topping up ⚡ credit\n"
            "\n"
            "Conversions are paid in ⚡ credit, and ⚡ is bought with Telegram Stars (⭐).\n"
            "1. Send /recharge and tap an amount ({options} ⭐), or \"✏️ Custom ⭐\" for your own. Or straight away: /recharge 200.\n"
            "2. Telegram asks you to pay. The ⚡ is on your balance as soon as the payment arrives.\n"
            "\n"
            "What one ⭐ buys depends on how many Stars you have paid in all, ever, in any of our bots:\n"
            "{ladder}\n"
            "{bonus_rule}\n"
            "• Bonus credit is spent first, the soonest-to-expire first, so only bonus you haven't used can run out. /balance shows how much of yours is bonus, and when it runs out.\n"
            "• Payments are final: Stars are not refunded, and ⚡ can't be withdrawn or turned back into Stars.\n"
            "• /donate is the same command.\n"
            "\n"
            "{example}"
        ),
        "helppage_recharge_step_first": "  • your first {stars} ⭐: {each} ⚡ each{split}",
        "helppage_recharge_step_next": "  • the next {stars} ⭐: {each} ⚡ each{split}",
        "helppage_recharge_step_after": "  • after that: {rate} ⚡ each",
        "helppage_recharge_flat": "  • {rate} ⚡ for every ⭐",
        "helppage_recharge_bonus_part": " ({rate} + {bonus} bonus)",
        "helppage_recharge_bonus_rule": "The {rate} ⚡ per ⭐ never expire. The bonus expires {days} days after the payment.",
        "helppage_recharge_example": "Example: a first payment of {stars} ⭐ gives {total} ⚡: {base} ⚡ that never expire, and {bonus} ⚡ bonus.",
        "helppage_recharge_example_flat": "Example: {stars} ⭐ give {total} ⚡.",
        "helppage_balance": (
            "⚡ /balance — your credit, and where it went\n"
            "\n"
            "/balance shows:\n"
            "• your balance, and in all: the Stars you paid, the ⚡ they gave, the ⚡ you spent;\n"
            "• how much of the balance is bonus, how much of that runs out first, and on which day;\n"
            "• what your next Stars would buy;\n"
            "• your last {rows} movements, each with its date and one word:\n"
            "  topup — ⚡ for Stars you paid\n"
            "  bonus — the extra ⚡ a top-up gave; it expires {days} days after the payment\n"
            "  grant — ⚡ given to you: a gift (bonus that expires at the end of the day it names) or credit added by the person who runs these bots (it doesn't expire)\n"
            "  spend — a conversion\n"
            "  returned — a conversion's ⚡ back, because I failed it\n"
            "  adjustment — a correction by the person who runs these bots\n"
            "  expired — bonus that ran out unused\n"
            "• Bonus is spent before the rest, the soonest-to-expire first.\n"
            "• One wallet: the same balance in all our bots.\n"
            "\n"
            "{example}"
        ),
        "helppage_balance_example": "Example: after a first payment of {stars} ⭐ you would see \"+{base} ⚡ topup\" and \"+{bonus} ⚡ bonus\".",
        "helppage_balance_example_one": "Example: after a first payment of {stars} ⭐ you would see \"+{total} ⚡ topup\".",
        "privacy_feedback_heading": "If you send /feedback:",
        "privacy_feedback": (
            "What you write reaches the person who runs these bots as a Telegram message, with "
            "which bot it came from and your language — not your name, your username or your id. "
            "Only they read it, and they cannot reply to it. A copy is kept in the bots' "
            "database for 30 days and then deleted."
        ),
        "cancel_item_conversion": "the .{ext} file you were converting",
        "cancel_button_conversion": "🔄 The file waiting to convert",

        "start_greeting": "Hey! Send me a file and I'll convert it to another format.\n\n",
        "help_text": "Send me a file and I'll convert it to another format — pictures, camera raw photos, video, audio, documents, presentations, spreadsheets, subtitles and archives.\n\nCommands:\n/convert - start a conversion (or just send a file directly)\n/formats - every format I read and write\n/balance (or /mystars) - your ⚡ credit and what it was spent on\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/feedback - suggest something or report a problem; only whoever runs these bots reads it, and they cannot reply\n/recharge (or /donate) - top up your ⚡ credit\n/en, /uz, /rus - switch language (or /language, which asks)\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n/fullhelp - this full guide (/help - the short one)\n\nPrice in ⚡ credit:\n{pricing}\n\n⚠️ NOTE: Payments are final — Stars are NOT refunded, and ⚡ credit can NOT be withdrawn. A conversion's ⚡ is taken when it STARTS, and goes back to your balance only if the bot fails it.\n\n",
        "convert_start_prompt": (
            "Send me a file to convert, up to {max_mb} MB — a picture, a video, a "
            "sound, a document, a presentation, a spreadsheet or a subtitle file. Send several "
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
        "gift_granted": "🎁 We have passed 100 users, thank you! You get {amount} ⚡ of free credit, good until {date}. It pays for about {conversions} paid conversions in {convert} or big-file downloads in {download}. Your balance: /balance",
        "gift_claimed": "🎁 Gift received: {amount} ⚡ of free credit! Mumu bots have passed {users} users, and this is our thank-you.\nIt is good until {date} (UTC) and pays for about {conversions} paid conversions in {convert} or big-file downloads in {download}.\nYour balance: /balance",
        "download_failed": "Couldn't download that file: {error}\n\nThat's usually a hiccup on the way — please send the file again.",
        "unsupported_format": "\".{ext}\" isn't a format I convert — /formats lists the ones I do.",
        "not_for_this_file": "That one isn't available for this file (an album, or a PDF with no scanned page).",
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
        "raw_too_big": "That raw photo is {mp} megapixels. This server converts camera raw photos up to {max}: past that even the half-size decode needs more memory than it has. Nothing was charged.",
        "raw_half_note": "⚠️ NOTE: this raw photo is {mp} MP. It is converted at half size ({out} MP): the full picture needs more memory than this server has.",
        "video_fit_hdr_note": "⚠️ NOTE: this video is {w}×{h} HDR. This server converts it at {fw}×{fh} — the full picture needs more memory than it has. The colours are kept.",
        "video_fit_big_note": "⚠️ NOTE: this video is {w}×{h}. WEBM is made at {fw}×{fh} here; MP4, MKV and MOV keep the full size.",
        "video_fit_huge_note": "⚠️ NOTE: this video is {w}×{h}. This server converts it at {fw}×{fh} — the full picture needs more memory than it has.",
        "nothing_sendable": 'Every format I could offer would come out over the {limit} MB a bot can send for a picture this size. Nothing was charged.',
        "too_big_to_send_alert": 'That format would come out over the {limit} MB a bot can send for this picture.',
        "keep_toggle_off": '📌 Keep file for more formats: off',
        "keep_toggle_on": '📌 Keep file for more formats: on',
        "ocr_lang_toggle": "🔤 Text language: {name} (tap to change)",
        "ocr_lang_set": "Text language is now {name}.",
        "ocr_lang_eng": "English",
        "ocr_lang_rus": "Russian",
        "ocr_lang_uzb": "Uzbek (Latin and Cyrillic)",
        "ocr_too_many_pages_note": "⚠️ NOTE: more than {max} pages of this PDF are pictures without text. Text is recognised on at most {max} such pages here, so TXT gives only the text the other pages already have, and a searchable PDF is not offered.",
        "target_ocrpdf": "Searchable PDF",
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
        "job_reason_timeout": 'That conversion ran past its {minutes}-minute limit, so I stopped it.',
        "job_reason_too_slow": "This one would take about {minutes} minutes to convert, and a conversion here can run for {limit}, so I stopped it now rather than make you wait for the limit. A shorter clip, or a lower resolution, will fit.",
        "job_reason_crash": 'The conversion failed on my side. You can try again — send the file once more.',
        "job_reason_no_memory": "This one needs more memory to convert than this server has — that happens with 4K and HDR video. Your file is fine: a version at 1080p or lower will convert.",
        "job_reason_too_large": 'The {target} came out at {mb} MB, more than the {limit} MB I can send back for this conversion — JPG, WEBP or AVIF will be far smaller.',
        "job_reason_send_failed": 'The file converted, but sending it to you failed. You can try again — send the file once more.',
        "job_reason_interrupted": 'I was restarted in the middle of that conversion. Send it again in a minute.',
        "unknown_order": "Unknown order.",
        "unrecognized_message": (
            "That's not a file I can convert — send me one, or /formats to see what "
            "I take. Name a format (\"heic\", \"epub\") and I'll tell you what it "
            "becomes."
        ),
        "unknown_command": "I don't recognize that command. Send /start to see what I can do.",

        "category_document": "document",
        "category_presentation": "presentation",
        "category_data": "data",
        "category_subtitle": "subtitle",
        "category_archive": "archive",
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
            "• PowerPoint: PPT ↔ PPTX ↔ PDF, a PDF as editable slides, or the slides as pictures\n"
            "• Word: DOC ↔ DOCX ↔ ODT ↔ PDF, or HTML and Markdown\n"
            "• Excel: XLS ↔ XLSX ↔ ODS, or CSV, JSON and PDF\n"
            "• CSV, JSON or XML → an XLSX spreadsheet\n"
            "• Camera raw (CR3, NEF, ARW, DNG…) → JPG, PNG or a 16-bit TIFF\n"
            "• A RAR or 7z your phone cannot open → ZIP\n"
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
        "report_button": "🐞 Qo'shimcha ma'lumot yuborish",
        "problem_logged_note": "Anonim texnik hisobot saqlandi.",
        "problem_logged_note_optin": "Anonim texnik hisobot saqlandi. Xohlasangiz, qo'shimcha ma'lumot yuborishingiz mumkin.",
        "report_disclaimer": "📨 {incident} hodisasiga qo'shimcha ma'lumot yuborasizmi?\n\nAllaqachon saqlangan, siz haqingizda hech narsa yo'q: bot, {code} kodi, vaqt, versiya.\n\n\"Yuborish\" qo'shadi:\n• Telegram ID raqamingiz\n• bo'lsa, @username'ingiz\n• tilingiz\n• shaxsiy suhbatmi yoki guruh\n\nXabarlaringiz va fayllaringiz hech qachon kirmaydi. 30 kundan keyin o'chiriladi, /deletemydata bilan esa darhol.",
        "report_send": '📨 Yuborish',
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — {incident} hodisasiga qo'shildi.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi.",
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
            "Rasm, kamera raw, video, audio, hujjat, taqdimot, jadval, subtitr va arxivlarni 100 ga yaqin format "
            "orasida o'giradi."
        ),
        "bot_description": "Fayl yuboring va qaysi formatga o'girishni tanlang. Rasm, kamera raw, video, audio, hujjat, taqdimot, jadval, subtitr, arxiv — 100 ga yaqin formatdan 60 ga yaqin formatga.\n\niPhone'dagi HEIC rasm — JPG ga. Bir nechta rasm — bitta PDF ga. PDF — rasm yoki matnga. Hammasi: /formats\n\n3 MB gacha bepul. Kattaroq fayl hajmiga qarab Stars bilan sotib olinadigan ⚡ kreditda to'lanadi, narx oldindan ko'rsatiladi. Bot xato qilsa, ⚡ balansga qaytadi.\n\nIngliz, o'zbek va rus tillarida. Nima saqlanishi: /privacy",

        "privacy_heading": "🔒 Maxfiylik",
        "privacy_kept_heading": "Bu bot nimalarni saqlaydi:",
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• yuborgan faylingiz — o'girilishi bilanoq o'chiriladi; «faylni saqlash» yoqilgan bo'lsa, boshqa formatlarga ham o'girish uchun har konvertatsiyadan keyin 15 daqiqagacha saqlanadi; nosozlikdan keyin qolib ketgan fayllar muntazam va bot ishga tushganda tozalanadi\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• har bir tugma necha marta bosilgani — butun bot bo'yicha kunlik umumiy hisob, kim bosgani haqida hech qanday ma'lumotsiz\n• qancha ish qilingani — sayt bo'yicha havolalar, konvertatsiyalar, stikerlar, yuborilgan xabarlar — butun bot bo'yicha kunlik hisob, kim ekani haqida ma'lumotsiz\n• ⚡ kredit balansingiz va har bir to'ldirish, konvertatsiya uchun yechilgan hamda balansga qaytgan ⚡ yozuvi: miqdori, nima uchunligi va pullik to'lovlarda Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nIshdan chiqish, bajarilmagan /deletemydata yoki /feedback, yoki sizda takror-takror yuz berayotgan xato ostidagi \"Qo'shimcha ma'lumot yuborish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• boshqa hech kim — fayllar botning o'z serverida o'giriladi va hech qanday tashqi xizmatga yuborilmaydi",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi; qancha ish qilinganining kunlik hisobi esa — unda kimligi yo'q — 400 kundan keyin. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
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
        "feedback_ask": (
            "💬 Bu botlarni yuritayotgan odamga nima demoqchisiz? Taklif, muammo — nima bo'lsa "
            "ham, bitta xabarda, shu xabarga javob qilib yozing.\n"
            "\n"
            "Uni faqat o'sha odam o'qiydi va sizga javob yoza olmaydi: xabar ismingiz va ID "
            "raqamingizsiz yuboriladi. To'xtatish: /cancel"
        ),
        "feedback_placeholder": "Fikringiz",
        "feedback_text_only": "Bu yerga faqat matn qabul qilinadi — fikringizni shu xabarga javob qilib so'z bilan yozing yoki /cancel yuboring.",
        "feedback_thanks": "✅ Rahmat — yuborildi. Uni faqat bu botlarni yuritayotgan odam o'qiydi va javob yoza olmaydi: xabarda kimligingiz ko'rsatilmagan.",
        "feedback_limit": "Bugun /feedback orqali {per_day} ta xabar yubordingiz — bir kunda shuncha qabul qilaman. Rahmat, ertaga yana yozishingiz mumkin.",
        "feedback_failed": "Fikringiz yuborilmadi — bot tomonida nimadir buzildi. Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring.",
        "cancel_button_feedback": "💬 Fikr-mulohaza",
        "cancel_item_feedback": "men so'ragan fikr-mulohaza",
        "help_brief": (
            "Bot qanday ishlaydi:\n"
            "\n"
            "• Menga fayl yuboring — rasm, kamera raw, video, audio, hujjat, taqdimot, jadval, subtitr yoki arxiv — va u nimaga aylanishini tanlang. Barcha formatlar: /formats\n"
            "• 📝 Rasm yoki skanerlangan PDF dagi matn: faylni yuboring va TXT yoki Matnli PDF ni tanlang.\n"
            "• Har bir konvertatsiya ⚡ kredit turadi, narxi esa hech narsa yechilishidan oldin ko'rsatiladi. Kreditni /recharge bilan to'ldirasiz; /balance qancha qolgani va nimaga sarflanganini ko'rsatadi.\n"
            "• Taklif yoki muammo: /feedback — uni faqat bu botlarni yuritayotgan odam o'qiydi, javob qaytmaydi.\n"
            "\n"
            "Asosiy buyruqlar: /convert · /formats · /balance · /recharge · /cancel\n"
            "Barcha buyruqlar va narxlar: to'liq qo'llanmada — pastdagi tugma yoki /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 To'liq qo'llanma",
        "help_brief_button": "↩️ Qisqa variant",
        "help_page_everything": "To'liq qo'llanma: /fullhelp",
        "help_page_gone": "Bu yordam sahifasi endi yo'q. Hozirgilarini ko'rish uchun /help yuboring.",
        "price_free_upto": "0–{mb} MB: ",
        "price_over": "{mb} MB dan ortiq: ",
        "helppage_convert": (
            "🔄 /convert — faylni boshqa formatga o'girish\n"
            "\n"
            "1. Faylni yuboring — yoki avval /convert, keyin faylni. {max_mb} MB gacha.\n"
            "2. Uni qaysi formatlarga o'girish mumkinligini ko'rsataman. Birini bosing; \"⋯ Yana formatlar\" qolganlarini ochadi.\n"
            "3. Bepul konvertatsiya darhol boshlanadi. Aks holda avval narxini ko'rasiz va uni faqat \"✅ O'girish\" tugmasi boshlaydi — undan oldin hech narsa yechilmaydi.\n"
            "\n"
            "⚡ kreditdagi narx:\n"
            "{pricing}\n"
            "\n"
            "• Bepul: yuborgan faylingiz va qaytadigan fayl birgalikda {free_mb} MB dan kichik bo'lsa.\n"
            "• ⚡ navbat kutayotganda emas, konvertatsiya boshlanganda yechiladi. Agar uni bajara olmasam (faylni rad etsam, vaqt yetmasa yoki natijani yuborib bo'lmasa), ⚡ balansingizga qaytadi. O'zingiz to'xtatsangiz, qaytmaydi.\n"
            "• Narx ekrani natija qanchalik katta bo'lishi mumkinligini aytadi. Undan katta chiqsa, yuborilmaydi va ⚡ qaytadi.\n"
            "• Rasmlar albomi uchun hammasiga bitta menyu chiqadi ({batch} tagacha fayl). PDF har bir rasmni alohida sahifaga qo'yadi; boshqa formatlar ZIP bo'lib keladi.\n"
            "• 📝 Rasm yoki skanerlangan PDF'dan matn: TXT (faqat matn) yoki Matnli PDF (o'sha sahifalar, matnini belgilash va qidirish mumkin) ni tanlang. Rasm uchun ikkalasi ham \"⋯ Yana formatlar\" ichida. Matnli PDF {ocr_pages} tagacha skanerlangan sahifadan yasaladi. \"🔤 Matn tili\" inglizcha, ruscha va o'zbekcha orasida almashtiradi. {ocr_free_pages} sahifagacha va fayllar {free_mb} MB dan kichik bo'lsa, matnni o'qish bepul.\n"
            "• \"📌 Faylni boshqa formatlar uchun saqlash\" faylingizni har bir konvertatsiyadan keyin {minutes} daqiqa saqlaydi — qayta yubormasdan yana o'girishingiz mumkin. Dastlab o'chiq: fayl darhol o'chiriladi.\n"
            "• Format tanlashingizni {minutes} daqiqa kutaman.\n"
            "\n"
            "Misol: hisobot.docx ni yuboring va PDF ni bosing. Kichik hujjat darhol va bepul o'giriladi. Kattarog'i avval narxini ko'rsatadi — {least} ⚡ yoki ko'proq — va uni \"✅ O'girish\" boshlaydi."
        ),
        "helppage_recharge": (
            "⭐ /recharge — ⚡ kreditni to'ldirish\n"
            "\n"
            "Konvertatsiyalar ⚡ kredit bilan to'lanadi, ⚡ esa Telegram Stars (⭐) bilan sotib olinadi.\n"
            "1. /recharge yuboring va miqdorni bosing ({options} ⭐) yoki o'z miqdoringiz uchun \"✏️ Boshqa ⭐\". Yoki to'g'ridan-to'g'ri: /recharge 200.\n"
            "2. Telegram to'lovni so'raydi. To'lov kelishi bilan ⚡ balansingizda bo'ladi.\n"
            "\n"
            "Bitta ⭐ qancha ⚡ berishi siz shu paytgacha istalgan botimizda jami qancha Stars to'laganingizga bog'liq:\n"
            "{ladder}\n"
            "{bonus_rule}\n"
            "• Avval bonus kredit sarflanadi, muddati eng tez tugaydigani birinchi, shuning uchun faqat ishlatilmagan bonus yo'qolishi mumkin. Bonusingiz qancha va qachon tugashini /balance ko'rsatadi.\n"
            "• To'lovlar qaytarilmaydi: Stars qaytarilmaydi, ⚡ ni yechib olib yoki Stars'ga aylantirib bo'lmaydi.\n"
            "• /donate — xuddi shu buyruq.\n"
            "\n"
            "{example}"
        ),
        "helppage_recharge_step_first": "  • dastlabki {stars} ⭐: har biri {each} ⚡{split}",
        "helppage_recharge_step_next": "  • keyingi {stars} ⭐: har biri {each} ⚡{split}",
        "helppage_recharge_step_after": "  • undan keyin: har biri {rate} ⚡",
        "helppage_recharge_flat": "  • har bir ⭐ uchun {rate} ⚡",
        "helppage_recharge_bonus_part": " ({rate} + {bonus} bonus)",
        "helppage_recharge_bonus_rule": "Har ⭐ uchun {rate} ⚡ hech qachon tugamaydi. Bonusning muddati to'lovdan {days} kun o'tib tugaydi.",
        "helppage_recharge_example": "Misol: birinchi marta {stars} ⭐ to'lasangiz, {total} ⚡ olasiz: muddati tugamaydigan {base} ⚡ va {bonus} ⚡ bonus.",
        "helppage_recharge_example_flat": "Misol: {stars} ⭐ — {total} ⚡.",
        "helppage_balance": (
            "⚡ /balance — kreditingiz va u qayerga ketgani\n"
            "\n"
            "/balance quyidagilarni ko'rsatadi:\n"
            "• balansingiz va jami: to'lagan Stars, ular bergan ⚡, sarflagan ⚡;\n"
            "• balansning qanchasi bonus, uning qanchasi birinchi bo'lib va qaysi kuni tugashi;\n"
            "• keyingi Stars'ingiz qancha ⚡ berishi;\n"
            "• oxirgi {rows} ta amal, har biri sanasi va bitta so'z bilan:\n"
            "  topup — to'lagan Stars'ingiz uchun ⚡\n"
            "  bonus — to'ldirish bergan qo'shimcha ⚡; to'lovdan {days} kun o'tib tugaydi\n"
            "  grant — sizga berilgan ⚡: sovg'a (ko'rsatilgan kun oxirida tugaydigan bonus) yoki botlarni yuritayotgan odam qo'shgan kredit (u tugamaydi)\n"
            "  spend — konvertatsiya\n"
            "  returned — men bajara olmagan konvertatsiyaning qaytgan ⚡ i\n"
            "  adjustment — botlarni yuritayotgan odamning tuzatishi\n"
            "  expired — ishlatilmay tugagan bonus\n"
            "• Bonus qolganidan oldin sarflanadi, muddati eng tez tugaydigani birinchi.\n"
            "• Hamyon bitta: barcha botlarimizda balans bir xil.\n"
            "\n"
            "{example}"
        ),
        "helppage_balance_example": "Misol: birinchi marta {stars} ⭐ to'lagach \"+{base} ⚡ topup\" va \"+{bonus} ⚡ bonus\" ni ko'rasiz.",
        "helppage_balance_example_one": "Misol: birinchi marta {stars} ⭐ to'lagach \"+{total} ⚡ topup\" ni ko'rasiz.",
        "privacy_feedback_heading": "/feedback yuborsangiz:",
        "privacy_feedback": (
            "Yozganingiz bu botlarni yuritayotgan odamga Telegram xabari sifatida yetib boradi — "
            "qaysi botdan kelgani va tilingiz bilan birga, lekin ismingiz, foydalanuvchi nomingiz "
            "va ID raqamingizsiz. Uni faqat o'sha odam o'qiydi va unga javob yoza olmaydi. "
            "Nusxasi botlar bazasida 30 kun saqlanadi, keyin o'chiriladi."
        ),
        "cancel_item_conversion": "o'girilishi kutilayotgan .{ext} fayli",
        "cancel_button_conversion": "🔄 Konvertatsiyani kutayotgan fayl",
        "start_greeting": "Salom! Menga faylni yuboring va men uni boshqa formatga o'giraman.\n\n",
        "help_text": "Menga fayl yuboring — uni boshqa formatga o'girib beraman: rasm, kamera raw, video, audio, hujjat, taqdimot, jadval, subtitr va arxivlar.\n\nBuyruqlar:\n/convert - konvertatsiyani boshlash (yoki shunchaki fayl yuboring)\n/formats - qo'llab-quvvatlanadigan barcha formatlar\n/balance (yoki /mystars) - ⚡ kreditingiz va u nimaga sarflangani\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/feedback - taklif yozish yoki muammo haqida xabar berish; uni faqat botlarni yuritayotgan odam o'qiydi, javob qaytmaydi\n/recharge (yoki /donate) - ⚡ kreditni to'ldirish\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/paysupport - to'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n/fullhelp - shu to'liq qo'llanma (/help - qisqasi)\n\nNarxlar ⚡ kreditda:\n{pricing}\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — to'langan Stars qaytarib berilmaydi, ⚡ kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Konvertatsiya narxi u BOSHLANGANDA yechiladi va faqat bot tomonidagi xatolik tufayli bajarilmasa, ⚡ balansingizga qaytib tushadi.\n\n",
        "convert_start_prompt": "O'girish uchun {max_mb} MB gacha fayl yuboring — rasm, kamera raw, video, audio, hujjat, taqdimot, jadval, subtitr yoki arxiv. Bir nechta rasmni birga yuborsangiz, ularni bitta PDF qilib beraman.\n\nBarcha formatlar: /formats\n\nNarxlar ⚡ kreditda:\n{pricing}\n\nBekor qilish uchun: /cancel",
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
        "gift_granted": "🎁 Bizda 100 dan ortiq foydalanuvchi bo'ldi, rahmat! Sizga {amount} ⚡ bepul kredit berildi, u {date} gacha amal qiladi. Bu {convert} orqali taxminan {conversions} ta pullik konvertatsiya yoki {download} orqali katta fayllarni yuklab olish uchun yetadi. Balansingiz: /balance",
        "gift_claimed": "🎁 Sovg'a: {amount} ⚡ bepul kredit! Mumu botlarida {users} dan ortiq foydalanuvchi bo'ldi, bu bizning minnatdorchiligimiz.\nU {date} gacha (UTC) amal qiladi va {convert} orqali taxminan {conversions} ta pullik konvertatsiya yoki {download} orqali katta fayllarni yuklab olish uchun yetadi.\nBalansingiz: /balance",
        "download_failed": "Faylni yuklab bo'lmadi: {error}\n\nBu odatda yo'ldagi vaqtinchalik uzilish — faylni qaytadan yuboring.",
        "unsupported_format": '".{ext}" formatini o\'gira olmayman. Qo\'llab-quvvatlanadigan formatlar: /formats',
        "not_for_this_file": "Bu variant bu fayl uchun mavjud emas (albom yoki skanerlangan sahifasi yo'q PDF).",
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
        "raw_too_big": "Bu raw suratning o'lchami {mp} megapiksel. Server raw suratlarni {max} megapikselgacha o'giradi: undan kattasiga yarim o'lchamda ochish uchun ham xotira yetmaydi. Balansdan hech narsa yechilmadi.",
        "raw_half_note": "⚠️ ESLATMA: bu raw surat {mp} MP. U yarim o'lchamda ({out} MP) o'giriladi: to'liq tasvir uchun serverda xotira yetmaydi.",
        "video_fit_hdr_note": "⚠️ ESLATMA: bu video {w}×{h} HDR. Server uni {fw}×{fh} o'lchamda o'giradi — to'liq tasvir uchun serverda xotira yetmaydi. Ranglar saqlanadi.",
        "video_fit_big_note": "⚠️ ESLATMA: bu video {w}×{h}. WEBM bu yerda {fw}×{fh} o'lchamda tayyorlanadi; MP4, MKV va MOV to'liq o'lchamda qoladi.",
        "video_fit_huge_note": "⚠️ ESLATMA: bu video {w}×{h}. Server uni {fw}×{fh} o'lchamda o'giradi — to'liq tasvir uchun serverda xotira yetmaydi.",
        "nothing_sendable": "Bu o'lchamdagi rasm istalgan formatda bot yubora oladigan {limit} MB dan katta chiqadi. Balansdan hech narsa yechilmadi.",
        "too_big_to_send_alert": 'Bu rasm shu formatda bot yubora oladigan {limit} MB dan katta chiqadi.',
        "keep_toggle_off": "📌 Faylni boshqa formatlar uchun saqlash: o'chirilgan",
        "keep_toggle_on": '📌 Faylni boshqa formatlar uchun saqlash: yoqilgan',
        "ocr_lang_toggle": "🔤 Matn tili: {name} (o'zgartirish uchun bosing)",
        "ocr_lang_set": "Endi matn tili: {name}.",
        "ocr_lang_eng": "inglizcha",
        "ocr_lang_rus": "ruscha",
        "ocr_lang_uzb": "o'zbekcha (lotin va kirill)",
        "ocr_too_many_pages_note": "⚠️ ESLATMA: bu PDF ning {max} tadan ortiq sahifasi matnsiz rasm. Bu yerda ko'pi bilan {max} ta shunday sahifadagi matn aniqlanadi, shuning uchun TXT faqat boshqa sahifalarda bor matnni beradi, matnli PDF esa taklif qilinmaydi.",
        "target_ocrpdf": "Matnli PDF",
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
        "job_reason_timeout": "Konvertatsiya {minutes} daqiqalik vaqt chegarasidan oshib ketgani uchun to'xtatildi.",
        "job_reason_too_slow": "Bu faylni o'girish taxminan {minutes} daqiqa olardi, bu yerda esa bitta konvertatsiya ko'pi bilan {limit} daqiqa ishlaydi. Shuning uchun chegaragacha kuttirib o'tirmay, hozir to'xtatdim. Qisqaroq video yoki pastroq sifat bemalol sig'adi.",
        "job_reason_crash": "Konvertatsiya bot tomonidagi xatolik tufayli bajarilmadi. Qayta urinib ko'rishingiz mumkin — faylni yana bir bor yuboring.",
        "job_reason_no_memory": "Bu faylni o'girishga serverning xotirasi yetmadi — 4K va HDR videolarda shunday bo'ladi. Faylingizda muammo yo'q: uning 1080p yoki undan past sifatdagi nusxasi bemalol o'giriladi.",
        "job_reason_too_large": "{target} fayli {mb} MB chiqdi, bu konvertatsiya natijasini esa faqat {limit} MB gacha yubora olaman. JPG, WEBP yoki AVIF ancha kichik bo'ladi.",
        "job_reason_send_failed": "Fayl o'girildi, lekin uni sizga yuborib bo'lmadi. Qayta urinib ko'rishingiz mumkin — faylni yana bir bor yuboring.",
        "job_reason_interrupted": 'Konvertatsiya vaqtida bot qayta ishga tushdi. Bir daqiqadan keyin faylni qaytadan yuboring.',
        "unknown_order": "Noma'lum buyurtma.",
        "unrecognized_message": 'Bu o\'girish mumkin bo\'lgan fayl emas — fayl yuboring yoki qabul qilinadigan formatlarni /formats orqali ko\'ring. Format nomini yozsangiz (masalan, "heic" yoki "epub"), uni nimaga o\'girish mumkinligini aytaman.',
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /start yuboring.",

        "category_document": "hujjat",
        "category_presentation": "taqdimot",
        "category_data": "ma'lumot",
        "category_subtitle": "subtitr",
        "category_archive": "arxiv",
        "formats_title": "📁 Qaysi formatlarni o'giraman",
        "formats_intro": "{sources} ta formatdan {targets} ta formatga — jami {pairs} xil yo'nalish. Fayl yuborsangiz, uni nimaga o'girish mumkinligini ko'rsataman; to'liq ro'yxat uchun quyidan turkumni tanlang.",
        "formats_highlights": "Ko'pchilik bilmaydigan imkoniyatlar:\n• iPhone rasmi (HEIC) → JPG yoki PNG\n• Istalgan rasm — yoki butun albom — bitta PDF\n• PDF yoki EPUB → PNG, JPG yoki oddiy matn\n• PowerPoint: PPT ↔ PPTX ↔ PDF, PDF'ni tahrirlanadigan slaydlarga yoki slaydlarni rasmlarga\n• Word: DOC ↔ DOCX ↔ ODT ↔ PDF, yoki HTML va Markdown\n• Excel: XLS ↔ XLSX ↔ ODS, yoki CSV, JSON va PDF\n• CSV, JSON yoki XML → XLSX jadval\n• Kamera raw (CR3, NEF, ARW, DNG…) → JPG, PNG yoki 16 bitli TIFF\n• Telefon ocha olmaydigan RAR yoki 7z → ZIP\n• Subtitrlar: SRT, VTT va ASS bir-biriga, yoki faqat matn",
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
        "flood_wait": "Вы отправляете быстрее, чем я успеваю — подождите примерно {seconds} секунд(ы) и продолжайте.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотрите ниже \U0001f447",
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
        "report_button": '🐞 Отправить подробности',
        "problem_logged_note": 'Анонимный технический отчёт сохранён.',
        "problem_logged_note_optin": 'Анонимный технический отчёт сохранён. По желанию можно отправить подробности.',
        "report_disclaimer": "📨 Отправить подробности к случаю {incident}?\n\nУже сохранено, без ничего о вас: бот, код {code}, время, версия.\n\n«Отправить» добавит:\n• ваш Telegram ID\n• ваш @username, если есть\n• ваш язык\n• личный чат или группа\n\nВаши сообщения и файлы — никогда. Стирается через 30 дней или сразу через /deletemydata.",
        "report_send": '📨 Отправить',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — добавлено к случаю {incident}.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено.',
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
            "Конвертирует картинки, raw-фото, видео, аудио, документы, презентации, таблицы, субтитры и архивы "
            "— около 100 форматов."
        ),
        "bot_description": 'Пришлите файл и выберите, во что его превратить. Картинки, raw-фото, видео, аудио, документы, презентации, таблицы, субтитры и архивы — около 100 форматов на вход, 60 на выход.\n\nHEIC с iPhone становится JPG. Набор картинок — одним PDF. PDF — картинками или текстом. Весь список — /formats\n\nВсё меньше 3 МБ — бесплатно. Дороже — цена по размеру файла в ⚡ кредите, купленном за Stars, и видна до выбора. Если конвертация сорвётся по вине бота, кредит вернётся.\n\nАнглийский, узбекский и русский. /privacy — что бот о вас хранит.',

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": '• ваш числовой id в Telegram и выбранный язык\n• присланный файл — удаляется сразу после конвертации, или хранится до 15 минут после каждой конвертации, если включить «хранить файл», чтобы конвертировать его и в другие форматы; всё, что осталось после сбоя, подчищается по таймеру и при запуске\n• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли ботом хоть кто-нибудь\n• сколько раз нажимают каждую кнопку — общий счёт за день по всему боту, без сведений о том, кто нажимал\n• сколько всего сделано — ссылки по сайтам, конвертации, стикеры, пересланные сообщения — общий счёт за день по всему боту, без сведений о том, кто\n• ваш баланс ⚡ кредита и запись о каждом пополнении, списании за конвертацию и возврате ⚡ на баланс: сумму, за что и платёжный id Telegram для оплаченного\n• то, что бот в этот момент для вас делает — пока не закончит',
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nПод сбоем, неудавшимся /deletemydata или /feedback, или ошибкой, которая повторяется у вас снова и снова, кнопка «Отправить подробности» предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
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
        "privacy_kept_for": 'Настройки и всё, что бот держит для вас, остаются, пока вы их не сотрёте или не перестанете пользоваться ботом. Отметки об использовании удаляются примерно через три месяца, а дневные счётчики сделанного — в них нет ничего о том, кто, — через 400 дней. Записи о платежах и баланс ⚡ хранятся дольше — по ним разбираются споры о платежах.\n\nНичего из этого не продаётся, не сдаётся в аренду и не используется для рекламы, и никому кроме перечисленных выше не передаётся.',
        "privacy_your_choices": (
            "Что можно сделать:\n"
            "/deletemydata — стереть всё, что бот хранит о вас\n"
            "/terms — для чего ботом можно пользоваться\n"
            "\n"
            "Блокировка бота в Telegram остановит его сообщения, но ничего не сотрёт — если "
            "нужно и то и другое, сначала отправьте /deletemydata."
        ),
        "terms_heading": "📜 Условия",
        "terms_use": (
            "Пользуйтесь ботом по назначению, в рамках закона и правил самого Telegram. Не "
            "используйте его, чтобы кого-то донимать, и не нагружайте сверх заданных лимитов — за то "
            "и другое аккаунт блокируется."
        ),
        "terms_specific": 'Файлы и оплата: конвертируйте то, что имеете право конвертировать. Всё меньше 3 МБ бесплатно; дороже — цена в ⚡ кредите, который покупается за Telegram Stars, и показывается до выбора формата. ⚡ списывается, когда конвертация НАЧИНАЕТСЯ. Если остановите идущую конвертацию сами, ⚡ НЕ вернётся; если сбой на стороне бота — ⚡ автоматически вернётся на баланс. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars.',
        "terms_money": 'О деньгах: /recharge покупает ⚡ кредит на конвертации: 2 ⚡ за ⭐, а за ваши первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держите свою копию всего, что вам важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о вас. Отменить будет нельзя.",
        "delete_data_consequences": 'Язык, место в напоминании о пополнении и все отметки о том, когда вы пользовались ботом, будут стёрты. Файлы тут ни при чём: то, что вы конвертировали, удалилось сразу после конвертации.\n\nОплаты останутся, без username, потому что по ним разбираются споры о платежах, — и баланс ⚡ тоже: /balance по-прежнему его покажет.',
        "delete_data_button_yes": "🗑 Стереть",
        "delete_data_button_no": "↩️ Оставить мои данные",
        "delete_data_kept": "Ничего не стёрто.",
        "delete_data_done": (
            "🗑 Готово — стёрто записей: {rows}.\n"
            "\n"
            "Отправьте /start когда захотите; бот примет вас как нового."
        ),
        "delete_data_failed": (
            "Сейчас стереть не получилось — что-то сломалось на моей стороне. Попробуйте ещё раз "
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
        "feedback_ask": (
            "💬 Что вы хотите сказать тому, кто ведёт этих ботов? Идея, проблема, что угодно — "
            "напишите одним сообщением в ответ на это.\n"
            "\n"
            "Его прочитает только он, и ответить вам он не сможет: сообщение уходит без вашего "
            "имени и id. Остановить: /cancel"
        ),
        "feedback_placeholder": "Ваш отзыв",
        "feedback_text_only": "Сюда нужен текст — напишите отзыв словами в ответ на это сообщение или отправьте /cancel.",
        "feedback_thanks": "✅ Спасибо — отправлено. Это прочитает только тот, кто ведёт этих ботов, и ответить он не сможет: в сообщении нет ничего о том, кто вы.",
        "feedback_limit": "Через /feedback сегодня пришло уже {per_day} ваших сообщений — больше за день я не принимаю. Спасибо, напишите завтра.",
        "feedback_failed": "Отзыв не отправлен — что-то сломалось на моей стороне. Попробуйте ещё раз через несколько минут.",
        "cancel_button_feedback": "💬 Отзыв",
        "cancel_item_feedback": "отзыв, который я просил написать",
        "help_brief": (
            "Как это устроено:\n"
            "\n"
            "• Пришлите файл — картинку, raw-фото, видео, аудио, документ, презентацию, таблицу, субтитры или архив — и выберите, во что его превратить. Все форматы: /formats\n"
            "• 📝 Текст с фото или скана PDF: отправьте файл и выберите TXT или PDF с текстом.\n"
            "• Конвертация стоит ⚡ кредит, и цена видна до того, как что-то списано. Пополнить — /recharge; /balance покажет остаток и на что он ушёл.\n"
            "• Идеи или проблемы: /feedback — это прочитает только тот, кто ведёт этих ботов, ответа не будет.\n"
            "\n"
            "Основные команды: /convert · /formats · /balance · /recharge · /cancel\n"
            "Все команды и цены — в полном руководстве: кнопка ниже или /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 Полное руководство",
        "help_brief_button": "↩️ Кратко",
        "help_page_everything": "Полное руководство: /fullhelp",
        "help_page_gone": "Этой страницы справки больше нет. Отправьте /help, чтобы увидеть актуальные.",
        "price_free_upto": "0–{mb} МБ: ",
        "price_over": "больше {mb} МБ: ",
        "helppage_convert": (
            "🔄 /convert — перевести файл в другой формат\n"
            "\n"
            "1. Пришлите файл — или сначала /convert, потом файл. До {max_mb} МБ.\n"
            "2. Я покажу, во что его можно перевести. Нажмите нужный формат; «⋯ Ещё форматы» покажет остальные.\n"
            "3. Бесплатная конвертация начинается сразу. Иначе вы сначала увидите цену, и запустит её только «✅ Конвертировать» — до этого ничего не списывается.\n"
            "\n"
            "Цена в ⚡ кредите:\n"
            "{pricing}\n"
            "\n"
            "• Бесплатно: присланный файл и готовый вместе меньше {free_mb} МБ.\n"
            "• ⚡ списывается, когда конвертация начинается, а не пока она ждёт очереди. Если я её не выполню (откажу, не уложусь во время или не смогу отправить результат), ⚡ вернётся на баланс. Если остановите её сами — не вернётся.\n"
            "• На экране с ценой сказано, каким большим может быть результат. Если он получится больше, его не отправят, а ⚡ вернётся.\n"
            "• На альбом картинок — одно меню на все (до {batch} файлов). PDF кладёт по картинке на страницу; остальные форматы приходят ZIP-архивом.\n"
            "• 📝 Текст с фото или скана PDF: выберите TXT (только текст) или «PDF с текстом» (те же страницы, текст можно выделять и искать). Для картинки оба варианта — в «⋯ Ещё форматы». PDF с текстом делается максимум из {ocr_pages} отсканированных страниц. «🔤 Язык текста» переключает английский, русский и узбекский. Распознавание бесплатно, если страниц не больше {ocr_free_pages} и файлы меньше {free_mb} МБ.\n"
            "• «📌 Хранить файл для других форматов» хранит файл {minutes} мин после каждой конвертации — можно перевести его ещё раз, не присылая заново. Сначала выключено: файл удаляется сразу.\n"
            "• Выбора формата я жду {minutes} мин.\n"
            "\n"
            "Пример: пришлите otchet.docx и нажмите PDF. Небольшой документ переведётся сразу и бесплатно. Для большего сначала будет цена — от {least} ⚡ — и запустит его «✅ Конвертировать»."
        ),
        "helppage_recharge": (
            "⭐ /recharge — пополнить ⚡ кредит\n"
            "\n"
            "Конвертации оплачиваются ⚡ кредитом, а ⚡ покупается за Telegram Stars (⭐).\n"
            "1. Отправьте /recharge и нажмите сумму ({options} ⭐) или «✏️ Другое ⭐». Или сразу: /recharge 200.\n"
            "2. Telegram попросит оплатить. ⚡ появится на балансе, как только придёт оплата.\n"
            "\n"
            "Сколько ⚡ даёт одна ⭐, зависит от того, сколько Stars вы заплатили всего, за всё время, в любом из наших ботов:\n"
            "{ladder}\n"
            "{bonus_rule}\n"
            "• Сначала тратится бонусный кредит, начиная с того, что сгорает раньше, — поэтому сгореть может только неиспользованный бонус. /balance покажет, сколько у вас бонуса и когда он сгорает.\n"
            "• Платежи окончательны: Stars не возвращаются, а ⚡ нельзя вывести или обратно превратить в Stars.\n"
            "• /donate — та же команда.\n"
            "\n"
            "{example}"
        ),
        "helppage_recharge_step_first": "  • первые {stars} ⭐: по {each} ⚡{split}",
        "helppage_recharge_step_next": "  • следующие {stars} ⭐: по {each} ⚡{split}",
        "helppage_recharge_step_after": "  • дальше: по {rate} ⚡",
        "helppage_recharge_flat": "  • {rate} ⚡ за каждую ⭐",
        "helppage_recharge_bonus_part": " ({rate} + {bonus} бонус)",
        "helppage_recharge_bonus_rule": "{rate} ⚡ за каждую ⭐ не сгорают никогда. Бонус сгорает через {days} дн. после оплаты.",
        "helppage_recharge_example": "Пример: первая оплата {stars} ⭐ даёт {total} ⚡: {base} ⚡, которые не сгорают, и {bonus} ⚡ бонуса.",
        "helppage_recharge_example_flat": "Пример: {stars} ⭐ дают {total} ⚡.",
        "helppage_balance": (
            "⚡ /balance — ваш кредит и куда он ушёл\n"
            "\n"
            "/balance показывает:\n"
            "• баланс и итоги: сколько Stars вы заплатили, сколько ⚡ они дали, сколько ⚡ потрачено;\n"
            "• сколько из баланса — бонус, сколько из него сгорает первым и в какой день;\n"
            "• сколько ⚡ дадут ваши следующие Stars;\n"
            "• последние {rows} операций, у каждой дата и одно слово:\n"
            "  topup — ⚡ за оплаченные Stars\n"
            "  bonus — дополнительные ⚡ от пополнения; сгорают через {days} дн. после оплаты\n"
            "  grant — ⚡, которые вам дали: подарок (бонус, сгорает в конце указанного в нём дня) или кредит от того, кто ведёт этих ботов (не сгорает)\n"
            "  spend — конвертация\n"
            "  returned — ⚡ конвертации вернулись, потому что я её не выполнил\n"
            "  adjustment — исправление от того, кто ведёт этих ботов\n"
            "  expired — бонус, сгоревший неиспользованным\n"
            "• Бонус тратится раньше остального, начиная с того, что сгорает раньше.\n"
            "• Кошелёк один: баланс одинаковый во всех наших ботах.\n"
            "\n"
            "{example}"
        ),
        "helppage_balance_example": "Пример: после первой оплаты {stars} ⭐ вы увидите «+{base} ⚡ topup» и «+{bonus} ⚡ bonus».",
        "helppage_balance_example_one": "Пример: после первой оплаты {stars} ⭐ вы увидите «+{total} ⚡ topup».",
        "privacy_feedback_heading": "Если вы отправляете /feedback:",
        "privacy_feedback": (
            "Написанное уходит тому, кто ведёт этих ботов, сообщением в Telegram — вместе с "
            "названием бота и вашим языком, но без имени, username и id. Копия хранится в базе "
            "ботов 30 дней, потом удаляется. Читает его только он, и ответить на него он не может."
        ),
        "cancel_item_conversion": "\u0444\u0430\u0439\u043b .{ext}, \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0432\u044b \u043a\u043e\u043d\u0432\u0435\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u043b\u0438",
        "cancel_button_conversion": "🔄 Файл, ждущий конвертации",
        "start_greeting": "Здравствуйте! Пришлите мне файл, и я преобразую его в другой формат.\n\n",
        "help_text": 'Пришлите мне файл, и я преобразую его в другой формат — картинки, raw-фото, видео, аудио, документы, презентации, таблицы, субтитры и архивы.\n\nКоманды:\n/convert - начать конвертацию (или просто отправьте файл напрямую)\n/formats - все форматы, которые я читаю и пишу\n/balance (или /mystars) - ваш ⚡ кредит и на что он потрачен\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/feedback - предложить идею или сообщить о проблеме; это прочитает только тот, кто ведёт этих ботов, ответа не будет\n/recharge (или /donate) - пополнить ⚡ кредит\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n/fullhelp - это полное руководство (/help - краткое)\n\nЦена в ⚡ кредите:\n{pricing}\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars НЕ возвращаются, а ⚡ кредит НЕЛЬЗЯ вывести. ⚡ за конвертацию списывается при СТАРТЕ и возвращается на баланс, только если сбой по вине бота.\n\n',
        "convert_start_prompt": (
            "Пришлите файл для конвертации, до {max_mb} МБ — картинку, видео, звук, "
            "документ, презентацию, таблицу или файл субтитров. Пришлите несколько картинок "
            "сразу — соберу их в один PDF.\n\n"
            "/formats покажет все форматы, которые я знаю.\n\n"
            "Цена в ⚡ кредите:\n{pricing}\n\n"
            "/cancel, чтобы остановиться."
        ),
        "cancelled": "Отменено.",
        "btn_cancel_conversion": "✖️ Отмена",
        "unknown_extension": (
            "Не удалось определить формат файла по названию — попробуйте отправить "
            "его как документ с обычным расширением (например, photo.png)."
        ),
        "file_too_large_download": "Этот файл больше {max_mb} МБ — боты Telegram не могут скачать ничего крупнее, увы.",
        "file_too_large_in_group": "Файлы больше {limit} МБ я принимаю только в личном чате. Пришлите этот файл мне напрямую — там можно до {max_mb} МБ.",
        "big_download_unavailable": "Файл не скачан: файлы больше {limit} МБ приходят ко мне через отдельное подключение к Telegram, а оно сейчас не отвечает. Попробуйте через несколько минут или пришлите файл меньше {limit} МБ.",
        "card_downloading": "📥 Скачиваю ваш файл…",
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
        "gift_granted": "🎁 Нас уже больше 100 — спасибо! Вам начислено {amount} ⚡ бесплатного кредита, он действует до {date}. Этого хватит примерно на {conversions} платных конвертаций в {convert} или на скачивание больших файлов в {download}. Ваш баланс: /balance",
        "gift_claimed": "🎁 Подарок: {amount} ⚡ бесплатного кредита! У Mumu ботов уже больше {users} пользователей — это наше спасибо.\nОн действует до {date} (UTC). Этого хватит на платные конвертации (около {conversions}) в {convert} или на скачивание больших файлов в {download}.\nВаш баланс: /balance",
        "download_failed": "Не удалось скачать этот файл: {error}\n\nОбычно это случайный сбой по дороге — пришлите файл ещё раз.",
        "unsupported_format": "«.{ext}» — не тот формат, который я конвертирую — /formats покажет те, что умею.",
        "not_for_this_file": "Для этого файла такой вариант недоступен (альбом или PDF без отсканированных страниц).",
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
        "converted_file_caption": "Вот ваш сконвертированный файл!",
        "converted_file_caption_free": 'Вот ваш сконвертированный файл! (бесплатно)',
        "conversion_expired": "Срок этой сессии конвертации истёк — отправьте файл заново.",
        "convert_invoice_title": "Конвертировать {src} в {target}",
        "convert_invoice_description": "Разовая конвертация вашего файла на {size_kb} КБ.",
        "convert_invoice_label": "{src}→{target} конвертация",
        "topup_needed": 'Это стоит {price} ⚡, а у вас {balance} ⚡.\n\nОтправлен счёт на {stars} ⭐ — он добавит {credited} ⚡: хватит на эту конвертацию, остаток останется на балансе. /cancel, чтобы отменить.',
        "credit_policy_note": '⚠️ ВНИМАНИЕ: ⚡ списывается, когда конвертация НАЧИНАЕТСЯ. Остановите её сами — ⚡ НЕ вернётся; если сбой на стороне бота, ⚡ сразу вернётся на баланс. Платежи окончательные — Stars не возвращаются.',
        "send_limit_note": '📤 Готовый файл может весить до {mb} МБ. Если он получится больше, отправлен он не будет — тогда ⚡ сразу вернётся на баланс.',
        "too_many_megapixels": 'В этой картинке {mp} мегапикселей — больше {max} МП, которые я могу безопасно конвертировать. Ничего не списано.',
        "too_big_to_send_note": '📐 {formats} не предлагаются: при {mp} МП они выйдут больше {limit} МБ, которые бот может отправить. JPG, WEBP или AVIF поместятся.',
        "raw_too_big": "Это raw-фото — {mp} мегапикселей. Сервер конвертирует raw-фото до {max} МП: для больших не хватает памяти даже на половинный размер. Ничего не списано.",
        "raw_half_note": "⚠️ ВАЖНО: это raw-фото — {mp} МП. Оно конвертируется в половинном размере ({out} МП): для полного кадра серверу не хватает памяти.",
        "video_fit_hdr_note": "⚠️ ВАЖНО: это видео {w}×{h} HDR. Сервер конвертирует его в {fw}×{fh} — для полного кадра ему не хватает памяти. Цвета сохраняются.",
        "video_fit_big_note": "⚠️ ВАЖНО: это видео {w}×{h}. WEBM здесь делается в {fw}×{fh}; MP4, MKV и MOV остаются в полном размере.",
        "video_fit_huge_note": "⚠️ ВАЖНО: это видео {w}×{h}. Сервер конвертирует его в {fw}×{fh} — для полного кадра ему не хватает памяти.",
        "nothing_sendable": 'Любой формат, который я могу предложить, для картинки такого размера выйдет больше {limit} МБ, которые бот может отправить. Ничего не списано.',
        "too_big_to_send_alert": 'Этот формат для такой картинки выйдет больше {limit} МБ, которые бот может отправить.',
        "keep_toggle_off": '📌 Хранить файл для других форматов: выкл',
        "keep_toggle_on": '📌 Хранить файл для других форматов: вкл',
        "ocr_lang_toggle": "🔤 Язык текста: {name} (нажмите, чтобы сменить)",
        "ocr_lang_set": "Теперь язык текста: {name}.",
        "ocr_lang_eng": "английский",
        "ocr_lang_rus": "русский",
        "ocr_lang_uzb": "узбекский (латиница и кириллица)",
        "ocr_too_many_pages_note": "⚠️ ВАЖНО: в этом PDF больше {max} страниц без текста (только картинка). Текст распознаётся максимум на {max} таких страницах, поэтому TXT содержит только текст остальных страниц, а PDF с текстом не предлагается.",
        "target_ocrpdf": "PDF с текстом",
        "keep_explained_on": 'После каждой конвертации я буду хранить файл {minutes} минут, чтобы вы могли конвертировать его и в другие форматы. /cancel удалит его раньше.',
        "keep_explained_off": 'Файл удалится сразу после конвертации.',
        "storage_full_user": 'У меня уже {used} МБ ваших файлов, а на одного человека я храню до {limit} МБ. Дождитесь окончания конвертации или отмените её через /cancel и пришлите снова.',
        "storage_full_global": 'Сейчас не хватает временного места — пришлите это снова через пару минут.',
        "cancel_item_job_running": 'конвертацию {size} МБ {src} в {target} — идёт',
        "cancel_item_job_queued": 'конвертацию {size} МБ {src} в {target} — в очереди, пока ничего не списано',
        "cancel_button_job": '⏹ Конвертация в {target}',
        "queue_full": 'У вас уже {count} конвертаций в очереди или в работе. Пришлите ещё, когда какие-то закончатся.',
        "job_queued": '⏳ {src} → {target} в очереди, перед ней {ahead}. Ничего не списывается, пока она не начнётся.',
        "job_starting": '⏳ {src} → {target}: начинаю…',
        "job_not_running": 'Эта конвертация уже закончилась.',
        "payment_kept_as_credit": 'Оплата получена — +{credited} ⚡, на балансе {balance} ⚡. Файл уже устарел, поэтому ничего не конвертировано; пришлите его снова — оплата пойдёт с баланса.',
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
        "job_reason_timeout": 'Конвертация не уложилась в {minutes} мин., и я её остановил.',
        "job_reason_too_slow": "На этот файл ушло бы около {minutes} мин., а конвертация здесь может идти не дольше {limit} мин., поэтому я остановил её сразу, а не заставил вас ждать до конца лимита. Подойдёт ролик покороче или в меньшем разрешении.",
        "job_reason_crash": 'Конвертация сломалась на моей стороне. Можно попробовать ещё раз — пришлите файл снова.',
        "job_reason_no_memory": "Для этого файла не хватило памяти сервера — так бывает с видео в 4K и HDR. С самим файлом всё в порядке: версия в 1080p или ниже сконвертируется.",
        "job_reason_too_large": '{target} получился на {mb} МБ, а по этой конвертации я могу отправить не больше {limit} МБ. JPG, WEBP или AVIF будут намного меньше.',
        "job_reason_send_failed": 'Файл сконвертирован, но отправить его вам не вышло. Можно попробовать ещё раз — пришлите файл снова.',
        "job_reason_interrupted": 'Меня перезапустили посреди конвертации. Пришлите файл снова через минуту.',
        "unknown_order": "Неизвестный заказ.",
        "unrecognized_message": (
            "Это не файл, который я могу конвертировать — пришлите файл или "
            "/formats, чтобы увидеть, что я принимаю. Назовёте формат («heic», "
            "«epub») — скажу, во что он превращается."
        ),
        "unknown_command": "Я не знаю такую команду. Отправьте /start, чтобы увидеть, что я умею.",

        "category_document": "документ",
        "category_presentation": "презентация",
        "category_data": "данные",
        "category_subtitle": "субтитры",
        "category_archive": "архив",
        "formats_title": "📁 Что я конвертирую",
        "formats_intro": (
            "{sources} форматов на вход, {targets} на выход — всего {pairs} "
            "комбинаций. Пришлите файл, и я покажу, во что его можно превратить; "
            "нажмите на категорию ниже, чтобы увидеть весь список."
        ),
        "formats_highlights": (
            "Из менее очевидного:\n"
            "• Фото с iPhone (HEIC) → JPG или PNG\n"
            "• Любая картинка — или целый альбом сразу — в один PDF\n"
            "• PDF или EPUB → PNG, JPG или обычный текст\n"
            "• PowerPoint: PPT ↔ PPTX ↔ PDF, PDF — в редактируемые слайды, слайды — в картинки\n"
            "• Word: DOC ↔ DOCX ↔ ODT ↔ PDF, или HTML и Markdown\n"
            "• Excel: XLS ↔ XLSX ↔ ODS, или CSV, JSON и PDF\n"
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
        "btn_what_formats": "📁 Что вы умеете конвертировать?",
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
            "Эти файлы разных форматов, так что отправляйте их по одному — или "
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

_TARGET_NAMES = {"ocrpdf": "target_ocrpdf"}

def target_label(lang: str | None, ext: str | None) -> str:
    """What a target format is called on a button or in a sentence: its extension in capitals (PNG), or for a pseudo-target its name."""
    key = _TARGET_NAMES.get(ext or "")
    return t(lang, key) if key else (ext or "?").upper()

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
        "feedback": "Taklif yoki muammo haqida yozish",
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
        "feedback": "Предложить идею или сообщить о проблеме",
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
        "report_button": '🐞 Send more details',
        "problem_logged_note": "Anonymous technical report saved.",
        "problem_logged_note_optin": "Anonymous technical report saved. You can opt in to send more details.",
        "report_disclaimer": "📨 Send more details with incident {incident}?\n\nSaved already, nothing about you: the bot, code {code}, the time, the version.\n\nSend adds:\n• your Telegram ID\n• your @username, if you have one\n• your language\n• private chat or group\n\nNever your messages or files. Cleared after 30 days, or now with /deletemydata.",
        "report_send": '📨 Send',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — added to incident {incident}.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent.',
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
            "• the links you send: each one while it is fetched, then the last five, so the "
            "buttons under those downloads work. They are dropped after 12 hours without using "
            "the bot\n"
            "• what it has just sent you, for 5 minutes, so the button under it and the same "
            "link sent again are answered without fetching it twice. Sending a different link, "
            "/deletemydata or a restart deletes it sooner. All of it is deleted no later than 12 "
            "hours after the download\n"
            "• references to files the bot has already sent (Telegram's file IDs), filed under a "
            "scrambled name of the post and not under who asked for it. They let the bot send the "
            "same post again without downloading it. Before re-using one, the bot checks at least "
            "every 12 hours that the post is still public. References nobody uses are deleted "
            "after 90 days\n"
            "• one row per download — which platform and when, which is what the daily allowance "
            "counts\n"
            "• a timestamp each time you use the bot, so its owner can tell whether anyone is "
            "using it\n"
            "• how many times each button is tapped, counted per day for the whole bot, with nothing about who tapped it\n• how much was done — links per site, conversions, stickers, relayed messages — counted per day for the whole bot, with nothing about who\n"
            "• a record of any donation: the amount and Telegram's payment id\n"
            "• whatever the bot is in the middle of doing with you, until it is finished\n"
            "\n"
            "Apart from those 5 minutes the media itself is not kept. It is fetched, sent to you, "
            "and deleted."
        ),
        "privacy_problems_heading": "When something goes wrong:",
        "privacy_problems": (
            "Every error this bot shows anybody is written down by itself: the error code, an "
            "incident number, when it happened and the bot's version. Nothing in that is about "
            "you — not your id, not your name, not what you sent. A fault nobody reports is "
            "still a fault, which is why it does not wait to be asked.\n"
            "\n"
            "Under a crash, a failed /deletemydata or /feedback, or an error that keeps "
            "happening to you, \"Send more details\" offers to attach four things to that one "
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
        "privacy_kept_for": 'Settings and anything the bot is holding for you stay until you erase them or stop using it. Counted use is dropped after about three months; the daily counts of what was done, which say nothing about who, after 400 days. Payment records and your ⚡ balance are kept longer, because a dispute about a payment is settled against them.\n\nNothing here is sold, rented or used for advertising, and nothing goes to anyone not named above.',
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
        "delete_data_consequences": 'Your language, your caption and quality settings, and every record of what you downloaded and when all go. Your daily allowance resets with them. It also deletes the last download if it is still being held; nothing older was ever kept here.\n\nDonation records stay, without your username, because a dispute about a payment is settled against them. Your ⚡ balance stays too, and is still yours if you come back.',
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
        "feedback_ask": (
            "💬 What would you like to tell the person who runs these bots? A suggestion, a "
            "problem, anything — write it in one message, as a reply to this one.\n"
            "\n"
            "Only they read it, and they can't write back: it is sent without your name or id. "
            "/cancel to stop."
        ),
        "feedback_placeholder": "Your feedback",
        "feedback_text_only": "That one has to be in words — write your feedback as a text reply to this message, or send /cancel.",
        "feedback_thanks": "✅ Thank you — sent. Only the person who runs these bots reads it, and they can't reply: nothing in it says who you are.",
        "feedback_limit": "You've sent {per_day} messages with /feedback today, which is as many as I take in a day. Thank you — write again tomorrow.",
        "feedback_failed": "Your feedback wasn't sent — something went wrong on my side. Please try again in a few minutes.",
        "cancel_button_feedback": "💬 Feedback",
        "cancel_item_feedback": "the feedback I asked you for",
        "help_brief": (
            "How it works:\n"
            "\n"
            "• Paste a link and I send back what's behind it — no command needed. Instagram, TikTok, X, Pinterest and Reddit.\n"
            "• /settings: the credit caption, the file quality, and large files over 48 MB, which cost ⚡ credit and only once you switch them on.\n"
            "• Ideas or problems: /feedback — only the person who runs these bots reads it, and they can't reply.\n"
            "\n"
            "Main commands: /settings · /balance · /cancel\n"
            "Every command: the full guide, below or /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 Full guide",
        "help_brief_button": "↩️ Short version",
        "help_page_everything": "The full guide: /fullhelp",
        "help_page_gone": "That help page no longer exists. Send /help to see the current ones.",
        "help_btn_download": "🔗 Sending a link",
        "helppage_download": (
            "🔗 Sending a link — how downloading works\n"
            "\n"
            "Paste a link to a post — no command needed — and I send back what's in it:\n"
            "  - Instagram: reels, photos, whole carousels\n"
            "  - TikTok: videos without the watermark, photo slideshows\n"
            "  - Twitter/X: video and photos, or a clean picture of a text post\n"
            "  - Pinterest: the pin, at full size\n"
            "  - Reddit: the media of a media post, or a picture of a text post\n"
            "\n"
            "{quota}\n"
            "• A download counts when it starts, even if it then fails. The 📄/🖼 button and the 📄 PDF / 🗜 ZIP buttons under a delivery count as one download each. The same link sent again while I'm still fetching it gets a 👌 and doesn't count.\n"
            "• Up to {waiting} of your links can be on the way at once; I fetch {at_once} at a time, and the rest wait their turn.\n"
            "\n"
            "Size: free up to {free_mb} MB. {large}\n"
            "\n"
            "Under a delivery:\n"
            "• \"📄 Get it as an uncompressed file\" (or \"🖼 Get it compressed instead\") sends the same post again in the other quality; each button works once.\n"
            "• Under an album: 📄 PDF puts its photos in one PDF, 🗜 ZIP puts everything in one archive. Up to {merge_items} files and {merge_mb} MB.\n"
            "• /settings: the caption, the quality, and large files.\n"
            "\n"
            "Example: paste a TikTok link like https://www.tiktok.com/@name/video/123 — the video comes back without the watermark."
        ),
        "helppage_download_quota": "It's free, up to {per_day} downloads in any 24 hours and {per_hour} in any hour. The count looks back from now; it doesn't reset at midnight. When you reach it, I say when the next one frees up. Anyone who has ever paid through /donate, any amount, gets {donor_day} a day and {donor_hour} an hour, for good.",
        "helppage_download_quota_off": "It's free.",
        "helppage_download_large": "Bigger, up to {max} MB, only if you turn on large files in /settings, in a private chat: ⚡{first} up to 100 MB, and each 100 MB after that adds less (⚡{top} for {max} MB). The ⚡ is taken only once the file has arrived, never if it fails.",
        "helppage_download_large_off": "Anything bigger is refused.",
        "helppage_settings": (
            "⚙️ /settings — how your downloads arrive\n"
            "\n"
            "/settings shows your switches and how each is set. Tap one to change it; it stays that way for every later download.\n"
            "• Caption (on at first): a \"via @{username}\" line under each download. Also /caption on or /caption off.\n"
            "• Lossless (off at first). On: downloads come as files, exactly as the source had them, with no Telegram compression — but they don't play or show in the chat until you open them. Off: they come as photos and videos that play in the chat, compressed by Telegram. Also /lossless on or /lossless off. For one download only, use the 📄/🖼 button under it instead.\n"
            "{large}\n"
            "Example: send /lossless on, then an Instagram link: the photos come as files, at full quality."
        ),
        "helppage_settings_large": "• Large files (off at first). On: a download over {free_mb} MB is still fetched, up to {max} MB, and sent as a file for ⚡ credit — ⚡{first} up to 100 MB, ⚡{top} for {max} MB — taken only once it has arrived. Off: anything over {free_mb} MB is refused, and nothing is charged. In a private chat only.",
        "privacy_feedback_heading": "If you send /feedback:",
        "privacy_feedback": (
            "What you write reaches the person who runs these bots as a Telegram message, with "
            "which bot it came from and your language — not your name, your username or your id. "
            "Only they read it, and they cannot reply to it. A copy is kept in the bots' "
            "database for 30 days and then deleted."
        ),

        "start_greeting": (
            "Hey! Send me a link (Instagram, TikTok, Pinterest, Reddit, or "
            "Twitter/X) and I'll grab it for you.\n\n"
        ),
        "help_text": 'Paste a link any time and I\'ll grab it — no command needed:\n  - Instagram: reels, photos, whole carousels\n  - TikTok: videos without the watermark, and photo slideshows\n  - Twitter/X: video and photos, or a clean image card for a text post\n  - Pinterest: the pin, at full size\n  - Reddit: the media if it\'s a media post, or a card if it\'s text\n\nUnder an album I add two buttons: 📄 PDF puts its photos into one PDF, 🗜 ZIP puts everything into one archive.\n\nCommands:\n/settings - the caption, the file quality, and large files (over 48 MB, for ⚡), on one screen\n/caption on|off - the "via @{username}" credit caption, on its own\n/lossless on|off - get downloads as uncompressed files\n/donate - chip in for hosting costs (totally optional)\n/cancel - stop something I\'m waiting on you for (I\'ll ask which)\n/feedback - suggest something or report a problem; only whoever runs these bots reads it, and they cannot reply\n/en, /uz, /rus - switch language (or /language, which asks)\n/balance - your ⚡ credit\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n/fullhelp - this full guide (/help - the short one)\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n',
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
        "gift_granted": '🎁 We have passed 100 users, thank you! You get {amount} ⚡ of free credit, good until {date}. It pays for about {conversions} paid conversions in {convert} or big-file downloads in {download}. Your balance: /balance',
        "gift_claimed": "🎁 Gift received: {amount} ⚡ of free credit! Mumu bots have passed {users} users, and this is our thank-you.\nIt is good until {date} (UTC) and pays for about {conversions} paid conversions in {convert} or big-file downloads in {download}.\nYour balance: /balance",
        "download_failed": "Couldn't download that: {error}\n\nYou can try again — send the link once more in a minute.",
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
        "merge_too_big": "📦 That's too much to pack into one file — I can do up to {items} files and {mb} MB in all. Everything is still in the chat above.",
        "merge_picture_too_big": "📦 One of the pictures is too big for a PDF (over {mp} megapixels), so there's no PDF this time. The pictures are in the chat above.",
        "merge_no_photos": "📄 A PDF needs at least two photos, and I found fewer than that in the post this time. Send the link again, or take the files from the chat above.",
        "merge_failed": "😕 Something went wrong while I was putting them into one file, so there's no PDF or ZIP this time. The files above are fine — send the link again to retry.",
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
        "report_button": "🐞 Qo'shimcha ma'lumot yuborish",
        "problem_logged_note": "Anonim texnik hisobot saqlandi.",
        "problem_logged_note_optin": "Anonim texnik hisobot saqlandi. Xohlasangiz, qo'shimcha ma'lumot yuborishingiz mumkin.",
        "report_disclaimer": "📨 {incident} hodisasiga qo'shimcha ma'lumot yuborasizmi?\n\nAllaqachon saqlangan, siz haqingizda hech narsa yo'q: bot, {code} kodi, vaqt, versiya.\n\n\"Yuborish\" qo'shadi:\n• Telegram ID raqamingiz\n• bo'lsa, @username'ingiz\n• tilingiz\n• shaxsiy suhbatmi yoki guruh\n\nXabarlaringiz va fayllaringiz hech qachon kirmaydi. 30 kundan keyin o'chiriladi, /deletemydata bilan esa darhol.",
        "report_send": '📨 Yuborish',
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — {incident} hodisasiga qo'shildi.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi.",
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
        "privacy_stored": "• Telegram ID raqamingiz, tilingiz, izoh va sifat sozlamalaringiz\n• siz yuborgan havolalar: har biri u bo'yicha fayl olinayotgan paytda, keyin esa oxirgi beshtasi — o'sha yuklamalar ostidagi tugmalar ishlashi uchun. Botdan 12 soat foydalanmasangiz, ular o'chiriladi\n• bot sizga hozirgina yuborgan fayl — 5 daqiqa davomida, uning ostidagi tugma va qayta yuborilgan o'sha havola faylni qaytadan yuklamasdan javob berishi uchun. Boshqa havola yuborsangiz, /deletemydata buyrug'ini bersangiz yoki bot qayta ishga tushsa, u oldinroq o'chiriladi. Bularning hammasi yuklab olinganidan keyin 12 soatdan kechiktirmay o'chiriladi\n• bot avval yuborgan fayllarning Telegram fayl ID'lari — postning qaytarib bo'lmaydigan kodi ostida saqlanadi, kim so'ragani esa saqlanmaydi. Ular yordamida bot o'sha postni qayta yuklab olmasdan yana yubora oladi. Fayl ID'sidan qayta foydalanishdan oldin bot post hali ham ochiq ekanini kamida har 12 soatda tekshiradi. Hech kim foydalanmagan fayl ID'lari 90 kundan keyin o'chiriladi\n• har bir yuklab olish uchun bitta yozuv: qaysi platformadan va qachon; kunlik limit shu asosida hisoblanadi\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• har bir tugma necha marta bosilgani — butun bot bo'yicha kunlik umumiy hisob, kim bosgani haqida hech qanday ma'lumotsiz\n• qancha ish qilingani — sayt bo'yicha havolalar, konvertatsiyalar, stikerlar, yuborilgan xabarlar — butun bot bo'yicha kunlik hisob, kim ekani haqida ma'lumotsiz\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n• bot siz uchun bajarayotgan ish — u tugagunicha\n\nShu 5 daqiqadan tashqari faylning o'zi saqlanmaydi: u olinadi, sizga yuboriladi va o'chiriladi.",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nIshdan chiqish, bajarilmagan /deletemydata yoki /feedback, yoki sizda takror-takror yuz berayotgan xato ostidagi \"Qo'shimcha ma'lumot yuborish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• siz havolasini yuborgan sayt, hamda sayt to'g'ridan-to'g'ri javob bermaganda bot murojaat qiladigan yuklab olish xizmatlari. Ular havolani oladi va so'rov sizdan emas, bot serveridan kelganini ko'radi; ular nimani qayd etishi o'z qoidalariga bog'liq, bu botning qoidalariga emas.",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi; qancha ish qilinganining kunlik hisobi esa — unda kimligi yo'q — 400 kundan keyin. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
        "privacy_your_choices": "Nima qilishingiz mumkin:\n/deletemydata — bot siz haqingizda saqlagan ma'lumotlarni o'chirish\n/terms — botdan foydalanish shartlari\n\nBotni Telegramda bloklasangiz, u sizga yozmay qo'yadi, lekin hech narsa o'chmaydi. Ikkalasini ham xohlasangiz, avval /deletemydata yuboring.",
        "terms_heading": "📜 Shartlar",
        "terms_use": "Botdan maqsadiga ko'ra, qonun va Telegram qoidalari doirasida foydalaning. Uni boshqalarni bezovta qilish uchun ishlatmang va belgilangan cheklovlardan oshirib yuklamang — aks holda akkaunt bloklanadi.",
        "terms_specific": "Yuklab olish haqida: bot faqat hammaga ochiq bo'lgan narsani olib beradi. Yopiq akkauntlarni chetlab o'tmaydi va bunga urinmaydi ham. Birovning surati, videosi yoki posti bilan keyin nima qilishingiz — siz, o'sha odam va qonun o'rtasidagi masala; yuklab olganingiz uni sizniki qilmaydi. Bitta odam botni boshqalar uchun band qilib qo'ymasligi uchun har bir kishiga kunlik limit bor.",
        "terms_money": "Pul haqida: /donate — ixtiyoriy, mablag' botlar xarajatlariga ketadi. Stars'dagi to'lov ConvertBot'da konvertatsiyalar uchun ⚡ kredit ham beradi: har ⭐ uchun 2 ⚡, umumiy hisobda birinchi 500 ta Stars uchun esa 6 ⚡ dan, keyingi 500 tasi uchun 4 ⚡ dan. 2 ⚡ dan ortig'i bonus kredit bo'lib, to'lovdan 90 kun o'tgach muddati tugaydi. To'lovlar QAYTARILMAYDI: Stars qaytarib berilmaydi, kreditni esa yechib olib ham, Stars'ga aylantirib ham BO'LMAYDI. Har bir to'lovni Telegram o'tkazadi, bot karta raqamingizni ko'rmaydi. To'lovda muammo bo'lsa: /paysupport.",
        "terms_no_warranty": "Kafolat yo'q: botni bir kishi yuritadi va u oldindan ogohlantirmasdan sekinlashishi, xato qilishi yoki butunlay to'xtab qolishi mumkin. Siz uchun muhim narsalarning nusxasini o'zingizda saqlang.",
        "policy_full_text": "To'liq matn: {url}",
        "policy_contact": "Savol, shikoyat yoki ma'lumot so'rovi uchun: {contact}",
        "delete_data_confirm": "⚠️ Bot siz haqingizda saqlagan ma'lumotlar o'chiriladi. Buni ortga qaytarib bo'lmaydi.",
        "delete_data_consequences": "Til, izoh va sifat sozlamalaringiz hamda nimani qachon yuklab olganingiz haqidagi qaydlar o'chiriladi. Kunlik limitingiz ham yangilanadi. Oxirgi yuklama hali saqlanayotgan bo'lsa, u ham o'chiriladi; undan oldingilari bu yerda umuman saqlanmagan.\n\nXayriya yozuvlari foydalanuvchi nomingizsiz saqlanib qoladi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi. ⚡ balansingiz ham saqlanadi — qaytib kelsangiz, u o'z joyida bo'ladi.",
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
        "feedback_ask": (
            "💬 Bu botlarni yuritayotgan odamga nima demoqchisiz? Taklif, muammo — nima bo'lsa "
            "ham, bitta xabarda, shu xabarga javob qilib yozing.\n"
            "\n"
            "Uni faqat o'sha odam o'qiydi va sizga javob yoza olmaydi: xabar ismingiz va ID "
            "raqamingizsiz yuboriladi. To'xtatish: /cancel"
        ),
        "feedback_placeholder": "Fikringiz",
        "feedback_text_only": "Bu yerga faqat matn qabul qilinadi — fikringizni shu xabarga javob qilib so'z bilan yozing yoki /cancel yuboring.",
        "feedback_thanks": "✅ Rahmat — yuborildi. Uni faqat bu botlarni yuritayotgan odam o'qiydi va javob yoza olmaydi: xabarda kimligingiz ko'rsatilmagan.",
        "feedback_limit": "Bugun /feedback orqali {per_day} ta xabar yubordingiz — bir kunda shuncha qabul qilaman. Rahmat, ertaga yana yozishingiz mumkin.",
        "feedback_failed": "Fikringiz yuborilmadi — bot tomonida nimadir buzildi. Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring.",
        "cancel_button_feedback": "💬 Fikr-mulohaza",
        "cancel_item_feedback": "men so'ragan fikr-mulohaza",
        "help_brief": (
            "Bot qanday ishlaydi:\n"
            "\n"
            "• Havola yuboring — ortidagi faylni yuboraman, buyruq kerak emas. Instagram, TikTok, X, Pinterest va Reddit.\n"
            "• /settings: «via» izohi, fayl sifati va 48 MB dan katta fayllar — ular ⚡ kredit turadi va faqat o'zingiz yoqsangiz ishlaydi.\n"
            "• Taklif yoki muammo: /feedback — uni faqat bu botlarni yuritayotgan odam o'qiydi, javob qaytmaydi.\n"
            "\n"
            "Asosiy buyruqlar: /settings · /balance · /cancel\n"
            "Barcha buyruqlar: to'liq qo'llanmada — pastdagi tugma yoki /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 To'liq qo'llanma",
        "help_brief_button": "↩️ Qisqa variant",
        "help_page_everything": "To'liq qo'llanma: /fullhelp",
        "help_page_gone": "Bu yordam sahifasi endi yo'q. Hozirgilarini ko'rish uchun /help yuboring.",
        "help_btn_download": "🔗 Havola yuborish",
        "helppage_download": (
            "🔗 Havola yuborish — yuklab olish qanday ishlaydi\n"
            "\n"
            "Postning havolasini yuboring — buyruq kerak emas — ichidagisini sizga yuboraman:\n"
            "  - Instagram: reels, rasmlar, butun karusellar\n"
            "  - TikTok: suv belgisisiz videolar, rasmli slayd-shoular\n"
            "  - Twitter/X: video va rasmlar yoki matnli post uchun toza rasm-karta\n"
            "  - Pinterest: pin, to'liq o'lchamda\n"
            "  - Reddit: media post bo'lsa media, matnli bo'lsa rasm-karta\n"
            "\n"
            "{quota}\n"
            "• Yuklab olish boshlanganda hisoblanadi, keyin xato bo'lsa ham. Yetkazilgan fayl ostidagi 📄/🖼 tugmasi hamda 📄 PDF / 🗜 ZIP tugmalari har biri bitta yuklab olish hisoblanadi. Hali yuklab olayotgan havolani qayta yuborsangiz, 👌 olasiz va u hisoblanmaydi.\n"
            "• Bir vaqtda {waiting} tagacha havolangiz yo'lda bo'lishi mumkin; bir paytda {at_once} tasini yuklayman, qolganlari navbat kutadi.\n"
            "\n"
            "Hajm: {free_mb} MB gacha bepul. {large}\n"
            "\n"
            "Yetkazilgan fayl ostida:\n"
            "• \"📄 Siqilmagan fayl sifatida olish\" (yoki \"🖼 Siqilgan holda olish\") o'sha postni boshqa sifatda yana yuboradi; har bir tugma bir marta ishlaydi.\n"
            "• Albom ostida: 📄 PDF uning rasmlarini bitta PDF'ga, 🗜 ZIP hammasini bitta arxivga joylaydi. {merge_items} tagacha fayl va {merge_mb} MB gacha.\n"
            "• /settings: izoh, sifat va katta fayllar.\n"
            "\n"
            "Misol: https://www.tiktok.com/@name/video/123 kabi TikTok havolasini yuboring — video suv belgisisiz keladi."
        ),
        "helppage_download_quota": "Bepul: istalgan 24 soatda {per_day} ta va istalgan bir soatda {per_hour} ta yuklab olish. Hisob hozirdan orqaga qarab yuritiladi, yarim tunda nolga tushmaydi. Chegaraga yetsangiz, keyingisi qachon bo'shashini aytaman. /donate orqali bir marta bo'lsa ham, istalgan miqdorda to'lagan har kim uchun chegara butunlay kuniga {donor_day} ta va soatiga {donor_hour} ta bo'ladi.",
        "helppage_download_quota_off": "Bepul.",
        "helppage_download_large": "Kattarog'i, {max} MB gacha, faqat /settings da katta fayllarni yoqsangiz va shaxsiy chatda: 100 MB gacha ⚡{first}, keyingi har 100 MB arzonroq ({max} MB uchun ⚡{top}). ⚡ fayl yetib kelgandan keyingina yechiladi, xato bo'lsa umuman yechilmaydi.",
        "helppage_download_large_off": "Undan kattasi rad etiladi.",
        "helppage_settings": (
            "⚙️ /settings — yuklamalaringiz qanday kelishi\n"
            "\n"
            "/settings kalitlaringizni va ularning holatini ko'rsatadi. O'zgartirish uchun birini bosing; keyingi barcha yuklamalar uchun shunday qoladi.\n"
            "• Izoh (dastlab yoniq): har bir yuklama ostida \"@{username} orqali\" qatori. Yana: /caption on yoki /caption off.\n"
            "• Siqilmagan rejim (dastlab o'chiq). Yoniq: fayllar asl sifatida, hujjat ko'rinishida keladi, Telegram ularni siqmaydi — lekin ochmaguningizcha chatda ko'rinmaydi va ijro etilmaydi. O'chiq: chatda ko'rinadigan rasm va video bo'lib keladi, Telegram ularni siqadi. Yana: /lossless on yoki /lossless off. Faqat bitta yuklama uchun uning ostidagi 📄/🖼 tugmasidan foydalaning.\n"
            "{large}\n"
            "Misol: /lossless on yuboring, keyin Instagram havolasini: rasmlar to'liq sifatda, fayl bo'lib keladi."
        ),
        "helppage_settings_large": "• Katta fayllar (dastlab o'chiq). Yoniq: {free_mb} MB dan katta yuklama ham {max} MB gacha olinadi va ⚡ kredit evaziga fayl sifatida yuboriladi — 100 MB gacha ⚡{first}, {max} MB uchun ⚡{top} — fayl yetib kelgandan keyingina yechiladi. O'chiq: {free_mb} MB dan kattasi rad etiladi va hech narsa yechilmaydi. Faqat shaxsiy chatda.",
        "privacy_feedback_heading": "/feedback yuborsangiz:",
        "privacy_feedback": (
            "Yozganingiz bu botlarni yuritayotgan odamga Telegram xabari sifatida yetib boradi — "
            "qaysi botdan kelgani va tilingiz bilan birga, lekin ismingiz, foydalanuvchi nomingiz "
            "va ID raqamingizsiz. Uni faqat o'sha odam o'qiydi va unga javob yoza olmaydi. "
            "Nusxasi botlar bazasida 30 kun saqlanadi, keyin o'chiriladi."
        ),
        "start_greeting": (
            "Salom! Menga havola yuboring (Instagram, TikTok, Pinterest, Reddit "
            "yoki Twitter/X) va men uni siz uchun yuklab beraman.\n\n"
        ),
        "help_text": 'Havola yuboring — faylni olib beraman, buyruq kerak emas:\n  - Instagram: reels, rasmlar, butun karusel\n  - TikTok: suv belgisiz video va rasm-slaydlar\n  - Twitter/X: video va rasmlar, matnli post uchun esa rasm-kartochka\n  - Pinterest: pin, asl o\'lchamda\n  - Reddit: media post bo\'lsa — media, matnli bo\'lsa — kartochka\n\nAlbom ostida ikkita tugma chiqadi: 📄 PDF — rasmlarni bitta PDF faylga jamlaydi, 🗜 ZIP — hamma narsani bitta arxivga soladi.\n\nBuyruqlar:\n/settings - izoh, fayl sifati va katta fayllar (48 MB dan katta, ⚡ evaziga) — hammasi bitta ekranda\n/caption on|off - fayllar ostidagi "via @{username}" yozuvini yoqish/o\'chirish\n/lossless on|off - fayllarni siqilmagan holda olish\n/donate - server xarajatlariga hissa qo\'shish (ixtiyoriy)\n/cancel - joriy amalni bekor qilish (bir nechta bo\'lsa, qaysi birini so\'rayman)\n/feedback - taklif yozish yoki muammo haqida xabar berish; uni faqat botlarni yuritayotgan odam o\'qiydi, javob qaytmaydi\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/balance - ⚡ kreditingiz\n/paysupport - to\'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o\'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n/fullhelp - shu to\'liq qo\'llanma (/help - qisqasi)\n\n⚠️ DIQQAT: To\'lovlar QAYTARILMAYDI — /donate orqali to\'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO\'LMAYDI.\n\n',
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
        "gift_granted": "🎁 Bizda 100 dan ortiq foydalanuvchi bo'ldi, rahmat! Sizga {amount} ⚡ bepul kredit berildi, u {date} gacha amal qiladi. Bu {convert} orqali taxminan {conversions} ta pullik konvertatsiya yoki {download} orqali katta fayllarni yuklab olish uchun yetadi. Balansingiz: /balance",
        "gift_claimed": "🎁 Sovg'a: {amount} ⚡ bepul kredit! Mumu botlarida {users} dan ortiq foydalanuvchi bo'ldi, bu bizning minnatdorchiligimiz.\nU {date} gacha (UTC) amal qiladi va {convert} orqali taxminan {conversions} ta pullik konvertatsiya yoki {download} orqali katta fayllarni yuklab olish uchun yetadi.\nBalansingiz: /balance",
        "download_failed": "Buni yuklab bo'lmadi: {error}\n\nQayta urinib ko'rishingiz mumkin — bir daqiqadan keyin havolani yana yuboring.",
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
        "merge_too_big": "📦 Bunchasini bitta faylga joylab bo'lmaydi — ko'pi bilan {items} ta fayl va jami {mb} MB. Fayllarning o'zi yuqorida turibdi.",
        "merge_picture_too_big": "📦 Rasmlardan biri PDF uchun juda katta ({mp} megapikseldan katta), shuning uchun bu safar PDF chiqmaydi. Rasmlarning o'zi yuqorida turibdi.",
        "merge_no_photos": "📄 PDF uchun kamida ikkita rasm kerak, postda esa bu safar ikkitadan kam rasm topildi. Havolani qayta yuboring yoki fayllarni yuqoridan oling.",
        "merge_failed": "😕 Fayllarni bitta qilib yig'ishda nimadir xato ketdi, shuning uchun bu safar PDF ham, ZIP ham chiqmadi. Yuqoridagi fayllar joyida — qayta urinish uchun havolani yana yuboring.",
        "unknown_command": "Bunday buyruq yo'q. Bot nimalar qila olishini bilish uchun /help yuboring.",
    },
    "ru": {
        "quota_hour": (
            "За последний час вы скачали {used} — это предел этого бота ({limit} в час). "
            "Он нужен, чтобы на маленьком сервере хватало всем. Следующая попытка "
            "освободится примерно через {minutes} минут(ы)."
        ),
        "quota_day": (
            "Сегодня вы скачали {used} — это дневной предел бота ({limit}). Он нужен, "
            "чтобы на маленьком сервере хватало всем. Снова откроется примерно через "
            "{minutes} минут(ы)."
        ),
        "quota_donor_hint": (
            "Если нужно больше: у всех, кто хоть раз поддержал бота через /donate, "
            "предел заметно выше и навсегда. Сумма значения не имеет."
        ),
        "flood_wait": "Вы отправляете быстрее, чем я успеваю — подождите примерно {seconds} секунд(ы) и продолжайте.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотрите ниже \U0001f447",
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
        "report_button": '🐞 Отправить подробности',
        "problem_logged_note": 'Анонимный технический отчёт сохранён.',
        "problem_logged_note_optin": 'Анонимный технический отчёт сохранён. По желанию можно отправить подробности.',
        "report_disclaimer": "📨 Отправить подробности к случаю {incident}?\n\nУже сохранено, без ничего о вас: бот, код {code}, время, версия.\n\n«Отправить» добавит:\n• ваш Telegram ID\n• ваш @username, если есть\n• ваш язык\n• личный чат или группа\n\nВаши сообщения и файлы — никогда. Стирается через 30 дней или сразу через /deletemydata.",
        "report_send": '📨 Отправить',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — добавлено к случаю {incident}.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено.',
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
            "Пришлите ссылку на пост в Instagram, TikTok, Pinterest, Reddit или X."
        ),
        "bot_description": (
            "Пришлите ссылку на открытый пост — вернётся сам файл. Команда не нужна.\n"
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
            "• ваш числовой id в Telegram, язык и настройки подписи и качества\n"
            "• ссылки, которые вы присылаете: каждую — пока загружается то, что по ней, затем "
            "последние пять, чтобы работали кнопки под этими загрузками. Они удаляются, если вы "
            "не пользуетесь ботом 12 часов\n"
            "• то, что бот только что вам отправил, — 5 минут, чтобы кнопка под ним и та же ссылка, "
            "присланная снова, срабатывали без повторной загрузки. Другая ссылка, /deletemydata "
            "или перезапуск бота удаляют это раньше. Всё это удаляется не позже чем через "
            "12 часов после скачивания\n"
            "• file ID Telegram для файлов, которые бот уже отправлял, — под необратимым кодом "
            "поста, без сведений о том, кто его запрашивал. Они позволяют отправить тот же пост "
            "ещё раз, не скачивая его заново. Прежде чем снова использовать file ID, бот не "
            "реже чем раз в 12 часов проверяет, что пост всё ещё публичный. File ID, которыми "
            "никто не пользуется, удаляются через 90 дней\n"
            "• по одной записи на скачивание: с какой площадки и когда — по ним считается "
            "дневной лимит\n"
            "• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли "
            "ботом хоть кто-нибудь\n"
            "• сколько раз нажимают каждую кнопку — общий счёт за день по всему боту, без сведений о том, кто нажимал\n• сколько всего сделано — ссылки по сайтам, конвертации, стикеры, пересланные сообщения — общий счёт за день по всему боту, без сведений о том, кто\n"
            "• запись о пожертвовании: сумму и платёжный id Telegram\n"
            "• то, что бот в этот момент для вас делает — пока не закончит\n"
            "\n"
            "Кроме этих 5 минут, сами файлы не хранятся: они загружаются, отправляются вам и "
            "удаляются."
        ),
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nПод сбоем, неудавшимся /deletemydata или /feedback, или ошибкой, которая повторяется у вас снова и снова, кнопка «Отправить подробности» предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
        "privacy_seen_by_heading": "Кто ещё это видит:",
        "privacy_seen_by": (
            "• Telegram — он передаёт каждое сообщение в обе стороны и действует по своим "
            "правилам\n"
            "• хостинг, на котором работает бот, и база данных, в которую он пишет"
        ),
        "privacy_others": (
            "• сайт, на который ведёт ссылка, и сервисы скачивания, к которым бот обращается, "
            "когда сайт не отвечает ему напрямую. Они получают ссылку и видят запрос с сервера "
            "бота, а не от вас; что они у себя пишут в логи — их дело и их правила, а не эти."
        ),
        "privacy_kept_for_heading": "Сколько это хранится:",
        "privacy_kept_for": 'Настройки и всё, что бот держит для вас, остаются, пока вы их не сотрёте или не перестанете пользоваться ботом. Отметки об использовании удаляются примерно через три месяца, а дневные счётчики сделанного — в них нет ничего о том, кто, — через 400 дней. Записи о платежах и баланс ⚡ хранятся дольше — по ним разбираются споры о платежах.\n\nНичего из этого не продаётся, не сдаётся в аренду и не используется для рекламы, и никому кроме перечисленных выше не передаётся.',
        "privacy_your_choices": (
            "Что можно сделать:\n"
            "/deletemydata — стереть всё, что бот хранит о вас\n"
            "/terms — для чего ботом можно пользоваться\n"
            "\n"
            "Блокировка бота в Telegram остановит его сообщения, но ничего не сотрёт — если "
            "нужно и то и другое, сначала отправьте /deletemydata."
        ),
        "terms_heading": "📜 Условия",
        "terms_use": (
            "Пользуйтесь ботом по назначению, в рамках закона и правил самого Telegram. Не "
            "используйте его, чтобы кого-то донимать, и не нагружайте сверх заданных лимитов — за то "
            "и другое аккаунт блокируется."
        ),
        "terms_specific": (
            "О скачивании: бот достаёт то, что и так открыто, и отдаёт вам. Это не обход "
            "закрытого аккаунта, и он даже не пытается им быть. Что вы потом сделаете с чужим "
            "фото, видео или постом — это между вами, автором и законом: скачать не значит "
            "присвоить. На каждого есть дневной лимит, чтобы один человек не сделал бота "
            "бесполезным для всех остальных."
        ),
        "terms_money": 'О деньгах: /donate — дело добровольное, деньги идут на то, во что обходятся боты. Платёж в Stars ещё и добавляет ⚡ кредит на конвертации в ConvertBot: 2 ⚡ за ⭐, а за ваши первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держите свою копию всего, что вам важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о вас. Отменить будет нельзя.",
        "delete_data_consequences": 'Язык, настройки подписи и качества и все записи о том, что и когда вы скачивали, будут стёрты. Дневной лимит вместе с ними обнулится. Заодно удаляется последняя загрузка, если бот ещё её хранит; более ранние загрузки здесь никогда не хранились.\n\nЗаписи о пожертвованиях останутся, без username, потому что по ним разбираются споры о платежах. Баланс ⚡ тоже останется — он ваш, если вернётесь.',
        "delete_data_button_yes": "🗑 Стереть",
        "delete_data_button_no": "↩️ Оставить мои данные",
        "delete_data_kept": "Ничего не стёрто.",
        "delete_data_done": (
            "🗑 Готово — стёрто записей: {rows}.\n"
            "\n"
            "Отправьте /start когда захотите; бот примет вас как нового."
        ),
        "delete_data_failed": (
            "Сейчас стереть не получилось — что-то сломалось на моей стороне. Попробуйте ещё раз "
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
        "feedback_ask": (
            "💬 Что вы хотите сказать тому, кто ведёт этих ботов? Идея, проблема, что угодно — "
            "напишите одним сообщением в ответ на это.\n"
            "\n"
            "Его прочитает только он, и ответить вам он не сможет: сообщение уходит без вашего "
            "имени и id. Остановить: /cancel"
        ),
        "feedback_placeholder": "Ваш отзыв",
        "feedback_text_only": "Сюда нужен текст — напишите отзыв словами в ответ на это сообщение или отправьте /cancel.",
        "feedback_thanks": "✅ Спасибо — отправлено. Это прочитает только тот, кто ведёт этих ботов, и ответить он не сможет: в сообщении нет ничего о том, кто вы.",
        "feedback_limit": "Через /feedback сегодня пришло уже {per_day} ваших сообщений — больше за день я не принимаю. Спасибо, напишите завтра.",
        "feedback_failed": "Отзыв не отправлен — что-то сломалось на моей стороне. Попробуйте ещё раз через несколько минут.",
        "cancel_button_feedback": "💬 Отзыв",
        "cancel_item_feedback": "отзыв, который я просил написать",
        "help_brief": (
            "Как это устроено:\n"
            "\n"
            "• Пришлите ссылку — пришлю то, что по ней лежит, без всяких команд. Instagram, TikTok, X, Pinterest и Reddit.\n"
            "• /settings: подпись «via», качество файлов и большие файлы больше 48 МБ — они стоят ⚡ кредит и работают, только если их включить.\n"
            "• Идеи или проблемы: /feedback — это прочитает только тот, кто ведёт этих ботов, ответа не будет.\n"
            "\n"
            "Основные команды: /settings · /balance · /cancel\n"
            "Все команды — в полном руководстве: кнопка ниже или /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 Полное руководство",
        "help_brief_button": "↩️ Кратко",
        "help_page_everything": "Полное руководство: /fullhelp",
        "help_page_gone": "Этой страницы справки больше нет. Отправьте /help, чтобы увидеть актуальные.",
        "help_btn_download": "🔗 Отправка ссылки",
        "helppage_download": (
            "🔗 Отправка ссылки — как устроено скачивание\n"
            "\n"
            "Пришлите ссылку на пост — команда не нужна, — и я пришлю, что в нём:\n"
            "  - Instagram: рилсы, фото, карусели целиком\n"
            "  - TikTok: видео без водяного знака, фото-слайдшоу\n"
            "  - Twitter/X: видео и фото или аккуратная картинка текстового поста\n"
            "  - Pinterest: пин в полном размере\n"
            "  - Reddit: медиа из медиапоста или картинка текстового поста\n"
            "\n"
            "{quota}\n"
            "• Загрузка засчитывается, когда начинается, даже если потом не удалась. Кнопка 📄/🖼 и кнопки 📄 PDF / 🗜 ZIP под доставкой — тоже по одной загрузке. Ту же ссылку, отправленную снова, пока я её ещё качаю, я отмечу 👌 и не засчитаю.\n"
            "• В пути одновременно может быть до {waiting} ваших ссылок; качаю я по {at_once} за раз, остальные ждут очереди.\n"
            "\n"
            "Размер: бесплатно до {free_mb} МБ. {large}\n"
            "\n"
            "Под доставкой:\n"
            "• «📄 Получить несжатым файлом» (или «🖼 Получить сжатым») присылает тот же пост ещё раз в другом качестве; каждая кнопка срабатывает один раз.\n"
            "• Под альбомом: 📄 PDF собирает его фото в один PDF, 🗜 ZIP — всё в один архив. До {merge_items} файлов и {merge_mb} МБ.\n"
            "• /settings: подпись, качество и большие файлы.\n"
            "\n"
            "Пример: пришлите ссылку TikTok вроде https://www.tiktok.com/@name/video/123 — видео придёт без водяного знака."
        ),
        "helppage_download_quota": "Бесплатно — до {per_day} загрузок за любые 24 часа и до {per_hour} за любой час. Счёт идёт назад от текущего момента и не обнуляется в полночь. Когда упрётесь в лимит, я скажу, когда освободится следующая загрузка. Каждый, кто хоть раз заплатил через /donate, любую сумму, получает навсегда {donor_day} в день и {donor_hour} в час.",
        "helppage_download_quota_off": "Бесплатно.",
        "helppage_download_large": "Больше — до {max} МБ — только если включить большие файлы в /settings, в личном чате: ⚡{first} до 100 МБ, каждые следующие 100 МБ дешевле ({max} МБ — ⚡{top}). ⚡ списывается, только когда файл уже скачан, и никогда — если не вышло.",
        "helppage_download_large_off": "Больше — не принимаю.",
        "helppage_settings": (
            "⚙️ /settings — в каком виде приходят загрузки\n"
            "\n"
            "/settings показывает ваши переключатели и как они стоят. Нажмите любой, чтобы изменить; так и останется для всех следующих загрузок.\n"
            "• Подпись (сначала вкл): строка «через @{username}» под каждой загрузкой. Ещё: /caption on или /caption off.\n"
            "• Режим без потерь (сначала выкл). Вкл: загрузки приходят файлом, ровно такими, как в источнике, без сжатия Telegram, — но не проигрываются в чате, пока вы их не откроете. Выкл: приходят фото и видео, которые играют прямо в чате, сжатые Telegram. Ещё: /lossless on или /lossless off. Только для одной загрузки — кнопка 📄/🖼 под ней.\n"
            "{large}\n"
            "Пример: отправьте /lossless on, потом ссылку на Instagram — фото придут файлами, в полном качестве."
        ),
        "helppage_settings_large": "• Большие файлы (сначала выкл). Вкл: загрузку больше {free_mb} МБ я всё равно скачаю, до {max} МБ, и пришлю файлом за ⚡ кредит — ⚡{first} до 100 МБ, ⚡{top} за {max} МБ, — списываю, только когда файл уже скачан. Выкл: всё больше {free_mb} МБ отклоняется, и ничего не списывается. Только в личном чате.",
        "privacy_feedback_heading": "Если вы отправляете /feedback:",
        "privacy_feedback": (
            "Написанное уходит тому, кто ведёт этих ботов, сообщением в Telegram — вместе с "
            "названием бота и вашим языком, но без имени, username и id. Копия хранится в базе "
            "ботов 30 дней, потом удаляется. Читает его только он, и ответить на него он не может."
        ),
        "start_greeting": (
            "Здравствуйте! Пришлите мне ссылку (Instagram, TikTok, Pinterest, Reddit "
            "или Twitter/X), и я скачаю это для вас.\n\n"
        ),
        "help_text": 'Просто пришлите ссылку в любое время — я её заберу, команда не нужна:\n  - Instagram: reels, фото, карусели целиком\n  - TikTok: видео без водяного знака и фото-слайдшоу\n  - Twitter/X: видео и фото, а для текстового поста — аккуратная карточка\n  - Pinterest: пин в полном размере\n  - Reddit: медиа, если это медиа-пост, или карточка, если это текст\n\nПод альбомом появятся две кнопки: 📄 PDF собирает фото в один PDF, 🗜 ZIP — всё в один архив.\n\nКоманды:\n/settings - подпись, качество файлов и большие файлы (больше 48 МБ, за ⚡), всё на одном экране\n/caption on|off - подпись "via @{username}" на загрузках, отдельно\n/lossless on|off - получать загрузки несжатыми файлами\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/feedback - предложить идею или сообщить о проблеме; это прочитает только тот, кто ведёт этих ботов, ответа не будет\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/balance - ваш ⚡ кредит\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n/fullhelp - это полное руководство (/help - краткое)\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
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
        "gift_granted": '🎁 Нас уже больше 100 — спасибо! Вам начислено {amount} ⚡ бесплатного кредита, он действует до {date}. Этого хватит примерно на {conversions} платных конвертаций в {convert} или на скачивание больших файлов в {download}. Ваш баланс: /balance',
        "gift_claimed": "🎁 Подарок: {amount} ⚡ бесплатного кредита! У Mumu ботов уже больше {users} пользователей — это наше спасибо.\nОн действует до {date} (UTC). Этого хватит на платные конвертации (около {conversions}) в {convert} или на скачивание больших файлов в {download}.\nВаш баланс: /balance",
        "download_failed": "Не удалось это скачать: {error}\n\nМожно попробовать ещё раз — пришлите ссылку снова через минуту.",
        "download_blocked": '🚫 Я перебрал все способы достать это, и сайт отказал всем. Дело не в ссылке, а в том, откуда пришёл запрос. Попробуйте через некоторое время — обычно это проходит само.',
        "download_missing": '🔍 Не нашёл этот пост. Обычно это значит, что его удалили или он из закрытого аккаунта. Публичные посты работают.',
        "download_too_big": '📦 Это больше, чем Telegram позволяет мне отправить. Попробуйте ролик покороче.',
        "download_all_routes_failed": '😕 Не получилось, а я пробовал все способы. Подождите минуту и пришлите снова — если повторяется, дело в сайте, а не в ссылке.',
        "fetching": "Загрузка...",
        "reddit_fetch_failed": "Не удалось получить этот пост Reddit: {error}",
        "twitter_fetch_failed_link": "Не удалось получить содержимое поста прямо сейчас — вот ссылка: {url}",
        "unrecognized_message": (
            "Это не похоже на ссылку, которую я узнаю — Instagram, TikTok, "
            "Pinterest, Reddit или Twitter/X — пришлите одну из них, чтобы скачать, "
            "или /help для списка команд."
        ),
        "redeliver_as_file": "📄 Получить несжатым файлом",
        "redeliver_as_compressed": "🖼 Получить сжатым",
        "redeliver_expired": (
            "Для кнопки это уже слишком старая загрузка — пришлите ссылку заново или "
            "поменяйте способ доставки через /lossless."
        ),
        "album_delivered": "Выше {count} файл(ов).",
        "merge_too_big": "📦 Слишком много, чтобы собрать в один файл. Мой предел: файлов — {items}, общий размер — {mb} МБ. Всё это по-прежнему в чате выше.",
        "merge_picture_too_big": "📦 Одно из фото слишком большое для PDF (больше {mp} мегапикселей), поэтому в этот раз PDF не получится. Сами фото — в чате выше.",
        "merge_no_photos": "📄 Для PDF нужно хотя бы два фото, а в этом посте сейчас нашлось меньше. Пришлите ссылку заново или возьмите файлы из чата выше.",
        "merge_failed": "😕 Что-то пошло не так, пока я собирал всё в один файл, — ни PDF, ни ZIP в этот раз не вышло. Файлы выше целы; пришлите ссылку заново, чтобы попробовать ещё раз.",
        "unknown_command": "Я не знаю такую команду. Отправьте /help, чтобы увидеть, что я умею.",
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
        "feedback": "Taklif yoki muammo haqida yozish",
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
        "feedback": "Предложить идею или сообщить о проблеме",
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
        "report_button": '🐞 Send more details',
        "problem_logged_note": "Anonymous technical report saved.",
        "problem_logged_note_optin": "Anonymous technical report saved. You can opt in to send more details.",
        "report_disclaimer": "📨 Send more details with incident {incident}?\n\nSaved already, nothing about you: the bot, code {code}, the time, the version.\n\nSend adds:\n• your Telegram ID\n• your @username, if you have one\n• your language\n• private chat or group\n\nNever your messages or files. Cleared after 30 days, or now with /deletemydata.",
        "report_send": '📨 Send',
        "report_cancel": '✖️ Cancel',
        "report_sent": '✅ Thank you — added to incident {incident}.',
        "report_already": 'Your details are already on incident {incident}. Nothing more was sent.',
        "report_cancelled": 'Cancelled — nothing about you was sent.',
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
            "• how many times each button is tapped, counted per day for the whole bot, with nothing about who tapped it\n• how much was done — links per site, conversions, stickers, relayed messages — counted per day for the whole bot, with nothing about who\n"
            "• a record of any donation: the amount and Telegram's payment id\n"
            "\n"
            "What is not kept is what anybody writes. Messages pass straight through and are "
            "never stored here: they live in the two Telegram chats, and each side can delete "
            "their own copy. Reactions pass through the same way — the bot puts the same one on "
            "the other person's copy and keeps no record of it. "
            "The "
            "one exception is what you choose to send with /feedback, below.\n"
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
            "Under a crash, a failed /deletemydata or /feedback, or an error that keeps "
            "happening to you, \"Send more details\" offers to attach four things to that one "
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
        "privacy_kept_for": 'Settings and anything the bot is holding for you stay until you erase them or stop using it. Counted use is dropped after about three months; the daily counts of what was done, which say nothing about who, after 400 days. Payment records and your ⚡ balance are kept longer, because a dispute about a payment is settled against them.\n\nNothing here is sold, rented or used for advertising, and nothing goes to anyone not named above.',
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
        "feedback_ask": (
            "💬 What would you like to tell the person who runs these bots? A suggestion, a "
            "problem, anything — write it in one message, as a reply to this one.\n"
            "\n"
            "Only they read it, and they can't write back: it is sent without your name or id. "
            "/cancel to stop."
        ),
        "feedback_placeholder": "Your feedback",
        "feedback_text_only": "That one has to be in words — write your feedback as a text reply to this message, or send /cancel.",
        "feedback_thanks": "✅ Thank you — sent. Only the person who runs these bots reads it, and they can't reply: nothing in it says who you are.",
        "feedback_limit": "You've sent {per_day} messages with /feedback today, which is as many as I take in a day. Thank you — write again tomorrow.",
        "feedback_failed": "Your feedback wasn't sent — something went wrong on my side. Please try again in a few minutes.",
        "cancel_button_feedback": "💬 Feedback",
        "cancel_item_feedback": "the feedback I asked you for",
        "privacy_feedback_heading": "If you send /feedback:",
        "privacy_feedback": (
            "What you write reaches the person who runs these bots as a Telegram message, with "
            "which bot it came from and your language — not your name, your username or your id. "
            "Only they read it, and they cannot reply to it. A copy is kept in the bots' "
            "database for 30 days and then deleted."
        ),

        "start_greeting": "Hey! This bot runs anonymous-question inboxes.\n\n",
        "help_brief": (
            "How it works:\n"
            "\n"
            "• Your own inbox: /link gives you a permanent link to post anywhere. Whoever taps it "
            "can write to you right here, and you never see who they are.\n"
            "• Answering: reply to the message you're answering — swipe it, or press and hold it "
            "and choose Reply. Every answer has to be a reply; it's how I know which conversation "
            "it belongs to.\n"
            "• Someone else's link: tap it and write. Your first message goes straight through, "
            "and your name stays hidden.\n"
            "• Reactions: react to a message in a conversation and the other person sees the same "
            "reaction, shown as mine. Standard emoji only — Telegram Premium ones don't go "
            "through.\n"
            "• Ideas or problems: /feedback — only the person who runs these bots reads it, and they can't reply.\n"
            "\n"
            "Main commands: /link · /conversations · /cancel\n"
            "Every command and every reaction: the full guide, below or /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 Full guide",
        "help_brief_button": "↩️ Short version",
        "help_page_everything": "The full guide: /fullhelp",
        "help_page_gone": "That help page no longer exists. Send /help to see the current ones.",
        "helppage_link": (
            "🔗 /link — your anonymous inbox link\n"
            "\n"
            "/link shows your link and whether it is taking messages. Post it anywhere: whoever opens it can write to you here, and you never see who they are. Each time someone opens it, a new conversation starts.\n"
            "Under it:\n"
            "• ⏸️ Pause: no new conversations until you resume; the ones already going still work. Also /pause and /resume.\n"
            "• 🔄 New link: the old link stops starting conversations; the ones already going still work, and a paused inbox stays paused. Also /newlink.\n"
            "• Two counts: how many different guests have written to you, across how many conversations. Also /stats.\n"
            "The link stays the same until you make a new one.\n"
            "\n"
            "Example: send /link, copy the link, and put it in your Instagram bio."
        ),
        "helppage_which": (
            "❓ /which — which conversation is this message from?\n"
            "\n"
            "Reply to any message in this chat with /which: swipe the message, or press and hold it and choose Reply.\n"
            "• You, the inbox's owner: I say its conversation's number. It works for your own replies too, for the later photos of an album, and for each part of a long message.\n"
            "• A guest: I point to where that conversation starts.\n"
            "Handy when several conversations are mixed together in the chat.\n"
            "\n"
            "Example: reply to a message with /which, and I answer: \"{example}\""
        ),
        "reactions_update_note": "🆕 You can now react to messages here — the other person sees your reaction, shown as mine. Send /help to see more.",
        "gift_ad": "🎉 Mumu bots have passed {users} unique users, so we decided to give out {amount} ⚡ of free credit! You can claim it and use it in {download} and {convert}.\n\n<i>To claim it, send any message to either bot: the gift is added automatically. Claim it by {claim_by}; once claimed, it lasts {days} days.</i>",
        "reaction_not_passed": "⚠️ The other person won't see that reaction — only standard emoji are passed on.",
        "reaction_one_only": "⚠️ The other person sees only your newest reaction — one per message is passed on.",
        "help_text": "Two ways to use this bot:\n\nGet your own inbox — /link gives you a permanent link. Post it anywhere public (bio, channel, story, wherever). Anyone who taps it can send you an anonymous message right here in this chat — you won't see who they are.\nAnswer by replying to the message — swipe it, or press and hold it and choose Reply. That is how I know which conversation your answer belongs to, so it is required rather than optional: one public link means several people can be mid-conversation with you at once, and a message that doesn't say which thread it answers could reach the wrong one. Your answer shows up on their end as a real reply too.\n\nGot sent someone else's link? Tap it and write — your first message goes straight through, with your identity hidden. After that, reply to the message you're answering, exactly as the other side does. Tapping the same link again later starts a brand-new conversation, it won't continue the old one.\n\nReactions: react to a message in a conversation and the other person sees the same reaction on their copy. It shows beside my picture, not yours, so it gives nothing away. Change it or take it off and that carries over too. One reaction per message gets through, and only these:\n{reactions}\n⚠️ NOTE: Telegram Premium reactions (custom emoji) can NOT be passed on — the other person won't see them.\n\nCommands:\n/link - get your inbox link\n/conversations - your conversations, open and archived\n/which - send it as a reply to any message: which conversation is that?\n/newlink, /pause, /resume - also buttons on the /link screen\n/blocked - review who you've blocked\n/stats - the counts, which are on the /link screen too\n/donate - chip in for hosting costs (totally optional)\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/feedback - suggest something or report a problem; only whoever runs these bots reads it, and they cannot reply\n/en, /uz, /rus - switch language (or /language, which asks)\n/balance - your ⚡ credit\n/paysupport - trouble with a payment\n/privacy - what I keep about you\n/terms - what I may be used for\n/deletemydata - delete everything I hold on you\n/start - what I do, and how to start\n/fullhelp - this full guide (/help - the short one)\n/archive - send it as a reply to a message to archive that conversation (every row in /conversations has the button too)\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n",
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
        "gift_granted": "🎁 We have passed 100 users, thank you! You get {amount} ⚡ of free credit, good until {date}. It pays for about {conversions} paid conversions in {convert} or big-file downloads in {download}. Your balance: /balance",
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
        "export_removed": "📦 /export has been removed: the bot now keeps less about your conversations. Your messages stay in your Telegram chat.",
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
        "report_button": "🐞 Qo'shimcha ma'lumot yuborish",
        "problem_logged_note": "Anonim texnik hisobot saqlandi.",
        "problem_logged_note_optin": "Anonim texnik hisobot saqlandi. Xohlasangiz, qo'shimcha ma'lumot yuborishingiz mumkin.",
        "report_disclaimer": "📨 {incident} hodisasiga qo'shimcha ma'lumot yuborasizmi?\n\nAllaqachon saqlangan, siz haqingizda hech narsa yo'q: bot, {code} kodi, vaqt, versiya.\n\n\"Yuborish\" qo'shadi:\n• Telegram ID raqamingiz\n• bo'lsa, @username'ingiz\n• tilingiz\n• shaxsiy suhbatmi yoki guruh\n\nXabarlaringiz va fayllaringiz hech qachon kirmaydi. 30 kundan keyin o'chiriladi, /deletemydata bilan esa darhol.",
        "report_send": '📨 Yuborish',
        "report_cancel": '✖️ Bekor qilish',
        "report_sent": "✅ Rahmat — {incident} hodisasiga qo'shildi.",
        "report_already": "Ma'lumotlaringiz {incident} hodisasiga allaqachon biriktirilgan. Boshqa hech narsa yuborilmadi.",
        "report_cancelled": "Bekor qilindi — siz haqingizda hech narsa yuborilmadi.",
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
        "privacy_stored": "• Telegram ID raqamingiz va tanlagan tilingiz\n• xabarlar havolangiz, agar yaratgan bo'lsangiz\n• kim kim bilan yozishayotgani: suhbat ikki foydalanuvchi ID raqami va tartib raqami sifatida saqlanadi — javob to'g'ri suhbatga yetib borishi shunga bog'liq\n• qaysi xabar qaysi suhbatga tegishli ekani (xabar raqami bo'yicha) va u qachon yetkazilgani\n• kimlarni bloklaganingiz\n• botdan foydalangan vaqtingiz — bot egasi botdan umuman foydalanilayotganini bilishi uchun\n• har bir tugma necha marta bosilgani — butun bot bo'yicha kunlik umumiy hisob, kim bosgani haqida hech qanday ma'lumotsiz\n• qancha ish qilingani — sayt bo'yicha havolalar, konvertatsiyalar, stikerlar, yuborilgan xabarlar — butun bot bo'yicha kunlik hisob, kim ekani haqida ma'lumotsiz\n• xayriya qilsangiz, uning yozuvi: miqdori va Telegram to'lov raqami\n\nYozilgan xabarlarning o'zi saqlanmaydi. Xabarlar to'g'ridan-to'g'ri yetkaziladi va bu yerda saqlanmaydi: ular ikkala tomonning Telegram chatida turadi va har kim o'z nusxasini o'chira oladi. Reaksiyalar ham xuddi shunday o'tadi: bot suhbatdoshingizdagi nusxaga xuddi shu reaksiyani qo'yadi, lekin buni hech qayerga yozib qo'ymaydi. Bunga yagona istisno — /feedback orqali o'zingiz yuborgan xabar (pastda).\n\nAnonimlik — siz yozayotgan odamga nisbatan: unga ismingiz, foydalanuvchi nomingiz yoki ID raqamingiz hech qachon ko'rsatilmaydi. Botning o'zidan esa yashirinib bo'lmaydi: yuqoridagi bog'lanishsiz javob umuman yetib bormasdi.",
        "privacy_problems_heading": "Nimadir noto'g'ri ketganda:",
        "privacy_problems": "Bot kimgadir xato ko'rsatsa, uni o'zi yozib qo'yadi: xato kodi, hodisa raqami, qachon yuz bergani va bot versiyasi. Bularda siz haqingizda hech narsa yo'q — ID raqamingiz ham, ismingiz ham, nima yuborganingiz ham. Hech kim xabar bermagan nosozlik ham nosozligicha qoladi, shuning uchun bot so'ralishini kutmaydi.\n\nIshdan chiqish, bajarilmagan /deletemydata yoki /feedback, yoki sizda takror-takror yuz berayotgan xato ostidagi \"Qo'shimcha ma'lumot yuborish\" tugmasi o'sha bitta hodisaga to'rt narsani biriktirishni taklif qiladi: Telegram ID raqamingiz, bo'lsa @username'ingiz, siz tanlagan til va bu suhbat shaxsiymi yoki guruhmi. To'rttasi ham avval ekranda aytiladi va \"Yuborish\"ni bosmasangiz hech narsa yuborilmaydi. Yozganlaringiz va yuborgan fayllaringiz esa bunga hech qachon kirmaydi.\n\nBu to'rttasi 30 kundan keyin o'z-o'zidan o'chiriladi, /deletemydata esa darhol o'chiradi. Xatolik yozuvining o'zi qoladi — u haqiqatan yuz bergan — shunchaki endi kim duch kelgani yozilmaydi. Yozuvlarning o'zi 180 kundan keyin o'chiriladi.",
        "privacy_seen_by_heading": "Yana kim ko'ra oladi:",
        "privacy_seen_by": "• Telegram — barcha xabarlar u orqali o'tadi va u o'z qoidalari asosida ishlaydi\n• bot joylashgan hosting va bot foydalanadigan ma'lumotlar bazasi",
        "privacy_others": "• boshqa hech kim — xabarlar faqat Telegram orqali o'tadi, tashqi xizmatlarga murojaat qilinmaydi",
        "privacy_kept_for_heading": "Qancha vaqt saqlanadi:",
        "privacy_kept_for": "Sozlamalaringiz va bot siz uchun saqlab turgan narsalar ularni o'chirmaguningizcha yoki botdan foydalanishni to'xtatmaguningizcha turadi. Foydalanish qaydlari taxminan uch oydan keyin o'chiriladi; qancha ish qilinganining kunlik hisobi esa — unda kimligi yo'q — 400 kundan keyin. To'lov yozuvlari va ⚡ balansingiz esa uzoqroq saqlanadi, chunki to'lov bo'yicha nizolar ular asosida hal qilinadi.\n\nBu ma'lumotlar sotilmaydi, ijaraga berilmaydi, reklamada ishlatilmaydi va yuqorida aytilganlardan boshqa hech kimga berilmaydi.",
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
        "feedback_ask": (
            "💬 Bu botlarni yuritayotgan odamga nima demoqchisiz? Taklif, muammo — nima bo'lsa "
            "ham, bitta xabarda, shu xabarga javob qilib yozing.\n"
            "\n"
            "Uni faqat o'sha odam o'qiydi va sizga javob yoza olmaydi: xabar ismingiz va ID "
            "raqamingizsiz yuboriladi. To'xtatish: /cancel"
        ),
        "feedback_placeholder": "Fikringiz",
        "feedback_text_only": "Bu yerga faqat matn qabul qilinadi — fikringizni shu xabarga javob qilib so'z bilan yozing yoki /cancel yuboring.",
        "feedback_thanks": "✅ Rahmat — yuborildi. Uni faqat bu botlarni yuritayotgan odam o'qiydi va javob yoza olmaydi: xabarda kimligingiz ko'rsatilmagan.",
        "feedback_limit": "Bugun /feedback orqali {per_day} ta xabar yubordingiz — bir kunda shuncha qabul qilaman. Rahmat, ertaga yana yozishingiz mumkin.",
        "feedback_failed": "Fikringiz yuborilmadi — bot tomonida nimadir buzildi. Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring.",
        "cancel_button_feedback": "💬 Fikr-mulohaza",
        "cancel_item_feedback": "men so'ragan fikr-mulohaza",
        "privacy_feedback_heading": "/feedback yuborsangiz:",
        "privacy_feedback": (
            "Yozganingiz bu botlarni yuritayotgan odamga Telegram xabari sifatida yetib boradi — "
            "qaysi botdan kelgani va tilingiz bilan birga, lekin ismingiz, foydalanuvchi nomingiz "
            "va ID raqamingizsiz. Uni faqat o'sha odam o'qiydi va unga javob yoza olmaydi. "
            "Nusxasi botlar bazasida 30 kun saqlanadi, keyin o'chiriladi."
        ),
        "cancel_item_anon_session": "ochiq turgan anonim suhbat — yangisini boshlash uchun havolani qayta bosing",
        "cancel_button_anon_session": "💬 Siz turgan anonim suhbat",
        "start_greeting": "Salom! Bu bot anonim savol-javob qutilarini boshqaradi.\n\n",
        "help_brief": (
            "Bot qanday ishlaydi:\n"
            "\n"
            "• O'z qutingiz: /link sizga doimiy havola beradi — uni istalgan joyga joylang. "
            "Havolani ochgan har kim sizga shu yerda yoza oladi, kimligi esa sizga ko'rinmaydi.\n"
            "• Javob berish: javob berayotgan xabaringizni o'ngga suring yoki uni bosib turib "
            "«Javob berish»ni tanlang. Har bir javob shunday yozilishi shart — javob qaysi "
            "suhbatga tegishli ekanini shundan bilaman.\n"
            "• Birovning havolasi: uni oching va yozing. Birinchi xabaringiz darhol yetib boradi, "
            "kimligingiz esa yashirin qoladi.\n"
            "• Reaksiyalar: suhbatdagi xabarga reaksiya qo'ysangiz, suhbatdoshingiz ham xuddi "
            "shuni ko'radi — u mening nomimdan chiqadi. Faqat oddiy emojilar o'tadi, Telegram "
            "Premium reaksiyalari o'tmaydi.\n"
            "• Taklif yoki muammo: /feedback — uni faqat bu botlarni yuritayotgan odam o'qiydi, javob qaytmaydi.\n"
            "\n"
            "Asosiy buyruqlar: /link · /conversations · /cancel\n"
            "Barcha buyruqlar va reaksiyalar: to'liq qo'llanmada — pastdagi tugma yoki "
            "/fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 To'liq qo'llanma",
        "help_brief_button": "↩️ Qisqa variant",
        "help_page_everything": "To'liq qo'llanma: /fullhelp",
        "help_page_gone": "Bu yordam sahifasi endi yo'q. Hozirgilarini ko'rish uchun /help yuboring.",
        "helppage_link": (
            "🔗 /link — anonim qutingiz havolasi\n"
            "\n"
            "/link havolangizni va u xabar qabul qilayotganini ko'rsatadi. Uni istalgan joyga joylang: uni ochgan har kim sizga shu yerda yoza oladi, siz esa kimligini hech qachon ko'rmaysiz. Har safar kimdir uni ochganda yangi suhbat boshlanadi.\n"
            "Ostida:\n"
            "• ⏸️ To'xtatish: davom ettirmaguningizcha yangi suhbatlar boshlanmaydi; boshlangan suhbatlar ishlayveradi. Yana: /pause va /resume.\n"
            "• 🔄 Yangi havola: eski havola endi suhbat boshlamaydi; boshlanganlari ishlayveradi, pauzadagi quti pauzada qoladi. Yana: /newlink.\n"
            "• Ikki son: sizga nechta turli mehmon yozgani va jami nechta suhbatda. Yana: /stats.\n"
            "Yangisini yaratmaguningizcha havola o'zgarmaydi.\n"
            "\n"
            "Misol: /link yuboring, havolani nusxalang va Instagram bio'ingizga qo'ying."
        ),
        "helppage_which": (
            "❓ /which — bu xabar qaysi suhbatdan?\n"
            "\n"
            "Chatdagi istalgan xabarga /which bilan javob bering: xabarni suring yoki bosib turing va \"Javob berish\" ni tanlang.\n"
            "• Siz, quti egasi: suhbatning raqamini aytaman. Bu o'z javoblaringiz, albomning keyingi rasmlari va uzun xabarning har bir qismi uchun ham ishlaydi.\n"
            "• Mehmon: o'sha suhbat qayerdan boshlanganini ko'rsataman.\n"
            "Chatda bir nechta suhbat aralashib ketganda qulay.\n"
            "\n"
            "Misol: xabarga /which bilan javob bering, men shunday javob beraman: \"{example}\""
        ),
        "reactions_update_note": "🆕 Endi bu yerda xabarlarga reaksiya qo'yishingiz mumkin — suhbatdoshingiz uni mening nomimdan ko'radi. Batafsil: /help",
        "gift_ad": "🎉 Mumu botlarida {users} dan ortiq foydalanuvchi bo'ldi, shuning uchun hammaga {amount} ⚡ bepul kredit berishga qaror qildik! Uni {download} va {convert} botlarida olib, ishlatishingiz mumkin.\n\n<i>Olish uchun ikki botdan biriga istalgan xabar yuboring: sovg'a avtomatik qo'shiladi. Uni {claim_by} gacha oling; olingandan keyin {days} kun amal qiladi.</i>",
        "reaction_not_passed": "⚠️ Suhbatdoshingiz bu reaksiyani ko'rmaydi — faqat oddiy emojilar yetkaziladi.",
        "reaction_one_only": "⚠️ Suhbatdoshingiz faqat oxirgi reaksiyangizni ko'radi — har bir xabarga bittasi yetkaziladi.",
        "help_text": "Bu botdan ikki xil foydalanish mumkin:\n\nO'z qutingizni oching — /link sizga doimiy havola beradi. Uni istalgan ochiq joyga joylang (bio, kanal, story — qayerda bo'lsa ham). Havolani ochgan har kim sizga shu chatning o'zida anonim xabar yubora oladi — kimligi sizga ko'rinmaydi.\nJavob berish uchun xabarni o'ngga suring yoki uni bosib turib «Javob berish»ni tanlang. Shunda javobingiz qaysi suhbatga tegishli ekanini bilaman, shuning uchun bu shart: havola ochiq joyda turgani uchun bir vaqtda bir nechta odam sizga yozayotgan bo'lishi mumkin, qaysi suhbatga javob ekani ko'rsatilmagan xabar esa boshqa odamga borib qolishi mumkin. Javobingiz ularga ham haqiqiy javob sifatida ko'rinadi.\n\nSizga boshqa birovning havolasini yuborishdimi? Uni bosing va yozing — birinchi xabaringiz kimligingiz yashirilgan holda darhol yetib boradi. Undan keyin xuddi qarshi tomon kabi, javob berayotgan xabaringizga javob tarzida yozing. Keyinroq havolani yana bossangiz, eski suhbat davom etmaydi — yangisi boshlanadi.\n\nReaksiyalar: suhbatdagi xabarga reaksiya qo'ysangiz, suhbatdoshingiz o'zidagi nusxada xuddi shu reaksiyani ko'radi. U sizning emas, mening rasmim yonida chiqadi, shuning uchun hech narsani oshkor qilmaydi. Reaksiyani almashtirsangiz yoki olib tashlasangiz, u tomonda ham shunday bo'ladi. Har bir xabarga bitta reaksiya o'tadi va faqat quyidagilar:\n{reactions}\n⚠️ DIQQAT: Telegram Premium reaksiyalari (maxsus emojilar) suhbatdoshingizga O'TMAYDI — u ularni ko'rmaydi.\n\nBuyruqlar:\n/link - qutingiz havolasini olish\n/conversations - suhbatlaringiz: ochiqlari va arxivdagilari\n/which - istalgan xabarga javob qilib yuboring: u qaysi suhbatdan ekanini aytaman\n/newlink, /pause, /resume - bular /link ekranida tugma sifatida ham bor\n/blocked - bloklanganlar ro'yxati\n/stats - qisqa statistika; u /link ekranida ham bor\n/donate - server xarajatlariga hissa qo'shish (ixtiyoriy)\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/feedback - taklif yozish yoki muammo haqida xabar berish; uni faqat botlarni yuritayotgan odam o'qiydi, javob qaytmaydi\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n/balance - ⚡ kreditingiz\n/paysupport - to'lov bilan muammo\n/privacy - siz haqingizda nimalarni saqlayman\n/terms - botdan foydalanish shartlari\n/deletemydata - siz haqingizdagi hamma narsani o'chirish\n/start - bu bot nima qiladi va qanday boshlash kerak\n/fullhelp - shu to'liq qo'llanma (/help - qisqasi)\n/archive - xabarga javob qilib yuboring: o'sha suhbat arxivga o'tadi (/conversations ichidagi har bir suhbatda ham shu tugma bor)\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — /donate orqali to'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO'LMAYDI.\n\n",
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
        "gift_granted": "🎁 Bizda 100 dan ortiq foydalanuvchi bo'ldi, rahmat! Sizga {amount} ⚡ bepul kredit berildi, u {date} gacha amal qiladi. Bu {convert} orqali taxminan {conversions} ta pullik konvertatsiya yoki {download} orqali katta fayllarni yuklab olish uchun yetadi. Balansingiz: /balance",
        "reply_forbidden": "Javobingizni yetkazib bo'lmadi — ular sizni bloklagan yoki botni tark etgan bo'lishi mumkin.",
        "reply_failed": "Javobingizni yetkazib bo'lmadi: {error}",
        "delivered_confirmation": "Yetkazildi ↩️",
        "reply_stale": "Xabaringiz yuborilmadi — javob bergan xabaringiz hech bir ochiq suhbatga tegishli emas. Men shu yerga yetkazgan xabarlardan biriga javob tarzida yozing: uni o'ngga suring yoki bosib turib «Javob berish»ni tanlang.",
        "generic_nudge": "Bu nima uchunligini tushunmadim — agar sizga kimdir havola yuborgan bo'lsa, avval o'shani bosing. O'z qutingiz kerakmi? /link yuboring.",
        "export_removed": "📦 /export olib tashlandi: bot endi suhbatlaringiz haqida kamroq ma'lumot saqlaydi. Xabarlaringiz Telegram chatingizda qoladi.",
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
        "flood_wait": "Вы отправляете быстрее, чем я успеваю — подождите примерно {seconds} секунд(ы) и продолжайте.",
        "sibling_blurb": "Тоже часть этой семьи ботов, смотрите ниже \U0001f447",
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
        "report_button": '🐞 Отправить подробности',
        "problem_logged_note": 'Анонимный технический отчёт сохранён.',
        "problem_logged_note_optin": 'Анонимный технический отчёт сохранён. По желанию можно отправить подробности.',
        "report_disclaimer": "📨 Отправить подробности к случаю {incident}?\n\nУже сохранено, без ничего о вас: бот, код {code}, время, версия.\n\n«Отправить» добавит:\n• ваш Telegram ID\n• ваш @username, если есть\n• ваш язык\n• личный чат или группа\n\nВаши сообщения и файлы — никогда. Стирается через 30 дней или сразу через /deletemydata.",
        "report_send": '📨 Отправить',
        "report_cancel": '✖️ Отмена',
        "report_sent": '✅ Спасибо — добавлено к случаю {incident}.',
        "report_already": 'Ваши данные уже на случае {incident}. Больше ничего не отправлено.',
        "report_cancelled": 'Отменено — о вас ничего не отправлено.',
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
            "Постоянная ссылка, по которой вам пишут анонимно."
        ),
        "bot_description": (
            "Получите ссылку и выложите где угодно. Любой, кто её откроет, напишет вам, не показав, "
            "кто он, а вы сможете ответить — настоящей веткой, и таких веток может идти сразу "
            "несколько.\n"
            "\n"
            "Они анонимны для вас, но не для бота: чтобы ответ попал в нужную ветку, бот хранит, "
            "какие два аккаунта переписываются, и никогда не хранит то, что вы пишете. "
            "Подробности — /privacy.\n"
            "\n"
            "Английский, узбекский и русский."
        ),

        "privacy_heading": "🔒 Конфиденциальность",
        "privacy_kept_heading": "Что бот хранит:",
        "privacy_stored": (
            "• ваш числовой id в Telegram и выбранный язык\n"
            "• вашу ссылку-инбокс, если вы её сделали\n"
            "• кто с кем говорит: разговор хранится как пара id и номер — именно поэтому ответ "
            "попадает в нужную ветку\n"
            "• какое сообщение к какому разговору относится, по id сообщения, и когда оно было доставлено\n"
            "• кого вы заблокировали\n"
            "• отметку времени на каждое обращение к боту — чтобы владелец видел, пользуется ли "
            "ботом хоть кто-нибудь\n"
            "• сколько раз нажимают каждую кнопку — общий счёт за день по всему боту, без сведений о том, кто нажимал\n• сколько всего сделано — ссылки по сайтам, конвертации, стикеры, пересланные сообщения — общий счёт за день по всему боту, без сведений о том, кто\n"
            "• запись о пожертвовании: сумму и платёжный id Telegram\n"
            "\n"
            "Чего здесь нет — самих сообщений. Они проходят насквозь и тут не сохраняются: они "
            "лежат в двух чатах Telegram, и каждый может удалить свою копию. Реакции проходят так "
            "же: бот ставит такую же на копию собеседника и нигде её не записывает. "
            "Единственное исключение — то, что вы отправите через /feedback (ниже).\n"
            "\n"
            "Анонимность — это анонимность от того, кому вы пишете. Ему никогда не показывают ни "
            "ваше имя, ни username, ни id. От самого бота это не анонимность: без той самой пары "
            "id ответ просто некуда было бы доставить."
        ),
        "privacy_problems_heading": "Когда что-то ломается:",
        "privacy_problems": "Каждую ошибку, которую бот кому-то показывает, он записывает сам: код ошибки, номер случая, когда это произошло и версию бота. О вас там нет ничего — ни вашего id, ни имени, ни того, что вы отправили. Сбой, о котором никто не сообщил, остаётся сбоем, поэтому бот не ждёт, пока его попросят.\n\nПод сбоем, неудавшимся /deletemydata или /feedback, или ошибкой, которая повторяется у вас снова и снова, кнопка «Отправить подробности» предлагает привязать к этому случаю четыре вещи: ваш Telegram id, ваш @username, если он есть, выбранный вами язык и то, личный это чат или группа. Все четыре сначала названы на экране, и ничего не отправляется, пока вы не нажмёте «Отправить». Того, что вы написали, и отправленных файлов там не бывает никогда.\n\nЭти четыре стираются сами через 30 дней, а /deletemydata стирает их сразу. Запись об ошибке остаётся — она действительно произошла — просто перестаёт говорить, кто на неё наткнулся. Сами записи удаляются через 180 дней.",
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
        "privacy_kept_for": 'Настройки и всё, что бот держит для вас, остаются, пока вы их не сотрёте или не перестанете пользоваться ботом. Отметки об использовании удаляются примерно через три месяца, а дневные счётчики сделанного — в них нет ничего о том, кто, — через 400 дней. Записи о платежах и баланс ⚡ хранятся дольше — по ним разбираются споры о платежах.\n\nНичего из этого не продаётся, не сдаётся в аренду и не используется для рекламы, и никому кроме перечисленных выше не передаётся.',
        "privacy_your_choices": (
            "Что можно сделать:\n"
            "/deletemydata — стереть всё, что бот хранит о вас\n"
            "/terms — для чего ботом можно пользоваться\n"
            "\n"
            "Блокировка бота в Telegram остановит его сообщения, но ничего не сотрёт — если "
            "нужно и то и другое, сначала отправьте /deletemydata."
        ),
        "terms_heading": "📜 Условия",
        "terms_use": (
            "Пользуйтесь ботом по назначению, в рамках закона и правил самого Telegram. Не "
            "используйте его, чтобы кого-то донимать, и не нагружайте сверх заданных лимитов — за то "
            "и другое аккаунт блокируется."
        ),
        "terms_specific": (
            "О сообщениях: скрытое имя — не индульгенция. Угрозы, травля и всё незаконное "
            "остаются ровно тем же самым, когда отправитель анонимен, а владелец инбокса может "
            "заблокировать отправителя навсегда. Кто открыл инбокс, тот и отвечает за то, что он "
            "предлагает ему присылать."
        ),
        "terms_money": 'О деньгах: /donate — дело добровольное, деньги идут на то, во что обходятся боты. Платёж в Stars ещё и добавляет ⚡ кредит на конвертации в ConvertBot: 2 ⚡ за ⭐, а за ваши первые 500 Stars — 6 и за следующие 500 — 4. Всё сверх 2 — бонусный кредит, он сгорает через 90 дней после платежа. Платежи ОКОНЧАТЕЛЬНЫЕ: Stars НЕ возвращаются, а кредит НЕЛЬЗЯ вывести или обменять обратно на Stars. Все платежи проводит Telegram, бот никогда не видит номер карты. Проблема с платежом — /paysupport.',
        "terms_no_warranty": (
            "Без обещаний: бота ведёт один человек, он бесплатный и может тормозить, ошибаться "
            "или вовсе не работать без предупреждения. Держите свою копию всего, что вам важно."
        ),
        "policy_full_text": "Полный текст: {url}",
        "policy_contact": "Вопросы, жалобы или запрос по данным: {contact}",
        "delete_data_confirm": "⚠️ Это сотрёт всё, что бот хранит о вас. Отменить будет нельзя.",
        "delete_data_consequences": 'Ваша ссылка перестанет работать — каждая её копия, которую кто-либо выложил, навсегда. Открытые разговоры перестанут маршрутизироваться: ответить в них не сможет ни одна из сторон, и список заблокированных уйдёт вместе с ними.\n\nУже отправленные сообщения это не затронет. Здесь они и не хранились — они в чатах Telegram, и каждый удаляет свою копию сам.\n\nЗаписи о пожертвованиях останутся, без username, потому что по ним разбираются споры о платежах. Баланс ⚡ тоже останется — он ваш, если вернётесь.',
        "delete_data_button_yes": "🗑 Стереть",
        "delete_data_button_no": "↩️ Оставить мои данные",
        "delete_data_kept": "Ничего не стёрто.",
        "delete_data_done": (
            "🗑 Готово — стёрто записей: {rows}.\n"
            "\n"
            "Отправьте /start, когда захотите; бот примет вас как нового."
        ),
        "delete_data_failed": (
            "Сейчас стереть не получилось — что-то сломалось на моей стороне. Попробуйте ещё раз "
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
        "feedback_ask": (
            "💬 Что вы хотите сказать тому, кто ведёт этих ботов? Идея, проблема, что угодно — "
            "напишите одним сообщением в ответ на это.\n"
            "\n"
            "Его прочитает только он, и ответить вам он не сможет: сообщение уходит без вашего "
            "имени и id. Остановить: /cancel"
        ),
        "feedback_placeholder": "Ваш отзыв",
        "feedback_text_only": "Сюда нужен текст — напишите отзыв словами в ответ на это сообщение или отправьте /cancel.",
        "feedback_thanks": "✅ Спасибо — отправлено. Это прочитает только тот, кто ведёт этих ботов, и ответить он не сможет: в сообщении нет ничего о том, кто вы.",
        "feedback_limit": "Через /feedback сегодня пришло уже {per_day} ваших сообщений — больше за день я не принимаю. Спасибо, напишите завтра.",
        "feedback_failed": "Отзыв не отправлен — что-то сломалось на моей стороне. Попробуйте ещё раз через несколько минут.",
        "cancel_button_feedback": "💬 Отзыв",
        "cancel_item_feedback": "отзыв, который я просил написать",
        "privacy_feedback_heading": "Если вы отправляете /feedback:",
        "privacy_feedback": (
            "Написанное уходит тому, кто ведёт этих ботов, сообщением в Telegram — вместе с "
            "названием бота и вашим языком, но без имени, username и id. Копия хранится в базе "
            "ботов 30 дней, потом удаляется. Читает его только он, и ответить на него он не может."
        ),
        "cancel_item_anon_session": "\u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0439 \u0430\u043d\u043e\u043d\u0438\u043c\u043d\u044b\u0439 \u0447\u0430\u0442 — \u043d\u0430\u0436\u043c\u0438\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443 \u0441\u043d\u043e\u0432\u0430, \u0447\u0442\u043e\u0431\u044b \u043d\u0430\u0447\u0430\u0442\u044c \u043d\u043e\u0432\u044b\u0439",
        "cancel_button_anon_session": "💬 Анонимный чат, в котором вы",
        "start_greeting": "Здравствуйте! Этот бот управляет анонимными почтовыми ящиками для вопросов.\n\n",
        "help_brief": (
            "Как это устроено:\n"
            "\n"
            "• Свой ящик: /link даёт постоянную ссылку — разместите её где угодно. Любой, кто по "
            "ней перейдёт, сможет написать вам сюда, а вы не увидите, кто это.\n"
            "• Ответы: отвечайте на конкретное сообщение — смахните его вправо или нажмите и "
            "удерживайте, затем «Ответить». Так нужно отвечать всегда: по ответу я понимаю, к "
            "какой беседе он относится.\n"
            "• Чужая ссылка: перейдите по ней и напишите. Первое сообщение уйдёт сразу, а ваше "
            "имя останется скрытым.\n"
            "• Реакции: поставьте реакцию на сообщение в беседе — собеседник увидит такую же, от "
            "моего имени. Только обычные эмодзи: реакции Telegram Premium не передаются.\n"
            "• Идеи или проблемы: /feedback — это прочитает только тот, кто ведёт этих ботов, ответа не будет.\n"
            "\n"
            "Основные команды: /link · /conversations · /cancel\n"
            "Все команды и все реакции — в полном руководстве: кнопка ниже или /fullhelp.\n"
            "\n"
        ),
        "help_full_button": "📖 Полное руководство",
        "help_brief_button": "↩️ Кратко",
        "help_page_everything": "Полное руководство: /fullhelp",
        "help_page_gone": "Этой страницы справки больше нет. Отправьте /help, чтобы увидеть актуальные.",
        "helppage_link": (
            "🔗 /link — ссылка на ваш анонимный ящик\n"
            "\n"
            "/link показывает вашу ссылку и принимает ли она сообщения. Разместите её где угодно: любой, кто её откроет, сможет написать вам здесь, а вы никогда не увидите, кто это. Каждый раз, когда кто-то её открывает, начинается новая беседа.\n"
            "Под ней:\n"
            "• ⏸️ Пауза: новых бесед не будет, пока не возобновите; уже идущие продолжают работать. Ещё: /pause и /resume.\n"
            "• 🔄 Новая ссылка: старая перестаёт начинать беседы; уже идущие работают, а ящик на паузе так и остаётся на паузе. Ещё: /newlink.\n"
            "• Два числа: сколько разных гостей вам написали и в скольких беседах. Ещё: /stats.\n"
            "Ссылка не меняется, пока вы не сделаете новую.\n"
            "\n"
            "Пример: отправьте /link, скопируйте ссылку и поставьте её в био Instagram."
        ),
        "helppage_which": (
            "❓ /which — из какой беседы это сообщение?\n"
            "\n"
            "Ответьте на любое сообщение в этом чате командой /which: смахните сообщение или зажмите его и выберите «Ответить».\n"
            "• Вы, владелец ящика: я назову номер беседы. Это работает и для ваших собственных ответов, и для следующих фото альбома, и для каждой части длинного сообщения.\n"
            "• Гость: я укажу, где эта беседа начинается.\n"
            "Удобно, когда в чате перемешались несколько бесед.\n"
            "\n"
            "Пример: ответьте на сообщение командой /which, и я отвечу: «{example}»"
        ),
        "reactions_update_note": "🆕 Теперь здесь можно ставить реакции на сообщения — собеседник увидит их от моего имени. Подробнее: /help",
        "gift_ad": "🎉 У Mumu ботов уже больше {users} уникальных пользователей, поэтому мы решили раздать {amount} ⚡ бесплатного кредита! Получить и потратить его можно в {download} и {convert}.\n\n<i>Чтобы получить подарок, отправьте любое сообщение любому из этих двух ботов: он начислится автоматически. Получите его до {claim_by}; после получения он действует {days} дней.</i>",
        "reaction_not_passed": "⚠️ Собеседник не увидит эту реакцию — передаются только обычные эмодзи.",
        "reaction_one_only": "⚠️ Собеседник видит только вашу последнюю реакцию — на сообщение передаётся одна.",
        "help_text": 'Есть два способа пользоваться этим ботом:\n\nЗаведите свой ящик — /link даёт вам постоянную ссылку. Разместите её где угодно на виду (в био, канале, истории — где хотите). Любой, кто по ней перейдёт, сможет отправить вам анонимное сообщение прямо в этот чат — вы не увидите, кто это.\nОтвечайте ответом на сообщение — смахните его вправо или нажмите и удерживайте и выберите «Ответить». Так я понимаю, к какой беседе относится ваш ответ, поэтому это обязательно, а не по желанию: ссылка открытая, с вами могут говорить сразу несколько человек, и сообщение, которое не говорит, на что отвечает, может уйти не туда. У собеседника ваш ответ тоже появится как настоящий ответ.\n\nВам прислали чужую ссылку? Перейдите по ней и напишите — первое сообщение уйдёт сразу, а ваша личность останется скрытой. Дальше отвечайте ответом на сообщение, точно так же, как другая сторона. Если позже перейти по той же ссылке снова, начнётся новая беседа, а не продолжение старой.\n\nРеакции: поставьте реакцию на сообщение в беседе — собеседник увидит такую же на своей копии. Она стоит рядом с моей картинкой, а не с вашей, так что ничего не выдаёт. Поменяете или уберёте её — у собеседника будет так же. На одно сообщение передаётся одна реакция, и только из этого списка:\n{reactions}\n⚠️ ВНИМАНИЕ: реакции Telegram Premium (особые эмодзи) НЕ передаются — собеседник их не увидит.\n\nКоманды:\n/link - получить ссылку на свой ящик\n/conversations - ваши разговоры: открытые и в архиве\n/which - отправьте ответом на любое сообщение: скажу, из какого оно разговора\n/newlink, /pause, /resume - они же кнопки на экране /link\n/blocked - посмотреть, кого вы заблокировали\n/stats - краткая статистика, она же на экране /link\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/feedback - предложить идею или сообщить о проблеме; это прочитает только тот, кто ведёт этих ботов, ответа не будет\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n/balance - ваш ⚡ кредит\n/paysupport - проблема с оплатой\n/privacy - что я о вас храню\n/terms - для чего можно пользоваться ботом\n/deletemydata - удалить всё, что я о вас храню\n/start - что этот бот делает и с чего начать\n/fullhelp - это полное руководство (/help - краткое)\n/archive - отправьте ответом на сообщение, и этот разговор уйдёт в архив (в /conversations такая кнопка есть у каждого разговора)\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
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
            "Это сообщение не относится ни к одной открытой здесь беседе. Возможно, оно ваше "
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
        "reply_no_match": "Ваше сообщение не отправлено — не удалось сопоставить этот ответ с какой-либо беседой.",
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
        "gift_granted": "🎁 Нас уже больше 100 — спасибо! Вам начислено {amount} ⚡ бесплатного кредита, он действует до {date}. Этого хватит примерно на {conversions} платных конвертаций в {convert} или на скачивание больших файлов в {download}. Ваш баланс: /balance",
        "reply_forbidden": "Не удалось доставить ваш ответ — возможно, вас заблокировали или человек покинул бота.",
        "reply_failed": "Не удалось доставить ваш ответ: {error}",
        "delivered_confirmation": "Доставлено ↩️",
        "reply_stale": (
            "Этого сообщения нет в моих записях, поэтому я не могу понять, какой беседе оно "
            "отвечает. Ничего не отправлено. Ответьте на одно из сообщений, которые я сюда "
            "доставил — смахните его или нажмите и удерживайте, затем «Ответить»."
        ),
        "generic_nudge": "Не совсем понял, для чего это — если кто-то прислал вам ссылку, сначала перейдите по ней. Хотите свой ящик? Отправьте /link.",
        "export_removed": "📦 Команда /export удалена: теперь бот хранит меньше данных о ваших переписках. Ваши сообщения остаются в чате Telegram.",
        "archive_needs_reply": (
            "Ответьте на сообщение из той беседы, которую хотите убрать в архив, и отправьте "
            "/archive ещё раз — смахните сообщение или нажмите и удержите его и выберите «Ответить». "
            "Либо откройте /conversations и выберите беседу из списка."
        ),
        "archive_not_owner": (
            "Архив — это дело владельца ящика: он убирает беседу из своего списка, а у вас "
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
        "unknown_command": "Я не знаю такую команду. Отправьте /help, чтобы увидеть, что я умею.",
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
        "cancel": "Kutayotgan amalimni to'xtatish",
        "help": "Nimalar qila olaman",
        "feedback": "Taklif yoki muammo haqida yozish",
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
        "cancel": "Остановить то, чего я жду",
        "help": "Что я умею",
        "feedback": "Предложить идею или сообщить о проблеме",
        "balance": "Ваш ⚡ кредит",
        "donate": "Помочь с расходами на хостинг",
        "paysupport": "Проблема с оплатой",
        "privacy": "Что я о вас храню",
        "terms": "Для чего можно пользоваться ботом",
        "deletemydata": "Удалить всё, что я о вас храню",
    },
}
