"""DownloaderBot's platforms, providers, the fetching, and large files.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("download.py is loaded section by section by main.py -- run main.py")


# ─── module: downloader_bot.platforms ────────────────────────────────────────
"""Which platform a pasted link belongs to, and the two page-scrapes that are about *text* rather than media."""
import math
import re
from urllib.parse import parse_qsl, urlsplit

import httpx

import net
from net import FetchError, client, close_client, fetch_bytes

__all__ = [
    "FetchError", "client", "close_client", "fetch_bytes",
    "detect_platform", "canonical_link", "ANY_LINK_RE",
    "fetch_reddit_post", "reddit_is_media", "reddit_direct_image_url",
    "fetch_tweet_syndication",
]

INSTAGRAM_RE = re.compile(
    r"https?://(?:www\.|m\.)?instagram\.com/\S+", re.IGNORECASE
)
TIKTOK_RE = re.compile(
    r"https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/\S+", re.IGNORECASE
)

PINTEREST_RE = re.compile(
    r"https?://(?:[a-z0-9-]{1,8}\.)?"
    r"(?:pinterest\.(?:com|co\.[a-z]{2}|com\.[a-z]{2}|[a-z]{2})|pin\.it)/\S+",
    re.IGNORECASE,
)
REDDIT_RE = re.compile(
    r"https?://(?:www\.|old\.|m\.)?reddit\.com/r/\S+|https?://redd\.it/\S+",
    re.IGNORECASE,
)
TWITTER_RE = re.compile(
    r"https?://(?:www\.|mobile\.)?(?:twitter\.com|x\.com)/\w+/status(?:es)?/\d+",
    re.IGNORECASE,
)

YOUTUBE_RE = re.compile(
    r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com/(?:watch\?(?:[^\s#]*&)?v=|shorts/|live/|embed/)"
    r"|youtu\.be/)\S+",
    re.IGNORECASE,
)

_PLATFORM_PATTERNS = [
    ("instagram", INSTAGRAM_RE),
    ("tiktok", TIKTOK_RE),
    ("youtube", YOUTUBE_RE),
    ("reddit", REDDIT_RE),
    ("twitter", TWITTER_RE),
    ("pinterest", PINTEREST_RE),
]

ANY_LINK_RE = re.compile(
    "|".join(f"(?:{p.pattern})" for _, p in _PLATFORM_PATTERNS), re.IGNORECASE
)

_TRAILING_PUNCT = ".,;:!?)]}>»\"'"

_IG_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
_IG_POST = re.compile(r"/(p|reel|reels|tv)/([A-Za-z0-9_-]+)(?:/|$)")

_IG_USER_POST = re.compile(r"/([^/]+)" + _IG_POST.pattern)
_IG_NOT_USERS = {"share", "stories"}

_TT_HOSTS = {"tiktok.com", "www.tiktok.com", "m.tiktok.com"}
_TT_SHORT_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}

_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_YT_ID = re.compile(r"[A-Za-z0-9_-]{11}")

_TW_HOSTS = {"twitter.com", "www.twitter.com", "mobile.twitter.com",
             "x.com", "www.x.com", "mobile.x.com"}
_TW_STATUS = re.compile(r"/(\w+)/status(?:es)?/(\d+)(?:/|$)")

_RD_HOSTS = {"reddit.com", "www.reddit.com", "old.reddit.com", "m.reddit.com"}

_PIN_HOST = re.compile(
    r"(?:[a-z0-9-]{1,8}\.)?"
    r"(?:pinterest\.(?:com|co\.[a-z]{2}|com\.[a-z]{2}|[a-z]{2})|pin\.it)"
)
_PIN_POST = re.compile(r"/pin/(\d+)(?:/|$)")

def _trim(text: str) -> str:
    return text.rstrip(_TRAILING_PUNCT)

def _keep_path(host: str, path: str) -> str:
    return f"https://{host}{_trim(path)}"

def _canonical(platform: str, url: str) -> str:
    parts = urlsplit(_trim(url.strip()))
    host = (parts.hostname or "").lower()
    path = parts.path

    if platform == "instagram" and host in _IG_HOSTS:
        m = _IG_USER_POST.match(path)
        if m and m.group(1).lower() in _IG_NOT_USERS:
            m = None
        if m:
            kind, code = m.group(2), m.group(3)
        else:
            m = _IG_POST.match(path)
            kind, code = (m.group(1), m.group(2)) if m else ("", "")
        if kind:
            return f"https://www.instagram.com/{'reel' if kind == 'reels' else kind}/{code}/"
        return _keep_path("www.instagram.com", path)

    if platform == "tiktok":
        if host in _TT_HOSTS:
            return _keep_path("www.tiktok.com", path)
        if host in _TT_SHORT_HOSTS:
            return _keep_path(host, path)

    if platform == "youtube":
        video = ""
        if host in _YT_HOSTS:
            segments = [s for s in path.split("/") if s]
            if path.rstrip("/") == "/watch":
                values = [v for k, v in parse_qsl(parts.query, keep_blank_values=True) if k == "v"]
                video = values[0] if values else ""
            elif len(segments) >= 2 and segments[0] in ("shorts", "live", "embed"):
                video = segments[1]
        elif host == "youtu.be":
            segments = [s for s in path.split("/") if s]
            video = segments[0] if segments else ""
        if _YT_ID.fullmatch(video):
            return f"https://www.youtube.com/watch?v={video}"
        return url

    if platform == "twitter" and host in _TW_HOSTS:
        m = _TW_STATUS.match(path)
        if m:
            return f"https://x.com/{m.group(1)}/status/{m.group(2)}"
        return url

    if platform == "reddit":
        if host in _RD_HOSTS:
            return _keep_path("www.reddit.com", path)
        if host == "redd.it":
            return _keep_path("redd.it", path)

    if platform == "pinterest" and _PIN_HOST.fullmatch(host):
        m = _PIN_POST.match(path)
        if m and host != "pin.it":
            return f"https://www.pinterest.com/pin/{m.group(1)}/"
        return _keep_path(host, path)

    return url

def canonical_link(platform: str, url: str) -> str:
    """The link written the one way that identifies the post: share trackers, query strings and fragments gone, the host and path normalised, the punctuation a sentence leaves on the end of a link taken off."""
    try:
        return _canonical(platform, url)
    except Exception:
        return url

def detect_platform(text: str) -> tuple[str, str] | None:
    """Returns (platform, canonical_link) for the first recognized link in text, or None if nothing matches."""
    for name, pattern in _PLATFORM_PATTERNS:
        m = pattern.search(text)
        if m:
            return name, canonical_link(name, m.group(0))
    return None

TEXT_PAGE_LIMIT_BYTES = 8 * 1024 * 1024

async def fetch_reddit_post(url: str) -> dict:
    """Reddit's own public .json endpoint on any post URL -- what old.reddit and countless tools already rely on, no login needed for public subreddits."""
    json_url = url.split("?")[0].rstrip("/") + ".json"
    headers = {
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    unreadable = "Couldn't read that Reddit post -- it may have been removed."
    try:
        resp = await net.read_page("GET", json_url, headers=headers, timeout=15,
                                   limit=TEXT_PAGE_LIMIT_BYTES, too_big=lambda: FetchError(unreadable))
    except net.BadEncoding as exc:
        raise FetchError(unreadable) from exc
    if resp.status_code in (403, 429):
        raise FetchError(
            "Reddit blocked this request (their anti-scraping, not a bug here) -- "
            "try again later, or open the link directly."
        )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data[0]["data"]["children"][0]["data"]
    except (IndexError, KeyError, TypeError) as exc:
        raise FetchError("Couldn't read that Reddit post -- it may have been removed.") from exc

def reddit_is_media(post: dict) -> bool:
    hint = post.get("post_hint", "")
    return bool(post.get("is_video")) or hint in ("image", "hosted:video", "rich:video")

def reddit_direct_image_url(post: dict) -> str | None:
    """A plain-image post's direct URL, if this isn't a gallery/video."""
    if post.get("post_hint") == "image":
        return post.get("url_overridden_by_dest") or post.get("url")
    return None

def _tweet_id_from_url(url: str) -> str | None:
    m = re.search(r"/status(?:es)?/(\d+)", url)
    return m.group(1) if m else None

def _base36(x: float, precision: int = 60) -> str:
    """Python doesn't have JS's Number.prototype.toString(36) built in -- this reimplements it (integer part + fractional digits) just precisely enough to reproduce the syndication token below."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    int_part = int(x)
    frac_part = x - int_part
    int_str = "0"
    if int_part > 0:
        int_str = ""
        n = int_part
        while n > 0:
            int_str = digits[n % 36] + int_str
            n //= 36
    if frac_part <= 0:
        return int_str
    frac_str = ""
    f = frac_part
    for _ in range(precision):
        f *= 36
        d = int(f)
        frac_str += digits[d]
        f -= d
        if f <= 0:
            break
    return f"{int_str}.{frac_str}"

def _syndication_token(tweet_id: str) -> str:
    """X's embed widget computes this the same way to authorize an otherwise open syndication request -- not a secret, just an obfuscation step: ((id / 1e15) * pi) in base 36, with zeros and the decimal point stripped."""
    n = (int(tweet_id) / 1e15) * math.pi
    return re.sub(r"(0+|\.)", "", _base36(n))

async def fetch_tweet_syndication(url: str) -> dict | None:
    tweet_id = _tweet_id_from_url(url)
    if not tweet_id:
        return None
    token = _syndication_token(tweet_id)
    api_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token={token}&lang=en"
    try:
        resp = await net.read_page("GET", api_url, timeout=15, limit=TEXT_PAGE_LIMIT_BYTES,
                                   too_big=lambda: FetchError("That tweet's answer was too big."))
    except (httpx.HTTPError, FetchError):
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None

    if not data or data.get("__typename") != "Tweet":
        return None
    return data

# ─── module: downloader_bot.net ──────────────────────────────────────────────
"""One HTTP client for the whole process, and the two ways this bot fetches media with it."""
from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import zlib

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

CRAWLER_UA = "TelegramBot (like TwitterBot)"

MAX_RESPONSE_BYTES = int(os.environ.get("DBOT_MAX_DOWNLOAD_MB", "48")) * 1024 * 1024

CONNECT_TIMEOUT = float(os.environ.get("DBOT_CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.environ.get("DBOT_READ_TIMEOUT", "30"))

FAILOVER_CONNECT_TIMEOUT = 4.0

class FetchError(Exception):
    """Raised with a message that is safe to show the user as-is."""

class BadEncoding(FetchError):
    """The server sent a body in an encoding this bot does not read (or one that did not decode). See body_chunks()."""

class Trickle(BadEncoding):
    """The server sent its body in far too many pieces for its size: see body_chunks()."""

ALLOW_PRIVATE_HOSTS = os.environ.get("DBOT_ALLOW_PRIVATE_HOSTS", "").strip().lower() in ("1", "true", "yes")

class BlockedAddress(Exception):
    """The name resolves to an address that is not on the public internet."""

def is_public_address(address: str) -> bool:
    """Whether an IP address is somewhere on the public internet: not this machine, a private network, a link-local address (which is where cloud metadata services live), shared address space, multicast, or unspecified."""
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(ip.is_global and not ip.is_multicast)

async def _resolve(host: str, port: int) -> list[str]:
    """Every address `host` resolves to. Its own function so that a test can say what a name resolves to."""
    infos = await asyncio.wait_for(
        asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM), CONNECT_TIMEOUT)
    addresses: list[str] = []
    for _family, _type, _proto, _canon, sockaddr in infos:
        if sockaddr[0] not in addresses:
            addresses.append(sockaddr[0])
    return addresses

async def public_addresses(host: str, port: int) -> list[str]:
    """The addresses to try for `host`, all of them public -- or BlockedAddress."""
    addresses = await _resolve(host, port)
    if not addresses:
        raise OSError(f"no address for {host}")
    if not ALLOW_PRIVATE_HOSTS:
        for address in addresses:
            if not is_public_address(address):
                raise BlockedAddress(f"{host} is not a public address")
    return addresses

def _guarded_transport(inner=None):
    """The transport `client()` uses: `inner` (an ordinary httpx transport) behind public_addresses()."""

    class Refused(httpx.ConnectError):
        pass

    class PublicOnlyTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self._inner = inner or httpx.AsyncHTTPTransport(
                limits=httpx.Limits(max_connections=8, max_keepalive_connections=4,
                                    keepalive_expiry=30.0))

        async def handle_async_request(self, request):
            url = request.url
            host = url.raw_host.decode("ascii")
            port = url.port or (443 if url.scheme == "https" else 80)
            try:
                addresses = await public_addresses(host, port)
            except BlockedAddress as exc:
                raise Refused(str(exc), request=request) from None
            except (OSError, asyncio.TimeoutError) as exc:
                raise httpx.ConnectError(f"could not resolve {host}: {exc}", request=request) from exc

            addresses = sorted(addresses, key=lambda address: ":" in address)
            failure = None
            for index, address in enumerate(addresses):

                extensions = dict(request.extensions)
                if url.scheme == "https":
                    extensions["sni_hostname"] = host
                if index < len(addresses) - 1:

                    timeouts = dict(extensions.get("timeout") or {})
                    if timeouts.get("connect") is not None:
                        timeouts["connect"] = min(timeouts["connect"], FAILOVER_CONNECT_TIMEOUT)
                        extensions["timeout"] = timeouts
                pinned = httpx.Request(request.method, url.copy_with(host=address),
                                       headers=request.headers, stream=request.stream,
                                       extensions=extensions)
                try:
                    response = await self._inner.handle_async_request(pinned)
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    failure = exc
                    continue
                return await _without_redirect_body(response)
            raise failure

        async def aclose(self):
            await self._inner.aclose()

    return PublicOnlyTransport()

_REDIRECTS = (301, 302, 303, 307, 308)

async def _without_redirect_body(response):
    """A redirect, with its body thrown away unread; anything else, as it came."""
    if response.status_code not in _REDIRECTS or "location" not in response.headers:
        return response
    await response.aclose()
    kept = [(k, v) for k, v in response.headers.multi_items()
            if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")]
    return httpx.Response(response.status_code, headers=kept, content=b"",
                          extensions=response.extensions)

_client: httpx.AsyncClient | None = None

ACCEPT_ENCODING = "gzip, deflate"

def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
            headers={"User-Agent": UA, "Accept-Encoding": ACCEPT_ENCODING},
            transport=_guarded_transport(),
        )
    return _client

async def close_client() -> None:
    """Called from the bot's shutdown hook."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None

_DECODE_BLOCK = 64 * 1024

_KNOWN_ENCODINGS = ("gzip", "x-gzip", "deflate", "br", "zstd", "compress", "x-compress")

def _content_encodings(response) -> list[str]:
    """The real encodings a body was sent in, lower-cased: "identity" (which means none), empty entries and tokens that are no encoding at all are dropped."""
    names = [part.strip() for part in response.headers.get("content-encoding", "").lower().split(",")]
    return [name for name in names if name in _KNOWN_ENCODINGS]

class _Inflater:
    """One gzip or deflate body, decompressed a bounded piece at a time."""

    def __init__(self, limit: int, too_big, deflate: bool):
        self.limit = limit
        self.too_big = too_big
        self.deflate = deflate
        self.total = 0
        self.finished = False
        self._first = deflate
        self._head = b""
        self.d = zlib.decompressobj() if deflate else zlib.decompressobj(16 + zlib.MAX_WBITS)

    def _room(self) -> int:
        """max_length for the next call: one byte more than what may still be accepted, so that a body over the limit shows as over rather than as exactly at it."""
        return max(min(self.limit - self.total + 1, _DECODE_BLOCK), 1)

    def _decompress(self, data: bytes, room: int) -> bytes:
        try:
            return self.d.decompress(data, room)
        except zlib.error:
            if not self._first:
                raise BadEncoding("The server sent a body that did not decode.") from None

        self._first = False
        self.d = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            return self.d.decompress(data, room)
        except zlib.error:
            raise BadEncoding("The server sent a body that did not decode.") from None

    def _drain(self, data: bytes):
        """Decoded pieces of `data`, none over _DECODE_BLOCK, until zlib has nothing more to give for it."""
        room = self._room()
        out = self._decompress(data, room)
        if data:
            self._first = False
        while True:
            self.total += len(out)
            if self.total > self.limit:
                raise self.too_big()
            if out:
                yield out
            if self.d.eof:

                self.finished = True
                return

            if self.d.unconsumed_tail or len(out) == room:
                room = self._room()
                out = self._decompress(self.d.unconsumed_tail, room)
            else:
                return

    def feed(self, data: bytes):
        if self._first and data:

            data = self._head + data
            if len(data) < 2:
                self._head = data
                return
            self._head = b""
        if data and not self.finished:
            yield from self._drain(data)

    def finish(self):

        if not self.finished:
            yield from self._drain(b"")

async def body_chunks(response, limit: int, too_big):
    """The body of a streamed `response`, decoded, in pieces; `too_big()` is called (it returns the exception to raise) the moment more than `limit` decoded bytes have arrived."""
    names = _content_encodings(response)
    if not names:
        inflater = None
    elif names in (["gzip"], ["x-gzip"]):
        inflater = _Inflater(limit, too_big, deflate=False)
    elif names == ["deflate"]:
        inflater = _Inflater(limit, too_big, deflate=True)
    else:
        raise BadEncoding("The server sent a body in an encoding this bot does not read.")
    total = 0
    if response.is_stream_consumed:

        content = response.content
        if len(content) > limit:
            raise too_big()
        if content:
            yield content
        return

    raw_cap = limit + limit // 50 + 64 * 1024
    raw_total = 0

    pieces_left = limit // 1024 + 1024
    raw_chunks = response.aiter_raw()
    try:
        async for raw in raw_chunks:
            pieces_left -= 1
            if pieces_left < 0:
                raise Trickle("The server sent its answer in pieces too small to read.")
            if inflater is None:
                total += len(raw)
                if total > limit:
                    raise too_big()
                if raw:
                    yield raw
                continue
            raw_total += len(raw)
            if raw_total > raw_cap:
                raise too_big()
            for piece in inflater.feed(raw):
                yield piece
            if inflater.finished:
                return
        if inflater is not None:
            for piece in inflater.finish():
                yield piece
    finally:
        await raw_chunks.aclose()

async def read_page(method: str, url: str, *, limit: int, too_big, declared_too_big=None,
                    **kwargs) -> httpx.Response:
    """A whole small document, read under a ceiling, as an ordinary `httpx.Response`: status, final URL, history, the body decoded."""
    async with client().stream(method, url, **kwargs) as resp:
        declared = resp.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise (declared_too_big(int(declared)) if declared_too_big else too_big())
        body = bytearray()
        async for chunk in body_chunks(resp, limit, too_big):
            body += chunk

        kept = [(k, v) for k, v in resp.headers.multi_items()
                if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")]
        done = httpx.Response(resp.status_code, headers=kept, content=bytes(body),
                              request=resp.request)
        done.history = list(resp.history)
        return done

async def fetch_bytes(url: str, limit: int = MAX_RESPONSE_BYTES,
                      headers: dict | None = None) -> bytes:
    """GET a URL into memory, refusing anything that would not fit in a Telegram upload anyway."""
    def too_big():
        return FetchError("That file is too big to send through Telegram.")

    async with client().stream("GET", url, headers=headers or {}) as response:
        response.raise_for_status()
        declared = response.headers.get("content-length")
        if declared and int(declared) > limit:
            raise too_big()
        chunks: list[bytes] = []
        async for chunk in body_chunks(response, limit, too_big):
            chunks.append(chunk)
    return b"".join(chunks)

ESTIMATE_SLACK = 1.25

class TooLarge(FetchError):
    """Over the size ceiling this download was given."""

async def stream_to_file(url: str, path: str, limit: int = MAX_RESPONSE_BYTES,
                         headers: dict | None = None) -> int:
    """Same, but to disk, for the things that are too big to want in memory."""
    def too_big():
        return TooLarge("That file is too big to send through Telegram.")

    total = 0
    with open(path, "wb") as out:
        async with client().stream("GET", url, headers=headers or {}) as response:
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared and int(declared) > limit:
                raise too_big()
            guessed = response.headers.get("estimated-content-length")
            if guessed and guessed.isdigit() and int(guessed) > limit * ESTIMATE_SLACK:
                raise too_big()
            async for chunk in body_chunks(response, limit, too_big):
                total += len(chunk)
                out.write(chunk)
    return total

# ─── module: downloader_bot.cards ────────────────────────────────────────────
"""Renders a plain, consistent 'quote card' image for text-based Reddit/ Twitter posts -- the actual reason to download these instead of just screenshotting: no UI chrome, no notification banners caught mid-shot, no light/dark-mode mismatch, and it's already square-ish and clean enough to repost as-is."""
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
PADDING = 56
LINE_HEIGHT = 50
MAX_BODY_LINES = 16

BG = (22, 24, 28)
FG = (235, 236, 240)
MUTED = (145, 150, 160)
ACCENT = {
    "reddit": (255, 69, 0),
    "twitter": (29, 155, 240),
}

@lru_cache(maxsize=8)
def _font(size: int) -> ImageFont.FreeTypeFont:
    """Cached: there are exactly four sizes in this file, and rebuilding the same four font objects for every card is work with no result."""
    return ImageFont.load_default(size=size)

def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        cur = ""
        if not words:
            lines.append("")
            continue
        for word in words:
            trial = f"{cur} {word}".strip()
            if draw.textlength(trial, font=font) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines

def render_card(platform: str, source: str, author: str, body: str, meta: str = "") -> bytes:
    """platform: "reddit" or "twitter" (picks the accent color)."""
    font_source = _font(34)
    font_author = _font(26)
    font_body = _font(38)
    font_meta = _font(26)

    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    max_text_width = WIDTH - PADDING * 2 - 16

    body = (body or "").strip() or "(no text)"
    body_lines = _wrap(scratch, body, font_body, max_text_width)
    truncated = len(body_lines) > MAX_BODY_LINES
    body_lines = body_lines[:MAX_BODY_LINES]
    if truncated:
        body_lines[-1] = body_lines[-1].rstrip() + "…"

    header_h = 100
    body_h = max(len(body_lines), 1) * LINE_HEIGHT
    footer_h = 56 if meta else 0
    height = PADDING + header_h + body_h + footer_h + PADDING

    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    accent = ACCENT.get(platform, (130, 130, 130))
    draw.rectangle([0, 0, 12, height], fill=accent)

    x = PADDING + 16
    draw.text((x, PADDING), source, font=font_source, fill=accent)
    draw.text((x, PADDING + 44), author, font=font_author, fill=MUTED)

    y = PADDING + header_h
    for line in body_lines:
        draw.text((x, y), line, font=font_body, fill=FG)
        y += LINE_HEIGHT

    if meta:
        draw.text((x, y + 12), meta, font=font_meta, fill=MUTED)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ─── module: downloader_bot.probe ────────────────────────────────────────────
#!/usr/bin/env python3
"""Ask every download route whether it still works, and say which ones do."""
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

# ─── module: downloader_bot.video ────────────────────────────────────────────
"""The yt-dlp provider: download a video with yt-dlp so the bot can re-send it."""
import asyncio
import contextlib
import glob
import json
import logging
import math
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass

MAX_DOWNLOAD_MB = int(os.environ.get("DBOT_MAX_DOWNLOAD_MB", "48"))

MAX_DURATION_S = int(os.environ.get("DBOT_MAX_DURATION_SECONDS", "10800"))

MAX_HEIGHT = int(os.environ.get("DBOT_MAX_HEIGHT") or 1080)
FRAGMENTS_AT_ONCE = max(1, int(os.environ.get("DBOT_YTDLP_FRAGMENTS") or 4))
SIZE_MARGIN = 0.96

SOCKET_TIMEOUT_S = int(os.environ.get("DBOT_SOCKET_TIMEOUT", "30"))

logger = logging.getLogger(__name__)

YT_PLAYER_CLIENTS = [
    c.strip() for c in (os.environ.get("DBOT_YT_PLAYER_CLIENTS") or "").split(",") if c.strip()
]

COOKIEFILE = os.environ.get("DBOT_COOKIES_FILE") or None
SITE_COOKIEFILES = {
    "youtube": os.environ.get("DBOT_YT_COOKIES_FILE") or None,
    "instagram": os.environ.get("DBOT_IG_COOKIES_FILE") or None,
    "tiktok": os.environ.get("DBOT_TT_COOKIES_FILE") or None,
    "twitter": os.environ.get("DBOT_TW_COOKIES_FILE") or None,
    "reddit": os.environ.get("DBOT_RD_COOKIES_FILE") or None,
}

_COOKIE_TEXT_VARS = {"youtube": "DBOT_YT_COOKIES", "instagram": "DBOT_IG_COOKIES",
                     "tiktok": "DBOT_TT_COOKIES", "twitter": "DBOT_TW_COOKIES",
                     "reddit": "DBOT_RD_COOKIES", "other": "DBOT_COOKIES"}
_cookie_text_files: dict = {}

_cookie_text_refused: dict = {}

def _cookie_text_problem(text: str) -> "str | None":
    """Why `text` is not a cookies.txt, or None if it is one."""

    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        if not line.strip() or (line.strip().startswith("#") and not line.startswith("#HttpOnly_")):
            continue
        line = line.removeprefix("#HttpOnly_")
        fields = line.split("\t")
        if len(fields) != 7:
            return (f"line {number} of {len(lines)} has {len(fields)} tab-separated field(s), not 7 "
                    "(were the tabs pasted as spaces?)")
        domain, flag, path, secure, expires, name, _value = fields

        if not domain:
            what = "an empty domain"
        elif flag != ("TRUE" if domain.startswith(".") else "FALSE"):
            what = "a subdomains flag (field 2) that does not match its domain"
        elif not path.startswith("/"):
            what = "a path (field 3) that does not start with /"
        elif secure not in ("TRUE", "FALSE"):
            what = "a secure flag (field 4) that is not TRUE or FALSE"
        elif not re.fullmatch(r"[0-9]*", expires):
            what = "an expiry (field 5) that is not digits"
        elif not name:
            what = "an empty name (field 6)"
        else:
            continue
        return f"line {number} of {len(lines)} has {what}"
    return None

_COOKIE_HEADER_RE = re.compile(r"#( Netscape)? HTTP Cookie File")

def _cookiefile_from_text(site: str) -> "str | None":
    var = _COOKIE_TEXT_VARS.get(site)
    text = os.environ.get(var) if var else None
    if not text or not text.strip():
        return None

    text = text.removeprefix("\ufeff")
    if not text.strip():
        return None
    path = _cookie_text_files.get(site)
    if path and os.path.exists(path):
        return path
    if _cookie_text_refused.get(site) == os.environ.get(var):
        return None

    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n").replace("\\t", "\t")
    problem = _cookie_text_problem(text)
    if problem:
        _cookie_text_refused[site] = os.environ.get(var)
        logger.warning("%s is not a cookies.txt: %s. Those cookies are not used.", var, problem)
        return None

    text = text.lstrip("\r\n \t")
    if not _COOKIE_HEADER_RE.match(text):
        text = "# Netscape HTTP Cookie File\n" + text
    fd, path = tempfile.mkstemp(prefix=f"cookies-{site}-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    _cookie_text_files[site] = path
    return path

def cookiefile_for(site: str) -> "str | None":
    """The cookie jar for this site: its own file, its own pasted text, then the every-site file, then the every-site text."""
    for candidate in (SITE_COOKIEFILES.get(site), _cookiefile_from_text(site),
                      COOKIEFILE, _cookiefile_from_text("other")):
        if candidate and os.path.exists(candidate):
            return candidate
    return None

PROXY = os.environ.get("DBOT_PROXY") or None
SITE_PROXIES = {
    "youtube": os.environ.get("DBOT_YT_PROXY") or None,
    "instagram": os.environ.get("DBOT_IG_PROXY") or None,
    "tiktok": os.environ.get("DBOT_TT_PROXY") or None,
    "twitter": os.environ.get("DBOT_TW_PROXY") or None,
    "reddit": os.environ.get("DBOT_RD_PROXY") or None,
}

BOT_CHECK_MARKERS = ("sign in to confirm", "confirm you're not a bot",
                     "confirm you are not a bot")

LOGIN_WALL_MARKERS = (
    "redirected to the login page",
    "rate-limit for accessing posts anonymously",
    "requested content is not available, rate-limit reached",
    "login required",
    "you need to log in",
    "use --cookies",
    "--cookies-from-browser",
)

def _site_of(url: str) -> str:
    """Which per-site cookie jar and proxy apply."""
    lowered = url.lower()
    for site in ("instagram", "tiktok", "youtube", "pinterest", "reddit"):
        if site in lowered:
            return site
    if "youtu.be" in lowered:
        return "youtube"
    if "twitter.com" in lowered or "//x.com" in lowered:
        return "twitter"
    if "redd.it" in lowered:
        return "reddit"
    if "pin.it" in lowered:
        return "pinterest"
    return "other"

class BlockedBySource(Exception):
    """The site refused the server, not the link."""

    def __init__(self, message: str, kind: str = "bot_check", site: str = "other"):
        super().__init__(message)
        self.kind = kind
        self.site = site

class TooLarge(Exception):
    """The clip is over the size/duration ceiling. Message is user-facing."""

def _reject_long(info, *, incomplete):
    """yt-dlp's match_filter hook: runs on the *metadata*, before a single byte of media is fetched."""
    duration = info.get("duration")
    if duration and duration > MAX_DURATION_S:
        return (
            f"that clip is {int(duration) // 60} minutes long, and this bot "
            f"caps downloads at {MAX_DURATION_S // 60}"
        )
    return None

def _size_of(fmt: dict, duration) -> "int | None":
    """A format's size in bytes, as yt-dlp states it or from its bitrate and the duration; None when neither is known."""
    for key in ("filesize", "filesize_approx"):
        value = fmt.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return int(value)
    rate = fmt.get("tbr")
    if isinstance(rate, (int, float)) and rate > 0 and duration:
        return int(rate * 125 * duration)
    return None

def _wanted(fmt: dict) -> bool:
    return (bool(fmt.get("format_id")) and fmt.get("ext") != "mhtml" and not fmt.get("has_drm")
            and "storyboard" not in str(fmt.get("format_note") or "").lower())

def _has(fmt: dict, kind: str) -> bool:
    return str(fmt.get(kind) or "none") != "none"

def _video_rank(fmt: dict) -> tuple:
    codec = str(fmt.get("vcodec") or "")
    plays = 2 if codec.startswith(("avc1", "h264")) else 1 if codec.startswith(("vp9", "vp09")) else 0
    return plays, min(fmt.get("height") or 0, MAX_HEIGHT), fmt.get("tbr") or 0

def _audio_rank(fmt: dict) -> tuple:
    codec = str(fmt.get("acodec") or "")
    return (1 if codec.startswith(("mp4a", "aac")) else 0), min(fmt.get("abr") or fmt.get("tbr") or 0, 192)

def pick_format(info: dict, budget_bytes: int) -> "str | None":
    """The best version with sound that fits the budget -- H.264 first, which every Telegram app plays, then the tallest up to MAX_HEIGHT -- as a yt-dlp format id, or None."""
    duration = info.get("duration") or 0
    formats = [fmt for fmt in info.get("formats") or () if _wanted(fmt)]
    room = budget_bytes * SIZE_MARGIN
    tall = lambda fmt: (fmt.get("height") or 0) <= MAX_HEIGHT
    audios = sorted((fmt for fmt in formats if _has(fmt, "acodec") and not _has(fmt, "vcodec")),
                    key=_audio_rank, reverse=True)
    best = None
    for fmt in formats:
        if not _has(fmt, "vcodec") or not tall(fmt):
            continue
        size = _size_of(fmt, duration)
        if size is None:
            continue
        if _has(fmt, "acodec"):
            choice = (_video_rank(fmt) + (1, 0), fmt["format_id"]) if size <= room else None
        else:
            choice = None
            for audio in audios:
                extra = _size_of(audio, duration)
                if extra is not None and size + extra <= room:
                    choice = (_video_rank(fmt) + _audio_rank(audio), f"{fmt['format_id']}+{audio['format_id']}")
                    break
        if choice is not None and (best is None or choice[0] > best[0]):
            best = choice
    return None if best is None else best[1]

def sizes_known(info: dict) -> bool:
    duration = info.get("duration") or 0
    return any(_size_of(fmt, duration) for fmt in info.get("formats") or () if _wanted(fmt) and _has(fmt, "vcodec"))

# The quality picker (private chats, for the sites whose routes list their versions: resolvers.PICK_PLATFORMS).
# A choice is AUDIO or a quality as people name it: the site's own label ("480p" -- it calls its 608x1080
# versions that), else the shorter side of the picture, so a vertical 1080x1920 clip is "1080p". The default
# download (no choice) is unchanged: the tallest picture up to MAX_HEIGHT that fits.
AUDIO = "audio"
PICK_MIN_QUALITY = 240
PICK_MAX_QUALITIES = 5

def quality_of(fmt: dict) -> int:
    label = re.match(r"(\d{3,4})p", str(fmt.get("format_note") or ""))
    if label:
        return int(label.group(1))
    width, height = fmt.get("width") or 0, fmt.get("height") or 0
    return min(width, height) if width and height else height

def _sound_rank(fmt: dict) -> tuple:
    """The video's own sound first (not a dubbed track, nor the dynamic-range-compressed copy), then as _audio_rank."""
    own = (fmt.get("language_preference") or 0) >= 0
    compressed = "drc" in str(fmt.get("format_id") or "").lower()
    return (own, not compressed) + _audio_rank(fmt)

def _best_audio(formats) -> "dict | None":
    audios = [fmt for fmt in formats if _has(fmt, "acodec") and not _has(fmt, "vcodec")]
    return max(audios, key=_sound_rank) if audios else None

def _picture_of(formats, quality: int) -> "dict | None":
    """The version to fetch for `quality`: H.264 first (every Telegram app plays it), then one whose size is stated (a plain file, not a stream: the size on the button is then the real one)."""
    pictures = [fmt for fmt in formats if _has(fmt, "vcodec") and quality_of(fmt) == quality]
    return max(pictures, key=lambda fmt: (_video_rank(fmt)[0], bool(fmt.get("filesize")),
                                          _has(fmt, "acodec"), fmt.get("tbr") or 0)) if pictures else None

def _choice_format(formats, choice, duration) -> "tuple[str, int | None] | None":
    """(yt-dlp format id, size in bytes or None) for one choice, or None when the video has no such version."""
    audio = _best_audio(formats)
    if choice == AUDIO:
        return (audio["format_id"], _size_of(audio, duration)) if audio else None
    picture = _picture_of(formats, choice)
    if picture is None:
        return None
    size = _size_of(picture, duration)
    if _has(picture, "acodec"):
        return picture["format_id"], size
    if audio is None:
        return None
    extra = _size_of(audio, duration)
    return (f"{picture['format_id']}+{audio['format_id']}",
            size + extra if size is not None and extra is not None else None)

def choices_of(info: dict, budget_bytes: int) -> dict:
    """What the picker can offer for a video yt-dlp has read: {"qualities": [(quality, bytes)], "audio": bytes or None}, only the versions whose stated size fits `budget_bytes` (a version with no stated size is left out: it could not be promised)."""
    duration = info.get("duration") or 0
    formats = [fmt for fmt in info.get("formats") or () if _wanted(fmt)]
    room = budget_bytes * SIZE_MARGIN
    found = sorted({quality_of(fmt) for fmt in formats if _has(fmt, "vcodec")})
    qualities = []
    for quality in found:
        if not PICK_MIN_QUALITY <= quality <= MAX_HEIGHT:
            continue
        chosen = _choice_format(formats, quality, duration)
        if chosen and chosen[1] is not None and chosen[1] <= room:
            qualities.append((quality, chosen[1]))
    audio = _choice_format(formats, AUDIO, duration)
    return {"qualities": qualities[-PICK_MAX_QUALITIES:],
            "audio": audio[1] if audio and audio[1] is not None and audio[1] <= room else None}

def pick_choice(info: dict, choice, budget_bytes: int) -> str:
    """The yt-dlp format id for what was picked; TooLarge when that version is not there or does not fit."""
    duration = info.get("duration") or 0
    formats = [fmt for fmt in info.get("formats") or () if _wanted(fmt)]
    chosen = _choice_format(formats, choice, duration)
    if chosen is None:
        raise TooLarge("That version of the video is not there any more.")
    if chosen[1] is not None and chosen[1] > budget_bytes * SIZE_MARGIN:
        raise TooLarge("That version is over this bot's size limit.")
    return chosen[0]

def _format_selector(max_mb: int | None = None) -> str:
    mb = MAX_DOWNLOAD_MB if max_mb is None else max_mb
    return (

        f"bv*[filesize<{mb}M]+ba/"
        f"bv*[filesize_approx<{mb}M]+ba/"

        f"b[filesize<{mb}M]/"
        f"b[filesize_approx<{mb}M]/"

        "bv*+ba/b"
    )

def _remove_leftovers(out_dir: str, unique_id: str, keep: str | None = None) -> None:
    """Everything yt-dlp wrote for this download except `keep`."""
    for path in glob.glob(os.path.join(glob.escape(out_dir), f"{unique_id}.*")):
        if keep is not None and os.path.abspath(path) == os.path.abspath(keep):
            continue
        try:
            os.remove(path)
        except OSError:
            pass

_slots = threading.Condition()
_slots_held = 0
_swapping = False
SWAP_WAIT_S = 300.0

@contextlib.contextmanager
def _slot():
    global _slots_held
    with _slots:
        while _swapping:
            _slots.wait(timeout=5.0)
        _slots_held += 1
    try:
        yield
    finally:
        with _slots:
            _slots_held -= 1
            _slots.notify_all()

def use_ytdlp_from(path: str) -> bool:
    """Make `path` (a folder holding a newer yt_dlp package) the one every later download imports."""
    global _swapping
    with _slots:
        _swapping = True
        try:
            deadline = time.monotonic() + SWAP_WAIT_S
            while _slots_held:
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                _slots.wait(timeout=min(left, 5.0))
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)

            for name in [n for n in sys.modules if n == "yt_dlp" or n.startswith("yt_dlp.")]:
                del sys.modules[name]
            return True
        finally:
            _swapping = False
            _slots.notify_all()

def ytdlp_version() -> "str | None":
    """The version a download would use right now, without importing it."""
    for entry in sys.path:
        candidate = os.path.join(entry, "yt_dlp", "version.py")
        if os.path.isfile(candidate):
            try:
                with open(candidate, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("__version__"):
                            return line.split("=", 1)[1].strip().strip("'\"")
            except OSError:
                return None
    return None

def download_video(url: str, out_dir: str, max_mb: int | None = None, cancel=None, choice=None) -> str:
    """Downloads the video at `url` into `out_dir`, returns the local file path. `choice` is what was picked in the quality picker (AUDIO or a quality), None for the default version."""
    mb = MAX_DOWNLOAD_MB if max_mb is None else max_mb
    with _slot():
        import yt_dlp

        os.makedirs(out_dir, exist_ok=True)
        unique_id = uuid.uuid4().hex
        outtmpl = os.path.join(out_dir, f"{unique_id}.%(ext)s")

        def stop_if_asked(*_ignored):
            if cancel is not None and cancel.is_set():
                raise yt_dlp.utils.DownloadCancelled("nobody is waiting for this download any more")

        def match_filter(info, *, incomplete):

            stop_if_asked()
            return None

        path = None
        try:
            path = _download(yt_dlp, url, mb, outtmpl, stop_if_asked, match_filter, choice)
            stop_if_asked()
            return path
        except BaseException:
            path = None
            raise
        finally:
            _remove_leftovers(out_dir, unique_id, keep=path)

def _blocked(exc: Exception, site: str) -> Exception:
    """`exc` as BlockedBySource when the site turned the request away (a bot check or a login wall), else `exc` itself."""
    lowered = str(exc).lower()
    if any(marker in lowered for marker in BOT_CHECK_MARKERS):
        return BlockedBySource(str(exc), "bot_check", site)
    if any(marker in lowered for marker in LOGIN_WALL_MARKERS):
        return BlockedBySource(str(exc), "login_required", site)
    return exc

def read_info(url: str) -> dict:
    """What yt-dlp reads about the video at `url` without fetching it (its title, length and versions), for the quality picker. BlockedBySource when the site turned the request away."""
    with _slot():
        import yt_dlp
        ydl_opts = _options(url, MAX_DOWNLOAD_MB, None, None, None)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:
                found = _blocked(exc, _site_of(url))
                if found is exc:
                    raise
                raise found from exc
    if info is None or info.get("_type") in ("playlist", "multi_video"):
        raise TooLarge("That link is not one video this bot can fetch.")
    return info

def _options(url: str, mb: int, outtmpl, progress_hook, match_filter) -> dict:
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": _format_selector(mb),
        "max_filesize": mb * 1024 * 1024,
        "match_filter": match_filter,
        "progress_hooks": [progress_hook],
        "socket_timeout": SOCKET_TIMEOUT_S,
        "retries": 3,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": FRAGMENTS_AT_ONCE,
        "http_chunk_size": 10 * 1024 * 1024,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "noprogress": True,

        "cachedir": False,
        "merge_output_format": "mp4",
    }
    for key in ("outtmpl", "match_filter"):
        if ydl_opts[key] is None:
            del ydl_opts[key]
    if progress_hook is None:
        del ydl_opts["progress_hooks"]
    if YT_PLAYER_CLIENTS:
        ydl_opts["extractor_args"] = {"youtube": {"player_client": YT_PLAYER_CLIENTS}}
    site = _site_of(url)
    cookiefile = cookiefile_for(site)
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile
    proxy = SITE_PROXIES.get(site) or PROXY
    if proxy:
        ydl_opts["proxy"] = proxy
    return ydl_opts

def _download(yt_dlp, url: str, mb: int, outtmpl: str, progress_hook, match_filter, choice=None) -> str:
    """Read the video's versions first, choose the best one that fits `mb` (pick_format) or the one picked (pick_choice), then fetch only that one."""
    ydl_opts = _options(url, mb, outtmpl, progress_hook, match_filter)
    site = _site_of(url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as exc:
            found = _blocked(exc, site)
            if found is exc:
                raise
            raise found from exc
    if info is None or info.get("_type") in ("playlist", "multi_video"):
        raise TooLarge("That link is not one video this bot can fetch.")
    too_long = _reject_long(info, incomplete=False)
    if too_long:
        raise TooLarge(f"Not fetched: {too_long} minutes.")
    if choice is not None:
        chosen = pick_choice(info, choice, mb * 1024 * 1024)
    else:
        chosen = pick_format(info, mb * 1024 * 1024)
    if chosen is None and sizes_known(info):
        raise TooLarge(f"Even its smallest version is over this bot's {mb} MB limit.")
    if chosen is not None:
        ydl_opts["format"] = chosen
        logger.info("yt-dlp: %s, %ss, format %s for a %d MB budget", site, info.get("duration"), chosen, mb)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            if site == "youtube":
                # Read afresh: fetching from the reading above was refused (HTTP 403) for most single-file
                # versions and some pairs, measured 2026-11-15 with yt-dlp 2026.10.26 -- the file addresses
                # don't survive being processed a second time. A fresh read costs ~3 s and fetched 6 of 6.
                info = ydl.extract_info(url, download=True)
            else:
                info = ydl.process_ie_result(info, download=True)
        except Exception as exc:
            found = _blocked(exc, site)
            if found is exc:
                raise
            raise found from exc
        path = ydl.prepare_filename(info)

        if not os.path.exists(path):
            base, _ = os.path.splitext(path)
            mp4_path = base + ".mp4"
            if os.path.exists(mp4_path):
                path = mp4_path
    if not os.path.exists(path):
        raise TooLarge(
            f"That file is over this bot's {mb} MB limit, so the "
            "download was stopped."
        )
    return path

PROBE_SECONDS = 5

PROBE_BUDGET_SECONDS = 10
PROBE_MAX_BYTES = 64 * 1024
MAX_SIDE = 16384
MAX_SECONDS = 2 ** 31 - 1

@dataclass(frozen=True)
class VideoShape:
    """What the player will show: the DISPLAYED size (the stored size, widened by a non-square pixel and turned a quarter when the file says so) and the length in whole seconds, or None when ffprobe did not say."""
    width: int
    height: int
    duration: "int | None" = None

class ProbeRun:
    """One delivery's probing."""

    def __init__(self):
        self.timed_out = False
        self.spent = 0.0

    @property
    def exhausted(self) -> bool:
        """No more probing for this delivery."""
        return self.timed_out or self.spent >= PROBE_BUDGET_SECONDS

    def allowance(self) -> float:
        """How long the next probe may take: its own limit, or what is left of the delivery's budget if that is less."""
        return min(PROBE_SECONDS, max(0.0, PROBE_BUDGET_SECONDS - self.spent))

def _side(value) -> "int | None":
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_SIDE:
        return None
    return value

def _quarter_turn(stream: dict) -> bool:
    """Whether the player turns the picture 90 or 270 degrees, which swaps its sides."""
    turn = None
    side_data = stream.get("side_data_list")
    for data in side_data if isinstance(side_data, list) else ():
        if isinstance(data, dict) and "rotation" in data:
            turn = data["rotation"]
            break
    if turn is None:
        tags = stream.get("tags")
        turn = tags.get("rotate") if isinstance(tags, dict) else None
    try:
        turn = float(turn)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(turn):
        return False
    return round(abs(turn) / 90) % 2 == 1

def _display_width(width: int, ratio) -> int:
    """`width` widened by a non-square pixel ("N:D"), as the player shows it."""
    if isinstance(ratio, str) and ratio.count(":") == 1:
        try:
            n, d = (int(part) for part in ratio.split(":"))
            if n > 0 and d > 0 and n != d:
                return min(MAX_SIDE, max(1, round(width * n / d)))
        except (ValueError, OverflowError):
            pass
    return width

def shape_from_ffprobe(data) -> "VideoShape | None":
    """The shape from ffprobe's JSON, or None for anything that is not a plausible picture. Pure."""
    try:
        streams = data["streams"]
        stream = streams[0]
        width, height = _side(stream.get("width")), _side(stream.get("height"))
    except (AttributeError, IndexError, KeyError, TypeError):
        return None
    if width is None or height is None:
        return None
    width = _display_width(width, stream.get("sample_aspect_ratio"))
    if _quarter_turn(stream):
        width, height = height, width
    duration = None
    try:
        seconds = float(data["format"]["duration"])
        if math.isfinite(seconds) and 0 <= seconds <= MAX_SECONDS:
            duration = int(round(seconds))
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    return VideoShape(width, height, duration)

def _ffprobe_argv() -> "list[str] | None":
    """The command that starts ffprobe, or None."""
    found = shutil.which("ffprobe")
    return [found] if found else None

async def _read_capped(stream, limit: int) -> "bytes | None":
    """Everything on `stream`, or None once it is more than `limit` bytes."""
    data = b""
    while True:
        chunk = await stream.read(limit + 1 - len(data))
        if not chunk:
            return data
        data += chunk
        if len(data) > limit:
            return None

async def probe(path: str, run: "ProbeRun | None" = None) -> "VideoShape | None":
    """The width, height and duration of the video at `path`, or None."""
    argv = _ffprobe_argv()
    if argv is None:
        return None
    if run is not None and run.exhausted:
        return None
    limit = PROBE_SECONDS if run is None else run.allowance()
    started = time.monotonic()
    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            *argv, "-v", "error", "-protocol_whitelist", "file", "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,sample_aspect_ratio:stream_tags=rotate:stream_side_data=rotation:format=duration",
            "-of", "json", "file:" + str(path),
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        async def answer():
            said = await _read_capped(process.stdout, PROBE_MAX_BYTES)
            if said is not None:
                await process.wait()
            return said

        output = await asyncio.wait_for(answer(), limit)
        if output is None:
            logger.debug("ffprobe said more than %d bytes; ignored", PROBE_MAX_BYTES)
            return None
        if process.returncode != 0:
            return None
        return shape_from_ffprobe(json.loads(output))
    except asyncio.TimeoutError:
        if run is not None:
            run.timed_out = True
        logger.debug("ffprobe took more than %s s", limit)
        return None
    except Exception as exc:
        logger.debug("ffprobe failed: %s", type(exc).__name__)
        return None
    finally:
        if process is not None and process.returncode is None:

            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                await process.wait()
            except Exception:
                pass
        if run is not None:
            run.spent += time.monotonic() - started

# ─── module: downloader_bot.resolvers ────────────────────────────────────────
"""Turning a pasted link into files, through whichever route is still working."""
from __future__ import annotations

import asyncio
import contextvars
import base64
import json
import logging
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urljoin, urlparse, urlsplit

import httpx

import net
from net import CRAWLER_UA, FetchError

logger = logging.getLogger(__name__)

PROVIDER_TIMEOUT_S = float(os.environ.get("DBOT_PROVIDER_TIMEOUT", "20"))

YTDLP_TIMEOUT_S = float(os.environ.get("DBOT_YTDLP_TIMEOUT", "120"))
YTDLP_SECONDS_PER_MB = float(os.environ.get("DBOT_YTDLP_SECONDS_PER_MB", "0.5"))

COOLDOWN_AFTER_FAILURES = int(os.environ.get("DBOT_PROVIDER_COOLDOWN_AFTER", "3"))
COOLDOWN_BASE_S = float(os.environ.get("DBOT_PROVIDER_COOLDOWN_BASE", "120"))
COOLDOWN_MAX_S = float(os.environ.get("DBOT_PROVIDER_COOLDOWN_MAX", "3600"))

@dataclass
class MediaItem:
    """One file."""
    kind: str
    url: str | None = None

    alt_urls: list[str] = field(default_factory=list)
    path: str | None = None
    filename: str = "download"
    headers: dict = field(default_factory=dict)

@dataclass
class Resolved:
    platform: str
    provider: str
    items: list[MediaItem]
    title: str | None = None
    author: str | None = None

    @property
    def has_video(self) -> bool:
        return any(i.kind == "video" for i in self.items)

class ProviderFailed(Exception):
    """This provider could not do it. Try the next one."""

    def __init__(self, message: str, kind: str = "error", skip=()):
        super().__init__(message)
        self.kind = kind

        self.skip = tuple(skip)

class NothingWorked(Exception):
    """Every provider for this platform failed."""

    def __init__(self, platform: str, failures: dict[str, ProviderFailed]):
        self.platform = platform
        self.failures = failures
        super().__init__(
            f"{platform}: " + "; ".join(f"{n}: {e}" for n, e in failures.items())
        )

    @property
    def kind(self) -> str:
        """The most specific verdict any provider reached."""
        kinds = {e.kind for e in self.failures.values()}
        for preferred in ("missing", "too_big", "blocked"):
            if preferred in kinds:
                return preferred
        return "error"

@dataclass
class Health:
    ok: int = 0
    failed: int = 0
    streak: int = 0
    last_ok: float | None = None
    last_fail: float | None = None
    last_error: str | None = None

    @property
    def cooling_until(self) -> float:
        """When this provider becomes a first-class citizen again."""
        if self.streak < COOLDOWN_AFTER_FAILURES or self.last_fail is None:
            return 0.0
        over = self.streak - COOLDOWN_AFTER_FAILURES
        return self.last_fail + min(COOLDOWN_BASE_S * (2 ** over), COOLDOWN_MAX_S)

_health: dict[str, Health] = {}
_health_dirty: set[str] = set()

def health(name: str) -> Health:
    return _health.setdefault(name, Health())

def _record_ok(name: str) -> None:
    h = health(name)
    h.ok += 1
    h.streak = 0
    h.last_ok = time.time()
    h.last_error = None
    _health_dirty.add(name)

def _record_fail(name: str, error: str) -> None:
    h = health(name)
    h.failed += 1
    h.streak += 1
    h.last_fail = time.time()
    h.last_error = error[:300]
    _health_dirty.add(name)

def take_dirty() -> dict[str, Health]:
    """The rows that changed since the last flush, and clears the flag."""
    dirty = {name: _health[name] for name in _health_dirty if name in _health}
    _health_dirty.clear()
    return dirty

def load(rows) -> None:
    """Seed from the database at startup, so a redeploy does not go back to hammering a provider that has been dead for a week."""
    for row in rows:
        name = row["provider"]
        _health[name] = Health(
            ok=row.get("ok_count") or 0,
            failed=row.get("fail_count") or 0,
            streak=row.get("consecutive_fails") or 0,
            last_ok=row.get("last_ok_at"),
            last_fail=row.get("last_fail_at"),
            last_error=row.get("last_error"),
        )

_META_OPEN_RE = re.compile("<meta", re.IGNORECASE)

_META_TAG_MAX = 4096

def _meta_tags(html: str):
    """Every `<meta ...>` tag of `html`, found in one pass."""
    pos = 0
    while True:
        opening = _META_OPEN_RE.search(html, pos)
        if opening is None:
            return
        start = opening.start()
        close = html.find(">", start)
        if close < 0:
            return
        pos = close + 1
        if close - start > 5 and close - start < _META_TAG_MAX:
            yield html[start:close + 1]

def _meta(html: str, prop: str) -> str | None:
    """Read one OpenGraph/Twitter-card meta tag's content."""
    wanted = re.compile(rf'(?:property|name)=["\']{re.escape(prop)}["\']', re.I)
    for tag in _meta_tags(html):
        if wanted.search(tag):
            m = re.search(r'content=["\']([^"\']+)["\']', tag, re.I)
            if m:
                return m.group(1).replace("&amp;", "&")
    return None

PAGE_LIMIT_BYTES = int(float(os.environ.get("DBOT_PAGE_LIMIT_MB", "8")) * 1024 * 1024)

async def _page(method: str, url: str, **kwargs) -> httpx.Response:
    """One small document, read under PAGE_LIMIT_BYTES (net.read_page), with this module's way of failing: a ProviderFailed, kind "error", that the chain moves past."""
    netloc = urlparse(url).netloc

    def declared_too_big(declared: int):
        return ProviderFailed(f"{netloc} answered with {declared:,} bytes, "
                              "more than a page may be", "error")

    def too_big():
        return ProviderFailed(f"{netloc} kept sending past {PAGE_LIMIT_BYTES:,} bytes", "error")

    try:
        return await net.read_page(method, url, limit=PAGE_LIMIT_BYTES, too_big=too_big,
                                   declared_too_big=declared_too_big, **kwargs)
    except net.Trickle:
        raise ProviderFailed(f"{netloc} sent its answer in pieces too small to read", "error") from None
    except net.BadEncoding:
        raise ProviderFailed(f"{netloc} answered in an encoding this bot does not read", "error") from None

async def _get(url: str, *, crawler: bool = False, **kwargs) -> httpx.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    if crawler:
        headers.setdefault("User-Agent", CRAWLER_UA)
    return await _page("GET", url, headers=headers, **kwargs)

async def _post(url: str, **kwargs) -> httpx.Response:
    """The same for a POST (cobalt)."""
    return await _page("POST", url, **kwargs)

def _ext_of(name: str, default: str) -> str:
    """The extension to give a downloaded file, or `default`."""
    _, dot, ext = name.rpartition(".")

    if not dot:
        return default
    ext = ext.lower()
    return ext if ext and len(ext) <= 5 and ext.isalnum() and ext.isascii() else default

def _kind_of(name: str) -> str:
    ext = _ext_of(name, "")
    if ext in ("mp4", "mov", "webm", "mkv", "m4v"):
        return "video"
    if ext in ("mp3", "m4a", "ogg", "opus", "wav"):
        return "audio"
    return "photo"

INSTAGRAM_CODE_RE = re.compile(
    r"instagram\.com/(?:[^/]+/)?(?:reels?|p|tv)/([A-Za-z0-9_-]+)", re.IGNORECASE
)

def instagram_code(url: str) -> str | None:
    m = INSTAGRAM_CODE_RE.search(url)
    return m.group(1) if m else None

def _jwt_payload(token: str) -> dict:
    """downloadgram wraps every media URL in an unsigned-to-us JWT whose payload carries the filename and the real source URL."""
    part = token.split(".")[1]
    part += "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part))

async def _ig_downloadgram(url: str) -> Resolved:
    """downloadgram.org's public endpoint."""
    resp = await _get("https://api.downloadgram.org/media", params={"url": url})
    if resp.status_code == 400:
        raise ProviderFailed("downloadgram rejected the link", "missing")
    resp.raise_for_status()
    body = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), resp.text)

    tokens: list[str] = []
    for tok in re.findall(r"https://cdn\.downloadgram\.org/\?token=([A-Za-z0-9_.-]+)", body):
        if tok not in tokens:
            tokens.append(tok)
    if not tokens:
        raise ProviderFailed("downloadgram returned no media", "missing")

    chosen: dict[str, tuple[str, str, bool]] = {}
    for tok in tokens:
        try:
            payload = _jwt_payload(tok)
        except Exception:
            payload = {}
        name = str(payload.get("filename") or "")
        media = str(payload.get("url") or "").split("?", 1)[0] or name or tok
        forced = bool(payload.get("force"))
        if media not in chosen or (forced and not chosen[media][2]):
            chosen[media] = (tok, name, forced)

    items: list[MediaItem] = []
    for tok, name, _forced in chosen.values():
        items.append(MediaItem(
            kind=_kind_of(name),
            url="https://cdn.downloadgram.org/?token=" + tok,
            filename=name or f"instagram.{_ext_of(name, 'mp4')}",
        ))

    if any(i.kind == "video" for i in items):
        items = [i for i in items if i.kind == "video"]
    return Resolved("instagram", "downloadgram", items)

async def _ig_instafix(url: str) -> Resolved:
    """An InstaFix instance (`eeinstagram.com`)."""
    code = instagram_code(url)
    if not code:
        raise ProviderFailed("not an Instagram post URL", "missing")
    host = os.environ.get("DBOT_INSTAFIX_HOST", "https://eeinstagram.com")
    resp = await _get(f"{host}/p/{code}/", crawler=True)
    resp.raise_for_status()
    html = resp.text

    video = _meta(html, "og:video") or _meta(html, "twitter:player:stream")
    image = _meta(html, "og:image")
    target = video or image
    if not target:
        raise ProviderFailed("InstaFix had no media for that post", "missing")
    target = urljoin(host, target)

    async with net.client().stream("GET", target, headers={"Range": "bytes=0-0"}) as probe:
        ctype = probe.headers.get("content-type", "")
    if video and not ctype.startswith("video/"):
        raise ProviderFailed(
            f"InstaFix promised a video and served {ctype or 'nothing'}", "blocked"
        )
    kind = "video" if ctype.startswith("video/") else "photo"
    ext = "mp4" if kind == "video" else "jpg"
    return Resolved("instagram", "instafix",
                    [MediaItem(kind, url=target, filename=f"instagram_{code}.{ext}")])

async def _tt_tikwm(url: str) -> Resolved:
    """tikwm.com's open API."""
    resp = await _get("https://tikwm.com/api/", params={"url": url, "hd": 1})
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise ProviderFailed(payload.get("msg") or "tikwm said no", "missing")
    data = payload.get("data") or {}
    vid = str(data.get("id") or "")

    images = data.get("images") or []
    if images:
        items = [MediaItem("photo", url=u, filename=f"tiktok_{vid}_{n}.jpg")
                 for n, u in enumerate(images[:20], start=1)]
    else:
        play = data.get("hdplay") or data.get("play") or data.get("wmplay")
        if not play:
            raise ProviderFailed("tikwm returned no playable media", "missing")
        which = "hdplay" if data.get("hdplay") else "play"
        alts = [f"https://tikwm.com/video/media/{which}/{vid}.mp4"] if vid else []
        items = [MediaItem("video", url=play, alt_urls=alts,
                           filename=f"tiktok_{vid or 'video'}.mp4")]
    author = (data.get("author") or {}).get("unique_id")
    return Resolved("tiktok", "tikwm", items, title=data.get("title"),
                    author=f"@{author}" if author else None)

async def _tt_tnktok(url: str) -> Resolved:
    """tnktok.com, the TikTok embed-fixer."""
    resp = await _get(re.sub(r"https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com",
                             "https://tnktok.com", url, flags=re.I), crawler=True)
    resp.raise_for_status()
    video = _meta(resp.text, "og:video") or _meta(resp.text, "twitter:player:stream")
    if not video:

        raise ProviderFailed("tnktok exposed no video for that link", "missing")
    return Resolved("tiktok", "tnktok",
                    [MediaItem("video", url=video, filename="tiktok.mp4")])

TWEET_ID_RE = re.compile(r"/status(?:es)?/(\d+)")

def tweet_id(url: str) -> str | None:
    m = TWEET_ID_RE.search(url)
    return m.group(1) if m else None

async def _tw_api(url: str, host: str, provider: str) -> Resolved:
    """fxtwitter and vxtwitter share a response shape close enough to read with one function."""
    tid = tweet_id(url)
    if not tid:
        raise ProviderFailed("not a tweet URL", "missing")
    resp = await _get(f"{host}/i/status/{tid}")
    if resp.status_code == 403:
        raise ProviderFailed(f"{provider} is behind a challenge", "blocked")
    if resp.status_code == 404:
        raise ProviderFailed("that post is gone or protected", "missing")
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError as exc:
        raise ProviderFailed(f"{provider} did not return JSON", "blocked") from exc

    tweet = data.get("tweet") if isinstance(data.get("tweet"), dict) else data
    items: list[MediaItem] = []
    media = (tweet.get("media") or {}).get("all") or tweet.get("media_extended") or []
    for n, m in enumerate(media, start=1):
        mtype = (m.get("type") or "").lower()
        murl = m.get("url")
        if not murl:
            continue
        if mtype in ("video", "gif", "animated_gif"):
            items.append(MediaItem("video", url=murl, filename=f"tweet_{tid}_{n}.mp4"))
        else:
            items.append(MediaItem("photo", url=murl, filename=f"tweet_{tid}_{n}.jpg"))
    if not items:
        for murl in tweet.get("mediaURLs") or []:
            items.append(MediaItem(_kind_of(urlparse(murl).path), url=murl,
                                   filename=f"tweet_{tid}.{_ext_of(urlparse(murl).path, 'jpg')}"))
    if not items:
        raise ProviderFailed("that post has no media", "missing")

    author = tweet.get("author") or {}
    handle = author.get("screen_name") or tweet.get("user_screen_name")
    return Resolved("twitter", provider, items, title=tweet.get("text"),
                    author=f"@{handle}" if handle else None)

async def _tw_fxtwitter(url: str) -> Resolved:
    return await _tw_api(url, "https://api.fxtwitter.com", "fxtwitter")

async def _tw_vxtwitter(url: str) -> Resolved:
    return await _tw_api(url, "https://api.vxtwitter.com", "vxtwitter")

_PIN_RESOURCE = "https://www.pinterest.com/resource/PinResource/get/"
_PIN_ID_RE = re.compile(r"/pin/(?:[^/]*?--)?(\d+)")

def _pin_best_video(video_list: dict | None) -> str | None:
    """The biggest .mp4 in one of Pinterest's video_list objects."""
    best, best_pixels = None, -1
    for entry in (video_list or {}).values():
        candidate = (entry or {}).get("url") or ""
        if not candidate.endswith(".mp4"):
            continue
        pixels = (entry.get("width") or 0) * (entry.get("height") or 0)
        if pixels > best_pixels:
            best, best_pixels = candidate, pixels
    return best

async def _pin_api(url: str) -> Resolved:
    """Ask Pinterest what the pin actually is."""

    resolved_url = str(url)
    if "/pin/" not in resolved_url or not _PIN_ID_RE.search(resolved_url):
        try:
            resolved_url = str((await _get(url)).url)
        except Exception as exc:
            raise ProviderFailed(f"couldn't follow that link: {exc}") from exc
    found = _PIN_ID_RE.search(resolved_url)
    if not found:
        raise ProviderFailed("that link has no pin id in it", "missing")
    pin_id = found.group(1)

    payload = json.dumps({"options": {"id": pin_id,
                                      "field_set_key": "unauth_react_main_pin"},
                          "context": {}})
    try:
        resp = await _get(_PIN_RESOURCE, params={"data": payload},
                          headers={"X-Pinterest-PWS-Handler": "www/[username].js"})
        resp.raise_for_status()
        data = resp.json()["resource_response"]["data"]
    except Exception as exc:
        raise ProviderFailed(f"pinterest would not describe that pin: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderFailed("pinterest returned no pin", "missing")

    items: list[MediaItem] = []

    top_list = (data.get("videos") or {}).get("video_list")
    saw_video = bool(top_list)
    video = _pin_best_video(top_list)
    if video:
        items.append(MediaItem("video", url=video, filename="pinterest.mp4"))

    for page in ((data.get("story_pin_data") or {}).get("pages") or []):
        for block in (page.get("blocks") or []):
            block_list = (block.get("video") or {}).get("video_list")
            saw_video = saw_video or bool(block_list)
            block_video = _pin_best_video(block_list)
            if block_video:
                items.append(MediaItem("video", url=block_video,
                                       filename=f"pinterest_{len(items) + 1}.mp4"))

    if not items and saw_video:

        raise ProviderFailed(
            "that pin is a video Pinterest serves only as a stream, which this route cannot fetch",
            "error", skip=("pinterest_og",))

    if not items:

        original = ((data.get("images") or {}).get("orig") or {}).get("url")
        if not original:
            raise ProviderFailed("that pin has no video or image", "missing")
        items.append(MediaItem("photo", url=original,
                               filename=f"pinterest.{_ext_of(urlparse(original).path, 'jpg')}"))
    return Resolved("pinterest", "api", items)

async def _pin_og(url: str) -> Resolved:
    """The pin page's own OpenGraph tags -- the fallback for when the endpoint above changes shape."""
    resp = await _get(url)
    resp.raise_for_status()
    video = _meta(resp.text, "og:video") or _meta(resp.text, "og:video:secure_url")
    if video:
        return Resolved("pinterest", "og", [MediaItem("video", url=video,
                                                      filename="pinterest.mp4")])
    image = _meta(resp.text, "og:image")
    if not image:
        raise ProviderFailed("that pin has no image or video tag", "missing")

    original = re.sub(r"/(?:\d{2,4}x\d{0,4}|originals)/", "/originals/", image, count=1)
    routes = [original, image] if original != image else [image]
    return Resolved("pinterest", "og",
                    [MediaItem("photo", url=routes[0], alt_urls=routes[1:],
                               filename=f"pinterest.{_ext_of(urlparse(image).path, 'jpg')}")])

COBALT_INSTANCES = [
    host.strip().rstrip("/") for host in os.environ.get(
        "DBOT_COBALT_INSTANCES",
        "https://api.cobalt.liubquanti.click,https://cobaltapi.cjs.nz,https://dwnld.nichind.dev",
    ).split(",") if host.strip()
]
COBALT_API_KEY = os.environ.get("DBOT_COBALT_API_KEY") or None

COBALT_QUALITY = os.environ.get("DBOT_COBALT_QUALITY", "720")

COBALT_INSTANCE_TIMEOUT_S = float(os.environ.get("DBOT_COBALT_INSTANCE_TIMEOUT", "15"))

COBALT_TIMEOUT_S = float(os.environ.get("DBOT_COBALT_TIMEOUT", "240"))

COBALT_STEP_DOWN = (480, 360)

COBALT_AUDIO = "audio"

AUDIO = "audio"  # what was picked, when it was just the sound: the same value as video.AUDIO

_COBALT_MISSING = ("content.video.unavailable", "content.post.unavailable",
                   "content.video.private", "content.post.private",
                   "content.video.age", "content.post.age", "link.invalid",
                   "link.unsupported", "content.video.live")
_COBALT_TOO_BIG = ("content.too_long", "content.too_large")
_COBALT_BLOCKED = (".login", "auth.", "fetch.rate", "rate_exceeded", "too_many_requests",
                   "content.video.region", "youtube.decipher", "youtube.token",
                   "no_valid_content", "fetch.critical")

_cobalt_last_good: str | None = None

def _cobalt_verdict(code: str) -> str:
    code = code.lower()
    if any(part in code for part in _COBALT_MISSING):
        return "missing"
    if any(part in code for part in _COBALT_TOO_BIG):
        return "too_big"
    if any(part in code for part in _COBALT_BLOCKED):
        return "blocked"
    return "error"

def _cobalt_items(data: dict, platform: str) -> list[MediaItem]:
    status = data.get("status")
    if status in ("tunnel", "redirect", "stream"):
        name = str(data.get("filename") or "")
        kind = _kind_of(name) if name else "video"
        return [MediaItem(kind, url=data["url"],
                          filename=f"{platform}.{_ext_of(name, 'mp4' if kind == 'video' else 'jpg')}")]
    if status == "picker":
        items = []
        for entry in data.get("picker") or []:
            url = entry.get("url")
            if not url:
                continue

            kind = "photo" if entry.get("type") == "photo" else "video"
            items.append(MediaItem(kind, url=url,
                                   filename=f"{platform}.{'jpg' if kind == 'photo' else 'mp4'}"))
        return items
    if status == "local-processing":

        tunnels = data.get("tunnel") or []
        if len(tunnels) == 1:
            return [MediaItem("video", url=tunnels[0], filename=f"{platform}.mp4")]
    return []

async def _cobalt_one(host: str, url: str, platform: str, key: str | None,
                      quality: "str | None" = None) -> Resolved:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Api-Key {key}"
    if quality == COBALT_AUDIO:
        body = {"url": url, "downloadMode": "audio", "audioFormat": "mp3", "filenameStyle": "basic"}
    else:
        body = {"url": url, "videoQuality": quality or COBALT_QUALITY, "filenameStyle": "basic"}
    resp = await _post(host + "/", json=body, headers=headers, timeout=COBALT_INSTANCE_TIMEOUT_S)
    try:
        data = resp.json()
    except ValueError:
        raise ProviderFailed(f"{urlparse(host).netloc} answered HTTP {resp.status_code}, not JSON",
                             "blocked" if resp.status_code in (401, 403, 429) else "error")
    if not isinstance(data, dict):
        raise ProviderFailed(f"{urlparse(host).netloc} answered something that is not an object", "error")
    if data.get("status") == "error":
        code = str((data.get("error") or {}).get("code") or "unknown")
        raise ProviderFailed(f"{urlparse(host).netloc}: {code}", _cobalt_verdict(code))
    items = _cobalt_items(data, platform)
    if not items:
        raise ProviderFailed(f"{urlparse(host).netloc}: nothing usable ({data.get('status')})", "error")
    if quality == COBALT_AUDIO:
        items = [i for i in items if i.kind == "audio"]
        if not items:
            raise ProviderFailed(f"{urlparse(host).netloc}: no sound in its answer", "error")
    elif any(i.kind == "video" for i in items) and platform == "youtube":
        items = [i for i in items if i.kind == "video"]
    return Resolved(platform, "cobalt", items)

MIN_MEDIA_BYTES = 1024

def _unlink(path: "str | None") -> None:
    if path:
        try:
            os.remove(path)
        except OSError:
            pass

def _looks_like_video(path: str) -> bool:
    """Does the file start the way an MP4 (the "ftyp" box) or a WebM/Matroska file does."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(12)
    except OSError:
        return False
    return head[4:8] == b"ftyp" or head[:4] == b"\x1a\x45\xdf\xa3"

def _limit_bytes() -> int:
    """The size ceiling of the download being resolved (see _LIMIT_MB)."""
    asked = _LIMIT_MB.get()
    return asked * 1024 * 1024 if asked else net.MAX_RESPONSE_BYTES

async def _take(url: str, ext: str, limit: int) -> str:
    """`url` into a new file in the work folder; its path."""
    os.makedirs(_WORK_DIR, exist_ok=True)
    path = os.path.join(_WORK_DIR, f"{uuid.uuid4().hex}.{ext}")
    parsed = urlparse(url)
    try:
        await net.stream_to_file(url, path, limit=limit,
                                 headers={"Referer": f"{parsed.scheme}://{parsed.netloc}/"})
    except BaseException:
        _unlink(path)
        raise
    return path

def _instances_verdict(failures: "list[ProviderFailed]") -> str:
    """What a route says when every one of its instances failed."""
    kinds = {f.kind for f in failures}
    return "blocked" if "blocked" in kinds else "missing" if kinds == {"missing"} else "error"

async def _cobalt_take(resolved: Resolved, netloc: str) -> None:
    """Fetch every item of a cobalt answer to disk and check it; the items then carry paths."""
    taken: list[str] = []
    try:
        for item in resolved.items:
            ext = _ext_of(item.filename, {"video": "mp4", "audio": "mp3"}.get(item.kind, "jpg"))
            taken.append(await _take(item.url, ext, _limit_bytes()))
            size = os.path.getsize(taken[-1])
            if size < MIN_MEDIA_BYTES or (item.kind == "video" and not _looks_like_video(taken[-1])):
                raise ProviderFailed(f"{netloc}: its tunnel sent {size:,} bytes that are not a {item.kind}",
                                     "blocked")
    except BaseException:
        for path in taken:
            _unlink(path)
        raise
    for item, path in zip(resolved.items, taken):
        item.path = path

def _cobalt_qualities() -> "list[str]":
    """The qualities to ask one instance for, in turn: COBALT_QUALITY, then the lower ones of COBALT_STEP_DOWN; just the one picked, when something was (no stepping down from a pick)."""
    choice = _CHOICE.get()
    if choice is not None:
        return [COBALT_AUDIO if choice == AUDIO else str(choice)]
    first = COBALT_QUALITY
    top = int(first) if first.isdigit() else 2160
    return [first] + [str(height) for height in COBALT_STEP_DOWN if height < top]

async def _cobalt_fetch(host: str, url: str, platform: str, key: "str | None") -> Resolved:
    """One instance, as far as files on disk (as far as its answer, for lookup())."""
    netloc = urlparse(host).netloc
    qualities = _cobalt_qualities()
    for number, quality in enumerate(qualities, start=1):
        try:

            resolved = await asyncio.wait_for(_cobalt_one(host, url, platform, key, quality),
                                              timeout=COBALT_INSTANCE_TIMEOUT_S)
        except asyncio.TimeoutError:
            raise ProviderFailed(f"{netloc}: no answer in {COBALT_INSTANCE_TIMEOUT_S:.0f}s", "error") from None
        if _LOOKUP.get():
            return resolved
        try:
            await _cobalt_take(resolved, netloc)
        except net.TooLarge:
            if number < len(qualities):
                logger.info("cobalt %s: over the size limit at %s, asking for %s",
                            netloc, quality, qualities[number])
                continue
            raise ProviderFailed(f"{netloc}: over the size limit at {quality}", "too_big") from None
        return resolved
    raise ProviderFailed(f"{netloc}: nothing asked for", "error")

def _cobalt_provider(platform: str):
    async def provider(url: str) -> Resolved:
        global _cobalt_last_good
        if not COBALT_INSTANCES:
            raise ProviderFailed("no cobalt instances configured", "error")
        hosts = list(COBALT_INSTANCES)
        if _cobalt_last_good in hosts:
            hosts.remove(_cobalt_last_good)
            hosts.insert(0, _cobalt_last_good)

        budget = _timeout_for("cobalt:") * INSTANCE_SHARE
        failures: list[ProviderFailed] = []
        for host in hosts:
            key = COBALT_API_KEY if host == COBALT_INSTANCES[0] else None
            netloc = urlparse(host).netloc
            try:
                resolved = await asyncio.wait_for(_cobalt_fetch(host, url, platform, key), timeout=budget)
            except ProviderFailed as exc:
                failures.append(exc)
                if exc.kind == "too_big":

                    raise
                continue
            except asyncio.TimeoutError:
                failures.append(ProviderFailed(f"{netloc}: its file was not here in {budget:.0f}s", "error"))
                continue
            except (httpx.HTTPError, FetchError, OSError, KeyError, TypeError) as exc:
                failures.append(ProviderFailed(f"{netloc}: {type(exc).__name__}: {exc}", "error"))
                continue
            _cobalt_last_good = host
            return resolved
        raise ProviderFailed("; ".join(str(f) for f in failures), _instances_verdict(failures))
    return provider

INVIDIOUS_INSTANCES = [
    host.strip().rstrip("/") for host in os.environ.get(
        "DBOT_INVIDIOUS_INSTANCES", "https://yt.chocolatemoo53.com").split(",") if host.strip()
]

INVIDIOUS_DIRECTORY = os.environ.get("DBOT_INVIDIOUS_DIRECTORY", "https://api.invidious.io/instances.json").strip()
INVIDIOUS_DIRECTORY_MAX = 6
INVIDIOUS_DIRECTORY_EVERY_S = 6 * 3600.0
INVIDIOUS_DIRECTORY_RETRY_S = 900.0
INVIDIOUS_INSTANCE_TIMEOUT_S = float(os.environ.get("DBOT_INVIDIOUS_INSTANCE_TIMEOUT", "15"))
INVIDIOUS_TIMEOUT_S = float(os.environ.get("DBOT_INVIDIOUS_TIMEOUT", "240"))

INSTANCE_SHARE = 0.75

INVIDIOUS_SIZE_MARGIN = 0.96
MUX_TIMEOUT_S = 120.0

_invidious_listed: list[str] = []
_invidious_listed_next = 0.0
_invidious_last_good: str | None = None

_YT_ID_RE = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")

_INVIDIOUS_BLOCKED = ("sign in", "not a bot", "login", "rate limit", "too many", "captcha", "blocked")
_INVIDIOUS_MISSING = ("unavailable", "private", "removed", "not available", "does not exist",
                      "terminated", "not found")

def _invidious_verdict(text: str) -> str:
    text = text.lower()
    if any(part in text for part in _INVIDIOUS_BLOCKED):
        return "blocked"
    if any(part in text for part in _INVIDIOUS_MISSING):
        return "missing"
    return "error"

def _invidious_from_directory(data) -> "list[str]":
    """The instances of the directory's answer that are reached over https and say their API is open, in the directory's order (it sorts by health), at most INVIDIOUS_DIRECTORY_MAX."""
    hosts: list[str] = []
    for entry in data if isinstance(data, list) else ():
        meta = entry[1] if isinstance(entry, (list, tuple)) and len(entry) == 2 else None
        if not isinstance(meta, dict) or meta.get("type") != "https" or meta.get("api") is not True:
            continue
        uri = str(meta.get("uri") or "").rstrip("/")
        if re.fullmatch(r"https://[A-Za-z0-9.-]+(?::\d+)?", uri) and uri not in hosts:
            hosts.append(uri)
    return hosts[:INVIDIOUS_DIRECTORY_MAX]

async def _invidious_hosts() -> "list[str]":
    """The instances to ask, in order: the one that answered last, the configured ones, then the directory's."""
    global _invidious_listed, _invidious_listed_next
    now = time.monotonic()
    if INVIDIOUS_DIRECTORY not in ("", "0") and now >= _invidious_listed_next:
        _invidious_listed_next = now + INVIDIOUS_DIRECTORY_RETRY_S
        try:
            resp = await asyncio.wait_for(_get(INVIDIOUS_DIRECTORY, timeout=10.0), timeout=10.0)
            resp.raise_for_status()
            _invidious_listed = _invidious_from_directory(resp.json())
            _invidious_listed_next = now + INVIDIOUS_DIRECTORY_EVERY_S
        except Exception as exc:
            logger.info("the Invidious directory was not read (%s: %s)", type(exc).__name__, exc)
    hosts = list(INVIDIOUS_INSTANCES) + [h for h in _invidious_listed if h not in INVIDIOUS_INSTANCES]
    if _invidious_last_good in hosts:
        hosts.remove(_invidious_last_good)
        hosts.insert(0, _invidious_last_good)
    return hosts

def _number(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0

def _invidious_height(fmt: dict) -> int:
    """A version's picture height: from its size ("720x1280" is 1280 high, the way yt-dlp counts it and MAX_HEIGHT caps it), else from its label ("720p")."""
    size = re.fullmatch(r"(\d+)x(\d+)", str(fmt.get("size") or ""))
    if size:
        return int(size.group(2))
    label = re.match(r"(\d+)p", str(fmt.get("resolution") or fmt.get("qualityLabel") or ""))
    return int(label.group(1)) if label else 0

def _invidious_quality(fmt: dict) -> int:
    """A version's quality as people name it (video.quality_of): its label ("480p"), else the shorter side ("720x1280" is 720p)."""
    label = re.match(r"(\d{3,4})p", str(fmt.get("qualityLabel") or fmt.get("resolution") or ""))
    if label:
        return int(label.group(1))
    size = re.fullmatch(r"(\d+)x(\d+)", str(fmt.get("size") or ""))
    if size:
        return min(int(size.group(1)), int(size.group(2)))
    return _invidious_height(fmt)

def _invidious_track(fmt: dict) -> int:
    """How much a sound track is the video's own: 2 the original, 1 the only one (nothing said), 0 a dubbed or described one."""
    tags = (parse_qs(urlsplit(str(fmt.get("url") or "")).query).get("xtags") or [""])[0]
    if "acont=" not in tags:
        return 1
    return 2 if "acont=original" in tags else 0

def _invidious_pick(formats, budget_bytes: int, height: "int | None" = None, exact: bool = False,
                    max_height: int = 1080, quality: "int | None" = None) -> "tuple[dict, dict]":
    """(picture, sound) for the best version that fits `budget_bytes`: H.264 with AAC, which every Telegram app plays and which go into one MP4 as they are; the tallest picture up to `max_height` (or `height`; with `exact`, that height and no other)."""
    formats = [fmt for fmt in formats or () if isinstance(fmt, dict) and fmt.get("url")]
    sounds = [fmt for fmt in formats
              if str(fmt.get("type") or "").startswith("audio/mp4") and _number(fmt.get("clen"))]
    if not sounds:
        raise ProviderFailed("no AAC sound is listed", "error")
    sound = max(sounds, key=lambda fmt: (_invidious_track(fmt), min(_number(fmt.get("bitrate")), 192_000)))
    cap = max_height if height is None else min(height, max_height)
    pictures = [fmt for fmt in formats
                if str(fmt.get("type") or "").startswith("video/mp4") and "avc1" in str(fmt.get("type"))
                and _number(fmt.get("clen")) and _invidious_height(fmt)
                and (_invidious_quality(fmt) == quality if quality is not None
                     else _invidious_height(fmt) == height if exact and height is not None
                     else _invidious_height(fmt) <= cap)]
    if not pictures:
        raise ProviderFailed("no H.264 picture of that height is listed", "error")
    room = budget_bytes * INVIDIOUS_SIZE_MARGIN - _number(sound.get("clen"))
    fitting = [fmt for fmt in pictures if _number(fmt.get("clen")) <= room]
    if not fitting:
        raise ProviderFailed("even the smallest version listed is over the size limit", "too_big")
    picture = max(fitting, key=lambda fmt: (_invidious_height(fmt), _number(fmt.get("fps")),
                                            _number(fmt.get("bitrate"))))
    return picture, sound

def _invidious_local(host: str, media_url: str) -> str:
    """The address of a file on the instance itself."""
    parts = urlsplit(media_url)
    if parts.path != "/videoplayback" or not parts.query:
        raise ProviderFailed(f"{urlparse(host).netloc}: a file address that is not a videoplayback one", "error")
    query = parts.query
    theirs = (parts.hostname or "").lower()
    if theirs.endswith(".googlevideo.com") and "host=" not in query:
        query += f"&host={theirs}"
    return f"{host}/videoplayback?{query}"

async def _mux(picture: str, sound: str, out: str) -> None:
    """One MP4 from a picture file and a sound file, nothing re-encoded, the index at the front (Telegram plays it while it loads)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ProviderFailed("ffmpeg is not installed", "error")
    argv = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    for path in (picture, sound):
        argv += ["-protocol_whitelist", "file", "-f", "mp4", "-i", path]
    argv += ["-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-movflags", "+faststart", "-f", "mp4", out]
    proc = await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE)
    try:
        _, said = await asyncio.wait_for(proc.communicate(), timeout=MUX_TIMEOUT_S)
    except asyncio.TimeoutError:
        raise ProviderFailed(f"ffmpeg had not joined the two files in {MUX_TIMEOUT_S:.0f}s", "error") from None
    finally:
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
    if proc.returncode != 0:
        raise ProviderFailed("ffmpeg could not join the picture and the sound: "
                             + (said or b"").decode("utf-8", "replace").strip()[-200:], "error")

async def _invidious_fetch(netloc: str, picture_url: str, sound_url: str,
                           picture_bytes: int, sound_bytes: int) -> str:
    """Both files, checked, joined; the path of the MP4. Nothing else is left on disk."""
    limit = _limit_bytes()
    parts: list = [None, None]
    out = None
    tasks = [asyncio.ensure_future(_take(picture_url, "mp4", limit)),
             asyncio.ensure_future(_take(sound_url, "m4a", limit))]
    try:
        try:
            parts = list(await asyncio.gather(*tasks))
        except BaseException:

            for task in tasks:
                task.cancel()
            for ended in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(ended, str):
                    _unlink(ended)
            raise
        for path, expected, what in ((parts[0], picture_bytes, "picture"), (parts[1], sound_bytes, "sound")):
            size = os.path.getsize(path)
            if size < MIN_MEDIA_BYTES or size < expected or not _looks_like_video(path):
                raise ProviderFailed(f"{netloc}: sent {size:,} of the {what}'s {expected:,} bytes", "blocked")
        out = os.path.join(_WORK_DIR, f"{uuid.uuid4().hex}.mp4")
        await _mux(parts[0], parts[1], out)
        if os.path.getsize(out) < MIN_MEDIA_BYTES or not _looks_like_video(out):
            raise ProviderFailed("ffmpeg wrote no video", "error")
        done, out = out, None
        return done
    finally:
        for path in (parts[0], parts[1], out):
            _unlink(path)

async def _invidious_one(host: str, video_id: str, platform: str) -> Resolved:
    import video
    netloc = urlparse(host).netloc
    try:
        resp = await asyncio.wait_for(
            _get(f"{host}/api/v1/videos/{video_id}", params={"local": "true"},
                 timeout=INVIDIOUS_INSTANCE_TIMEOUT_S),
            timeout=INVIDIOUS_INSTANCE_TIMEOUT_S)
    except asyncio.TimeoutError:
        raise ProviderFailed(f"{netloc}: no answer in {INVIDIOUS_INSTANCE_TIMEOUT_S:.0f}s", "error") from None
    try:
        data = resp.json()
    except ValueError:
        raise ProviderFailed(f"{netloc} answered HTTP {resp.status_code}, not JSON",
                             "blocked" if resp.status_code in (401, 403, 429) else "error") from None
    if not isinstance(data, dict):
        raise ProviderFailed(f"{netloc} answered something that is not an object", "error")
    if resp.status_code != 200 or data.get("error"):
        said = str(data.get("error") or f"HTTP {resp.status_code}")[:120]
        raise ProviderFailed(f"{netloc}: {said}", _invidious_verdict(said))
    if data.get("liveNow") or data.get("isUpcoming"):
        raise ProviderFailed(f"{netloc}: a live stream, not a video", "missing")
    seconds = _number(data.get("lengthSeconds"))
    if seconds > video.MAX_DURATION_S:
        raise ProviderFailed(f"that clip is {seconds // 60} minutes long, and this bot caps downloads "
                             f"at {video.MAX_DURATION_S // 60}", "too_big")
    choice = _CHOICE.get()
    if choice == AUDIO:
        return await _invidious_sound(host, data, platform)
    picture, sound = _invidious_pick(data.get("adaptiveFormats"), _limit_bytes(), max_height=video.MAX_HEIGHT,
                                     quality=choice)
    picture_url, sound_url = _invidious_local(host, picture["url"]), _invidious_local(host, sound["url"])
    if _LOOKUP.get():
        return Resolved(platform, "invidious", [MediaItem("video", url=picture_url, filename=f"{platform}.mp4")])
    logger.info("invidious %s: %ss, %sp picture, %s + %s bytes", netloc, seconds, _invidious_height(picture),
                picture.get("clen"), sound.get("clen"))
    path = await _invidious_fetch(netloc, picture_url, sound_url,
                                  _number(picture.get("clen")), _number(sound.get("clen")))
    return Resolved(platform, "invidious", [MediaItem("video", path=path, filename=f"{platform}.mp4")])

def _invidious_sound_format(formats) -> dict:
    """The sound to give somebody who picked just the sound: the video's own AAC track (see _invidious_pick)."""
    sounds = [fmt for fmt in formats or () if isinstance(fmt, dict) and fmt.get("url")
              and str(fmt.get("type") or "").startswith("audio/mp4") and _number(fmt.get("clen"))]
    if not sounds:
        raise ProviderFailed("no AAC sound is listed", "error")
    return max(sounds, key=lambda fmt: (_invidious_track(fmt), min(_number(fmt.get("bitrate")), 192_000)))

async def _invidious_sound(host: str, data: dict, platform: str) -> Resolved:
    netloc = urlparse(host).netloc
    sound = _invidious_sound_format(data.get("adaptiveFormats"))
    expected = _number(sound.get("clen"))
    if expected > _limit_bytes() * INVIDIOUS_SIZE_MARGIN:
        raise ProviderFailed("the sound alone is over the size limit", "too_big")
    sound_url = _invidious_local(host, sound["url"])
    if _LOOKUP.get():
        return Resolved(platform, "invidious", [MediaItem("audio", url=sound_url, filename=f"{platform}.m4a")])
    path = await _take(sound_url, "m4a", _limit_bytes())
    size = os.path.getsize(path)
    if size < MIN_MEDIA_BYTES or size < expected or not _looks_like_video(path):
        _unlink(path)
        raise ProviderFailed(f"{netloc}: sent {size:,} of the sound's {expected:,} bytes", "blocked")
    return Resolved(platform, "invidious", [MediaItem("audio", path=path, filename=f"{platform}.m4a")])

def _invidious_provider(platform: str):
    async def provider(url: str) -> Resolved:
        global _invidious_last_good
        found = _YT_ID_RE.search(url)
        if not found:
            raise ProviderFailed("no video id in that link", "missing")
        hosts = await _invidious_hosts()
        if not hosts:
            raise ProviderFailed("no Invidious instances configured", "error")
        budget = _timeout_for("invidious:") * INSTANCE_SHARE
        failures: list[ProviderFailed] = []
        for host in hosts:
            netloc = urlparse(host).netloc
            try:
                resolved = await asyncio.wait_for(_invidious_one(host, found.group(1), platform), timeout=budget)
            except ProviderFailed as exc:
                failures.append(exc)
                if exc.kind == "too_big":
                    raise
                continue
            except asyncio.TimeoutError:
                failures.append(ProviderFailed(f"{netloc}: its files were not here in {budget:.0f}s", "error"))
                continue
            except (httpx.HTTPError, FetchError, OSError, KeyError, TypeError, ValueError) as exc:
                failures.append(ProviderFailed(f"{netloc}: {type(exc).__name__}: {exc}", "error"))
                continue
            _invidious_last_good = host
            return resolved
        raise ProviderFailed("; ".join(str(f) for f in failures), _instances_verdict(failures))
    return provider

def _ytdlp_provider(platform: str):
    async def provider(url: str) -> Resolved:
        import video

        stop = threading.Event()
        try:
            path = await asyncio.to_thread(video.download_video, url, _WORK_DIR, _LIMIT_MB.get(), stop,
                                           _CHOICE.get())
        except asyncio.CancelledError:
            stop.set()
            raise
        except video.BlockedBySource as exc:
            raise ProviderFailed(str(exc), "blocked") from exc
        except video.TooLarge as exc:
            raise ProviderFailed(str(exc), "too_big") from exc
        except Exception as exc:
            raise ProviderFailed(str(exc), "error") from exc
        kind = "audio" if _CHOICE.get() == AUDIO else "video"
        return Resolved(platform, "ytdlp",
                        [MediaItem(kind, path=path,
                                   filename=os.path.basename(path))])
    return provider

_WORK_DIR = os.environ.get("DBOT_WORK_DIR") or tempfile.gettempdir()

PROVIDERS: dict[str, list[tuple[str, object]]] = {
    "instagram": [
        ("downloadgram", _ig_downloadgram),
        ("instafix", _ig_instafix),
        ("ytdlp:instagram", _ytdlp_provider("instagram")),
    ],
    "tiktok": [
        ("tikwm", _tt_tikwm),
        ("tnktok", _tt_tnktok),
        ("ytdlp:tiktok", _ytdlp_provider("tiktok")),
    ],
    "twitter": [
        ("vxtwitter", _tw_vxtwitter),
        ("fxtwitter", _tw_fxtwitter),
        ("ytdlp:twitter", _ytdlp_provider("twitter")),
    ],

    "pinterest": [
        ("pinterest_api", _pin_api),
        ("pinterest_og", _pin_og),
        ("ytdlp:pinterest", _ytdlp_provider("pinterest")),
    ],

    "reddit": [
        ("ytdlp:reddit", _ytdlp_provider("reddit")),
    ],

    "youtube": [
        ("ytdlp:youtube", _ytdlp_provider("youtube")),
        ("cobalt:youtube", _cobalt_provider("youtube")),
        ("invidious:youtube", _invidious_provider("youtube")),
    ],
}

def _ordered(platform: str) -> list[tuple[str, object]]:
    """Registry order, with the currently-unwell moved to the back."""
    now = time.time()
    ready, cooling = [], []
    for entry in PROVIDERS.get(platform, []):
        h = health(entry[0])
        (cooling if h.cooling_until > now else ready).append(entry)
    return ready + cooling

_LIMIT_MB: contextvars.ContextVar = contextvars.ContextVar("download_limit_mb", default=None)

_LOOKUP: contextvars.ContextVar = contextvars.ContextVar("lookup_only", default=False)

# What was picked in the quality picker (AUDIO or a quality), None for the default version. Only the
# routes of PICK_PLATFORMS read it; the others have one version to give.
_CHOICE: contextvars.ContextVar = contextvars.ContextVar("download_choice", default=None)

def _timeout_for(name: str) -> float:
    """How long the route called `name` gets before the chain moves on: PROVIDER_TIMEOUT_S, except for the routes that fetch the file while they resolve it."""
    if name.startswith("ytdlp:"):
        base = YTDLP_TIMEOUT_S
    elif _LOOKUP.get():
        return PROVIDER_TIMEOUT_S
    elif name.startswith("cobalt:"):
        base = COBALT_TIMEOUT_S
    elif name.startswith("invidious:"):
        base = INVIDIOUS_TIMEOUT_S
    else:
        return PROVIDER_TIMEOUT_S
    free_mb = net.MAX_RESPONSE_BYTES // (1024 * 1024)
    over_mb = max(0, (_LIMIT_MB.get() or free_mb) - free_mb)
    return max(PROVIDER_TIMEOUT_S, base + over_mb * YTDLP_SECONDS_PER_MB)

async def resolve(platform: str, url: str, max_mb: int | None = None, choice=None) -> Resolved:
    """Walk the chain until something produces media, with `max_mb` as the ceiling for anything downloaded on the way, and `choice` the version picked (None: the default one)."""
    token = _LIMIT_MB.set(max_mb)
    picked = _CHOICE.set(choice)
    try:
        return await _resolve(platform, url)
    finally:
        _CHOICE.reset(picked)
        _LIMIT_MB.reset(token)

# ---------------------------------------------------------------------------
# The quality picker's list
# ---------------------------------------------------------------------------
# For the sites below, a link pasted in a private chat first gets a card -- the picture, the title, a
# button per quality and one for the sound -- when one of the routes can say which versions there are and
# how big each is (yt-dlp's reading, or an Invidious instance's). When none can in PICK_LIST_TIMEOUT_S,
# the link is downloaded the default way, as before: the card is never the reason a download fails.
# A lister whose download route is resting after failures (Health.cooling_until) is not asked: from a
# server address yt-dlp is refused, and waiting on it for every link would only delay the download.
PICK_PLATFORMS = ("youtube",)
PICK_LIST_TIMEOUT_S = float(os.environ.get("DBOT_PICK_LIST_TIMEOUT", "10"))
PICK_INVIDIOUS_HOSTS = 2

@dataclass
class Choices:
    title: "str | None"
    duration: "int | None"
    thumbnail: "str | None"
    qualities: "list[tuple[int, int]]"
    audio: "int | None"

    @property
    def worth_asking(self) -> bool:
        """At least two things to choose between."""
        return len(self.qualities) + (1 if self.audio else 0) >= 2

    def offers(self, choice) -> bool:
        if choice == AUDIO:
            return bool(self.audio)
        return any(quality == choice for quality, _ in self.qualities)

def _thumbnail_for(video_id: "str | None") -> "str | None":
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None

async def _choices_ytdlp(url: str) -> Choices:
    import video
    info = await asyncio.to_thread(video.read_info, url)
    if info.get("is_live"):
        raise ProviderFailed("a live stream", "missing")
    if (info.get("duration") or 0) > video.MAX_DURATION_S:
        raise ProviderFailed("over the length limit", "too_big")  # the default path says so, as before
    found = video.choices_of(info, _limit_bytes())
    duration = info.get("duration")
    return Choices(info.get("title"), int(duration) if isinstance(duration, (int, float)) else None,
                   info.get("thumbnail") or _thumbnail_for(info.get("id")), found["qualities"], found["audio"])

def _invidious_choices(data: dict, video_id: str) -> Choices:
    import video
    formats = [fmt for fmt in data.get("adaptiveFormats") or () if isinstance(fmt, dict) and fmt.get("url")]
    room = _limit_bytes() * INVIDIOUS_SIZE_MARGIN
    try:
        sound = _invidious_sound_format(formats)
    except ProviderFailed:
        sound = None
    sound_bytes = _number(sound.get("clen")) if sound else 0
    qualities = []
    found = sorted({_invidious_quality(fmt) for fmt in formats
                    if str(fmt.get("type") or "").startswith("video/mp4") and "avc1" in str(fmt.get("type"))
                    and _number(fmt.get("clen"))})
    for quality in found:
        if not video.PICK_MIN_QUALITY <= quality <= video.MAX_HEIGHT or not sound:
            continue
        try:
            picture, _ = _invidious_pick(formats, _limit_bytes(), quality=quality)
        except ProviderFailed:
            continue
        qualities.append((quality, _number(picture.get("clen")) + sound_bytes))
    seconds = _number(data.get("lengthSeconds"))
    return Choices(data.get("title"), seconds or None, _thumbnail_for(video_id),
                   qualities[-video.PICK_MAX_QUALITIES:], sound_bytes if sound and sound_bytes <= room else None)

async def _choices_invidious(url: str) -> Choices:
    import video
    found = _YT_ID_RE.search(url)
    if not found:
        raise ProviderFailed("no video id in that link", "missing")
    for host in (await _invidious_hosts())[:PICK_INVIDIOUS_HOSTS]:
        try:
            resp = await _get(f"{host}/api/v1/videos/{found.group(1)}", params={"local": "true"},
                              timeout=INVIDIOUS_INSTANCE_TIMEOUT_S)
            data = resp.json()
        except Exception as exc:
            logger.info("picker: %s did not list the versions (%s)", urlparse(host).netloc, type(exc).__name__)
            continue
        if resp.status_code != 200 or not isinstance(data, dict) or data.get("error") \
                or data.get("liveNow") or data.get("isUpcoming"):
            continue
        if _number(data.get("lengthSeconds")) > video.MAX_DURATION_S:
            raise ProviderFailed("over the length limit", "too_big")
        return _invidious_choices(data, found.group(1))
    raise ProviderFailed("no Invidious instance listed the versions", "error")

_PICK_LISTERS = (("ytdlp:youtube", "_choices_ytdlp"), ("invidious:youtube", "_choices_invidious"))

async def _list_choices(url: str) -> "Choices | None":
    now = time.time()
    for name, fn_name in _PICK_LISTERS:
        if health(name).cooling_until > now:
            logger.info("picker: %s is resting, not asked", name)
            continue
        fn = globals()[fn_name]
        try:
            found = await fn(url)
        except Exception as exc:
            logger.info("picker: %s could not list the versions (%s: %s)", name, type(exc).__name__,
                        str(exc)[:150])
            continue
        if found.worth_asking:
            return found
        logger.info("picker: %s listed nothing worth a choice", name)
    return None

async def choices(platform: str, url: str, max_mb: "int | None" = None) -> "Choices | None":
    """The versions the picker can offer for `url`, or None: the site has no picker, nothing listed them in time, or there is nothing to choose between. Never raises. `max_mb` is the largest version worth listing (the large-file ceiling where large files are set up; the free ceiling otherwise)."""
    if platform not in PICK_PLATFORMS:
        return None
    token = _LIMIT_MB.set(max_mb)
    try:
        return await asyncio.wait_for(_list_choices(url), timeout=PICK_LIST_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.info("picker: nothing listed the versions in %.0fs", PICK_LIST_TIMEOUT_S)
    except Exception:
        logger.warning("picker: listing the versions failed", exc_info=True)
    finally:
        _LIMIT_MB.reset(token)
    return None

MAX_ITEMS_PER_POST = max(1, int(os.environ.get("DBOT_MAX_ITEMS_PER_POST", "40")))

def _cut_items(resolved: Resolved) -> None:
    """Keep the first MAX_ITEMS_PER_POST items of `resolved`."""
    if len(resolved.items) <= MAX_ITEMS_PER_POST:
        return
    logger.warning("a delivery of %d items was cut to %d", len(resolved.items), MAX_ITEMS_PER_POST)
    for item in resolved.items[MAX_ITEMS_PER_POST:]:
        if item.path:
            try:
                os.remove(item.path)
            except OSError:
                pass
    del resolved.items[MAX_ITEMS_PER_POST:]

async def _resolve(platform: str, url: str) -> Resolved:
    """Walk the chain until something produces media."""
    failures: dict[str, ProviderFailed] = {}
    chain = _ordered(platform)
    if not chain:
        raise NothingWorked(platform, {})

    skipped: set[str] = set()
    for name, fn in chain:
        if name in skipped:
            logger.info("provider %s skipped for %s: an earlier route ruled it out", name, platform)
            continue
        started = time.perf_counter()
        timeout = _timeout_for(name)
        try:
            resolved = await asyncio.wait_for(fn(url), timeout=timeout)
            if not resolved.items:
                raise ProviderFailed("returned nothing", "missing")
        except ProviderFailed as exc:
            failures[name] = exc
            skipped.update(exc.skip)
            _record_fail(name, str(exc))
            logger.info("provider %s failed for %s: %s", name, platform, exc)
        except asyncio.TimeoutError:
            exc = ProviderFailed(f"timed out after {timeout:.0f}s", "error")
            failures[name] = exc
            _record_fail(name, str(exc))
            logger.info("provider %s timed out for %s", name, platform)
        except Exception as exc:
            wrapped = ProviderFailed(f"{type(exc).__name__}: {exc}", "error")
            failures[name] = wrapped
            _record_fail(name, str(wrapped))
            logger.warning("provider %s raised for %s", name, platform, exc_info=True)
        else:
            _cut_items(resolved)
            _record_ok(name)
            logger.info("provider %s resolved %s in %.1fs (%d item(s))",
                        name, platform, time.perf_counter() - started,
                        len(resolved.items))
            return resolved

    raise NothingWorked(platform, failures)

async def lookup(platform: str, url: str) -> str:
    """Is the post still public? "present", "missing" or "unknown" -- asked of the routes without taking any media (sent_files.py: a stored file id is trusted only while the post was seen public in the last few hours)."""
    asked = said_missing = 0
    skipped: set[str] = set()
    only_asking = _LOOKUP.set(True)
    try:
        for name, fn in _ordered(platform):
            if name.startswith("ytdlp:") or name in skipped:
                continue
            asked += 1
            try:
                found = await asyncio.wait_for(fn(url), timeout=_timeout_for(name))
            except ProviderFailed as exc:
                skipped.update(exc.skip)
                if exc.kind == "missing":
                    said_missing += 1
                continue
            except Exception as exc:
                logger.info("lookup: route %s gave no answer for %s (%s)", name, platform, type(exc).__name__)
                continue
            if found.items:
                return "present"
            said_missing += 1
    finally:
        _LOOKUP.reset(only_asking)
    return "missing" if asked and said_missing == asked else "unknown"

SAMPLES = {
    "instagram": "https://www.instagram.com/reel/DTxk5orCKEv/",
    "tiktok": "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    "twitter": "https://x.com/SpaceX/status/2042988940756480302",
    "pinterest": "https://www.pinterest.com/pin/27725353928390009/",
    "youtube": "https://www.youtube.com/shorts/W05mCB2bDAU",
}

PROBE_FETCH_BYTES = 64 * 1024

PROBE_FETCH_TIMEOUT_S = 20.0

async def probe_route(name, fn, url: str, fetch: bool = False,
                      timeout: float | None = None) -> dict:
    """One route, one link. Never raises. The relays that fetch the file inside the route are asked the way lookup() asks them."""
    only_asking = _LOOKUP.set(True)
    timeout = _timeout_for(name) if timeout is None else timeout
    started = time.perf_counter()
    row = {"provider": name, "url": url, "ok": False, "detail": "", "items": 0,
           "seconds": 0.0, "fetched": None}
    try:
        resolved = await asyncio.wait_for(fn(url), timeout=timeout)
    except ProviderFailed as exc:
        row["detail"] = f"{exc.kind}: {exc}"
    except asyncio.TimeoutError:
        row["detail"] = f"timed out after {timeout:.0f}s"
    except Exception as exc:
        row["detail"] = f"{type(exc).__name__}: {exc}"
    else:
        row["ok"] = True
        row["items"] = len(resolved.items)
        kinds = ", ".join(sorted({i.kind for i in resolved.items}))
        row["detail"] = f"{len(resolved.items)} item(s) [{kinds}]"
        if fetch and resolved.items:
            try:
                row["fetched"] = await asyncio.wait_for(_probe_fetch(resolved.items[0]),
                                                        PROBE_FETCH_TIMEOUT_S)
            except asyncio.TimeoutError:

                row["fetched"] = f"fetch failed: no media in {PROBE_FETCH_TIMEOUT_S:.0f}s"
    finally:
        _LOOKUP.reset(only_asking)
    row["seconds"] = round(time.perf_counter() - started, 1)
    return row

async def _probe_fetch(item: MediaItem) -> str:
    """Prove the media URL actually serves, without pulling the whole file."""
    if item.path:
        try:
            size = os.path.getsize(item.path)
            os.remove(item.path)
            return f"{size:,} bytes on disk"
        except OSError as exc:
            return f"file gone: {exc}"
    last = "no address to fetch"

    class CapReached(Exception):
        """Not an error here: the cap is what this fetch is for."""

    for route in [u for u in [item.url, *item.alt_urls] if u]:
        try:
            async with net.client().stream("GET", route) as resp:
                resp.raise_for_status()
                got = 0

                pieces = net.body_chunks(resp, PROBE_FETCH_BYTES, CapReached)
                try:
                    async for chunk in pieces:
                        got += len(chunk)
                        if got >= PROBE_FETCH_BYTES:
                            break
                except CapReached:
                    got = max(got, PROBE_FETCH_BYTES)
                finally:
                    await pieces.aclose()
                if not got:
                    last = "it sent nothing"
                    continue
                return f"{got:,} bytes, {resp.headers.get('content-type', '?')}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
    return f"fetch failed: {last}"

async def probe_all(urls: dict[str, str] | None = None, fetch: bool = False,
                    timeout: float | None = None) -> dict:
    """Every route for every platform in `urls` (default: SAMPLES)."""
    urls = urls or SAMPLES

    async def one(platform: str, url: str) -> tuple[str, list[dict]]:
        rows = []
        for name, fn in PROVIDERS.get(platform, []):
            rows.append(await probe_route(name, fn, url, fetch=fetch, timeout=timeout))
        return platform, rows

    done = await asyncio.gather(*(one(p, u) for p, u in urls.items()))
    return {platform: rows for platform, rows in done}

_URL_RE = re.compile(r"https?://\S+")

_NOISE_MARKERS = ((re.compile("please report this issue on", re.IGNORECASE), True),
                  (re.compile("confirm you are on the latest version", re.IGNORECASE), False))

_TIDY_READS = 4000

def tidy_error(text: str, limit: int = 150) -> str:
    text = (text or "")[:_TIDY_READS]
    cuts = [(m.start(), semicolon) for marker, semicolon in _NOISE_MARKERS
            for m in [marker.search(text)] if m]
    if cuts:
        at, semicolon = min(cuts)
        text = text[:at].rstrip()
        if semicolon:
            text = text[:-1].rstrip() if text.endswith(";") else text
    text = _URL_RE.sub("<link>", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"

def format_probe(results: dict) -> str:
    """The report, as plain text -- it goes to a Telegram message and to a terminal, and both want the same thing."""
    lines = []
    for platform, rows in results.items():
        lines.append(f"\n{platform}:")
        for row in rows:
            mark = "OK  " if row["ok"] else "FAIL"
            line = (f"  {mark} {row['provider']:<18} {row['seconds']:>4.1f}s  "
                    f"{tidy_error(row['detail'])}")
            if row["fetched"]:
                line += f"  [{row['fetched']}]"
            lines.append(line)
    return "\n".join(lines).strip()

async def download(item: MediaItem, work_dir: str | None = None, max_mb: int | None = None) -> str:
    """Put one MediaItem on disk and return the path, no bigger than `max_mb` (the free ceiling if None)."""
    if item.path:
        return item.path
    routes = [u for u in [item.url, *item.alt_urls] if u]
    if not routes:
        raise FetchError("Nothing to download.")

    work_dir = work_dir or _WORK_DIR
    os.makedirs(work_dir, exist_ok=True)
    ext = _ext_of(item.filename, "mp4" if item.kind == "video" else "jpg")

    last: Exception | None = None
    for route in routes:
        path = os.path.join(work_dir, f"{uuid.uuid4().hex}.{ext}")
        headers = dict(item.headers)
        parsed = urlparse(route)
        headers.setdefault("Referer", f"{parsed.scheme}://{parsed.netloc}/")
        try:
            await net.stream_to_file(route, path, headers=headers,
                                     limit=max_mb * 1024 * 1024 if max_mb else net.MAX_RESPONSE_BYTES)
        except net.TooLarge:

            if os.path.exists(path):
                os.remove(path)
            raise
        except Exception as exc:
            if os.path.exists(path):
                os.remove(path)
            last = exc
            logger.info("media route failed (%s: %s), trying the next one",
                        type(exc).__name__, exc)
            continue
        item.path = path
        return path
    raise FetchError(str(last) if last else "Nothing to download.")

# ─── module: downloader_bot.routewatch ───────────────────────────────────────
"""Once a day, ask every download route whether it still works -- and whether yt-dlp is still current -- from inside the container, and tell the owner when something is about to run out rather than after a user has hit it."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import family_link
import net
import resolvers

logger = logging.getLogger(__name__)

_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off", "")

def _flag(name: str, default: str) -> bool:
    """A switch from the environment."""
    value = os.environ.get(name, default).strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    return default.strip().lower() in _TRUE

ENABLED = _flag("DBOT_ROUTEWATCH", "1")
FIRST_RUN_S = float(os.environ.get("DBOT_ROUTEWATCH_FIRST_S", "600"))
TICK_S = 6 * 3600
MIN_GAP_S = 20 * 3600
PROBE_TIMEOUT_S = float(os.environ.get("DBOT_PROBE_TIMEOUT", "12"))
REALERT_DOWN_S = 3 * 86400
YTDLP_STALE_DAYS = int(os.environ.get("DBOT_YTDLP_STALE_DAYS", "14"))
YTDLP_COOLDOWN_DAYS = int(os.environ.get("DBOT_YTDLP_COOLDOWN_DAYS", "3"))
AUTOUPDATE = _flag("DBOT_YTDLP_AUTOUPDATE", "0")
PYPI_JSON = "https://pypi.org/pypi/yt-dlp/json"

REPLY_WITHIN_S = 75.0

ALERT_PLATFORMS = ("instagram", "tiktok", "twitter", "pinterest")

UP, LAST_RESORT, DOWN, SAMPLE_GONE = "up", "last_resort", "down", "sample_gone"
_KEY = "routewatch:state:"
_LAST_RUN_KEY = "routewatch:last_run"
_YTDLP_ALERTED_KEY = "routewatch:ytdlp_alerted"

_lock = asyncio.Lock()

_ytdlp_lock = asyncio.Lock()

_background: set = set()

STILL_RUNNING = "A route check is already running; /nightly shows the states once it is done."

async def check_platform(platform: str, url: str, timeout: float = PROBE_TIMEOUT_S) -> list[dict]:
    """The chain's routes in order, stopping at the first that works."""
    rows: list[dict] = []
    for name, fn in resolvers.PROVIDERS.get(platform, []):

        if name.startswith("ytdlp:"):
            allowed = max(timeout, resolvers._timeout_for(name))

            async with _ytdlp_lock:
                row = await resolvers.probe_route(name, fn, url, fetch=True, timeout=allowed)
        else:
            row = await resolvers.probe_route(name, fn, url, fetch=True, timeout=timeout)
        fetched = str(row.get("fetched") or "")
        if row["ok"] and fetched.startswith(("fetch failed", "file gone")):
            row["ok"] = False
            row["detail"] = f"resolved, but its media did not serve: {fetched}"
        rows.append(row)
        if row["ok"]:
            break
    return rows

def classify(rows: list[dict], chain_length: int) -> str:
    working = [i for i, row in enumerate(rows) if row["ok"]]
    if working:
        return LAST_RESORT if chain_length > 1 and working[0] == chain_length - 1 else UP
    if rows and all(row["detail"].startswith("missing") for row in rows):
        return SAMPLE_GONE
    return DOWN

def _parse(record: "str | None") -> "tuple[str, float, float] | None":
    try:
        state, since, alerted = (record or "").split("|")
        return state, float(since), float(alerted)
    except ValueError:
        return None

def transition(record: "str | None", new_state: str, now: float):
    """What a platform's new state means, given what it was."""
    old = _parse(record)
    if old is None:
        old_state, since, alerted = UP, now, 0.0
    else:
        old_state, since, alerted = old
    alert = None
    if new_state == old_state:
        if new_state == DOWN and now - alerted >= REALERT_DOWN_S:
            alert, alerted = ("error", "still_down"), now
    else:
        since = now
        if new_state == DOWN:
            alert, alerted = ("error", "down"), now
        elif new_state == LAST_RESORT:
            alert, alerted = ("warning", "last_resort"), now
        elif new_state == SAMPLE_GONE:
            alert, alerted = ("warning", "sample_gone"), now
        elif old_state in (DOWN, LAST_RESORT):
            alert = ("info", "recovered")
    return f"{new_state}|{since:.0f}|{alerted:.0f}", alert

def _lines(rows: list[dict]) -> list[str]:
    return [f"{'ok  ' if row['ok'] else 'FAIL'} {row['provider']}: {resolvers.tidy_error(row['detail'])}"
            for row in rows]

def _message(platform: str, key: str, rows: list[dict], since_days: float) -> str:
    name = platform.capitalize()
    if key == "down":
        return (f"No download route works for {name}, asked from inside the container. "
                f"People who paste a {name} link get DL-ALL-ROUTES-FAILED until one comes back.")
    if key == "still_down":
        return f"{name} still has no working download route -- {since_days:.0f} days now."
    if key == "last_resort":
        return (f"{name} is down to its last download route ({rows[-1]['provider']}); "
                "the ones ahead of it failed. One more failure and it is down.")
    if key == "sample_gone":
        return (f"Every {name} route says the sample link is gone. Probably the post was "
                "deleted: replace it in resolvers.SAMPLES.")
    return f"{name} has a working download route again."

_VERSION_RE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d+))?")

def version_key(text: "str | None") -> "tuple | None":
    """'2026.08.19' and '2026.8.19' are the same release; a '.1' tail is a later one the same day."""
    m = _VERSION_RE.search(text or "")
    if not m:
        return None
    return tuple(int(g or 0) for g in m.groups())

def _installed_ytdlp() -> "str | None":
    try:
        import video
        found = video.ytdlp_version()
    except Exception:
        found = None
    if found:
        return found
    try:
        from importlib import metadata
        return metadata.version("yt-dlp")
    except Exception:
        return None

async def latest_ytdlp() -> "tuple[str, datetime] | None":
    """(version, when it was published) of yt-dlp's newest release, or None if PyPI did not say."""
    try:
        raw = await net.fetch_bytes(PYPI_JSON, limit=8 * 1024 * 1024)
        data = json.loads(raw)
        tag = str(data["info"]["version"])

        uploads = [datetime.fromisoformat(str(f["upload_time_iso_8601"]).replace("Z", "+00:00"))
                   for f in data.get("urls") or []]

        uploads = [t if t.tzinfo else t.replace(tzinfo=timezone.utc) for t in uploads]
        if not uploads:
            return None
        return tag, min(uploads)
    except Exception as exc:
        logger.warning("Could not ask PyPI for yt-dlp's newest release: %s: %s", type(exc).__name__, exc)
        return None

def ytdlp_verdict(installed: "str | None", latest_tag: str, published: datetime,
                  now: "datetime | None" = None) -> dict:
    """Pure: is the container behind, by how much, and is the release old enough to take (it has been out YTDLP_COOLDOWN_DAYS)."""
    now = now or datetime.now(timezone.utc)
    have, want = version_key(installed), version_key(latest_tag)
    behind = bool(have and want and have < want)
    gap_days = 0
    if behind:
        gap_days = (datetime(*want[:3], tzinfo=timezone.utc) - datetime(*have[:3], tzinfo=timezone.utc)).days
    age_days = (now - published).total_seconds() / 86400
    return {"behind": behind, "gap_days": gap_days, "age_days": age_days,
            "stale": behind and gap_days >= YTDLP_STALE_DAYS,
            "cooled": age_days >= YTDLP_COOLDOWN_DAYS}

async def update_ytdlp(tag: str) -> "tuple[bool, str]":
    """Fetch yt-dlp `tag` from PyPI into a folder of its own and make every later download use it."""
    version = tag.lstrip("v")
    base = Path(os.environ.get("DBOT_YTDLP_DIR") or tempfile.gettempdir())
    target = base / f"yt-dlp-{version}"
    if not (target / "yt_dlp" / "version.py").is_file():
        cmd = [sys.executable, "-m", "pip", "install", "--no-deps", "--only-binary=:all:",
               "--disable-pip-version-check", "--no-input", "--quiet",
               "--target", str(target), f"yt-dlp=={version}"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            return False, "pip did not finish in 5 minutes"
        except OSError as exc:
            return False, f"pip could not be started: {exc}"
        if proc.returncode != 0:
            return False, "pip failed: " + resolvers.tidy_error(out.decode("utf-8", "replace")[-400:])

    probe = ("import sys; sys.path.insert(0, sys.argv[1]); "
             "import yt_dlp, yt_dlp.version as v; print(v.__version__)")
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", probe, str(target),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
    except (asyncio.TimeoutError, OSError) as exc:
        return False, f"the new yt-dlp could not be tried: {type(exc).__name__}"
    got = out.decode().strip()
    if proc.returncode != 0 or version_key(got) != version_key(version):
        return False, "the new yt-dlp did not import as " + version + ": " + \
            resolvers.tidy_error((err or out).decode("utf-8", "replace")[-300:])
    import video
    swapped = await asyncio.to_thread(video.use_ytdlp_from, str(target))
    if not swapped:
        return False, "downloads were still running after 5 minutes; will try again"
    return True, got

async def check_ytdlp() -> "str | None":
    """Compare, say so once, and update if allowed. Returns a line for the report."""
    latest = await latest_ytdlp()
    if latest is None:
        return None
    tag, published = latest
    installed = _installed_ytdlp()
    verdict = ytdlp_verdict(installed, tag, published)
    if not verdict["behind"]:
        return f"yt-dlp {installed} is current ({tag})."
    line = (f"yt-dlp {installed} is {verdict['gap_days']} days behind {tag} "
            f"(released {verdict['age_days']:.0f} days ago).")
    if AUTOUPDATE and verdict["cooled"]:
        done, what = await update_ytdlp(tag)
        if done:
            family_link.report_event_soon("info", "ytdlp", f"DownloaderBot updated yt-dlp {installed} -> {what}.")
            return line + f" Updated to {what}."
        line += f" Update failed: {what}."
        problem = f"The automatic yt-dlp update to {tag} failed: {what}"
    elif AUTOUPDATE:

        return line + f" Waiting {YTDLP_COOLDOWN_DAYS} days before taking it."
    elif verdict["stale"]:
        problem = (f"yt-dlp in the container is {installed}; {tag} has been out {verdict['age_days']:.0f} "
                   "days. TikTok, Instagram and YouTube extractors break between releases. Redeploy "
                   "without the build cache, or set DBOT_YTDLP_AUTOUPDATE=1.")
    else:
        return line

    already = await asyncio.to_thread(family_link.get_setting, _YTDLP_ALERTED_KEY)
    if already != tag:
        await asyncio.to_thread(family_link.set_setting, _YTDLP_ALERTED_KEY, tag)
        family_link.report_event_soon("warning", "ytdlp", problem)
    return line

def _header() -> str:
    return ("Download routes, asked from inside this container "
            f"({os.environ.get('RAILWAY_ENVIRONMENT') or 'local'}):")

class _Progress:
    """What a run has finished so far, for a forced run that has to answer before the run does (see run())."""

    def __init__(self):
        self.order = list(resolvers.SAMPLES)
        self.waiting = list(self.order)
        self.blocks: dict = {}

    def partial(self) -> str:
        lines = [_header()]
        for platform in self.order:
            lines += self.blocks.get(platform, [])

        names = ", ".join(self.waiting) or "yt-dlp's newest release"
        lines.append(f"Still checking: {names}. The check carries on; any change is alerted "
                     "as usual, and /nightly shows the states once it is done.")
        return "\n".join(lines)

async def _check(force: bool, progress: _Progress) -> str:
    """The run itself. The caller holds _lock."""
    now = time.time()
    if not force:
        last = await asyncio.to_thread(family_link.get_setting, _LAST_RUN_KEY)
        try:
            if last and now - float(last) < MIN_GAP_S:
                return "skipped: checked less than 20 hours ago"
        except ValueError:
            pass
    await asyncio.to_thread(family_link.set_setting, _LAST_RUN_KEY, f"{now:.0f}")
    samples = dict(resolvers.SAMPLES)
    progress.order, progress.waiting = list(samples), list(samples)

    async def one(platform: str, url: str) -> None:
        try:
            chain = resolvers.PROVIDERS.get(platform, [])
            try:
                rows = await check_platform(platform, url)
            except Exception:
                logger.warning("route check for %s failed", platform, exc_info=True)
                return
            state = classify(rows, len(chain))
            key = _KEY + platform
            old = await asyncio.to_thread(family_link.get_setting, key)
            record, alert = transition(old, state, now)
            await asyncio.to_thread(family_link.set_setting, key, record)
            progress.blocks[platform] = [f"{platform}: {state}"] + ["  " + line for line in _lines(rows)]
            if alert and platform in ALERT_PLATFORMS:
                level, what = alert
                since = (now - (_parse(record) or ("", now, 0))[1]) / 86400
                family_link.report_event_soon(level, "routes", _message(platform, what, rows, since),
                                              "\n".join(_lines(rows)))
        finally:
            progress.waiting.remove(platform)

    results = await asyncio.gather(*(one(p, u) for p, u in samples.items()), return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            raise result
    report = [_header()]
    for platform in progress.order:
        report += progress.blocks.get(platform, [])
    line = await check_ytdlp()
    if line:
        report.append(line)
    text = "\n".join(report)
    logger.info("%s", text)
    return text

async def _check_logged(force: bool, progress: _Progress) -> str:
    """_check as a task of its own."""
    try:
        return await _check(force, progress)
    except Exception:
        logger.warning("the route check failed", exc_info=True)
        raise

def _background_done(task) -> None:
    """However the run ended -- and even if it was cancelled before it began, when its own code would never have run -- the lock it was started holding is let go."""
    _background.discard(task)
    _lock.release()
    if not task.cancelled():
        task.exception()

async def run(force: bool = False, reply_within: "float | None" = None) -> str:
    """The whole check. Returns the report as text (the bus command shows it)."""
    if force and _lock.locked():
        return STILL_RUNNING
    progress = _Progress()
    if reply_within is None:
        async with _lock:
            return await _check(force, progress)
    await _lock.acquire()
    task = asyncio.ensure_future(_check_logged(force, progress))
    _background.add(task)
    task.add_done_callback(_background_done)
    done, _ = await asyncio.wait({task}, timeout=reply_within)
    if task in done:
        return task.result()
    return progress.partial()

async def _tick(_context=None) -> None:
    try:
        await run()
    except Exception:
        logger.warning("the daily route check failed", exc_info=True)

def schedule(application) -> None:
    """Called from _post_init."""
    if not ENABLED or application.job_queue is None:
        return
    application.job_queue.run_repeating(_tick, interval=TICK_S, first=FIRST_RUN_S)

# ─── module: downloader_bot.merge ────────────────────────────────────────────
"""An album as one file: a PDF of its photos, or a ZIP of everything in it."""
import asyncio
import io
import os
import re
import shutil
import struct
import zipfile
from datetime import datetime, timezone

from PIL import Image

MIN_PDF_PHOTOS = 2
MIN_ZIP_ITEMS = 2
MAX_MEGAPIXELS = 20

MAX_PAGE_POINTS = 14400
MAX_SIDE = 65_500

JPEG_QUALITY = 92

MAX_HEADER_PARTS = 1000
MAX_PNG_IDATS = 50_000
MAX_GIF_SUB_BLOCKS = 300_000

_MAX_JPEG_FILL = 4096

MAX_JPEG_SCANS = 200
_CHUNK_HEAD = struct.Struct(">I4s")

PHOTO_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")

_EXIF_ORIENTATION = 0x0112

class MergeError(Exception):
    """Something this module will not or cannot build."""

class PictureTooLarge(MergeError):
    """An image over MAX_MEGAPIXELS. Refused from its header, before a pixel is decoded."""

class NotAPhoto(MergeError):
    """A file that is not a still picture in one of PHOTO_FORMATS: another format, or an animation."""

class PhotoCutShort(MergeError):
    """A JPEG, PNG or GIF whose file ends inside its own header: a photo that was cut."""

class NothingToMerge(MergeError):
    """No file was given, or not enough of them were photographs to make a PDF of (build_pdf left the others out)."""

def output_name(platform: str, ext: str, now: "datetime | None" = None) -> str:
    """`instagram_20261007-1432.pdf`: what the person sees the file called."""
    now = now or datetime.now(timezone.utc)
    stem = re.sub(r"[^a-z0-9]+", "", (platform or "").lower()) or "album"
    return f"{stem}_{now:%Y%m%d-%H%M}.{ext}"

def _safe_ext(path: str, default: str = "bin") -> str:
    """The extension of a file on OUR disk, or `default` if it is not plainly one."""
    ext = os.path.splitext(str(path))[1].lstrip(".").lower()
    return ext if ext and len(ext) <= 5 and ext.isascii() and ext.isalnum() else default

def entry_name(index: int, path: str, width: int = 2) -> str:
    """`01.jpg` for the first file, `02.mp4` for the second."""
    return f"{index:0{width}d}.{_safe_ext(path)}"

def build_zip(paths: "list[str]", out_path: str) -> int:
    """Every file in `paths`, in order, stored (not compressed) in one ZIP. Returns how many went in."""
    if not paths:
        raise NothingToMerge("nothing to put in a ZIP")
    width = max(2, len(str(len(paths))))
    stamp = datetime.now(timezone.utc).timetuple()[:6]
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as archive:
        for number, path in enumerate(paths, start=1):

            info = zipfile.ZipInfo(entry_name(number, path, width), date_time=stamp)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            with open(path, "rb") as source, archive.open(info, "w", force_zip64=False) as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
    return len(paths)

_NEXT_MARKER = re.compile(rb"\xff[^\x00\xd0-\xd7\xff]")
_NOT_FILL = re.compile(rb"[^\xff]")

_MAX_SEGMENTS = 10_000

def _jpeg_layout(data: bytes):
    """(width, height, components, length) of a JPEG that can go into a PDF untouched, or None."""
    n = len(data)
    if data[:2] != b"\xff\xd8":
        return None
    pos, frame, segments = 2, None, 0
    while pos + 2 <= n:
        if data[pos] != 0xFF:
            return None
        marker = data[pos + 1]
        if marker == 0xFF:
            found = _NOT_FILL.search(data, pos)
            if not found:
                return None
            pos = found.start() - 1
            continue
        segments += 1
        if segments > _MAX_SEGMENTS:
            return None
        if marker == 0xD9:
            return frame + (pos + 2,) if frame else None
        if marker == 0x00:
            return None
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            pos += 2
            continue
        if pos + 4 > n:
            return None
        length = int.from_bytes(data[pos + 2:pos + 4], "big")
        if length < 2:
            return None
        if marker in (0xC0, 0xC2):
            body = data[pos + 4:pos + 2 + length]
            if len(body) < 6 or frame is not None or body[0] != 8:
                return None
            height, width = int.from_bytes(body[1:3], "big"), int.from_bytes(body[3:5], "big")
            if not width or not height or body[5] not in (1, 3):
                return None
            frame = (width, height, body[5])
        elif marker in (0xC1, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return None
        pos += 2 + length
        if marker == 0xDA:
            if frame is None:
                return None
            found = _NEXT_MARKER.search(data, pos)
            if not found:
                return None
            pos = found.start()
    return None

def _orientation(image) -> int:
    try:
        return int(image.getexif().get(_EXIF_ORIENTATION, 1) or 1)
    except Exception:
        return 1

def _upright(image):
    """The picture the way up the camera meant it."""
    if _orientation(image) not in (2, 3, 4, 5, 6, 7, 8):
        return image
    from PIL import ImageOps
    turned = ImageOps.exif_transpose(image)
    if turned is not image:
        image.close()
    return turned

def _flatten(image):
    """RGB, with any transparency laid over white."""
    if image.mode in ("I;16", "I;16L", "I;16B", "I"):

        image = image.point(lambda value: value * (1 / 256)).convert("L")
    if image.mode in ("RGBA", "LA", "PA", "RGBa", "La") or "transparency" in image.info:
        rgba = image if image.mode == "RGBA" else image.convert("RGBA")
        page = Image.new("RGB", rgba.size, (255, 255, 255))
        page.paste(rgba, mask=rgba)
        return page
    return image if image.mode == "RGB" else image.convert("RGB")

def _check_size(width: int, height: int) -> None:
    if width * height > MAX_MEGAPIXELS * 1_000_000:
        raise PictureTooLarge(f"{width} x {height} is over {MAX_MEGAPIXELS} megapixels")
    if max(width, height) > MAX_SIDE:
        raise PictureTooLarge(f"{width} x {height} has a side over {MAX_SIDE} pixels")

def _too_many(parts: int) -> None:
    if parts > MAX_HEADER_PARTS:
        raise NotAPhoto(f"more than {MAX_HEADER_PARTS} parts in a header before the picture")

def _count_scans(source) -> None:
    """Refuses a JPEG with more than MAX_JPEG_SCANS start-of-scan markers."""
    source.seek(0)
    scans, tail = 0, b""
    while True:
        piece = source.read(1 << 20)
        if not piece:
            return
        scans += (tail + piece).count(b"\xff\xda")
        if scans > MAX_JPEG_SCANS:
            raise NotAPhoto(f"more than {MAX_JPEG_SCANS} scans in a JPEG")
        tail = piece[-1:]

def _walk_jpeg(source, size: int) -> None:
    """Segment by segment, jumping over each by its length, from the SOI to the first SOS (or EOI)."""
    pos, parts, filler = 2, 0, 0
    while True:
        source.seek(pos)
        pair = source.read(2)
        if len(pair) < 2:
            raise PhotoCutShort("a JPEG that ends before its picture")
        if pair[0] != 0xFF or pair[1] in (0x00, 0xFF):
            filler += 1
            if filler > _MAX_JPEG_FILL:
                raise NotAPhoto("junk between a JPEG's segments")
            pos += 1
            continue
        parts += 1
        _too_many(parts)
        marker = pair[1]
        if marker in (0xDA, 0xD9):
            return
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            pos += 2
            continue
        raw = source.read(2)
        if len(raw) < 2:
            raise PhotoCutShort("a JPEG that ends inside a segment's length")
        length = int.from_bytes(raw, "big")
        if length < 2:
            raise NotAPhoto("a JPEG segment without a length")
        pos += 2 + length
        if pos > size:
            raise PhotoCutShort("a JPEG segment that runs past the end of the file")

def _walk_png(source, size: int) -> None:
    """Chunk by chunk (length, type, data, CRC), jumping over each, from the signature to IEND (or the end of the file)."""
    pos, others, idats = 8, 0, 0
    while True:
        source.seek(pos)
        window = source.read(65536)
        end = len(window)
        offset = 0
        while offset + 8 <= end:
            length, kind = _CHUNK_HEAD.unpack_from(window, offset)
            if kind == b"IDAT":
                idats += 1
                if idats > MAX_PNG_IDATS:
                    raise NotAPhoto(f"more than {MAX_PNG_IDATS} IDAT chunks in a PNG")
            else:
                others += 1
                _too_many(others)
                if kind == b"IEND":
                    return
            offset += 12 + length
            if pos + offset > size:
                raise PhotoCutShort("a PNG chunk that runs past the end of the file")
        pos += offset
        if pos >= size:
            if pos == size and idats:
                return
            raise PhotoCutShort("a PNG that ends before its picture is over")
        if not offset:
            raise PhotoCutShort("a PNG that ends inside a chunk's header")

def _gif_sub_blocks(source, pos: int, count: list, comment: bool) -> int:
    """Past the sub-blocks that start at `pos` (each a length byte and that many bytes, ended by a zero length): the position after the terminator."""
    seen = count[0]
    room = MAX_GIF_SUB_BLOCKS - seen
    if comment:
        room = min(room, MAX_HEADER_PARTS - count[1])
    taken = 0
    while True:
        source.seek(pos)
        window = source.read(65536)
        if not window:
            raise PhotoCutShort("a GIF block that runs past the end of the file")
        end = len(window)
        offset = 0
        while offset < end:
            length = window[offset]
            if not length:
                count[0] += taken
                if comment:
                    count[1] += taken
                return pos + offset + 1
            offset += 1 + length
            taken += 1
            if taken > room:
                if comment and taken + count[1] > MAX_HEADER_PARTS:
                    raise NotAPhoto(f"more than {MAX_HEADER_PARTS} sub-blocks in a GIF comment")
                raise NotAPhoto(f"more than {MAX_GIF_SUB_BLOCKS} sub-blocks in a GIF")
        pos += offset

def _walk_gif(source, size: int, head: bytes) -> None:
    """Block by block, the WHOLE file, to the trailer (or the end of the file): extension blocks and the picture's own data, sub-block by sub-block, every one counted."""
    if len(head) < 13:
        raise PhotoCutShort("a GIF without its screen descriptor")
    pos = 13 + (3 * (2 << (head[10] & 7)) if head[10] & 0x80 else 0)
    blocks, images, count = 0, 0, [0, 0]
    while True:
        source.seek(pos)
        block = source.read(1)
        if not block or block == b"\x3b":
            if images:
                return
            raise PhotoCutShort("a GIF that ends before its picture")
        if block == b"\x21":
            blocks += 1
            _too_many(blocks)
            label = source.read(1)
            if not label:
                raise PhotoCutShort("a GIF extension that runs past the end of the file")
            pos = _gif_sub_blocks(source, pos + 2, count, label == b"\xfe")
        elif block == b"\x2c":
            images += 1
            if images > 1:
                raise NotAPhoto("an animated picture")
            descriptor = source.read(9)
            if len(descriptor) < 9:
                raise PhotoCutShort("a GIF that ends inside its picture's descriptor")
            pos += 10
            if descriptor[8] & 0x80:
                pos += 3 * (2 << (descriptor[8] & 7))
            pos = _gif_sub_blocks(source, pos + 1, count, False)
        else:
            raise NotAPhoto("something in a GIF that is not a block")

def _walk_webp(source, size: int) -> None:
    """Chunk by chunk (fourcc, little-endian size, data padded to even), up to the first picture chunk."""
    pos, parts = 12, 0
    while True:
        source.seek(pos)
        head = source.read(8)
        if len(head) < 8:
            raise NotAPhoto("a WEBP that ends before its picture")
        parts += 1
        _too_many(parts)
        if head[:4] in (b"VP8 ", b"VP8L", b"ANMF"):
            return
        length = int.from_bytes(head[4:8], "little")
        pos += 8 + length + (length & 1)
        if pos > size:
            raise NotAPhoto("a WEBP chunk that runs past the end of the file")

def _check_header(path: str) -> None:
    """Refuse, from the file's start and before Pillow is asked to open it, what open() itself would pay for."""
    with open(path, "rb") as source:
        head = source.read(30)
        size = os.fstat(source.fileno()).st_size
        if len(head) >= 30 and head[:4] == b"RIFF" and head[8:12] == b"WEBP" and head[12:16] == b"VP8X":
            _check_size(1 + int.from_bytes(head[24:27], "little"), 1 + int.from_bytes(head[27:30], "little"))
            if head[20] & 0x02:
                raise NotAPhoto("an animated picture")
        elif len(head) >= 10 and head[:6] in (b"GIF87a", b"GIF89a"):
            _check_size(int.from_bytes(head[6:8], "little"), int.from_bytes(head[8:10], "little"))
        if head[:3] == b"\xff\xd8\xff":
            _walk_jpeg(source, size)
            _count_scans(source)
        elif head[:8] == b"\x89PNG\r\n\x1a\n":
            _walk_png(source, size)
        elif head[:6] in (b"GIF87a", b"GIF89a"):
            _walk_gif(source, size, head)
        elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            _walk_webp(source, size)

def _animated(image) -> bool:
    """More than one picture in it, now that Pillow has opened it."""
    if image.format == "MPO":
        return False
    if image.format == "GIF":
        return False
    return bool(getattr(image, "is_animated", False)) or getattr(image, "n_frames", 1) > 1

def _open_photo(path: str):
    """The file opened as a Pillow image, if it is a still photograph of a size this module takes: everything that can be told without decoding a pixel."""
    _check_header(path)
    try:

        image = Image.open(path, formats=PHOTO_FORMATS)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise PictureTooLarge("an image far over the limit") from exc
    except Image.UnidentifiedImageError as exc:
        raise NotAPhoto("not a JPEG, PNG, WEBP or GIF") from exc
    except OSError as exc:

        if "could not create decoder object" in str(exc):
            raise NotAPhoto("a WEBP that cannot be decoded") from exc
        raise
    try:
        width, height = image.size
        _check_size(width, height)
        if _animated(image):
            raise NotAPhoto("an animated picture")
    except Exception:
        image.close()
        raise
    return image

def _prepare(path: str):
    """(width, height, colour space, JPEG bytes) for one page of the PDF."""
    image = _open_photo(path)
    with image:
        width, height = image.size
        if _orientation(image) == 1:
            with open(path, "rb") as source:
                data = source.read()
            layout = _jpeg_layout(data)
            if layout and layout[:2] == (width, height):
                w, h, components, length = layout

                return (w, h, "/DeviceGray" if components == 1 else "/DeviceRGB",
                        data if length == len(data) else memoryview(data)[:length])
            del data
        image.load()
        _check_size(*image.size)
        picture = _flatten(_upright(image))
        buffer = io.BytesIO()
        picture.save(buffer, "JPEG", quality=JPEG_QUALITY)
        size = picture.size
        picture.close()
        return size[0], size[1], "/DeviceRGB", buffer.getvalue()

def _points(value: float) -> bytes:

    text = f"{max(1.0, min(value, MAX_PAGE_POINTS)):.3f}".rstrip("0").rstrip(".")
    return text.encode()

def build_pdf(paths: "list[str]", out_path: str) -> int:
    """One page per photograph in `paths`, in order, written to `out_path`."""
    if not paths:
        raise NothingToMerge("nothing to put in a PDF")
    photos = []
    for path in paths:
        try:
            _open_photo(path).close()
        except NotAPhoto:
            continue
        photos.append(path)
    if not photos or (len(photos) < len(paths) and len(photos) < MIN_PDF_PHOTOS):
        raise NothingToMerge(f"{len(photos)} of {len(paths)} files are photographs")
    paths = photos
    pages = len(paths)

    total = 3 + 3 * pages
    offsets: "dict[int, int]" = {}
    with open(out_path, "wb") as out:
        def obj(number: int, body: bytes, stream: "bytes | None" = None) -> None:
            offsets[number] = out.tell()
            out.write(b"%d 0 obj\n" % number)
            if stream is None:
                out.write(body + b"\nendobj\n")
            else:
                out.write(body[:-2] + b" /Length %d >>\nstream\n" % len(stream))
                out.write(stream)
                out.write(b"\nendstream\nendobj\n")

        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = b" ".join(b"%d 0 R" % (3 + 3 * i) for i in range(pages))
        obj(2, b"<< /Type /Pages /Count %d /Kids [%s] >>" % (pages, kids))
        for index, path in enumerate(paths):
            width, height, colour, jpeg = _prepare(path)
            scale = min(1.0, MAX_PAGE_POINTS / max(width, height))
            page_w, page_h = _points(width * scale), _points(height * scale)
            page, content, image = 3 + 3 * index, 4 + 3 * index, 5 + 3 * index
            obj(page, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] "
                      b"/Resources << /XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>"
                % (page_w, page_h, image, content))
            obj(content, b"<< >>", b"q %s 0 0 %s 0 0 cm /Im0 Do Q" % (page_w, page_h))
            obj(image, b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s "
                       b"/BitsPerComponent 8 /Filter /DCTDecode >>" % (width, height, colour.encode()),
                jpeg)
            del jpeg
            out.flush()
        table = out.tell()
        out.write(b"xref\n0 %d\n0000000000 65535 f \n" % total)
        for number in range(1, total):
            out.write(b"%010d 00000 n \n" % offsets[number])
        out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (total, table))
    return pages

_pdf_gate: "asyncio.Semaphore | None" = None

def pdf_gate() -> "asyncio.Semaphore":
    global _pdf_gate
    if _pdf_gate is None:
        _pdf_gate = asyncio.Semaphore(1)
    return _pdf_gate

async def build_pdf_queued(paths: "list[str]", out_path: str) -> int:
    """build_pdf in a pool thread, after any other PDF being built has finished."""
    gate = pdf_gate()
    await gate.acquire()
    try:

        task = asyncio.ensure_future(asyncio.to_thread(build_pdf, paths, out_path))
    except BaseException:
        gate.release()
        raise

    def finished(done: "asyncio.Future") -> None:
        gate.release()
        if not done.cancelled():
            done.exception()

    task.add_done_callback(finished)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:

        def discard(_done: "asyncio.Future") -> None:
            try:
                os.remove(out_path)
            except OSError:
                pass

        task.add_done_callback(discard)
        raise

# ─── module: downloader_bot.delivery_cache ───────────────────────────────────
"""The last download, kept for five minutes, so the redo button and the same link sent again are answered without fetching the post a second time."""
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MB = 1024 * 1024

def _env_int(name: str, default: int, unreadable: "int | None" = None) -> int:
    """A whole number from the environment, never negative; `unreadable` (the default when it is None) for anything else -- a typo here must not stop the bot starting."""
    try:
        return max(0, int(os.environ.get(name) or default))
    except ValueError:
        return default if unreadable is None else unreadable

LIFE_SECONDS = _env_int("DBOT_CACHE_SECONDS", 300, unreadable=0)

MAX_LIFE_SECONDS = 12 * 60 * 60

ENTRY_MAX_MB = _env_int("DBOT_CACHE_ENTRY_MAX_MB", 100)
TOTAL_MAX_MB = _env_int("DBOT_CACHE_MAX_MB", 400)

LATEST_KEEP_SECONDS = 60 * 60

SHARED_SENDER_IDS = frozenset({1087968824, 136817688, 777000})

_clock = time.monotonic

@dataclass(eq=False)
class Entry:
    user_id: int
    key: tuple
    items: list
    dir: str
    size: int
    expires_at: float
    last_used: float
    pins: int = 0
    kept_at: float = 0.0
    dead: bool = False

_work_dir = None
_root = None
_entries = {}
_dead = []
_latest = {}
_hits = 0
_misses = 0

def configure(work_dir) -> None:
    """Where downloads are staged; the cache folder is inside it."""
    global _work_dir, _root
    _work_dir = work_dir
    _root = os.path.join(work_dir, "dbot-cache") if work_dir else None

def enabled() -> bool:
    return LIFE_SECONDS > 0 and _root is not None

def usable(user_id) -> bool:
    """Whether anything may be cached, taken or noted for this sender: the cache is on and the id is one person's (not SHARED_SENDER_IDS)."""
    return enabled() and user_id not in SHARED_SENDER_IDS

def free_mb() -> "int | None":
    """Free space on the disk the downloads are staged on, or None."""
    try:
        return shutil.disk_usage(_work_dir).free // MB
    except (OSError, TypeError):
        return None

def _remove_dir(path: str) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    except OSError as exc:

        logger.warning("couldn't delete a cached delivery (%s)", type(exc).__name__)

def _discard(entry: Entry) -> None:
    """The entry is no longer offered. Its files go now, or at the last release if a send is still reading them."""
    if _entries.get(entry.user_id) is entry:
        del _entries[entry.user_id]
    if entry.pins > 0:
        entry.dead = True
        if not any(each is entry for each in _dead):
            _dead.append(entry)
    else:
        _remove_dir(entry.dir)

def _used_bytes() -> int:
    return sum(e.size for e in _entries.values()) + sum(e.size for e in _dead)

NOTED_OFF = "off"
NOTED_NEW = "new"
NOTED_AGAIN_CACHED = "again.cached"
NOTED_AGAIN_NOT_CACHED = "again.not_cached"

def note_link(user_id: int, platform: str, url: str) -> str:
    """The person has just sent (or tapped) this link."""
    if not usable(user_id):
        return NOTED_OFF
    now = _clock()
    key = (platform, url)
    before = _latest.get(user_id)
    again = before is not None and before[0] == key
    _latest[user_id] = (key, now)
    entry = _entries.get(user_id)
    live = entry is not None and entry.key == key and entry.expires_at > now
    if entry is not None:
        if live:
            entry.expires_at = _renewed(entry, now)
            entry.last_used = now
        else:
            _discard(entry)
    if not again:
        return NOTED_NEW
    return NOTED_AGAIN_CACHED if live else NOTED_AGAIN_NOT_CACHED

def keep(user_id: int, platform: str, url: str, items_with_paths, floor_mb: int = 0) -> bool:
    """Take over these delivered files."""
    try:
        return _keep(user_id, (platform, url), list(items_with_paths), floor_mb)
    except Exception as exc:

        logger.warning("couldn't keep a delivery (%s)", type(exc).__name__)
        return False

def _keep(user_id: int, key: tuple, items_with_paths: list, floor_mb: int) -> bool:
    if not usable(user_id) or not items_with_paths:
        return False
    latest = _latest.get(user_id)
    if latest is None or latest[0] != key:
        return False
    size = sum(os.path.getsize(path) for _, path in items_with_paths)
    if size > ENTRY_MAX_MB * MB:
        return False
    previous = _entries.get(user_id)
    if previous is not None:
        _discard(previous)

    candidates = sorted((e for e in _entries.values() if e.pins == 0), key=lambda e: e.last_used)
    over = _used_bytes() + size - TOTAL_MAX_MB * MB
    need = 0
    freed = 0
    while over - freed > 0:
        if need >= len(candidates):
            return False
        freed += candidates[need].size
        need += 1
    if floor_mb > 0:
        free = free_mb()
        if free is None:
            return False
        freed_disk = sum(c.size for c in candidates[:need])
        while free + freed_disk / MB < floor_mb:
            if need >= len(candidates):
                return False
            freed_disk += candidates[need].size
            need += 1
    for victim in candidates[:need]:
        _discard(victim)

    directory = os.path.join(_root, uuid.uuid4().hex)
    os.makedirs(directory, mode=0o700)
    moved, kept = [], []
    try:
        for item, path in items_with_paths:
            destination = os.path.join(directory, os.path.basename(path))
            if os.path.lexists(destination):
                raise FileExistsError("two files with one name")
            os.replace(path, destination)
            moved.append((path, destination))
            kept.append((item, destination))
    except Exception:
        for path, destination in reversed(moved):
            try:
                os.replace(destination, path)
            except OSError:
                try:
                    os.remove(destination)
                except OSError:
                    pass
        _remove_dir(directory)
        return False
    now = _clock()
    _entries[user_id] = Entry(user_id, key, kept, directory, size, now + LIFE_SECONDS, now, kept_at=now)
    return True

def _renewed(entry: Entry, now: float) -> float:
    """The five minutes again from now, but never past MAX_LIFE_SECONDS after keeping."""
    return min(now + LIFE_SECONDS, entry.kept_at + MAX_LIFE_SECONDS)

def take(user_id: int, platform: str, url: str):
    """The person's kept delivery of exactly this link, pinned for the send (call release() when it is over, whatever happens) and with its life restarted; or None."""
    global _hits, _misses
    if not usable(user_id):
        return None
    now = _clock()
    key = (platform, url)
    entry = _entries.get(user_id)
    if entry is not None and entry.expires_at <= now:
        _discard(entry)
        entry = None
    if entry is not None and entry.key == key and not all(os.path.exists(p) for _, p in entry.items):
        _discard(entry)
        entry = None
    if entry is None or entry.key != key:
        _misses += 1
        return None
    entry.pins += 1
    entry.expires_at = _renewed(entry, now)
    entry.last_used = now
    _hits += 1
    return entry

def has(user_id: int, platform: str, url: str) -> bool:
    """Whether take() would find this download now, without taking it."""
    if not usable(user_id):
        return False
    entry = _entries.get(user_id)
    return (entry is not None and entry.key == (platform, url) and entry.expires_at > _clock()
            and all(os.path.exists(p) for _, p in entry.items))

def release(entry) -> None:
    """The send from `entry` is over."""
    entry.pins = max(0, entry.pins - 1)
    if entry.dead and entry.pins == 0:
        _dead[:] = [each for each in _dead if each is not entry]
        _remove_dir(entry.dir)

def drop(user_id: int) -> None:
    """Forget this person's kept delivery."""
    entry = _entries.get(user_id)
    if entry is not None:
        _discard(entry)

def forget_user(user_id: int) -> None:
    """/deletemydata: the kept delivery, and also what makes a download that is still in flight kept when it lands (their latest link)."""
    drop(user_id)
    _latest.pop(user_id, None)

def sweep(now=None) -> None:
    """Drop what has expired, and forget latest links that nothing is waiting on (an hour old, LATEST_KEEP_SECONDS: not the cache's own life, which a slow download outlasts)."""
    now = _clock() if now is None else now
    for entry in list(_entries.values()):
        if not enabled() or entry.expires_at <= now:
            _discard(entry)
    for user_id, (_key, noted) in list(_latest.items()):
        if user_id not in _entries and (not enabled() or noted + LATEST_KEEP_SECONDS <= now):
            del _latest[user_id]

def make_room(mb: int, min_free_mb: int = 0) -> None:
    """A download is about to need up to `mb` MB of the disk, on top of the `min_free_mb` it must always leave free: delete kept deliveries, least recently used first, until the disk has both or nothing that can be deleted is left."""
    try:
        if not enabled():
            return
        free = free_mb()
        if free is None:
            return
        need = min_free_mb + mb
        freed = 0
        for victim in sorted((e for e in _entries.values() if e.pins == 0), key=lambda e: e.last_used):
            if free + freed / MB >= need:
                break
            freed += victim.size
            _discard(victim)
    except Exception as exc:
        logger.warning("couldn't make room (%s)", type(exc).__name__)

def wipe() -> None:
    """Delete everything in the cache folder (at startup: it can only hold what a previous process left behind) and forget all state."""
    _entries.clear()
    _dead.clear()
    _latest.clear()
    if _root is not None:
        _remove_dir(_root)

def stats() -> dict:
    """Counts only, for the owner's /status."""
    return {"enabled": enabled(), "entries": len(_entries), "bytes": _used_bytes(),
            "hits": _hits, "misses": _misses}

# ─── module: downloader_bot.sent_files ───────────────────────────────────────
"""Telegram's file IDs for what this bot has already sent, kept so the same post can be sent again without being downloaded again."""
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import delivery_cache

logger = logging.getLogger(__name__)

STORE_VERSION = 1

MAX_ITEMS = 10

KINDS = ("video", "photo")

def _whole_number(name: str, default: int):
    """The number in the environment, `default` when it is not set, None when it is not a whole number."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return None

def read_settings() -> "tuple[bool, int]":
    """(on, confirm hours) from the environment."""
    flag = _whole_number("DBOT_SENT_FILES", 1)
    hours = _whole_number("DBOT_FILEID_CONFIRM_HOURS", 12)
    return (flag is not None and flag > 0), (hours if hours is not None and hours >= 1 else 12)

ENABLED, CONFIRM_HOURS = read_settings()

_clock = lambda: datetime.now(timezone.utc)

_key: "bytes | None" = None

def configure(token) -> None:
    """The hash key, from the bot's token."""
    global _key
    _key = hashlib.sha256(b"dbot-sent-files|" + token.encode()).digest() if token else None

def enabled() -> bool:
    return ENABLED and _key is not None

def usable(user_id) -> bool:
    """Whether the store may be read or written for this sender: it is on, and the id is one person's."""
    return enabled() and user_id not in delivery_cache.SHARED_SENDER_IDS

def post_key(platform: str, url: str, lossless: bool) -> str:
    """The row of this post in this form: a hex HMAC-SHA256. See the module docstring."""
    form = "file" if lossless else "media"
    message = f"{STORE_VERSION}|{platform}|{url}|{form}".encode("utf-8")
    return hmac.new(_key, message, hashlib.sha256).hexdigest()

@dataclass(frozen=True)
class StoredFile:
    """One stored file as bot._send_media takes it in place of a MediaItem: what it was (the kind of the item sent, whatever the form) and the id to send it by."""
    kind: str
    file_id: str
    filename: str = "download"

def _valid_pairs(pairs) -> bool:
    if not isinstance(pairs, (list, tuple)) or not 1 <= len(pairs) <= MAX_ITEMS:
        return False
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return False
        kind, file_id = pair
        if kind not in KINDS or not isinstance(file_id, str) or not file_id:
            return False
    return True

def encode_items(pairs) -> "str | None":
    """[(kind, file id), ...] as the JSON text of a row, or None if it is not something a row may hold (1 to 10 items, kind video or photo, an id that is a non-empty string)."""
    if not _valid_pairs(pairs):
        return None
    return json.dumps([[kind, file_id] for kind, file_id in pairs], separators=(",", ":"))

def decode_items(text) -> "list[tuple[str, str]] | None":
    """The pairs in a row, or None for anything that is not a list of 1 to 10 [kind, id]: such a row is treated as if it were absent."""
    try:
        pairs = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not _valid_pairs(pairs):
        return None
    return [(kind, file_id) for kind, file_id in pairs]

def stored_files(pairs) -> list:
    return [StoredFile(kind, file_id) for kind, file_id in pairs]

def is_fresh(confirmed_at, now=None) -> bool:
    """Whether the post was seen public less than CONFIRM_HOURS ago."""
    if not isinstance(confirmed_at, datetime):
        return False
    now = now if now is not None else _clock()
    if confirmed_at.tzinfo is None:
        confirmed_at = confirmed_at.replace(tzinfo=timezone.utc)
    age = now - confirmed_at
    return -timedelta(minutes=5) <= age < timedelta(hours=CONFIRM_HOURS)

_INVALID_ID_MARKERS = (
    "wrong file identifier", "wrong remote file identifier", "file_id",
    "type of file mismatch", "file reference", "file_reference", "media_empty",
)

def is_invalid_file_id(exc: BaseException) -> bool:
    from telegram.error import BadRequest
    if not isinstance(exc, BadRequest):
        return False
    message = str(exc).lower()
    return any(marker in message for marker in _INVALID_ID_MARKERS)

_counts = {"hit": 0, "stale": 0, "miss": 0, "present": 0, "missing": 0, "unknown": 0,
           "invalid": 0, "stored": 0}

def note(name: str) -> None:
    _counts[name] += 1

def stats() -> dict:
    return dict(_counts, enabled=enabled())

def reset_stats() -> None:
    for name in _counts:
        _counts[name] = 0

# ─── module: downloader_bot.large_files ──────────────────────────────────────
"""Downloads over 48 MB: fetched anyway, sent over MTProto, and paid for -- only for somebody who has said yes."""
from __future__ import annotations

import math
import os

import big_files
import pricing

MB = 1024 * 1024
big_files.configure("DBOT", "downloaderbot")

FREE_MAX_MB = int(os.environ.get("DBOT_MAX_DOWNLOAD_MB", "48"))

LARGE_MAX_MB = min(int(os.environ.get("DBOT_LARGE_MAX_MB") or big_files.MTPROTO_MAX_BYTES // MB),
                   big_files.MTPROTO_MAX_BYTES // MB)

RUNNING_SECONDS = 60

BOT_API_SEND_BYTES = big_files.BOT_API_SEND_BYTES
CONFIGURED = big_files.CONFIGURED

def _refused() -> None:
    """Telegram refused the API id and hash (big_files.verify): no switch, and FREE_MAX_MB is the limit, as if they had never been set."""
    global CONFIGURED
    CONFIGURED = False

big_files.on_disabled(_refused)

def price_for(size_bytes: int) -> int:
    """⚡ for a large download of this size, by the 100 MB begun."""
    blocks = max(1, math.ceil(size_bytes / (100 * MB)))
    return pricing.price(pricing.cost(RUNNING_SECONDS, blocks * 100 * MB))

def first_price() -> int:
    """What the first 100 MB cost, and the least any large download does."""
    return price_for(1)

def top_price() -> int:
    """What the largest download there is costs."""
    return price_for(LARGE_MAX_MB * MB)

def available(chat_id: int) -> bool:
    """Whether a file over the free ceiling can be had in this chat at all: the route is on, and this is a private chat."""
    return big_files.usable(chat_id)
