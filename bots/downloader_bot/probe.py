#!/usr/bin/env python3
"""Ask every download route whether it still works, and say which ones do.

    python probe.py                       # the built-in sample links
    python probe.py <url> [<url> ...]     # your own
    python probe.py --fetch               # also pull the first 256 KB back
    python probe.py --platform instagram  # just one platform's chain

WHY THIS EXISTS
    resolvers.py is a chain of other people's services, and the whole design
    assumes they die without telling anyone. `/providers` reports what the
    live bot has learned from real traffic, which is the honest answer but
    only covers routes somebody happened to exercise. This asks all of them,
    on demand, without needing a user to paste anything.

    Two things worth knowing before reading the output:

    - It talks to the network from wherever you run it. Run it on the laptop
      and you learn what a residential address gets; the container is on a
      datacenter range and can be told something different by the same
      service. That gap is the reason the chain exists, so a green row here
      is encouraging rather than conclusive. To ask from where it actually
      matters, use the family bus: `/run downloaderbot probe` runs these same
      checks inside the deployed container.
    - It deliberately does NOT touch the database, so it cannot be run
      against a bot that is live without also skewing its scores. The counts
      it prints are from this run only.

    The sample links are public posts chosen for being unlikely to vanish.
    When one does vanish the row will say "missing" for every provider at
    once, which is the tell: a real outage looks like one provider failing,
    not all of them agreeing.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import net
import platforms
import resolvers

# The sample links live in resolvers.py, so this CLI and the `probe` family-bus
# command ask exactly the same questions of exactly the same posts.
SAMPLES = list(resolvers.SAMPLES.values())

GREEN, RED, YELLOW, DIM, OFF = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    GREEN = RED = YELLOW = DIM = OFF = ""


async def probe_one(url: str, fetch: bool) -> None:
    detected = platforms.detect_platform(url)
    if not detected:
        print(f"{RED}?{OFF} {url}\n    not a link this bot recognises")
        return
    platform, matched = detected
    print(f"\n{platform}  {DIM}{matched}{OFF}")

    for name, fn in resolvers.PROVIDERS.get(platform, []):
        row = await resolvers.probe_route(name, fn, matched, fetch=fetch)
        mark = f"{GREEN}v{OFF}" if row["ok"] else f"{RED}x{OFF}"
        line = f"  {mark} {name:<18} {row['seconds']:>4.1f}s  {row['detail']}"
        if row["fetched"]:
            line += f"  {DIM}[{row['fetched']}]{OFF}"
        print(line)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="*", help="links to probe (default: the samples)")
    parser.add_argument("--fetch", action="store_true",
                        help="also pull the first 256 KB back, to prove the media URL serves")
    parser.add_argument("--platform", help="only probe the samples for this platform")
    args = parser.parse_args()

    urls = args.urls or SAMPLES
    if args.platform:
        urls = [u for u in urls
                if (platforms.detect_platform(u) or ("", ""))[0] == args.platform]
        if not urls:
            print(f"No sample link for platform {args.platform!r}.")
            return 2

    print("Probing download routes. A green row means that provider answered "
          "from THIS machine;\nthe container is on a different network and can "
          "be told something else.")
    try:
        for url in urls:
            await probe_one(url, args.fetch)
    finally:
        await net.close_client()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
