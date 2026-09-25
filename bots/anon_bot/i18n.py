"""Translation strings for AnonBot's end-user-facing text (English, Uzbek,
Russian). Deliberately duplicated per bot -- same "no shared files between
bots" independence as shared_features.py -- but the STRINGS content here is
specific to this bot's own commands and flows.

Admin-only output (/dbdump, /status) is intentionally NOT translated -- see
build_status_text/error_summary/detect_host_environment in
shared_features.py, and bot.py's dbdump_command/status_command, left as
plain English since only the bot owner reads them.

The keys below split into two groups:
  - "Shared" keys (donate flow, sibling-bot blurb) exist under the exact
    same names in every bot's i18n.py, since shared_features.py is
    duplicated byte-identical across the family and calls t() with these
    names regardless of which bot it's running in.
  - Bot-specific keys, everything below the shared block, for this bot's
    own bot.py strings only.
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
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
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
        # ---- anon_bot-specific keys ----
        "start_greeting": "Hey! This bot runs anonymous-question inboxes.\n\n",
        "help_text": "Two ways to use this bot:\n\nGet your own inbox — /link gives you a permanent link. Post it anywhere public (bio, channel, story, wherever). Anyone who taps it can send you an anonymous message right here in this chat — you won't see who they are.\nAnswer by replying to the message — swipe it, or press and hold it and choose Reply. That is how I know which conversation your answer belongs to, so it is required rather than optional: one public link means several people can be mid-conversation with you at once, and a message that doesn't say which thread it answers could reach the wrong one. Your answer shows up on their end as a real reply too.\n\nGot sent someone else's link? Tap it and write — your first message goes straight through, with your identity hidden. After that, reply to the message you're answering, exactly as the other side does. Tapping the same link again later starts a brand-new conversation, it won't continue the old one.\n\nCommands:\n/link - get your inbox link\n/newlink, /pause, /resume - also buttons on the /link screen\n/blocked - review who you've blocked\n/stats - the counts, which are on the /link screen too\n/export - get a conversation back, copied here or as a document\n/donate - chip in for hosting costs (totally optional)\n/cancel - stop something I'm waiting on you for (I'll ask which)\n/en, /uz, /rus - switch language (or /language, which asks)\n\n⚠️ NOTE: Payments are final — Stars paid through /donate are NOT refunded, and the ⚡ credit they add can NOT be withdrawn.\n\n",
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
        # ---- /conversations: the owner's own view of their own inbox ----
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
        # ---- /which: which conversation does this message belong to ----
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
        # ---- how long ago, without a date and without a timezone ----
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
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
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
        "help_text": "Bu botdan ikki xil foydalanish mumkin:\n\nO'z qutingizni oching — /link sizga doimiy havola beradi. Uni istalgan ochiq joyga joylang (bio, kanal, story — qayerda bo'lsa ham). Havolani ochgan har kim sizga shu chatning o'zida anonim xabar yubora oladi — kimligi sizga ko'rinmaydi.\nJavob berish uchun xabarni o'ngga suring yoki uni bosib turib «Javob berish»ni tanlang. Shunda javobingiz qaysi suhbatga tegishli ekanini bilaman, shuning uchun bu shart: havola ochiq joyda turgani uchun bir vaqtda bir nechta odam sizga yozayotgan bo'lishi mumkin, qaysi suhbatga javob ekani ko'rsatilmagan xabar esa boshqa odamga borib qolishi mumkin. Javobingiz ularga ham haqiqiy javob sifatida ko'rinadi.\n\nSizga boshqa birovning havolasini yuborishdimi? Uni bosing va yozing — birinchi xabaringiz kimligingiz yashirilgan holda darhol yetib boradi. Undan keyin xuddi qarshi tomon kabi, javob berayotgan xabaringizga javob tarzida yozing. Keyinroq havolani yana bossangiz, eski suhbat davom etmaydi — yangisi boshlanadi.\n\nBuyruqlar:\n/link - qutingiz havolasini olish\n/newlink, /pause, /resume - bular /link ekranida tugma sifatida ham bor\n/blocked - bloklanganlar ro'yxati\n/stats - qisqa statistika; u /link ekranida ham bor\n/export - suhbatni qaytarib olish: shu yerga nusxalab yoki hujjat qilib\n/donate - server xarajatlariga hissa qo'shish (ixtiyoriy)\n/cancel - joriy amalni bekor qilish (bir nechta bo'lsa, qaysi birini so'rayman)\n/en, /uz, /rus - tilni almashtirish (yoki /language)\n\n⚠️ DIQQAT: To'lovlar QAYTARILMAYDI — /donate orqali to'langan Stars qaytarib berilmaydi, ular bergan ⚡ kreditni esa yechib olib BO'LMAYDI.\n\n",
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
        # ---- /conversations ----
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
        # ---- /which ----
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
        # ---- qancha vaqt oldin ----
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
        # ---- shared policy keys (/privacy, /terms, /deletemydata) ----
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
        "help_text": 'Есть два способа пользоваться этим ботом:\n\nЗаведите свой ящик — /link даёт вам постоянную ссылку. Разместите её где угодно на виду (в био, канале, истории — где хотите). Любой, кто по ней перейдёт, сможет отправить вам анонимное сообщение прямо в этот чат — вы не увидите, кто это.\nОтвечайте, смахнув сообщение вправо или нажав и удерживая его и выбрав «Ответить» — ваш ответ уйдёт именно этому человеку и появится у него как настоящий ответ, поэтому легко не путать несколько бесед, даже если они приходят в один и тот же чат.\n\nВам прислали чужую ссылку? Перейдите по ней, затем просто напишите — ваше сообщение уйдёт адресату, а личность останется скрытой. Если позже перейти по той же ссылке снова, начнётся новая беседа, а не продолжение старой.\n\nКоманды:\n/link - получить ссылку на свой ящик\n/newlink, /pause, /resume - они же кнопки на экране /link\n/blocked - посмотреть, кого вы заблокировали\n/stats - краткая статистика, она же на экране /link\n/export - получить разговор обратно: копией сюда или документом\n/donate - помочь с расходами на хостинг (совершенно необязательно)\n/cancel - остановить то, чего я от вас жду (спрошу, что именно)\n/en, /uz, /rus - сменить язык (или /language — он спрашивает)\n\n⚠️ ВНИМАНИЕ: платежи окончательные — Stars, оплаченные через /donate, НЕ возвращаются, а добавленный ими ⚡ кредит НЕЛЬЗЯ вывести.\n\n',
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
        # ---- /conversations ----
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
        # ---- /which ----
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
        # ---- как давно ----
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


# Every problem a person can run into ends with its code, and the code is what
# puts a "Report the issue" button under it -- see problems.py. Imported here,
# below the tables, because it is pure data and nothing above needs it.
import problems  # noqa: E402

_BOT = "anon_bot"


def t(lang: str | None, key: str, **kwargs) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    template = table.get(key) or STRINGS["en"].get(key, key)
    text = template.format(**kwargs) if kwargs else template
    return text + problems.code_line(problems.code_for(_BOT, key))


async def get_lang(user_id: int, context) -> str:
    """Cached in context.user_data to avoid a DB round-trip on every handler
    call. Falls back to "en" for a user who hasn't chosen a language yet
    (only reachable outside /start's first-run gate, e.g. someone who sends
    a link before ever running /start)."""
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
