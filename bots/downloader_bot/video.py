"""The yt-dlp provider: download a video with yt-dlp so the bot can re-send it.

Since v1.2.1 this is one link in resolvers.py's chain rather than the whole
download path, and it is deliberately *last* in every chain. yt-dlp makes the
request from this container's own address, and a datacenter address is the
thing Instagram and YouTube object to -- so it is the route most likely to
come back with a login page, and the only route that gets better the moment
DBOT_<SITE>_COOKIES_FILE or DBOT_<SITE>_PROXY is set. It is also the only
route that works for YouTube at all, and the only one that muxes Reddit's
separate DASH video and audio tracks.

yt-dlp is imported lazily, inside download_video(). Importing it costs
roughly 30-40 MB of resident memory and a second of startup for its
several-hundred extractor modules, and a bot that goes a whole day without
anyone pasting a link should not be paying that the whole time. The first
download pays it once, and it stays loaded from then on.
"""
import os
import uuid

# Telegram itself refuses uploads over 50 MB without a local Bot API server,
# so anything larger was always going to be downloaded and then thrown away.
# Telling yt-dlp up front turns "fill the container's disk, then fail" into
# "don't start". The default leaves headroom under that 50 MB ceiling.
MAX_DOWNLOAD_MB = int(os.environ.get("DBOT_MAX_DOWNLOAD_MB", "48"))

# Nothing this bot handles is a feature film. A ceiling here is what stops a
# mis-pasted link to a three-hour stream from occupying the one worker slot
# (and the disk) for as long as it takes.
MAX_DURATION_S = int(os.environ.get("DBOT_MAX_DURATION_SECONDS", "1800"))

SOCKET_TIMEOUT_S = int(os.environ.get("DBOT_SOCKET_TIMEOUT", "30"))


# YouTube asks a server to prove it is not a bot, and a cloud host's IP is
# exactly what makes it ask. There is no fix for this in the bot, only
# mitigations, and which one works changes month to month -- so both are env
# vars with sensible defaults rather than decisions baked into the code.
#
# player_client picks which of YouTube's own clients yt-dlp pretends to be.
# They are gated differently and the gating moves; yt-dlp tries these in
# order and the list is worth revisiting whenever downloads start failing.
YT_PLAYER_CLIENTS = [
    c.strip() for c in
    os.environ.get("DBOT_YT_PLAYER_CLIENTS", "tv,web_safari,android_vr,web").split(",")
    if c.strip()
]

# A cookies.txt exported from a logged-in browser is the reliable answer, and
# it is deliberately not the default: it ties this bot to a real account, the
# cookies expire in days, and the account can be banned for it. If you use
# one, use a throwaway account -- never your own.
#
# DBOT_COOKIES_FILE applies to every site. The per-site ones win where they
# are set, because the two problems want different accounts: a Google account
# for YouTube and an Instagram one for Instagram, and handing either site the
# other's cookie jar is worse than handing it none.
COOKIEFILE = os.environ.get("DBOT_COOKIES_FILE") or None
SITE_COOKIEFILES = {
    "youtube": os.environ.get("DBOT_YT_COOKIES_FILE") or None,
    "instagram": os.environ.get("DBOT_IG_COOKIES_FILE") or None,
    "tiktok": os.environ.get("DBOT_TT_COOKIES_FILE") or None,
    "twitter": os.environ.get("DBOT_TW_COOKIES_FILE") or None,
    "reddit": os.environ.get("DBOT_RD_COOKIES_FILE") or None,
}

# Where the request goes out from. The reason cookies are not always enough:
# these sites rate-limit by IP as well as by session, every cloud host's
# address is a known datacenter range, and a datacenter IP is most of why the
# server is challenged when a phone on the same link is not. A residential or
# mobile proxy is the robust answer and the only one that does not expire.
PROXY = os.environ.get("DBOT_PROXY") or None
SITE_PROXIES = {
    "youtube": os.environ.get("DBOT_YT_PROXY") or None,
    "instagram": os.environ.get("DBOT_IG_PROXY") or None,
    "tiktok": os.environ.get("DBOT_TT_PROXY") or None,
    "twitter": os.environ.get("DBOT_TW_PROXY") or None,
    "reddit": os.environ.get("DBOT_RD_PROXY") or None,
}

# What the "sign in to confirm you're not a bot" wall looks like coming back
# out of yt-dlp. Matched so the user gets a sentence instead of a stack of
# yt-dlp's documentation links.
BOT_CHECK_MARKERS = ("sign in to confirm", "confirm you're not a bot",
                     "confirm you are not a bot")

# And what a login wall looks like. Instagram stopped serving reels to
# anonymous callers from datacenter addresses, so this is now the *ordinary*
# outcome there rather than an edge case -- and until it was matched here the
# user got yt-dlp's raw text, complete with a link to its FAQ that Telegram
# then expanded into a full-width GitHub preview card. That reads as the bot
# having crashed and helpfully shown you its documentation.
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
    """Which per-site cookie jar and proxy apply. The split matters: the
    YouTube problem wants a Google account and the Instagram one wants an
    Instagram account, and handing either site the other's cookies is worse
    than handing it none."""
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
    """The site refused the server, not the link.

    `kind` says which way it refused, because the two want different
    sentences: "bot_check" is a challenge that may pass on a retry, and
    "login_required" will not pass on any retry -- it needs a credential this
    bot does not have, and saying "try again later" about it is a lie.
    """

    def __init__(self, message: str, kind: str = "bot_check", site: str = "other"):
        super().__init__(message)
        self.kind = kind
        self.site = site


class TooLarge(Exception):
    """The clip is over the size/duration ceiling. Message is user-facing."""


def _reject_long(info, *, incomplete):
    """yt-dlp's match_filter hook: runs on the *metadata*, before a single
    byte of media is fetched."""
    duration = info.get("duration")
    if duration and duration > MAX_DURATION_S:
        return (
            f"that clip is {int(duration) // 60} minutes long, and this bot "
            f"caps downloads at {MAX_DURATION_S // 60}"
        )
    return None


# Every branch below either is a muxed stream (`b`, which by definition has
# both) or explicitly merges video with audio (`+ba`). That sounds obvious and
# it is the whole bug this replaced:
#
#     best[filesize<48M]/best[filesize_approx<48M]/mp4/bestvideo+bestaudio/best
#
# A bare `mp4` in a yt-dlp format chain means "the best format whose extension
# is mp4", and on YouTube the best standalone mp4 is a *video-only* DASH
# stream. It sat ahead of `bestvideo+bestaudio`, so it won whenever the two
# filesize branches missed -- and on YouTube they miss almost always, because
# DASH formats report `filesize: None` and a format whose size is unknown
# *fails* `[filesize<48M]` rather than passing it. Instagram and TikTok hand
# back muxed streams with known sizes, so the chain never reached the bad
# branch there. The result was a bug that only existed on one platform and
# only showed up after the download had already succeeded.
#
# The size filters are kept because downloading 400 MB to throw it away is
# worse than picking a smaller stream, but they are now applied to the video
# half of a merge rather than being the only thing standing between the bot
# and a silent file.

def _format_selector(max_mb: int | None = None) -> str:
    mb = MAX_DOWNLOAD_MB if max_mb is None else max_mb
    return (
        # A video stream that fits, plus the best audio, merged.
        f"bv*[filesize<{mb}M]+ba/"
        f"bv*[filesize_approx<{mb}M]+ba/"
        # Or a single already-muxed stream that fits.
        f"b[filesize<{mb}M]/"
        f"b[filesize_approx<{mb}M]/"
        # Nothing advertised a size it could keep to: take the best merge, or
        # the best muxed stream, and let max_filesize stop it if it runs long.
        "bv*+ba/b"
    )


def download_video(url: str, out_dir: str) -> str:
    """Downloads the video at `url` into `out_dir`, returns the local file path.

    Blocking -- call it through asyncio.to_thread.
    """
    import yt_dlp  # deferred: see the module docstring

    os.makedirs(out_dir, exist_ok=True)
    unique_id = uuid.uuid4().hex
    outtmpl = os.path.join(out_dir, f"{unique_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": _format_selector(),
        "max_filesize": MAX_DOWNLOAD_MB * 1024 * 1024,
        "match_filter": _reject_long,
        "socket_timeout": SOCKET_TIMEOUT_S,
        "retries": 2,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "noprogress": True,
        # Nothing here reads a cache, and the default location is a writeable
        # directory this process would otherwise keep growing.
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
                # Nothing the user did is wrong and nothing they can do
                # will help, so the answer says so plainly rather than
                # handing them yt-dlp's advice about exporting cookies.
                raise BlockedBySource(str(exc), "bot_check", site) from exc
            if any(marker in lowered for marker in LOGIN_WALL_MARKERS):
                raise BlockedBySource(str(exc), "login_required", site) from exc
            raise
        if info is None:
            # match_filter rejected it -- the reason is already in the log,
            # and there is no file to hand back.
            raise TooLarge(
                f"That one is too long -- this bot caps downloads at "
                f"{MAX_DURATION_S // 60} minutes and {MAX_DOWNLOAD_MB} MB."
            )
        path = ydl.prepare_filename(info)
        # merge_output_format can change the extension after download
        if not os.path.exists(path):
            base, _ = os.path.splitext(path)
            mp4_path = base + ".mp4"
            if os.path.exists(mp4_path):
                path = mp4_path
    if not os.path.exists(path):
        raise TooLarge(
            f"That file is over this bot's {MAX_DOWNLOAD_MB} MB limit, so the "
            "download was stopped."
        )
    return path
