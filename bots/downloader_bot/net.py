"""One HTTP client for the whole process, and the two ways this bot fetches
media with it.

Every fetch used to build its own `httpx.AsyncClient` inside an `async with`
-- a fresh TCP connection and TLS handshake per request, thrown away straight
after, against hosts considerably further away than the database this family
already learned that lesson on. One client, kept open, reuses connections
across requests and across users. The pool is small on purpose: this bot is
never talking to more than a handful of hosts at once.

Split out of platforms.py at v1.2.1, because resolvers.py needs the same
client and importing it back out of a module about *page scraping* had the
dependency arrow pointing the wrong way.
"""
from __future__ import annotations

import os

import httpx

# A real browser's UA. Several of the media hosts below serve a challenge page
# to anything that admits to being a script, and a challenge page is not
# something this bot can answer.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# The other half of the story: the "fix the embed" services (tnktok,
# eeinstagram, fxtwitter, ...) exist to serve link-preview crawlers, and they
# decide what to put in the page from the User-Agent. Ask as a browser and you
# get the human-facing page; ask as a crawler and you get the OpenGraph tags
# with the media URL in them. So those providers ask as a crawler, on purpose.
CRAWLER_UA = "TelegramBot (like TwitterBot)"

# Telegram itself refuses uploads over 50 MB without a local Bot API server,
# so anything larger was always going to be fetched and then thrown away.
MAX_RESPONSE_BYTES = int(os.environ.get("DBOT_MAX_DOWNLOAD_MB", "48")) * 1024 * 1024

CONNECT_TIMEOUT = float(os.environ.get("DBOT_CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.environ.get("DBOT_READ_TIMEOUT", "30"))


class FetchError(Exception):
    """Raised with a message that is safe to show the user as-is."""


_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
            headers={"User-Agent": UA},
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4,
                                keepalive_expiry=30.0),
        )
    return _client


async def close_client() -> None:
    """Called from the bot's shutdown hook."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def fetch_bytes(url: str, limit: int = MAX_RESPONSE_BYTES,
                      headers: dict | None = None) -> bytes:
    """GET a URL into memory, refusing anything that would not fit in a
    Telegram upload anyway.

    Streamed and counted as it arrives, so a server that lies about (or omits)
    Content-Length still cannot make this process hold an unbounded amount of
    data.
    """
    async with client().stream("GET", url, headers=headers or {}) as response:
        response.raise_for_status()
        declared = response.headers.get("content-length")
        if declared and int(declared) > limit:
            raise FetchError("That file is too big to send through Telegram.")
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > limit:
                raise FetchError("That file is too big to send through Telegram.")
            chunks.append(chunk)
    return b"".join(chunks)


async def stream_to_file(url: str, path: str, limit: int = MAX_RESPONSE_BYTES,
                         headers: dict | None = None) -> int:
    """Same, but to disk, for the things that are too big to want in memory.

    Returns the byte count. Videos go this way and images do not, because
    python-telegram-bot streams a file object off disk to Telegram rather than
    reading it in first -- so a 45 MB video is never resident, while a 2 MB
    JPEG is not worth the round trip through the filesystem.

    HEAD is deliberately never used to size-check first. TikTok's CDN answers
    HEAD with a 503 while serving the identical GET perfectly, which turned a
    working download into a "that file is unavailable" for no reason at all.
    Content-Length on the GET says the same thing a beat later and is always
    there when it matters.
    """
    total = 0
    with open(path, "wb") as out:
        async with client().stream("GET", url, headers=headers or {}) as response:
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared and int(declared) > limit:
                raise FetchError("That file is too big to send through Telegram.")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > limit:
                    raise FetchError("That file is too big to send through Telegram.")
                out.write(chunk)
    return total
