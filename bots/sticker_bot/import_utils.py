"""Mass-import stickers into a pack that's currently being edited.

Two sources are supported:
- Another Telegram sticker pack (public, any name/link) -- reuses each
  source sticker's existing file_id, so there's no re-encoding at all: full
  quality, and it keeps the original emoji tags.
- A WhatsApp sticker-pack export (.wastickers / .zip) -- these are just zip
  files full of .webp images, optionally with a contents.json manifest (the
  format used by most open-source "sticker maker" apps) mapping each image
  to its emoji list. Falls back to the default emoji when there's no
  manifest, or it doesn't parse.
"""
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

MAX_IMPORT_PER_RUN = 100  # stays comfortably under Telegram's ~120-sticker set cap

# A zip entry's declared uncompressed size, above which it is skipped rather
# than decompressed. A sticker image is tens of kilobytes; anything claiming
# 32 MB is either not a sticker or is a zip bomb, and either way expanding it
# to find out is the expensive mistake.
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
    """Returns the list of Sticker objects from a public set, or raises
    ImportError_ with a human-readable reason."""
    try:
        sticker_set = await bot.get_sticker_set(source_name)
    except Exception as exc:
        raise ImportError_(i18n.t(lang, "import_pack_not_found", source=source_name)) from exc
    return sticker_set.stickers


def sticker_to_input_sticker(sticker) -> InputSticker | None:
    """Reuses the source sticker's file_id directly -- no download/re-encode
    needed since it's already a valid Telegram sticker file. Returns None
    for formats we can't carry over (Lottie/.tgs animated stickers)."""
    if sticker.is_animated:  # Lottie/.tgs
        return None
    fmt = "video" if sticker.is_video else "static"
    emoji_list = [sticker.emoji] if sticker.emoji else ["\U0001F62D"]
    return InputSticker(sticker=sticker.file_id, emoji_list=emoji_list, format=fmt)


# ---------- WhatsApp zip import ----------

_IMG_EXT_RE = re.compile(r"\.(webp|png|jpg|jpeg)$", re.IGNORECASE)


def parse_whatsapp_zip(raw: bytes, lang: str = "en") -> list[tuple[bytes, list[str]]]:
    """Returns a list of (sticker_png_bytes, emoji_list) pulled out of a
    .wastickers/.zip export. Raises ImportError_ if it isn't a readable zip
    or has no usable images inside."""
    try:
        zf = zipfile.ZipFile(BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ImportError_(i18n.t(lang, "import_bad_zip")) from exc

    # Optional manifest used by most WhatsApp "sticker maker" export tools:
    # {"stickers": [{"image_file": "01.webp", "emojis": ["😀"]}, ...]}
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
                pass  # manifest is a nice-to-have, not required

    results: list[tuple[bytes, list[str]]] = []
    for info in sorted(zf.infolist(), key=lambda i: i.filename):
        if len(results) >= MAX_IMPORT_PER_RUN:
            # Stop at the cap rather than converting the whole archive and
            # then slicing it: a 400-image export used to mean 400 decodes
            # and 400 PNGs held in memory to use the first hundred.
            break
        if not _IMG_EXT_RE.search(info.filename):
            continue
        if info.file_size > _MAX_UNCOMPRESSED_ENTRY:
            continue  # a zip bomb, or something that was never a sticker
        base = info.filename.rsplit("/", 1)[-1]
        try:
            png_bytes = to_sticker_png(zf.read(info)).getvalue()
        except Exception:
            continue  # skip unreadable entries rather than failing the whole import
        emojis = emoji_by_filename.get(base) or emoji_by_filename.get(info.filename) or ["\U0001F62D"]
        results.append((png_bytes, emojis))

    zf.close()
    if not results:
        raise ImportError_(i18n.t(lang, "import_zip_no_images"))
    return results