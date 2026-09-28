# Privacy and terms

For the four public bots: **StickerBot**, **ConvertBot**, **DownloaderBot** and
**AnonBot**. Each bot's `/privacy` and `/terms` are the short versions, in
English, Uzbek and Russian, and link to their own sections below. The shared
sections apply to all four; a bot's own section adds what is particular to it.

**Operator contact:** mukhtorovmurodbek@gmail.com

_Last reviewed: 26 September 2026._

**Privacy:** [every bot](#privacy-every-bot) ·
[StickerBot](#stickerbot-privacy) · [ConvertBot](#convertbot-privacy) ·
[DownloaderBot](#downloaderbot-privacy) · [AnonBot](#anonbot-privacy)
**Terms:** [every bot](#terms-every-bot) · [StickerBot](#stickerbot-terms) ·
[ConvertBot](#convertbot-terms) · [DownloaderBot](#downloaderbot-terms) ·
[AnonBot](#anonbot-terms)

---

## Privacy, every bot

### What is held

- **A Telegram user id.** A number, held from the first message, because it is
  the only thing a bot can address a person by.
- **A chosen language**, once one is picked.
- **A timestamp per use** — one row saying this id used a bot at this minute,
  so the operator can tell whether anybody is using it. It carries no content
  and says nothing about what was done.
- **Payments and donations**, if any: the amount, the currency, what it was
  for, the status, and Telegram's payment id.
- **A ⚡ credit balance, and its ledger**, once you have paid or been given
  credit. One balance is shared by all four bots: the balance, and one row for
  every top-up, bonus, conversion charge, credit returned and correction, with
  the amount, which bot, and why. `/balance` and `/mystars` read it.
- **Bonus credit, and when it expires** — for each payment that earned a
  bonus: how much, how much of it is left, and the date it runs out. Bonus that
  runs out unused is taken off the balance, and the ledger says so.
- **Problems, whenever one is shown to anybody** — the error code, an incident
  number, when it happened and the bot's version. This is written down
  automatically, because a fault nobody reports is still a fault, and nothing in
  it is about you: not your id, not your name, not what you sent. The message
  that carries the code says so, above the button.
- **Your own details, only if you add them** — tapping "Add my details" under
  an error offers to attach four things to that incident: your Telegram user
  id, your @username if you have one, the language you picked, and whether the
  chat is private or a group. All four are named on screen before anything is
  sent, and nothing is sent unless you tap Send. Never what you wrote and never
  a file you sent. Those four are **cleared after 30 days**, automatically; the
  record of the error stays, without them, and is deleted after **180 days**.
  `/deletemydata` clears them straight away.

  The operator is messaged the moment a serious error happens — a crash, or a
  message a bot accepted and failed to deliver. That message says which error
  and when. It does not say who, even when somebody has attached their
  details; those have to be looked up deliberately.
- **Work in progress**, so it survives a restart — what each bot means by that
  is in its own section.

### What is not held

Card or payment details. Telegram processes every payment; a bot is told only
that one succeeded, and its id.

### Who else sees it

- **Telegram.** Every message in either direction passes through Telegram,
  which is a separate company operating under its own terms and privacy
  policy. Nothing reaches a bot that Telegram has not already handled.
- **The hosting provider.** The bots run on a commercial host and write to a
  managed Postgres database. Both are operated by third parties under their own
  terms; neither is given access for any purpose beyond running the bots.

Anything beyond those two is named in the bot's own section. Nothing is sold,
rented, shared for advertising, or used to build a profile of anybody. There is
no analytics service, no advertising identifier and no tracking of any kind — a
Telegram bot has no browser to put one in.

### Why

Every item exists because a bot cannot do what it is for without it, or — for
the timestamp per use — because the person running the bots would otherwise
have no way of telling whether they are worth continuing to run. Nothing is
collected speculatively, and nothing is collected to be sold later.

### How long it is kept

| what | how long |
|---|---|
| user id, language, and what a bot's own section lists as kept "until erased" | until erased, or indefinitely while the bot is in use |
| timestamp per use | about 90 days |
| work in progress | 12 hours |
| details added to a problem report | 30 days |
| problem records | 180 days |
| payments and donations | kept, for accounts and payment disputes |
| ⚡ credit balance and its ledger | kept, like the payments |

### Erasing it

`/deletemydata`, inside the bot. It asks once, then erases in that moment. No
account, no form, and no waiting period. It erases what that bot holds; each
bot has its own `/deletemydata`.

What survives is the payment record, without the username on it. A payment
record has to outlive the payer asking to be forgotten: it is what a payment
dispute is settled against, and what the totals are counted from. The username
is cleared because it is the one free-text identifier on the row; the numeric
id stays, because a dispute cannot be settled with nobody. The ⚡ credit
balance and its ledger survive for the same reason and hold no username at
all. Erasing does not forfeit credit: it is still there if you come back, and
the operator removes it on request.

Blocking a bot in Telegram stops it from sending anything, but erases nothing —
`/deletemydata` is the one that removes data. There is no separate export
command: everything held is listed here, and `/deletemydata` reports how many
records it removed.

### Age

Telegram sets the minimum age for holding a Telegram account, and the bots are
available to anyone who has one. They do not ask for a date of birth, do not
hold one, and have no way of telling how old anyone is.

### Changes and contact

Material changes are announced in the bots before they take effect. The date at
the top of this file is when it was last reviewed. Questions, complaints and
data requests go to the operator contact at the top.

---

## StickerBot privacy

StickerBot turns images, GIFs, videos and stickers into Telegram sticker packs.
Everything under [Privacy, every bot](#privacy-every-bot) applies. Also held:

- **The packs made through the bot** — each pack's short name and title, and
  the display name and username its creator had at the time. This is what
  `/mypacks`, `/addsticker` and `/whomade` read.
- **Co-editing records** — the share links issued for a pack, and who has been
  granted permission to add to it through one.
- **Work in progress** — a pack half-built when the bot restarts.

Not held: the images, videos and stickers sent in (they are handed to
Telegram, which builds the pack), any message content beyond a pack title, and
anything about anyone who has not messaged the bot. Stickers are prepared on the
machine the bot runs on; no outside service is called.

Packs and co-editing records are kept until erased. Erasing makes the bot
forget the packs created through it: it stops listing them and can no longer
add to them. **The packs themselves are not deleted** — they exist on Telegram,
keep working for everyone who installed them, and can only be removed by their
owner, from Telegram.

## ConvertBot privacy

ConvertBot converts files between formats: pictures, video, audio, documents,
e-books, spreadsheets and subtitles. Everything under
[Privacy, every bot](#privacy-every-bot) applies. Also held:

- **The file being converted, while it is being converted.** It is written to a
  staging directory, converted, sent back, and deleted. Anything a crash leaves
  behind is removed by a sweeper that runs every five minutes and again at
  startup, and nothing survives longer than 15 minutes. **With "keep file for
  more formats" turned on** under the format menu, the file is kept until 15
  minutes pass without a conversion of it, so it can be converted again. It is
  off unless you turn it on, the choice is remembered, and /cancel deletes the
  file sooner. A file waiting in the queue is kept until its conversion has
  run.
- **Work in progress** — a conversion waiting on a format choice; and, while
  a paid conversion runs, who it is for, its price and its formats, so that its
  ⚡ can be given back even if the bot is stopped in the middle of it. That
  record goes when the conversion ends — or, after a restart, a day after the ⚡
  has been returned.

Not held: the converted file once it has been sent back, and the contents of
any file, at any point, in the database. Files are converted on the machine the
bot runs on — by ffmpeg, Pillow, PyMuPDF and a handful of other libraries, all
running locally — and are never handed to an outside service. A file over
20 MB is fetched from Telegram and sent back to Telegram over Telegram's own
protocol rather than its Bot API; it still travels only between Telegram and
the bot. So does a video shot in HDR, which is tone-mapped on the way; nothing
about how it is handled changes.

Erasing does not touch files: whatever was converted was deleted when the
conversion ended, and a file kept for more formats is gone within 15 minutes of
its last conversion.

## DownloaderBot privacy

DownloaderBot takes a link to a public post on Instagram, TikTok, Pinterest,
Reddit or X and sends back the media behind it. Everything under
[Privacy, every bot](#privacy-every-bot) applies. Also held:

- **The caption, quality and large-file settings** that go with the chosen
  language.
- **The link sent in**, for as long as it takes to fetch what is behind it.
- **One row per download** — which platform, and when. The daily allowance is
  counted from it; the link is not part of the row. Kept 7 days.
- **Work in progress** — a download waiting on a choice.

Not held: the media itself (fetched, sent, and deleted), the link once the
download is done, and anything about the author of the post beyond what is
inside the media file they published. A large file (over 48 MB, with large
files switched on) is sent over Telegram's own protocol rather than its Bot
API; it still travels only between Telegram and the bot.

Also sees it:

- **The site the link points to.** The bot requests the post from it directly
  first, so that site sees a request from the bot's server.
- **Fallback download services.** When a site refuses the bot directly, the link
  is handed to a third-party resolver instead. That service receives the link
  and sees the request as coming from the bot's server, not from the person who
  sent it. What those services log is governed by their own policies.

Erasing the download rows resets the daily allowance along with them. Nothing
already downloaded is affected — it was never kept here.

## AnonBot privacy

AnonBot gives each of its users a permanent personal link. Anyone who opens it
can send that person an anonymous message, and the two can then hold a real
threaded conversation. Everything under [Privacy, every bot](#privacy-every-bot)
applies. Also held:

- **An inbox link**, for anyone who has created one: a random token, and
  whether it is currently accepting new conversations.
- **The pairing behind each conversation** — the two user ids, a conversation
  number, when it started, when it was last spoken in, and whether the inbox
  owner has filed it away. This is what makes a reply reach the right thread.
  Kept until erased, or until the conversation is.
- **A message-id map** — which message belongs to which conversation, when each
  was relayed, and whether the bot or the person wrote it. This is what lets a
  reply be matched to what it answers, and a transcript be sorted into
  conversations. Pruned once a conversation has gone quiet.
- **A block list** — who an inbox owner has blocked.

Not held: **what anybody writes.** Messages are relayed and never stored. They
exist in the two Telegram chats, where each side can delete their own copy, and
in no database belonging to this bot. Nor are the names, usernames or profile
photos of the people writing anonymously. Messages travel over Telegram and no
further; no outside service is called.

**Getting a conversation back (`/export`).** It works from the message-id map,
so nothing is forwarded by hand and no chat history is read, which no bot can
do. There are two ways, and the bot says which is which before either runs:

- **Copied back here.** The bot gives Telegram a list of message numbers and
  Telegram makes the copies. The bot does not see what is in them; everything
  arrives exactly as it was, and the copies stay in the chat until deleted.
- **Written into a document.** To put words on a page the bot has to read
  them: it forwards each message to itself, reads it, and deletes what it read
  straight away, one at a time. It reads the text or caption, what kind of
  media it is, and when it was sent; media is not downloaded, only named by
  kind. It keeps nothing — the page is assembled in memory, sent, and dropped.
  Nobody is named: the inbox holder is "Owner", the person writing is "Anon",
  and the other person is not told. A document holds what somebody else wrote;
  sharing it is your responsibility.

**What "anonymous" means here.** Anonymity is towards the person being written
to: they are never shown a sender's name, username or user id, and there is no
command, button or owner-only view that reveals one. It is not anonymity from
the service: the pairing above is stored, and an operator with database access
could read which two ids are in a conversation — though not anything that was
said, because none of it is stored. Anyone who needs anonymity from the service
as well should not use a service like this one.

For an inbox owner, erasing invalidates the link — permanently, including every
copy of it anybody has posted — and open conversations stop being routable, so
neither side can reply into them again. Messages already sent are untouched:
they were never held here, and each side deletes their own copy.

---

## Terms, every bot

Using a bot means accepting these terms and its own section below.

### Use

Use the bots for what they are for, within the law and within Telegram's own
terms of service. They may not be used to harass anyone, to break the law of
the place they are used from, or to place load on them beyond the limits they
set.

### Money

A payment in Telegram Stars adds **⚡ credit** to one balance shared by all four
bots. Credit pays for conversions in ConvertBot, where `/recharge` buys it,
and for DownloaderBot's large files; in the other three, `/donate` is voluntary
and goes towards what the bots cost to run. `/balance` shows the balance and everything it was spent on.

How much credit a payment adds depends on how many Stars have been paid in
total, over every payment in every bot. The ordinary rate is two ⚡ for each
Star. The first 500 Stars anybody pays earn three times that, six ⚡ each; the
next 500 earn twice that, four ⚡ each; after 1,000 Stars each one earns the
ordinary two. Paying in several small amounts earns exactly what paying once
would. The bot says what the next Stars earn before payment.

**The part above the ordinary rate is bonus credit, and it expires 90 days
after the payment that earned it.** Ordinary credit does not expire.
Conversions use bonus credit first, the soonest to expire first, so what
expires is only bonus that went unused.

**Payments are final. Stars are not refunded, and credit is not money and it is
not Stars: it cannot be withdrawn, turned back into Stars, or transferred.**
Every bot says so in `/help`, and ConvertBot again before a paid conversion. If
a payment went wrong — charged with no credit to show for it, or charged twice
— `/paysupport` says how to reach the operator, and it is put right with
credit. Telegram processes every payment; the bots never see a card number.

### Availability

The bots are run by one person and come with no promise of availability,
correctness or continuity. They can be slow, wrong, or switched off entirely,
with or without notice. Nothing here should be relied on for anything that
cannot be lost; anyone who needs a copy of something should keep their own.
Nothing in these terms limits any right that cannot be limited under the law
that applies to the person using a bot.

### Suspension

Use that breaks these terms, breaks Telegram's own terms, or costs other people
the service — automated flooding especially — is blocked, without notice and at
the operator's discretion.

### Changes and contact

Material changes are announced in the bots before they take effect. Questions
and complaints go to the operator contact at the top.

## StickerBot terms

Everything under [Terms, every bot](#terms-every-bot) applies.

Stickers are made out of what the person making them uploads, and uploading
something is a claim that it is theirs to upload. Building a pack out of
somebody else's photographs, artwork or footage without their permission is not
what this is for, and neither is a pack of anything Telegram's own terms forbid.

A pack, once created, lives on Telegram under this bot's name. The bot can be
made to forget a pack; deleting one for real is done through Telegram, by the
person who owns it. Complaints about a specific pack are best taken to
Telegram, which hosts it and can remove it; the operator can also be told, and
will forget the pack here.

## ConvertBot terms

Everything under [Terms, every bot](#terms-every-bot) applies.

**Files and copyright.** Convert what there is a right to convert. The bot does
not inspect what it is given and takes no view on it, which is not the same as
permission: converting somebody else's file does not create a right to it, and
re-publishing the result is the sender's responsibility, not the operator's.

**Price.** Conversions under 3 MB are free. Above that the price is set by the
size of the file, what it is estimated to become, and how hard the conversion
is to run -- from ⚡6, and never more than ⚡84 -- is shown in ⚡ credit
before the conversion is confirmed, and is taken from the balance **when the
conversion starts** — not when it is queued, so a conversion removed from the
queue costs nothing. When the balance does not cover it, the bot asks only for
the Stars needed to make up the difference.

**Stopping a running conversion yourself does NOT give its ⚡ back.** The note
shown when a file arrives says so.

**A conversion that fails for the bot's reasons gives its ⚡ back
automatically**, to the balance, with the reason: it ran past its time limit
(or was on course to, and was stopped early), it crashed, the result came out larger than the bot could send back for it,
sending it failed, or the bot was restarted in the middle of it. A file the bot
cannot read gets its ⚡ back the same way. A picture too large to convert, or a
format that would come out too large to send, is refused before anything is
charged. Credit comes back as credit; the Stars paid for it are never refunded.
Credit expected back that does not arrive is put right by hand, on request.

## DownloaderBot terms

Everything under [Terms, every bot](#terms-every-bot) applies.

**What it fetches, and copyright.** The bot fetches posts that are already
public and hands them back. It is not a way around a private account, does not
attempt to be one, and will say so rather than try. Downloading something does
not create a right to it. A photograph, a video or a post belongs to whoever
made it, and what happens to it after it has been downloaded — republishing it,
selling it, presenting it as somebody else's own work — is between the person
who downloaded it, the person who made it, and the law. The operator neither
reviews nor licenses any of it. Rights holders who want a specific post to stop
being retrievable should approach the platform hosting it; this bot stores
nothing and has nothing to take down.

**Fair share.** There is a daily allowance per person, so that one heavy user
cannot make the bot unusable or unaffordable for everyone else. Working around
it, by any means, is grounds for being blocked.

**Large files.** A download over 48 MB costs **⚡7 for the first 100 MB and less
for each 100 MB after (⚡76 for 2000 MB)**.
The bot fetches one only after you have switched large files on in
`/settings` -- they are off until you do -- says before it starts that it
costs credit, and charges only once the file has arrived. A balance that does
not cover it is charged nothing. A large file that cannot be sent costs
nothing: its credit goes back.

## AnonBot terms

Everything under [Terms, every bot](#terms-every-bot) applies.

A hidden name is not a licence. Threats, harassment, extortion and anything
otherwise illegal are all still exactly those things when the sender is
anonymous, and they are grounds for being blocked by the recipient and by the
operator.

An inbox owner is responsible for the inbox they open. Inviting people to send
things that should not be sent is the owner's doing, not the bot's.

A transcript made with `/export` holds what other people wrote, and what happens
to it after the bot sends it is the exporter's to answer for. Publishing what
somebody wrote anonymously can still harm them, and it is subject to the same
law as sharing any other private correspondence.

Every inbox owner can block a sender permanently, pause new conversations, or
issue a new link that invalidates the old one. Those three are the tools this
bot offers, and they work immediately. Reports of abuse should go to the
operator, and — where a Telegram account is involved — to Telegram, which is
the only party able to act on an account.
