# Privacy — StickerBot

StickerBot turns images, GIFs, videos and stickers into Telegram sticker
packs.

This describes what the bot holds about the people who use it, who else sees
it, how long it stays, and how to have it erased. The short version is
available inside the bot as `/privacy`, in English, Uzbek and Russian.

**Operator contact:** mukhtorovmurodbek@gmail.com

_Last reviewed: 10 September 2026._

---

## What is held

- **A Telegram user id.** A number. It is the only thing a bot can address a
  person by, so it is held from the first message and cannot be opted out of
  while the bot is in use.
- **A chosen language**, once one is picked.
- **The packs made through the bot** — each pack's short name and title, and
  the display name and username its creator had at the time. This is what
  `/mypacks`, `/addsticker` and `/whomade` read.
- **Co-editing records** — the share links issued for a pack, and who has been
  granted permission to add to it through one.
- **A timestamp per use.** One row saying that this id used the bot at this
  minute, so the operator can tell whether anybody is using it at all. It
  carries no content and says nothing about what was done.
- **Donations**, if any: the amount, the status, and Telegram's payment id.
- **A ⚡ credit balance, and its ledger**, once you have paid or been given
  credit. It is shared by the family's four bots: the balance, and one row for
  every top-up, bonus, charge, credit returned and correction, with the amount, which
  bot, and why. `/balance` shows it.
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
  In this bot that is never the picture or sticker you sent.
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
- **Work in progress** — a pack half-built when the bot restarts, so that it
  survives the restart.

## What is not held

- The images, videos and stickers sent in. They are handed to Telegram, which
  is what builds the pack, and are not stored by the bot.
- Any message content beyond a pack title.
- Anything at all about anyone who has not messaged the bot.

## Who else sees it

- **Telegram.** Every message in either direction passes through Telegram,
  which is a separate company operating under its own terms and privacy
  policy. Nothing reaches this bot that Telegram has not already handled.
- **The hosting provider.** The bot runs as a container on a commercial host,
  and writes to a managed Postgres database. Both are operated by third
  parties under their own terms; neither is given access for any purpose
  beyond running the bot.

Nothing else. Stickers are prepared on the machine the bot runs on, and no
outside service is called.

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
| user id, language, packs, co-editing records | until erased, or indefinitely while the bot is in use |
| timestamp per use | about 90 days (`ACTIVITY_RETENTION_DAYS`) |
| work in progress | 12 hours (`DEPLOY_STATE_TTL_HOURS`) |
| donation records | kept, for accounts and payment disputes |
| ⚡ credit balance and its ledger | kept, like the donation records |

## Erasing it

`/deletemydata`, inside the bot. It asks once, then erases in that moment. No
account, no form, and no waiting period.

Erasing makes the bot forget the packs created through it: it stops listing
them and can no longer add to them. **The packs themselves are not deleted** —
they exist on Telegram, keep working for everyone who installed them, and can
only be removed by their owner, from Telegram.

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
