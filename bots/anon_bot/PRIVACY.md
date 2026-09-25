# Privacy — AnonBot

AnonBot gives each of its users a permanent personal link. Anyone who opens it
can send that person an anonymous message, and the two can then hold a real
threaded conversation.

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
- **An inbox link**, for anyone who has created one: a random token, and
  whether it is currently accepting new conversations.
- **The pairing behind each conversation** — the two user ids, a
  conversation number, when it started, when it was last spoken in, and
  whether the inbox owner has filed it away. This is what makes a reply
  reach the right thread.
- **A message-id map** — which message belongs to which conversation, when
  each was relayed, and whether the bot or the person wrote it. This is what
  lets a reply be matched to what it answers, and a transcript be sorted into
  conversations.
- **A block list** — who an inbox owner has blocked.
- **A timestamp per use** — one row saying this id used the bot at this
  minute, so the operator can tell whether anybody is using it.
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
- **Your own details, only if you add them** — tapping "Add my details" under
  an error offers to attach four things to that incident: your Telegram user
  ID, your @username if you have one, the language you picked, and whether the
  chat is private or a group. All four are named on screen before anything is
  sent, and nothing is sent unless you tap Send. Not what you wrote and not
  the file you sent, ever.

  Those four are **cleared after 30 days**, automatically, whether or not you
  ask. The record of the error itself stays — it still happened, and a count
  of it is not about anybody — but after a month it no longer says who hit it.
  `/deletemydata` clears them straight away instead of waiting.

  The error records themselves are kept for **180 days** and then deleted.

  One more thing worth saying plainly: the operator is messaged the moment a
  serious error happens — a crash, or a message this bot accepted and failed
  to deliver — so those are seen the same day rather than in a list. That
  message says which error and when. It does not say who, even when somebody
  has attached their details; the operator has to look those up deliberately.

## What is not held

- **What anybody writes.** Messages are relayed and never stored. They exist
  in the two Telegram chats, where each side can delete their own copy, and in
  no database belonging to this bot.
- Names, usernames or profile photos of the people writing anonymously.

## Getting a conversation back (`/export`)

`/export` hands you one conversation, or all of them. It works from the
message-id map above — which message in this chat belonged to which
conversation — so you do not forward anything and the bot does not read a
chat's history, which no bot can do.

You choose between two ways, and the bot says which is which before either
runs:

- **Copied back here.** The bot gives Telegram a list of message numbers and
  Telegram makes the copies. **The bot does not see what is in them.**
  Everything arrives exactly as it was — stickers, photos, voice messages,
  files — and the copies stay in the chat until you delete them.
- **Written into a document.** To put words on a page the bot has to read
  them. It forwards each message to itself, reads it, and **deletes what it
  read straight away**, one at a time. You will see messages appear and
  vanish while it works.

For the document:

- **What it reads:** the text or caption, what kind of media it is, and when
  it was sent. Photos, voice messages, videos and files are not downloaded;
  the document names them by kind. Shared contacts and locations are named the
  same way, and what is in them is not copied into the document.
- **What it keeps:** nothing. The page is assembled in the bot's memory, sent
  to you, and dropped. It is never written to the database.
- **Who is named:** nobody. The inbox holder is "Owner" and the person writing
  to them is "Anon", whichever of the two is doing the exporting. No name, no
  username and no id appears in it. The other person is not told.

A conversation stops being exportable when its message-id rows are cleared —
see the retention section below.

A document holds what somebody else wrote to you. Sharing it is your
responsibility; treat it like a screenshot.

## What "anonymous" means here

Anonymity is towards the person being written to. They are never shown a
sender's name, username or user id, and there is no command, button or
owner-only view that reveals one.

It is not anonymity from the bot. The pairing described above is exactly what
makes a reply possible, and it is stored: an operator with database access
could read which two ids are in a conversation. What they could not read is
anything that was said, because none of it is stored.

Anyone who needs anonymity from the service as well as from the recipient
should not use a service like this one.

## Who else sees it

- **Telegram.** Every message in either direction passes through Telegram,
  which is a separate company operating under its own terms and privacy
  policy. Nothing reaches this bot that Telegram has not already handled.
- **The hosting provider.** The bot runs as a container on a commercial host,
  and writes to a managed Postgres database. Both are operated by third
  parties under their own terms; neither is given access for any purpose
  beyond running the bot.

Nothing else. Messages travel over Telegram and no further, and no outside
service is called.

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
| user id, language, link, block list | until erased, or indefinitely while the bot is in use |
| conversation pairings | until erased, or the conversation is |
| message-id map | pruned once a conversation has gone quiet |
| timestamp per use | about 90 days (`ACTIVITY_RETENTION_DAYS`) |
| donation records | kept, for accounts and payment disputes |
| ⚡ credit balance and its ledger | kept, like the donation records |

## Erasing it

`/deletemydata`, inside the bot. It asks once, then erases in that moment. No
account, no form, and no waiting period.

For an inbox owner, erasing invalidates the link — permanently, including
every copy of it anybody has posted — and open conversations stop being
routable, so neither side can reply into them again. Messages already sent are
untouched: they were never held here, and each side deletes their own copy
from their own chat.

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
