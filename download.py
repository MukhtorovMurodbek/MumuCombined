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

import httpx

import net
from net import FetchError, client, close_client, fetch_bytes

__all__ = [
    "FetchError", "client", "close_client", "fetch_bytes",
    "detect_platform", "ANY_LINK_RE",
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
    r"https?://(?:[a-z0-9-]{1,8}\.)?(?:pinterest\.[a-z.]+|pin\.it)/\S+", re.IGNORECASE
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
    r"https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/)|youtu\.be/)\S+",
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

def detect_platform(text: str) -> tuple[str, str] | None:
    """Returns (platform, matched_url) for the first recognized link in text, or None if nothing matches."""
    for name, pattern in _PLATFORM_PATTERNS:
        m = pattern.search(text)
        if m:
            return name, m.group(0)
    return None

async def fetch_reddit_post(url: str) -> dict:
    """Reddit's own public .json endpoint on any post URL -- what old.reddit and countless tools already rely on, no login needed for public subreddits."""
    json_url = url.split("?")[0].rstrip("/") + ".json"
    headers = {
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = await net.client().get(json_url, headers=headers, timeout=15)
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
        resp = await net.client().get(api_url, timeout=15)
    except httpx.HTTPError:
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

import os

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

CRAWLER_UA = "TelegramBot (like TwitterBot)"

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
    """GET a URL into memory, refusing anything that would not fit in a Telegram upload anyway."""
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

class TooLarge(FetchError):
    """Over the size ceiling this download was given."""

async def stream_to_file(url: str, path: str, limit: int = MAX_RESPONSE_BYTES,
                         headers: dict | None = None) -> int:
    """Same, but to disk, for the things that are too big to want in memory."""
    total = 0
    with open(path, "wb") as out:
        async with client().stream("GET", url, headers=headers or {}) as response:
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared and int(declared) > limit:
                raise TooLarge("That file is too big to send through Telegram.")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > limit:
                    raise TooLarge("That file is too big to send through Telegram.")
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
import os
import uuid

MAX_DOWNLOAD_MB = int(os.environ.get("DBOT_MAX_DOWNLOAD_MB", "48"))

MAX_DURATION_S = int(os.environ.get("DBOT_MAX_DURATION_SECONDS", "1800"))

SOCKET_TIMEOUT_S = int(os.environ.get("DBOT_SOCKET_TIMEOUT", "30"))

YT_PLAYER_CLIENTS = [
    c.strip() for c in
    os.environ.get("DBOT_YT_PLAYER_CLIENTS", "tv,web_safari,android_vr,web").split(",")
    if c.strip()
]

COOKIEFILE = os.environ.get("DBOT_COOKIES_FILE") or None
SITE_COOKIEFILES = {
    "youtube": os.environ.get("DBOT_YT_COOKIES_FILE") or None,
    "instagram": os.environ.get("DBOT_IG_COOKIES_FILE") or None,
    "tiktok": os.environ.get("DBOT_TT_COOKIES_FILE") or None,
    "twitter": os.environ.get("DBOT_TW_COOKIES_FILE") or None,
    "reddit": os.environ.get("DBOT_RD_COOKIES_FILE") or None,
}

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

def _format_selector(max_mb: int | None = None) -> str:
    mb = MAX_DOWNLOAD_MB if max_mb is None else max_mb
    return (

        f"bv*[filesize<{mb}M]+ba/"
        f"bv*[filesize_approx<{mb}M]+ba/"

        f"b[filesize<{mb}M]/"
        f"b[filesize_approx<{mb}M]/"

        "bv*+ba/b"
    )

def download_video(url: str, out_dir: str, max_mb: int | None = None) -> str:
    """Downloads the video at `url` into `out_dir`, returns the local file path."""
    mb = MAX_DOWNLOAD_MB if max_mb is None else max_mb
    import yt_dlp

    os.makedirs(out_dir, exist_ok=True)
    unique_id = uuid.uuid4().hex
    outtmpl = os.path.join(out_dir, f"{unique_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": _format_selector(mb),
        "max_filesize": mb * 1024 * 1024,
        "match_filter": _reject_long,
        "socket_timeout": SOCKET_TIMEOUT_S,
        "retries": 2,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "noprogress": True,

        "cachedir": False,
        "merge_output_format": "mp4",
        "extractor_args": {"youtube": {"player_client": YT_PLAYER_CLIENTS}},
    }
    site = _site_of(url)
    cookiefile = SITE_COOKIEFILES.get(site) or COOKIEFILE
    if cookiefile and os.path.exists(cookiefile):
        ydl_opts["cookiefile"] = cookiefile
    proxy = SITE_PROXIES.get(site) or PROXY
    if proxy:
        ydl_opts["proxy"] = proxy
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except Exception as exc:
            lowered = str(exc).lower()
            if any(marker in lowered for marker in BOT_CHECK_MARKERS):

                raise BlockedBySource(str(exc), "bot_check", site) from exc
            if any(marker in lowered for marker in LOGIN_WALL_MARKERS):
                raise BlockedBySource(str(exc), "login_required", site) from exc
            raise
        if info is None:

            raise TooLarge(
                f"That one is too long -- this bot caps downloads at "
                f"{MAX_DURATION_S // 60} minutes and {mb} MB."
            )
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
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

import net
from net import CRAWLER_UA, FetchError

logger = logging.getLogger(__name__)

PROVIDER_TIMEOUT_S = float(os.environ.get("DBOT_PROVIDER_TIMEOUT", "20"))

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

_OG_TAG_RE = re.compile(r"<meta[^>]+>", re.IGNORECASE)

def _meta(html: str, prop: str) -> str | None:
    """Read one OpenGraph/Twitter-card meta tag's content."""
    for tag in _OG_TAG_RE.findall(html):
        if re.search(rf'(?:property|name)=["\']{re.escape(prop)}["\']', tag, re.I):
            m = re.search(r'content=["\']([^"\']+)["\']', tag, re.I)
            if m:
                return m.group(1).replace("&amp;", "&")
    return None

async def _get(url: str, *, crawler: bool = False, **kwargs) -> httpx.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    if crawler:
        headers.setdefault("User-Agent", CRAWLER_UA)
    return await net.client().get(url, headers=headers, **kwargs)

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

    items: list[MediaItem] = []
    for tok in tokens:
        try:
            name = str(_jwt_payload(tok).get("filename") or "")
        except Exception:
            name = ""
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

    probe = await net.client().get(target, headers={"Range": "bytes=0-0"})
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

def _ytdlp_provider(platform: str):
    async def provider(url: str) -> Resolved:
        import video
        try:
            path = await asyncio.to_thread(video.download_video, url, _WORK_DIR, _LIMIT_MB.get())
        except video.BlockedBySource as exc:
            raise ProviderFailed(str(exc), "blocked") from exc
        except video.TooLarge as exc:
            raise ProviderFailed(str(exc), "too_big") from exc
        except Exception as exc:
            raise ProviderFailed(str(exc), "error") from exc
        return Resolved(platform, "ytdlp",
                        [MediaItem("video", path=path,
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

async def resolve(platform: str, url: str, max_mb: int | None = None) -> Resolved:
    """Walk the chain until something produces media, with `max_mb` as the ceiling for anything downloaded on the way."""
    token = _LIMIT_MB.set(max_mb)
    try:
        return await _resolve(platform, url)
    finally:
        _LIMIT_MB.reset(token)

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
        try:
            resolved = await asyncio.wait_for(fn(url), timeout=PROVIDER_TIMEOUT_S)
            if not resolved.items:
                raise ProviderFailed("returned nothing", "missing")
        except ProviderFailed as exc:
            failures[name] = exc
            skipped.update(exc.skip)
            _record_fail(name, str(exc))
            logger.info("provider %s failed for %s: %s", name, platform, exc)
        except asyncio.TimeoutError:
            exc = ProviderFailed(f"timed out after {PROVIDER_TIMEOUT_S:.0f}s", "error")
            failures[name] = exc
            _record_fail(name, str(exc))
            logger.info("provider %s timed out for %s", name, platform)
        except Exception as exc:
            wrapped = ProviderFailed(f"{type(exc).__name__}: {exc}", "error")
            failures[name] = wrapped
            _record_fail(name, str(wrapped))
            logger.warning("provider %s raised for %s", name, platform, exc_info=True)
        else:
            _record_ok(name)
            logger.info("provider %s resolved %s in %.1fs (%d item(s))",
                        name, platform, time.perf_counter() - started,
                        len(resolved.items))
            return resolved

    raise NothingWorked(platform, failures)

SAMPLES = {
    "instagram": "https://www.instagram.com/reel/DTxk5orCKEv/",
    "tiktok": "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    "twitter": "https://x.com/SpaceX/status/2042988940756480302",
    "pinterest": "https://www.pinterest.com/pin/27725353928390009/",
}

PROBE_FETCH_BYTES = 64 * 1024

async def probe_route(name, fn, url: str, fetch: bool = False,
                      timeout: float | None = None) -> dict:
    """One route, one link. Never raises."""
    timeout = PROVIDER_TIMEOUT_S if timeout is None else timeout
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
            row["fetched"] = await _probe_fetch(resolved.items[0])
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
    for route in [u for u in [item.url, *item.alt_urls] if u]:
        try:
            async with net.client().stream("GET", route) as resp:
                resp.raise_for_status()
                got = 0
                async for chunk in resp.aiter_bytes():
                    got += len(chunk)
                    if got >= PROBE_FETCH_BYTES:
                        break
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
_NOISE_RE = re.compile(
    r"\s*;?\s*please report this issue on.*|\s*Confirm you are on the latest version.*",
    re.IGNORECASE | re.DOTALL)

def tidy_error(text: str, limit: int = 150) -> str:
    text = _NOISE_RE.sub("", text or "")
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
        except FetchError:

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
