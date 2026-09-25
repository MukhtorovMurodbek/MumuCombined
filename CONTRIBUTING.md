# Contributing

Thank you for looking — but read the first line before writing any code.

## This repository is generated

The five bots are developed together in a private monorepo, where each one is
also published as a repository of its own. This repository is built from the
same source on every release — the bots' folders rearranged, the modules they
share stored once, and `bot.py` added to run them together — and is
**overwritten wholesale** each time.

So:

- **A pull request here cannot be merged.** The next release would overwrite
  it even if it were. Please do not spend an evening on one.
- **Commits here are not the project's history.** One commit per release, not
  one per change.

## What is useful instead

**Open an issue.** Bug reports, a platform that stopped working, a
translation that reads wrong, a problem specific to running everything in one
process — all of it is read, and issues are the one thing on this repository
that is not overwritten.

Useful in a bug report: which bot, what was sent, what came back, and roughly
when. Never include a token, and never include somebody else's message.

**Security bugs go elsewhere.** See `SECURITY.md` — privately first, not as an
issue.

## Running it yourself

`README.md` has the whole of it. Forking and running a copy is the intended
way to build on this.
