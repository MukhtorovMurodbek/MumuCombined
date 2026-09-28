"""StickerBot's pictures, emoji, imports and video stickers.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("stickers.py is loaded section by section by main.py -- run main.py")


# ─── module: sticker_bot.emoji_utils ─────────────────────────────────────────
"""Heuristics for the 'send emoji right after a sticker to override the default' flow."""
import re

DEFAULT_EMOJI = "\U0001F62D"
_HAS_LETTER_OR_DIGIT = re.compile(r"[A-Za-z0-9]")
_VARIATION_SELECTOR = "\uFE0F"
MAX_LEN = 16
MAX_EMOJI_PER_STICKER = 20

def looks_like_emoji_message(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > MAX_LEN:
        return False
    return not _HAS_LETTER_OR_DIGIT.search(text)

def split_emoji(text: str) -> list[str]:
    """Best-effort split of a short string into individual emoji."""
    chars = list(text.strip())
    out: list[str] = []
    i = 0
    while i < len(chars):
        c = chars[i]
        if i + 1 < len(chars) and chars[i + 1] == _VARIATION_SELECTOR:
            out.append(c + chars[i + 1])
            i += 2
        else:
            out.append(c)
            i += 1

    seen = set()
    deduped = []
    for e in out:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    return deduped[:MAX_EMOJI_PER_STICKER] or [DEFAULT_EMOJI]

# ─── module: sticker_bot.image_utils ─────────────────────────────────────────
"""Resize/convert arbitrary images into Telegram static-sticker-compliant PNGs."""
from io import BytesIO

from PIL import Image

STICKER_SIDE = 512

Image.MAX_IMAGE_PIXELS = 40_000_000

def to_sticker_png(image_bytes: bytes) -> BytesIO:
    """Blocking (Pillow decodes and resamples in-process) -- call it through asyncio.to_thread so a large image doesn't stall every other user."""
    img = Image.open(BytesIO(image_bytes))

    img.draft("RGB", (STICKER_SIDE, STICKER_SIDE))

    w, h = img.size
    if w >= h:
        new_w = STICKER_SIDE
        new_h = max(1, round(h * STICKER_SIDE / w))
    else:
        new_h = STICKER_SIDE
        new_w = max(1, round(w * STICKER_SIDE / h))

    img = img.resize((new_w, new_h), Image.LANCZOS)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    out = BytesIO()
    img.save(out, format="PNG")
    img.close()
    out.seek(0)
    out.name = "sticker.png"
    return out

# ─── module: sticker_bot.import_utils ────────────────────────────────────────
"""Mass-import stickers into a pack that's currently being edited."""
import json
import re
import zipfile
from io import BytesIO

from telegram import InputSticker

import i18n
from image_utils import to_sticker_png

TELEGRAM_PACK_RE = re.compile(
    r"(?:https?://)?t\.me/addstickers/([A-Za-z0-9_]+)|^([A-Za-z0-9_]{1,64})$"
)

MAX_IMPORT_PER_RUN = 100

_MAX_UNCOMPRESSED_ENTRY = 32 * 1024 * 1024

class ImportError_(Exception):
    pass

def parse_telegram_pack_source(text: str) -> str | None:
    """Pulls a short sticker-set name out of a link or raw name the user sent."""
    text = text.strip()
    m = TELEGRAM_PACK_RE.match(text)
    if not m:
        return None
    return m.group(1) or m.group(2)

async def fetch_importable_stickers(bot, source_name: str, lang: str = "en"):
    """Returns the list of Sticker objects from a public set, or raises ImportError_ with a human-readable reason."""
    try:
        sticker_set = await bot.get_sticker_set(source_name)
    except Exception as exc:
        raise ImportError_(i18n.t(lang, "import_pack_not_found", source=source_name)) from exc
    return sticker_set.stickers

def sticker_to_input_sticker(sticker) -> InputSticker | None:
    """Reuses the source sticker's file_id directly -- no download/re-encode needed since it's already a valid Telegram sticker file."""
    if sticker.is_animated:
        return None
    fmt = "video" if sticker.is_video else "static"
    emoji_list = [sticker.emoji] if sticker.emoji else ["\U0001F62D"]
    return InputSticker(sticker=sticker.file_id, emoji_list=emoji_list, format=fmt)

_IMG_EXT_RE = re.compile(r"\.(webp|png|jpg|jpeg)$", re.IGNORECASE)

def parse_whatsapp_zip(raw: bytes, lang: str = "en") -> list[tuple[bytes, list[str]]]:
    """Returns a list of (sticker_png_bytes, emoji_list) pulled out of a .wastickers/.zip export."""
    try:
        zf = zipfile.ZipFile(BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ImportError_(i18n.t(lang, "import_bad_zip")) from exc

    emoji_by_filename: dict[str, list[str]] = {}
    for name in zf.namelist():
        if name.lower().endswith(("contents.json", "sticker_pack.json", "manifest.json")):
            try:
                data = json.loads(zf.read(name).decode("utf-8"))
                for entry in data.get("stickers", []):
                    img = entry.get("image_file")
                    emojis = entry.get("emojis") or entry.get("emoji")
                    if img and emojis:
                        emoji_by_filename[img] = list(emojis) if isinstance(emojis, list) else [emojis]
            except Exception:
                pass

    results: list[tuple[bytes, list[str]]] = []
    for info in sorted(zf.infolist(), key=lambda i: i.filename):
        if len(results) >= MAX_IMPORT_PER_RUN:

            break
        if not _IMG_EXT_RE.search(info.filename):
            continue
        if info.file_size > _MAX_UNCOMPRESSED_ENTRY:
            continue
        base = info.filename.rsplit("/", 1)[-1]
        try:
            png_bytes = to_sticker_png(zf.read(info)).getvalue()
        except Exception:
            continue
        emojis = emoji_by_filename.get(base) or emoji_by_filename.get(info.filename) or ["\U0001F62D"]
        results.append((png_bytes, emojis))

    zf.close()
    if not results:
        raise ImportError_(i18n.t(lang, "import_zip_no_images"))
    return results

# ─── module: sticker_bot.video_sticker ───────────────────────────────────────
"""Convert arbitrary GIFs/videos (and already-valid Telegram video stickers, re-encoded for safety) into Telegram-compliant video stickers."""
import os
import shutil
import subprocess
import tempfile

import i18n

STICKER_SIDE = 512
MAX_DURATION_S = 3
MAX_FPS = 30
MAX_BYTES = 256 * 1024

_FIRST_CRF = 34
_MIN_CRF, _MAX_CRF = 20, 63
_MAX_ATTEMPTS = int(os.environ.get("STICKER_ENCODE_ATTEMPTS", "4"))

_TIMEOUT_S = int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "120"))

_THREADS = os.environ.get("FFMPEG_THREADS", "2")

_SCALE_FILTER = (
    f"scale=w='if(gte(iw,ih),{STICKER_SIDE},-2)':h='if(gte(iw,ih),-2,{STICKER_SIDE})'"
)

class ConversionError(Exception):
    """Raised when ffmpeg is missing or the clip can't be made to fit."""

def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

def _next_crf(crf: int, size: int, fps: int) -> tuple[int, int]:
    """Given an attempt that came out `size` bytes at `crf`, guess the CRF that lands under the limit -- and drop the frame rate once CRF alone has run out of room."""
    overshoot = size / MAX_BYTES
    step = 6
    while overshoot > 2 and step < 24:
        overshoot /= 2
        step += 6
    target = crf + step
    if target <= _MAX_CRF:
        return target, fps

    return _MAX_CRF, 15 if fps <= 24 else 24

def _encode(in_path: str, out_path: str, crf: int, fps: int) -> subprocess.CompletedProcess:
    cmd = [
        "ffmpeg", "-nostdin", "-y",
        "-i", in_path,
        "-t", str(MAX_DURATION_S),
        "-an",
        "-r", str(fps),
        "-vf", _SCALE_FILTER,
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
        "-b:v", "0",
        "-deadline", "good",
        "-cpu-used", "5",
        "-row-mt", "1",
        "-threads", _THREADS,
        out_path,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_S)

def to_video_sticker_webm(input_bytes: bytes, lang: str = "en") -> bytes:
    """Takes raw bytes of a GIF, video, or video sticker and returns bytes of a compliant WEBM/VP9 video sticker."""
    if not _ffmpeg_available():
        raise ConversionError(i18n.t(lang, "video_convert_ffmpeg_missing"))
    if not input_bytes:
        raise ConversionError(i18n.t(lang, "video_convert_empty_file"))

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "in.bin")
        with open(in_path, "wb") as f:
            f.write(input_bytes)

        crf, fps = _FIRST_CRF, MAX_FPS
        last_note = "unknown error"
        seen: set[tuple[int, int]] = set()

        for attempt in range(_MAX_ATTEMPTS):
            out_path = os.path.join(tmp, f"out_{attempt}.webm")
            try:
                proc = _encode(in_path, out_path, crf, fps)
            except subprocess.TimeoutExpired:
                raise ConversionError(
                    i18n.t(lang, "video_convert_too_big", note=f"encoding timed out after {_TIMEOUT_S}s")
                ) from None

            if proc.returncode != 0:

                raise ConversionError(
                    i18n.t(lang, "video_convert_too_big",
                           note=proc.stderr.strip()[-300:] or "ffmpeg failed with no output")
                )

            size = os.path.getsize(out_path)
            if size <= MAX_BYTES:
                with open(out_path, "rb") as f:
                    return f.read()

            last_note = f"still {size // 1024} KB at crf={crf}, {fps}fps"
            seen.add((crf, fps))
            crf, fps = _next_crf(crf, size, fps)
            if (crf, fps) in seen:
                break

        raise ConversionError(i18n.t(lang, "video_convert_too_big", note=last_note))
