"""What this bot converts, what it converts it to, and what this particular
host can actually do.

Three things live here and nothing else -- no conversion code, no Telegram,
no database. `convert_utils.py` and the two `*_convert.py` modules do the
work; `bot.py` builds the buttons; this file is the single place that answers
"is .heic a thing we take, and if so what can it become".

## Why the answer is not a constant

Every backend past Pillow is optional. `pymupdf` is what reads a PDF or an
EPUB, `pillow-heif` is what reads an iPhone photo, `openpyxl` is what reads a
spreadsheet, and ffmpeg is a system binary that may be built without the
encoder a particular target needs. Any of them can be missing -- on a
developer's laptop, on a host whose build failed halfway, on a slimmer image
somebody deploys later.

A bot that advertised a format it could not produce would take somebody's
Stars and hand back an exception, so the matrix below is **declared in full
and then filtered by what imports**. `probe()` runs once at startup and the
menu, `/formats`, and the invoice all read the filtered view. Nothing that
cannot run is ever offered, and nothing has to be edited to say so.

## The shape of the matrix

A file has an **extension**, which normalises to a **format** (`.jpeg` and
`.jfif` are both `jpg`), which belongs to a **category** (image, video,
audio, document, data, subtitle). Targets are looked up per format first and
per category second, because within one category the answers genuinely
differ: an EPUB converts to a PDF and a PDF does not convert to an EPUB.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
# Six, and they are user-visible: /formats has a button per category and the
# conversion menu groups by them. Vector graphics (svg) live in `image`
# deliberately -- svg answers the same question a png does ("a picture"), and
# splitting it out would give /formats a category with one member in it.

IMAGE = "image"
VIDEO = "video"
AUDIO = "audio"
DOCUMENT = "document"
DATA = "data"
SUBTITLE = "subtitle"

CATEGORIES = (IMAGE, VIDEO, AUDIO, DOCUMENT, DATA, SUBTITLE)

# ---------------------------------------------------------------------------
# Extensions in, formats out
# ---------------------------------------------------------------------------
# ALIASES collapses the spellings of one format onto one name. It runs before
# anything else looks at an extension, so the rest of this file -- and every
# TARGETS list, every button, every price line -- deals in one spelling per
# format. `.jpeg` and `.jpg` must not be offered as two separate targets.

ALIASES = {
    "jpeg": "jpg", "jpe": "jpg", "jfif": "jpg",
    "tif": "tiff",
    "dib": "bmp",
    "j2c": "jp2", "jpf": "jp2", "jpx": "jp2",
    "pgm": "ppm", "pbm": "ppm", "pnm": "ppm",
    "yml": "yaml",
    "markdown": "md", "mdown": "md",
    "htm": "html", "xhtml": "html",
    "ssa": "ass",
    "oga": "ogg",
    "mpeg": "mpg", "m2v": "mpg",
    "mts": "m2ts",
    "aif": "aiff", "aifc": "aiff",
    "text": "txt",
}

# What each category takes IN. Not the same as what it puts out: this bot
# reads a .psd and a .mobi and writes neither, which is the normal shape of
# a converter -- reading a format is somebody else's library problem and
# writing one is a design decision.
SOURCES = {
    IMAGE: (
        "png", "jpg", "webp", "bmp", "tiff", "ico", "cur",
        "heic", "heif", "avif", "jp2", "psd", "tga", "pcx", "dds",
        "ppm", "sgi", "xbm", "xpm", "icns", "qoi", "blp", "im", "svg",
    ),
    VIDEO: (
        "mp4", "mov", "m4v", "avi", "webm", "mkv", "flv", "wmv",
        "ts", "m2ts", "mpg", "3gp", "ogv", "asf", "gif", "apng",
    ),
    AUDIO: (
        "mp3", "wav", "ogg", "opus", "m4a", "aac", "flac", "aiff",
        "wma", "amr", "ac3", "mp2", "au", "caf", "w64", "voc",
    ),
    DOCUMENT: (
        "pdf", "docx", "epub", "mobi", "fb2", "cbz", "xps", "md",
        "txt", "html",
    ),
    DATA: ("csv", "tsv", "json", "yaml", "xlsx", "xml"),
    SUBTITLE: ("srt", "vtt", "ass"),
}

# The reverse index, built once.
CATEGORY_OF: dict[str, str] = {}
for _category, _exts in SOURCES.items():
    for _ext in _exts:
        CATEGORY_OF.setdefault(_ext, _category)

# GIF, WEBP and APNG are each two different files wearing one extension: a
# single frame, which is a picture, and an animation, which is a video with no
# sound. Guessing from the extension is wrong in both directions and both
# wrong answers are bad ones -- offering PNG for a five-second animation
# throws away every frame but the first, silently, and refusing PDF for a
# one-frame GIF withholds a conversion that would have worked.
#
# So the file is asked instead. `convert_utils.gif_is_animated()` reads the
# header (cheap: Pillow does not decode the frames) and the answer is passed
# to `category_of()` and `targets_for()` as `animated=`. GIF_IS_VIDEO is only
# the fallback for when nobody looked, and it points at the safe direction:
# keeping frames that turn out not to exist costs nothing, losing frames that
# do costs the whole file.
ANIMATED_CAPABLE = ("gif", "webp", "apng")
GIF_IS_VIDEO = True

# What an animation converts to, whichever of the three it arrived as. PNG and
# JPG are on it deliberately -- "just give me the picture" is a real request,
# and ffmpeg answers it with the first frame.
ANIMATED_TARGETS = ("mp4", "webm", "gif", "webp", "apng", "mkv", "mov", "png", "jpg")

# ---------------------------------------------------------------------------
# What converts to what
# ---------------------------------------------------------------------------
# Order is the order the buttons appear in, and it is by demand rather than
# alphabetical: whatever most people came for is first, and POPULAR_COUNT
# below cuts each list where the rest stops being worth a first screen.

TARGETS_BY_CATEGORY = {
    IMAGE: (
        "png", "jpg", "webp", "pdf", "ico", "tiff",
        "bmp", "gif", "avif", "heic", "jp2", "tga", "ppm", "qoi", "icns",
    ),
    VIDEO: (
        "mp4", "webm", "gif", "mp3", "mkv", "mov",
        "avi", "webp", "apng", "m4a", "aac", "ogg", "opus", "wav", "flac",
    ),
    AUDIO: (
        "mp3", "m4a", "ogg", "wav", "flac", "opus",
        "aac", "aiff", "wma", "ac3",
    ),
    DATA: (
        "json", "csv", "xlsx", "yaml", "md", "html",
        "tsv", "pdf", "txt",
    ),
    SUBTITLE: ("srt", "vtt", "ass", "txt"),
    # DOCUMENT has no category-wide answer worth having: see below.
}

# The per-format overrides, which for documents *are* the rule. A PDF and an
# EPUB are both documents and share almost no targets: one is a finished
# page, the other is reflowable text, and the arrow between them only points
# one way.
TARGETS_BY_FORMAT = {
    "pdf": ("docx", "png", "jpg", "txt", "html", "webp", "svg", "tiff"),
    "epub": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "mobi": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "fb2": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "xps": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "cbz": ("pdf", "png", "jpg"),
    "docx": ("pdf", "html", "md", "txt"),
    "md": ("pdf", "docx", "html", "txt"),
    "html": ("pdf", "docx", "txt", "png", "jpg"),
    "txt": ("pdf", "docx", "html"),
    # An SVG is a picture, so it sits in the image category, but it is drawn
    # by the PDF engine rather than by Pillow, and it has no business being
    # offered "convert to ICO at whatever size we guess".
    "svg": ("png", "pdf", "jpg", "webp"),
    # An animated source keeps its frames. A still target here would quietly
    # discard all but the first, which is the one mistake that looks like it
    # worked.
    "gif": ("mp4", "webm", "webp", "apng", "png", "jpg"),
    "apng": ("gif", "mp4", "webm", "webp", "png"),
    # Lossless in, lossless out first: somebody sending a FLAC is usually not
    # looking for a 128 kbps MP3.
    "flac": ("wav", "aiff", "mp3", "m4a", "ogg", "opus", "aac"),
    "wav": ("mp3", "flac", "m4a", "ogg", "opus", "aiff", "aac"),
    "xml": ("json", "yaml", "md", "html", "txt", "pdf"),
}

# What each format shows before "More formats". Six is what fits two rows of
# three on a phone without the message itself scrolling, and the seventh
# onwards is where the tail of every list starts.
POPULAR_COUNT = 6

# ---------------------------------------------------------------------------
# What each format needs to exist at all
# ---------------------------------------------------------------------------
# The keys are requirement names; probe() fills in which ones are met.
#
#   heif      pillow-heif, for HEIC/HEIF -- which is what an iPhone photo is.
#   avif      AVIF, native in Pillow 11+ and via pillow-heif before that.
#   jp2       JPEG 2000, which needs Pillow built against OpenJPEG.
#   mupdf     PyMuPDF: PDF, EPUB, MOBI, FB2, CBZ, XPS, SVG, and HTML or text
#             rendered onto a page.
#   mammoth   .docx to semantic HTML, which mupdf then renders. Reading a
#             .docx, not writing one.
#   pydocx    python-docx, which is what *writes* a .docx. A different
#             library from mammoth and a different direction -- which is why
#             DOCX appears in TARGET_NEEDS as well as in FORMAT_NEEDS.
#   markdown  Markdown to HTML, likewise.
#   openpyxl  .xlsx.
#   yaml      PyYAML.
#   xml       defusedxml -- the *safe* XML parser, and the only one this bot
#             will point at a stranger's file. See data_convert.py.
#   ffmpeg    the binary, on PATH, with the encoder the target needs.
#
# Pillow itself is a hard dependency: without it the bot does not import, so
# it is not listed against anything.
#
# A format needs the same thing whichever side of the arrow it is on, with
# one exception -- TARGET_NEEDS below.

FORMAT_NEEDS = {
    "heic": ("heif",), "heif": ("heif",),
    "avif": ("avif",),
    "jp2": ("jp2",),
    "pdf": ("mupdf",), "svg": ("mupdf",),
    "epub": ("mupdf",), "mobi": ("mupdf",), "fb2": ("mupdf",),
    "cbz": ("mupdf",), "xps": ("mupdf",),
    "docx": ("mammoth",),
    "md": ("markdown",),
    "html": ("mupdf",),
    "xlsx": ("openpyxl",),
    "yaml": ("yaml",),
    "xml": ("xml",),
}

# The one place a format's requirement depends on which side it is on. Every
# still image Pillow can open, it can also write straight into a PDF page --
# no PDF engine involved, because there is no PDF being *read*. Without this
# override, a host with no PyMuPDF would refuse the single most asked-for
# conversion in the bot for no reason at all.
TARGET_NEEDS = {
    (IMAGE, "pdf"): (),
    # Reading a .docx is mammoth's job; writing one is python-docx's, and the
    # text to put in it comes from the PDF engine. A host with mammoth and no
    # python-docx reads .docx files and does not offer DOCX as a target, which
    # is exactly what this table is for.
    (DOCUMENT, "docx"): ("pydocx", "mupdf"),
}

# Formats that are only reachable through ffmpeg, and the encoder each one
# needs. nixpkgs' ffmpeg carries all of these, but a leaner build somewhere
# else may not, and "Unknown encoder 'libopus'" is not a message any user
# should have to read. Probed once, at startup, from `ffmpeg -encoders`.
ENCODERS = {
    "mp4": "libx264", "mkv": "libx264", "mov": "libx264", "avi": "libx264",
    "webm": "libvpx-vp9",
    "gif": "gif", "apng": "apng", "webp": "libwebp",
    "mp3": "libmp3lame", "ogg": "libvorbis", "opus": "libopus",
    "m4a": "aac", "aac": "aac", "flac": "flac", "wav": "pcm_s16le",
    "aiff": "pcm_s16be", "wma": "wmav2", "ac3": "ac3",
    "srt": "srt", "vtt": "webvtt", "ass": "ass",
}

# Which categories go through ffmpeg at all. A format named in ENCODERS is
# still Pillow's job when the source is a still image -- webp and gif are in
# both worlds.
FFMPEG_CATEGORIES = (VIDEO, AUDIO, SUBTITLE)

# ---------------------------------------------------------------------------
# What this host turned out to have
# ---------------------------------------------------------------------------

_MET: set[str] = set()
_ENCODERS_PRESENT: set[str] = set()
_PROBED = False


def _module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _pillow_feature(name: str) -> bool:
    try:
        from PIL import features
        return bool(features.check(name))
    except Exception:
        return False


def _ffmpeg_encoders() -> set[str]:
    """The encoder names this ffmpeg was built with.

    One subprocess, once, at startup. If it fails -- no ffmpeg, a build with
    no `-encoders`, a host that took too long -- the answer is the empty set,
    which turns every ffmpeg target off rather than promising one.
    """
    if not shutil.which("ffmpeg"):
        return set()
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        logger.warning("Could not ask ffmpeg what it can encode; ffmpeg targets are off.")
        return set()
    names = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        # Every entry is "FLAGS name description"; the header lines above the
        # separator have no six-character flag field to match.
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return names


def probe() -> set[str]:
    """Work out what this host can do. Idempotent; called once from main()."""
    global _PROBED, _MET, _ENCODERS_PRESENT
    found = set()
    if _module("pillow_heif"):
        found.add("heif")
    if _pillow_feature("avif") or _module("pillow_heif"):
        found.add("avif")
    if _pillow_feature("jpg_2000"):
        found.add("jp2")
    for requirement, module in (
        ("mupdf", "pymupdf"), ("mammoth", "mammoth"), ("markdown", "markdown"),
        ("openpyxl", "openpyxl"), ("yaml", "yaml"), ("xml", "defusedxml"),
        ("pydocx", "docx"),
    ):
        if _module(module):
            found.add(requirement)
    _ENCODERS_PRESENT = _ffmpeg_encoders()
    if _ENCODERS_PRESENT:
        found.add("ffmpeg")
    _MET = found
    _PROBED = True
    logger.info(
        "Converters available: %s; %d ffmpeg encoders.",
        ", ".join(sorted(found)) or "Pillow only", len(_ENCODERS_PRESENT),
    )
    absent = [name for name in ("mupdf", "heif", "openpyxl", "yaml", "markdown", "mammoth",
                                "pydocx")
              if name not in found]
    if absent:
        logger.warning(
            "Not installed, so those formats are not offered: %s. "
            "pip install -r requirements.txt puts them back.", ", ".join(absent),
        )
    return found


def _ensure_probed() -> None:
    if not _PROBED:
        probe()


def met(requirement: str) -> bool:
    _ensure_probed()
    return requirement in _MET


def _needs_are_met(needs) -> bool:
    _ensure_probed()
    return all(need in _MET for need in needs)


def _encoder_ok(category: str, target: str) -> bool:
    """True unless ffmpeg is the one who would have to write this and cannot."""
    if category not in FFMPEG_CATEGORIES:
        return True
    encoder = ENCODERS.get(target)
    if encoder is None:
        return True           # written by Python, not by ffmpeg (e.g. txt)
    return encoder in _ENCODERS_PRESENT


# ---------------------------------------------------------------------------
# The questions the rest of the bot asks
# ---------------------------------------------------------------------------

def normalise(ext: str | None) -> str:
    """`.JPEG` -> `jpg`. The only way an extension should ever enter."""
    if not ext:
        return ""
    ext = ext.lower().lstrip(".").strip()
    return ALIASES.get(ext, ext)


def category_of(ext: str, animated: bool | None = None) -> str | None:
    """Which category a source file belongs to, or None if it is not one we
    read.

    `animated` is the answer for the three extensions that can be either; pass
    it whenever the file is on disk to be looked at. Without it a GIF is
    answered as video and a WEBP as an image, which are the defaults that lose
    the least when they are wrong.
    """
    ext = normalise(ext)
    if ext in ANIMATED_CAPABLE and animated is not None:
        return VIDEO if animated else IMAGE
    if ext == "gif":
        return VIDEO if GIF_IS_VIDEO else IMAGE
    return CATEGORY_OF.get(ext)


def is_supported_source(ext: str) -> bool:
    ext = normalise(ext)
    if category_of(ext) is None:
        return False
    return _needs_are_met(FORMAT_NEEDS.get(ext, ()))


def declared_targets(ext: str, animated: bool | None = None) -> tuple[str, ...]:
    """Everything this format converts to on a host that has everything.

    The unfiltered view: what the tests check, and what nothing user-facing
    should use.
    """
    ext = normalise(ext)
    if ext in ANIMATED_CAPABLE and animated is not None:
        listed = ANIMATED_TARGETS if animated else TARGETS_BY_CATEGORY[IMAGE]
    else:
        listed = TARGETS_BY_FORMAT.get(ext)
        if listed is None:
            listed = TARGETS_BY_CATEGORY.get(category_of(ext), ())
    return tuple(target for target in listed if target != ext)


def targets_for(ext: str, animated: bool | None = None) -> list[str]:
    """Everything this format converts to *here*. What the buttons are built
    from, and the list a chosen format is checked against before anything
    runs."""
    ext = normalise(ext)
    category = category_of(ext, animated)
    if category is None or not is_supported_source(ext):
        return []
    out = []
    for target in declared_targets(ext, animated):
        needs = TARGET_NEEDS.get((category, target), FORMAT_NEEDS.get(target, ()))
        if _needs_are_met(needs) and _encoder_ok(category, target):
            out.append(target)
    return out


def popular_targets(ext: str, animated: bool | None = None) -> list[str]:
    """The first screenful. A short list stays whole -- there is no point in
    hiding two buttons behind a button."""
    targets = targets_for(ext, animated)
    if len(targets) <= POPULAR_COUNT + 2:
        return targets
    return targets[:POPULAR_COUNT]


def supported_sources(category: str) -> list[str]:
    """Every extension of this category this host can read, in the order it
    is declared -- which is roughly by how common it is."""
    return [ext for ext in SOURCES.get(category, ())
            if category_of(ext) == category and is_supported_source(ext)]


def supported_targets(category: str) -> list[str]:
    """Every format this host can write, for sources of this category.

    In the category's own declared order first, so that /formats reads by
    demand like the buttons do, and anything a single format adds on its own
    (an EPUB's PDF, a GIF's MP4) after it.
    """
    seen = []
    for source in supported_sources(category):
        for target in targets_for(source):
            if target not in seen:
                seen.append(target)
    declared = [target for target in TARGETS_BY_CATEGORY.get(category, ()) if target in seen]
    return declared + [target for target in seen if target not in declared]


def counts() -> tuple[int, int, int]:
    """(formats in, formats out, source-to-target pairs) -- for /formats,
    which should not contain a number somebody has to remember to update."""
    sources, targets, pairs = set(), set(), 0
    for category in CATEGORIES:
        for source in supported_sources(category):
            available = targets_for(source)
            if not available:
                continue
            sources.add(source)
            targets.update(available)
            pairs += len(available)
    return len(sources), len(targets), pairs


def find_format(text: str) -> str | None:
    """`png`, `.PNG`, `png file`, `image/png` -> `png`, when we know it.

    Used by `/formats <thing>` and by the catch-all handler, so that somebody
    who just types "heic" at the bot gets an answer rather than a form letter.
    """
    if not text:
        return None
    word = text.strip().lower().rsplit("/", 1)[-1].strip().lstrip(".")
    word = word.split()[0] if word.split() else ""
    word = normalise(word)
    return word if word in CATEGORY_OF else None


# ---------------------------------------------------------------------------
# What a conversion is allowed to cost in work rather than in bytes
# ---------------------------------------------------------------------------
# The price is calculated from the file size, and size is a poor proxy for
# work here in a way it was not when this bot only did images and ffmpeg: a
# 900 KB PDF can be four hundred pages, and rendering all of them is minutes
# of CPU sold for the free tier. These are the ceilings that stop the gap
# between "small file" and "small job" from becoming everybody else's
# problem, and they are the reason the pricing model did not have to change.

MAX_PAGES = int(os.environ.get("CONVERT_MAX_PAGES") or 200)
MAX_ROWS = int(os.environ.get("CONVERT_MAX_ROWS") or 100_000)
MAX_CELLS = int(os.environ.get("CONVERT_MAX_CELLS") or 2_000_000)
# How many files one batch may hold. Telegram caps an album at 10; a longer
# run of separate messages is collected the same way, and this is where it
# stops.
MAX_BATCH = int(os.environ.get("CONVERT_MAX_BATCH") or 20)
