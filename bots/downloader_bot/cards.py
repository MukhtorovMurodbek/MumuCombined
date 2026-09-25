"""Renders a plain, consistent 'quote card' image for text-based Reddit/
Twitter posts -- the actual reason to download these instead of just
screenshotting: no UI chrome, no notification banners caught mid-shot, no
light/dark-mode mismatch, and it's already square-ish and clean enough to
repost as-is.

Uses Pillow's built-in scalable default font (load_default(size=...),
Pillow >=10.1) instead of bundling a .ttf -- works identically wherever
this bot ends up hosted, no font files to ship or find on the host OS.
"""
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
    """Cached: there are exactly four sizes in this file, and rebuilding the
    same four font objects for every card is work with no result."""
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
    """platform: "reddit" or "twitter" (picks the accent color).
    source: e.g. "r/aww" or "@handle" -- shown large, in the accent color.
    author: e.g. "u/someone" or "Display Name" -- shown small, muted.
    body: the post/tweet text, wrapped and truncated to MAX_BODY_LINES.
    meta: an optional footer line, e.g. score/like counts.
    """
    font_source = _font(34)
    font_author = _font(26)
    font_body = _font(38)
    font_meta = _font(26)

    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    max_text_width = WIDTH - PADDING * 2 - 16  # 16 for the accent bar

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
