# Security

## Reporting a vulnerability

**Do not open a public issue.** A bug that lets one person reach another
person's data is worth reporting privately first, so that it can be fixed
before it is described in public.

Use GitHub's private reporting — **Security → Report a vulnerability** on this
repository — or message the operator through the bot itself.

A report is more useful with:

- what the bot does that it should not,
- the steps that produce it,
- and roughly when it happened, so it can be found in the logs.

There is no bounty and no formal response time. This is a small project run by
one person; reports are read and acted on, and a report that turns out to be a
real hole gets a fix released ahead of whatever else was planned.

## What is in scope

Anything that lets somebody:

- read, receive or infer another user's files, messages or account id;
- get the bot to act as another user, or to reach an owner-only command;
- extract database contents, tokens or environment variables;
- make the bot fetch or execute something it was not asked to.

## What is not

- Rate limits and quotas being reachable. They are deliberate and documented.
- The bot refusing something, or failing on a malformed file.
- Reports about Telegram itself, or about a third-party service the bot talks
  to. Those belong with whoever runs them.
- Anything that requires the operator's own credentials to begin with.

## What this bot holds

`/privacy` inside the bot, and `PRIVACY.md` in this repository, say exactly
what is stored, who else can see it and how long it stays. `/deletemydata`
erases it. Those documents are the reference for what a leak would actually
expose.
