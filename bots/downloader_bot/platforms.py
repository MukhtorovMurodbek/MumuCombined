"""Which platform a pasted link belongs to, and the two page-scrapes that are
about *text* rather than media.

Media resolution moved to resolvers.py at v1.2.1. What is left here is
recognition -- the regexes bot.py's MessageHandler filters on -- plus the
Reddit and Twitter/X reads that exist to render a card for a post with no
media in it, which is a different job from downloading one.

Instagram and TikTok used to share a single regex, because they shared a
single code path: yt-dlp. They no longer share a code path -- they have
separate provider chains with nothing in common -- so they are separate
platforms here too.
"""
import math
import re

import httpx

import net
from net import FetchError, client, close_client, fetch_bytes  # re-exported

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
# Pinterest runs a country subdomain per market -- co.pinterest.com,
# br.pinterest.com, in.pinterest.com, ru.pinterest.com -- and the share sheet
# hands out whichever one the sharer was on. Allowing only `www.` meant a link
# from anywhere but the default host was answered with "that is not a link I
# recognise", which reads as the bot not supporting Pinterest at all.
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
# Deliberately undocumented everywhere else (see bot.py's HELP_TEXT and
# BOT_COMMANDS) -- handled if someone pastes one, never mentioned in any
# command list or help text. It is also the one platform with no provider but
# yt-dlp, so it is the one most likely to be refusing a server on any given
# day; advertising it would be promising something the bot cannot keep.
YOUTUBE_RE = re.compile(
    r"https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/)|youtu\.be/)\S+",
    re.IGNORECASE,
)

# Ordered so the most specific patterns are tried first.
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
    """Returns (platform, matched_url) for the first recognized link in text,
    or None if nothing matches."""
    for name, pattern in _PLATFORM_PATTERNS:
        m = pattern.search(text)
        if m:
            return name, m.group(0)
    return None


# ---------- Reddit: public .json endpoint, no auth ----------

async def fetch_reddit_post(url: str) -> dict:
    """Reddit's own public .json endpoint on any post URL -- what old.reddit
    and countless tools already rely on, no login needed for public
    subreddits. Reddit's anti-scraping has gotten more aggressive about this
    over time though (IP-reputation based, not just User-Agent), so this can
    403 from some hosts even for a perfectly public post -- that's surfaced
    as a FetchError with a clear message, not a stack trace."""
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


# ---------- Twitter/X: public syndication endpoint, no auth ----------
# The same unauthenticated endpoint X's own embed widget
# (platform.twitter.com/widgets.js) calls to render an embedded tweet -- not a
# private or reverse-engineered API. Kept for the *card*: resolvers.py handles
# a tweet's media through fxtwitter/vxtwitter, but a text-only tweet has no
# media to resolve and this is where its text, author and like count come
# from. Best-effort by nature: X can rate-limit or change it without notice,
# which is why the caller falls back to handing back the link.

def _tweet_id_from_url(url: str) -> str | None:
    m = re.search(r"/status(?:es)?/(\d+)", url)
    return m.group(1) if m else None


def _base36(x: float, precision: int = 60) -> str:
    """Python doesn't have JS's Number.prototype.toString(36) built in --
    this reimplements it (integer part + fractional digits) just precisely
    enough to reproduce the syndication token below."""
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
    """X's embed widget computes this the same way to authorize an otherwise
    open syndication request -- not a secret, just an obfuscation step:
    ((id / 1e15) * pi) in base 36, with zeros and the decimal point
    stripped."""
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
    # Deleted/protected/age-restricted tweets come back as a "tombstone" with
    # a moderation notice instead of real content -- treat that the same as
    # "couldn't fetch it" rather than rendering the notice as if it were the
    # tweet.
    if not data or data.get("__typename") != "Tweet":
        return None
    return data
