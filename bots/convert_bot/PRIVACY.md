# Privacy — ConvertBot

ConvertBot converts files between formats: pictures, video, audio, documents,
e-books, spreadsheets and subtitles. Conversions under 3 MB are free; larger
ones are priced in Telegram Stars.

This describes what the bot holds about the people who use it, who else sees
it, how long it stays, and how to have it erased. The short version is
available inside the bot as `/privacy`, in English, Uzbek and Russian.

**Operator contact:** mukhtorovmurodbek@gmail.com

_Last reviewed: 10 September 2026._

---

## What is held

- **A Telegram user id.** A number, held from the first message, because it is
  the only thing a bot can address a person by.
- **A chosen language**, once one is picked.
- **The file being converted, while it is being converted.** It is written to
  a staging directory, converted, sent back, and deleted. Anything a crash
  leaves behind is removed by a sweeper that runs every five minutes and again
  at startup, and nothing survives longer than 15 minutes. **If you turn on
  "keep file for more formats"** under the format menu, the file is instead
  kept until 15 minutes pass without a conversion of it, so the same file can
  be converted again. It is off unless you turn it on, the choice is
  remembered, and /cancel deletes the file sooner. A file waiting in the queue
  is kept until its conversion has run.
- **A timestamp per use** — one row saying this id used the bot at this
  minute, so the operator can tell whether anybody is using it. It carries no
  content.
- **A payment ledger** — every payment and donation: the amount, the
  currency, what it was for, the status, and Telegram's payment id.
- **A ⚡ credit balance, and its ledger** — shared by the family's four bots:
  the balance, and one row for every top-up, bonus, conversion charge, credit returned
  and correction, with the amount, which bot, and why. This is what `/balance`
  and `/mystars` read and what credit returned after a failed conversion is issued against.
- **Bonus credit, and when it expires** — for each payment that earned a
  bonus: how much, how much of it is left, and the date it runs out. Bonus
  that runs out unused is taken off the balance, and the ledger says so.
- **Problems, whenever one is shown to anybody** — the error code, an
  incident number, when it happened and the bot's version. This is written
  down automatically, because a fault nobody reports is still a fault, and
  nothing in it is about you: not your ID, not your name, not what you sent.
  The message that carries the code says so, above the button.
- **A report, only if you send one** — tapping "Report this" under an error
  shows, on screen, exactly what the report would carry, and nothing is sent
  unless you tap Send. It carries only what is related to that error:
  In this bot that is never the file you sent.
  Plus the language the bot speaks to you in, whether the chat is private or a
  group, and a comment if you choose to write one. Never your name or your
  @username. Your Telegram user ID goes only if you turn on "Let the owner
  reply to me" — without it, the report is not linked to your account.

  All of it is **cleared after 30 days**, automatically, whether or not you
  ask. The record of the error itself stays — it still happened, and a count
  of it is not about anybody — but after a month it no longer carries
  anything you sent. `/deletemydata` clears straight away any report that has
  your user ID on it; one sent without it cannot be told apart from anybody
  else's, so the 30-day clock clears it instead.

  The error records themselves are kept for **180 days** and then deleted.

  One more thing worth saying plainly: the operator is messaged the moment a
  serious error happens — a crash, or a message this bot accepted and failed
  to deliver — so those are seen the same day rather than in a list. That
  message says which error and when. It does not say who, or what a report
  says; the operator has to look a report up deliberately.
- **Work in progress** — a conversion waiting on a format choice, so it
  survives a restart.

## What is not held

- The converted file, once it has been sent back.
- The contents of any file, at any point, in the database.
- Card or payment details. Telegram processes every payment; the bot is told
  only that one succeeded, and its id.

## Who else sees it

- **Telegram.** Every message in either direction passes through Telegram,
  which is a separate company operating under its own terms and privacy
  policy. Nothing reaches this bot that Telegram has not already handled.
- **The hosting provider.** The bot runs as a container on a commercial host,
  and writes to a managed Postgres database. Both are operated by third
  parties under their own terms; neither is given access for any purpose
  beyond running the bot.

Nothing else. Files are converted on the machine the bot runs on — by
ffmpeg, Pillow, PyMuPDF and a handful of other libraries, all of them running
locally — and are never handed to an outside service. No conversion here
uploads a file anywhere, which is the one thing most online converters cannot
say.

Nothing is sold, rented, shared for advertising, or used to build a profile of
anybody. There is no analytics service, no advertising identifier and no
tracking of any kind — a Telegram bot has no browser to put one in.

## Why

Every item above exists because the bot cannot do what it is for without it,
or — in the case of the timestamp per use — because the person running it
would otherwise have no way of telling whether it is worth continuing to run.
Nothing is collected speculatively, and nothing is collected to be sold later.

## How long it is kept

| what | how long |
|---|---|
| user id, language | until erased, or indefinitely while the bot is in use |
| the file being converted | until the conversion ends; with "keep file" on, until 15 minutes pass without a conversion of it |
| timestamp per use | about 90 days (`ACTIVITY_RETENTION_DAYS`) |
| work in progress | 12 hours (`DEPLOY_STATE_TTL_HOURS`) |
| payment ledger | kept, for accounts and payment disputes |
| ⚡ credit balance and its ledger | kept, like the payment ledger |

## Erasing it

`/deletemydata`, inside the bot. It asks once, then erases in that moment. No
account, no form, and no waiting period.

Files are not affected by erasing: whatever was converted was deleted when the
conversion ended, and a file kept for more formats is gone within 15 minutes of
its last conversion.

What survives is the payment ledger, without the username on it. A payment
record has to outlive the payer asking to be forgotten: it is what a payment
dispute is settled against, and what the totals are counted from. The username is cleared
because it is the one free-text identifier on the row; the numeric id stays,
because a dispute cannot be settled with nobody.

The ⚡ credit balance and its ledger survive erasing for the same reason, and
hold no username at all. Erasing does not forfeit credit: it is still there if
you come back, and the operator removes it on request.

Blocking the bot in Telegram stops it from sending anything, but erases
nothing — the two are separate actions, and `/deletemydata` is the one that
removes data.

There is no separate export command. Everything held is listed above, and
`/deletemydata` reports how many records it removed.

## Age

Telegram sets the minimum age for holding a Telegram account, and this bot is
available to anyone who has one. It does not ask for a date of birth, does not
hold one, and has no way of telling how old anyone is.

## Changes

Material changes are announced in the bot before they take effect. The date at
the top of this file is when it was last reviewed.

## Contact

Questions, complaints and data requests go to the operator named at the top of
this file.
