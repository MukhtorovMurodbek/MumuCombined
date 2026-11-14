"""ConvertBot's formats, converters, the worker process that runs them, and the queue.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("convert.py is loaded section by section by main.py -- run main.py")


# ─── module: convert_bot.formats ─────────────────────────────────────────────
"""What this bot converts, what it converts it to, and what this particular host can actually do."""
from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

IMAGE = "image"
VIDEO = "video"
AUDIO = "audio"
DOCUMENT = "document"
DATA = "data"
SUBTITLE = "subtitle"
ARCHIVE = "archive"
PRESENTATION = "presentation"

CATEGORIES = (IMAGE, VIDEO, AUDIO, DOCUMENT, PRESENTATION, DATA, SUBTITLE, ARCHIVE)

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
    "tbz": "tbz2", "tb2": "tbz2", "taz": "tgz",
    # A slide show is the same file as its deck; PowerPoint only opens it differently.
    "pps": "ppt", "ppsx": "pptx", "pptm": "pptx",
}

COMPOUND_EXTENSIONS = (("tar.gz", "tgz"), ("tar.bz2", "tbz2"), ("tar.xz", "txz"))

def compound_extension(filename: "str | None") -> "str | None":
    """`photos.TAR.GZ` -> `tgz`; None when the name does not end in one."""
    lowered = (filename or "").lower()
    for ending, name in COMPOUND_EXTENSIONS:
        if lowered.endswith("." + ending):
            return name
    return None

RAW_FORMATS = ("dng", "cr2", "cr3", "nef", "arw", "raf", "orf", "rw2")

SOURCES = {
    IMAGE: (
        "png", "jpg", "webp", "bmp", "tiff", "ico", "cur",
        "heic", "heif", "avif", "jp2", "psd", "tga", "pcx", "dds",
        "ppm", "sgi", "xbm", "xpm", "icns", "qoi", "blp", "im", "svg",
        *RAW_FORMATS,
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
        "pdf", "docx", "doc", "odt", "rtf", "epub", "mobi", "fb2", "cbz", "xps", "md",
        "txt", "html",
    ),
    PRESENTATION: ("pptx", "ppt", "odp"),
    DATA: ("csv", "tsv", "json", "yaml", "xlsx", "xls", "ods", "xml"),
    SUBTITLE: ("srt", "vtt", "ass"),

    ARCHIVE: ("zip", "tar", "tgz", "tbz2", "txz", "7z", "rar"),
}

CATEGORY_OF: dict[str, str] = {}
for _category, _exts in SOURCES.items():
    for _ext in _exts:
        CATEGORY_OF.setdefault(_ext, _category)

ANIMATED_CAPABLE = ("gif", "webp", "apng")
GIF_IS_VIDEO = True

ANIMATED_TARGETS = ("mp4", "webm", "gif", "webp", "apng", "mkv", "mov", "png", "jpg")

TARGETS_BY_CATEGORY = {

    IMAGE: (
        "png", "jpg", "webp", "pdf", "ico", "tiff",
        "bmp", "gif", "avif", "heic", "jp2", "tga", "ppm", "qoi", "icns",
        "txt", "ocrpdf",
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

    ARCHIVE: ("zip", "7z", "tgz", "tar", "txz", "tbz2"),

    PRESENTATION: ("pdf", "pptx", "ppt", "odp", "png", "jpg", "txt"),

}

TARGETS_BY_FORMAT = {
    "pdf": ("docx", "pptx", "png", "jpg", "txt", "ocrpdf", "html", "webp", "svg", "tiff", "odp"),
    "epub": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "mobi": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "fb2": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "xps": ("pdf", "docx", "txt", "html", "png", "jpg"),
    "cbz": ("pdf", "png", "jpg"),
    "docx": ("pdf", "odt", "doc", "html", "md", "txt", "rtf", "png", "jpg"),
    "doc": ("pdf", "docx", "odt", "txt", "rtf", "html", "png", "jpg"),
    "odt": ("pdf", "docx", "doc", "txt", "rtf", "html", "png", "jpg"),
    "rtf": ("pdf", "docx", "doc", "odt", "txt", "html"),
    "xlsx": ("json", "csv", "ods", "xls", "yaml", "md", "html", "tsv", "pdf", "txt"),
    "xls": ("xlsx", "csv", "ods", "pdf", "json", "html", "md", "yaml", "tsv", "txt"),
    "ods": ("xlsx", "csv", "xls", "pdf", "json", "html", "md", "yaml", "tsv", "txt"),
    "md": ("pdf", "docx", "html", "txt"),
    "html": ("pdf", "docx", "txt", "png", "jpg"),
    "txt": ("pdf", "docx", "html"),

    "svg": ("png", "pdf", "jpg", "webp"),

    **{raw: ("jpg", "png", "webp", "avif", "heic", "tiff") for raw in RAW_FORMATS},

    "gif": ("mp4", "webm", "webp", "apng", "png", "jpg"),
    "apng": ("gif", "mp4", "webm", "webp", "png"),

    "flac": ("wav", "aiff", "mp3", "m4a", "ogg", "opus", "aac"),
    "wav": ("mp3", "flac", "m4a", "ogg", "opus", "aiff", "aac"),
    "xml": ("json", "yaml", "md", "html", "txt", "pdf"),
}

POPULAR_COUNT = 6

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
    "7z": ("bsdtar",), "rar": ("bsdtar",),
    **{raw: ("rawpy",) for raw in RAW_FORMATS},

    "ocrpdf": ("ocr",),

    **{office: ("office",) for office in ("pptx", "ppt", "odp", "doc", "odt", "rtf", "xls", "ods")},
}

TARGET_NEEDS = {
    (IMAGE, "pdf"): (),

    (DOCUMENT, "docx"): ("pydocx", "mupdf"),

    (IMAGE, "txt"): ("ocr",),

    # A PDF opened as slides needs LibreOffice's PDF import as well.
    (DOCUMENT, "pptx"): ("office", "pdfimport"),
    (DOCUMENT, "odp"): ("office", "pdfimport"),
}

ENCODERS = {
    "mp4": "libx264", "mkv": "libx264", "mov": "libx264", "avi": "libx264",
    "webm": "libvpx-vp9",
    "gif": "gif", "apng": "apng", "webp": "libwebp",
    "mp3": "libmp3lame", "ogg": "libvorbis", "opus": "libopus",
    "m4a": "aac", "aac": "aac", "flac": "flac", "wav": "pcm_s16le",
    "aiff": "pcm_s16be", "wma": "wmav2", "ac3": "ac3",
    "srt": "srt", "vtt": "webvtt", "ass": "ass",
}

FFMPEG_CATEGORIES = (VIDEO, AUDIO, SUBTITLE)

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

def bsdtar_path() -> "str | None":
    """libarchive's tar, which reads 7z and RAR and writes 7z: `bsdtar` where it is installed as that (Debian's libarchive-tools), and on Windows the system's own tar.exe, which is the same program."""
    explicit = os.environ.get("CBOT_BSDTAR")
    if explicit and os.path.isfile(explicit):
        return explicit
    found = shutil.which("bsdtar")
    if found:
        return found
    if os.name == "nt":
        candidate = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "tar.exe")
        if os.path.isfile(candidate):
            return candidate
    return None

def _ffmpeg_encoders() -> set[str]:
    """The encoder names this ffmpeg was built with."""
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

        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return names

def _ocr_available() -> bool:
    """Whether text can be recognised here: PyMuPDF with Tesseract in it, and the language data on disk (ocr_convert.available)."""
    try:
        import ocr_convert
        return bool(ocr_convert.available())
    except Exception:
        logger.debug("Text recognition is not available", exc_info=True)
        return False

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
        ("pydocx", "docx"), ("rawpy", "rawpy"),
    ):
        if _module(module):
            found.add(requirement)
    if bsdtar_path():
        found.add("bsdtar")
    if _ocr_available():
        found.add("ocr")
    try:
        import office_convert
        if office_convert.soffice_path():
            found.add("office")
            if office_convert.has_pdf_import():
                found.add("pdfimport")
    except Exception:
        logger.debug("LibreOffice could not be looked for", exc_info=True)
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
                                "pydocx", "bsdtar", "rawpy", "ocr", "office")
              if name not in found]
    if absent:
        logger.warning(
            "Not installed, so those formats are not offered: %s. "
            "pip install -r requirements.txt (LibreOffice: the Dockerfile) puts them back.", ", ".join(absent),
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
        return True
    return encoder in _ENCODERS_PRESENT

def normalise(ext: str | None) -> str:
    """`.JPEG` -> `jpg`. The only way an extension should ever enter."""
    if not ext:
        return ""
    ext = ext.lower().lstrip(".").strip()
    return ALIASES.get(ext, ext)

def category_of(ext: str, animated: bool | None = None) -> str | None:
    """Which category a source file belongs to, or None if it is not one we read."""
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
    """Everything this format converts to on a host that has everything."""
    ext = normalise(ext)
    if ext in ANIMATED_CAPABLE and animated is not None:
        listed = ANIMATED_TARGETS if animated else TARGETS_BY_CATEGORY[IMAGE]
    else:
        listed = TARGETS_BY_FORMAT.get(ext)
        if listed is None:
            listed = TARGETS_BY_CATEGORY.get(category_of(ext), ())
    return tuple(target for target in listed if target != ext)

def targets_for(ext: str, animated: bool | None = None) -> list[str]:
    """Everything this format converts to *here*."""
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
    """The first screenful. A short list stays whole -- there is no point in hiding two buttons behind a button."""
    targets = targets_for(ext, animated)
    if len(targets) <= POPULAR_COUNT + 2:
        return targets
    return targets[:POPULAR_COUNT]

def supported_sources(category: str) -> list[str]:
    """Every extension of this category this host can read, in the order it is declared -- which is roughly by how common it is."""
    return [ext for ext in SOURCES.get(category, ())
            if category_of(ext) == category and is_supported_source(ext)]

def supported_targets(category: str) -> list[str]:
    """Every format this host can write, for sources of this category."""
    seen = []
    for source in supported_sources(category):
        for target in targets_for(source):
            if target not in seen:
                seen.append(target)
    declared = [target for target in TARGETS_BY_CATEGORY.get(category, ()) if target in seen]
    return declared + [target for target in seen if target not in declared]

def counts() -> tuple[int, int, int]:
    """(formats in, formats out, source-to-target pairs) -- for /formats, which should not contain a number somebody has to remember to update."""
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
    """`png`, `.PNG`, `png file`, `image/png` -> `png`, when we know it."""
    if not text:
        return None
    word = text.strip().lower().rsplit("/", 1)[-1].strip().lstrip(".")
    word = word.split()[0] if word.split() else ""
    word = normalise(word)
    return word if word in CATEGORY_OF else None

MAX_PAGES = int(os.environ.get("CONVERT_MAX_PAGES") or 200)
MAX_ROWS = int(os.environ.get("CONVERT_MAX_ROWS") or 100_000)
MAX_CELLS = int(os.environ.get("CONVERT_MAX_CELLS") or 2_000_000)

MAX_PAGE_MEGAPIXELS = int(os.environ.get("CONVERT_MAX_PAGE_MEGAPIXELS") or 100)

MAX_BATCH = int(os.environ.get("CONVERT_MAX_BATCH") or 20)

# ─── module: convert_bot.convert_utils ───────────────────────────────────────
"""The conversions themselves, and the Telegram Stars pricing table."""
from __future__ import annotations

import json
import logging
import math
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import NamedTuple

from PIL import Image

import big_files
import formats

logger = logging.getLogger(__name__)

class Result(NamedTuple):
    """One file to send, and enough about it to caption it honestly."""
    path: Path
    items: int = 1
    zipped: bool = False

class ConversionError(Exception):
    pass

class OutOfMemory(ConversionError):
    """The converter was killed for memory: the file is fine, the machine is too small for it."""

def _killed(returncode) -> bool:
    """Killed by SIGKILL -- the kernel's out-of-memory killer, when this process did not do it itself (its own time limits raise before this is asked)."""
    return returncode in (-9, 137)

def remove_tree(path) -> None:
    """Remove a folder and everything in it, whatever the modes inside say."""
    path = str(path)
    tried: set = set()

    def make_writable(target: str) -> None:
        try:
            mode = os.lstat(target).st_mode
            if stat.S_ISLNK(mode):
                return
            os.chmod(target, (mode | (stat.S_IRWXU if stat.S_ISDIR(mode) else stat.S_IRUSR | stat.S_IWUSR)) & 0o777)
        except OSError:
            pass

    def retry(function, target, _error) -> None:

        target = str(target)
        if target in tried:
            return
        tried.add(target)
        if target != path:
            make_writable(os.path.dirname(target))
        make_writable(target)
        try:
            if function in (os.scandir, os.listdir, os.open):

                shutil.rmtree(target, **{_ON_ERROR: retry})
            elif function is os.path.islink:
                return
            else:
                function(target)
        except OSError:
            pass

    try:
        if os.path.islink(path):
            os.unlink(path)
            return
        if not os.path.lexists(path):
            return

        waiting = [path]
        while waiting:
            folder = waiting.pop()
            make_writable(folder)
            try:
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if entry.is_dir(follow_symlinks=False):
                            waiting.append(entry.path)
                        elif os.name == "nt" and entry.is_file(follow_symlinks=False):
                            make_writable(entry.path)
            except OSError:
                continue
        shutil.rmtree(path, **{_ON_ERROR: retry})
    except (OSError, RecursionError):
        logger.debug("Could not remove %s", path, exc_info=True)

_ON_ERROR = "onexc" if sys.version_info >= (3, 12) else "onerror"

PROGRESS = None

def report(done: float, total: float) -> None:
    if PROGRESS is None or not total:
        return
    try:
        PROGRESS(min(done, total), total)
    except Exception:
        pass

_LOCAL_BOT_API = bool(os.environ.get("LOCAL_BOT_API_URL"))
big_files.configure("CBOT", "convertbot")
BIG_FILES = _LOCAL_BOT_API or big_files.CONFIGURED
BOT_API_MAX_MB = big_files.BOT_API_DOWNLOAD_BYTES // (1024 * 1024)
MAX_FILE_MB = int(os.environ.get("CONVERT_MAX_FILE_MB")
                  or (big_files.MTPROTO_MAX_BYTES // (1024 * 1024) if BIG_FILES else BOT_API_MAX_MB))
if not BIG_FILES:
    MAX_FILE_MB = min(MAX_FILE_MB, BOT_API_MAX_MB)

def _big_files_refused() -> None:
    """Telegram refused the API id and hash (big_files.verify): promise, and take, only what the Bot API allows -- as if they had never been set."""
    global BIG_FILES, MAX_FILE_MB
    if _LOCAL_BOT_API:
        return
    BIG_FILES = False
    MAX_FILE_MB = min(MAX_FILE_MB, BOT_API_MAX_MB)

big_files.on_disabled(_big_files_refused)

def max_file_mb_in(chat_id: int) -> int:
    """The largest upload taken in this chat."""
    if _LOCAL_BOT_API or big_files.usable(chat_id):
        return MAX_FILE_MB
    return min(MAX_FILE_MB, BOT_API_MAX_MB)

Image.MAX_IMAGE_PIXELS = 80_000_000

MAX_FRAMES = int(os.environ.get("CONVERT_MAX_FRAMES") or 1200)

PAGE_DPI = int(os.environ.get("CONVERT_PAGE_DPI") or 150)

_MB = 1024 * 1024

FREE_UNDER_MB = 3

def price_for_size(size_bytes: int) -> int | None:
    """None if a file this size cannot be taken at all (over MAX_FILE_MB); otherwise what converting it into something its own size would cost."""
    if size_bytes > MAX_FILE_MB * _MB:
        return None
    return _price(size_bytes, size_bytes, 1.0)

BILLABLE = (os.environ.get("CONVERT_BILLABLE") or "sum").strip().lower()

_RATIO_BY_PAIR = {

    ("docx", "pdf"): 20.0, ("docx", "html"): 1.2, ("docx", "md"): 0.3, ("docx", "txt"): 0.15,
    ("md", "pdf"): 4.0, ("md", "html"): 1.3, ("md", "txt"): 0.9,
    ("txt", "pdf"): 3.0, ("txt", "html"): 1.2,
    ("html", "pdf"): 2.0, ("html", "txt"): 0.3,
    ("pdf", "txt"): 0.05, ("pdf", "html"): 0.3, ("pdf", "svg"): 1.5,
    ("epub", "pdf"): 2.5, ("epub", "txt"): 0.25, ("epub", "html"): 0.7,
    ("mobi", "pdf"): 2.5, ("mobi", "txt"): 0.25, ("mobi", "html"): 0.7,
    ("fb2", "pdf"): 2.5, ("fb2", "txt"): 0.3, ("fb2", "html"): 0.8,
    ("xps", "pdf"): 1.1, ("cbz", "pdf"): 1.05,
    ("pdf", "docx"): 0.6,

    ("pptx", "pdf"): 0.8, ("pptx", "ppt"): 1.5, ("pptx", "odp"): 0.9, ("pptx", "txt"): 0.02,
    ("ppt", "pptx"): 0.6, ("ppt", "pdf"): 0.6, ("ppt", "odp"): 0.6, ("ppt", "txt"): 0.01,
    ("odp", "pptx"): 1.1, ("odp", "ppt"): 1.6, ("odp", "pdf"): 0.9, ("odp", "txt"): 0.02,
    ("pdf", "pptx"): 0.8, ("pdf", "odp"): 0.8,
    ("doc", "docx"): 0.4, ("doc", "pdf"): 1.5, ("doc", "odt"): 0.4, ("doc", "rtf"): 2.0, ("doc", "txt"): 0.1,
    ("odt", "docx"): 1.1, ("odt", "pdf"): 3.0, ("odt", "doc"): 2.5, ("odt", "rtf"): 4.0, ("odt", "txt"): 0.2,
    ("rtf", "docx"): 0.2, ("rtf", "pdf"): 0.5, ("rtf", "doc"): 0.6, ("rtf", "odt"): 0.2, ("rtf", "txt"): 0.05,
    ("docx", "odt"): 1.1, ("docx", "doc"): 2.5, ("docx", "rtf"): 4.0,
    ("xlsx", "ods"): 1.1, ("xlsx", "xls"): 2.5, ("xls", "xlsx"): 0.4, ("xls", "ods"): 0.4,
    ("ods", "xlsx"): 1.1, ("ods", "xls"): 2.5, ("xls", "pdf"): 1.0, ("ods", "pdf"): 2.0,

    ("wav", "mp3"): 0.10, ("wav", "m4a"): 0.09, ("wav", "ogg"): 0.10,
    ("wav", "opus"): 0.07, ("wav", "aac"): 0.09, ("wav", "flac"): 0.6,
    ("flac", "mp3"): 0.25, ("flac", "wav"): 1.7, ("flac", "m4a"): 0.22,
    ("flac", "opus"): 0.18, ("flac", "ogg"): 0.25, ("flac", "aac"): 0.22,
    ("aiff", "mp3"): 0.10, ("aiff", "flac"): 0.6,
    ("mp3", "wav"): 9.0, ("mp3", "flac"): 5.0, ("mp3", "aiff"): 9.0,
    ("m4a", "wav"): 9.0, ("ogg", "wav"): 9.0, ("opus", "wav"): 12.0,

    ("png", "jpg"): 0.15, ("png", "webp"): 0.25, ("png", "avif"): 0.15,
    ("jpg", "png"): 3.5, ("jpg", "bmp"): 12.0, ("jpg", "tiff"): 10.0,
    ("svg", "png"): 20.0, ("svg", "jpg"): 8.0, ("svg", "pdf"): 1.5,
    ("heic", "jpg"): 2.0, ("heic", "png"): 6.0,

    ("7z", "zip"): 1.6, ("rar", "zip"): 1.15, ("txz", "zip"): 1.25, ("tbz2", "zip"): 1.1,
    ("tgz", "zip"): 1.02, ("tar", "zip"): 0.5,
    ("zip", "7z"): 0.8, ("zip", "txz"): 0.85, ("zip", "tgz"): 1.0, ("zip", "tbz2"): 0.95, ("zip", "tar"): 1.5,
}

_RAW_RATIO = {"jpg": 0.25, "png": 3.0, "webp": 0.2, "avif": 0.15, "heic": 0.2, "tiff": 4.0}

_RATIO_BY_CATEGORY = {
    (formats.VIDEO, "gif"): 6.0, (formats.VIDEO, "apng"): 9.0, (formats.VIDEO, "webp"): 2.0,
    (formats.VIDEO, "mp4"): 0.9, (formats.VIDEO, "webm"): 0.7, (formats.VIDEO, "mkv"): 1.02,
    (formats.VIDEO, "mov"): 1.05, (formats.VIDEO, "avi"): 1.3,

    (formats.VIDEO, "mp3"): 0.10, (formats.VIDEO, "m4a"): 0.09, (formats.VIDEO, "aac"): 0.09,
    (formats.VIDEO, "ogg"): 0.10, (formats.VIDEO, "opus"): 0.07,
    (formats.VIDEO, "wav"): 0.9, (formats.VIDEO, "flac"): 0.5,
    (formats.VIDEO, "png"): 0.05, (formats.VIDEO, "jpg"): 0.02,
    (formats.IMAGE, "pdf"): 1.05, (formats.IMAGE, "ico"): 0.05, (formats.IMAGE, "icns"): 0.1,
    (formats.DATA, "xlsx"): 0.6, (formats.DATA, "pdf"): 2.0, (formats.DATA, "html"): 1.4,
    (formats.DATA, "md"): 1.1, (formats.DATA, "json"): 1.3, (formats.DATA, "yaml"): 1.1,
    (formats.SUBTITLE, "txt"): 0.7,
    (formats.PRESENTATION, "png"): 2.0, (formats.PRESENTATION, "jpg"): 0.8,

    (formats.ARCHIVE, "zip"): 1.1, (formats.ARCHIVE, "tgz"): 1.1, (formats.ARCHIVE, "tbz2"): 1.05,
    (formats.ARCHIVE, "txz"): 0.95, (formats.ARCHIVE, "7z"): 0.9, (formats.ARCHIVE, "tar"): 1.5,
}

_RATIO_BY_TARGET = {
    "png": 3.0, "bmp": 10.0, "ppm": 10.0, "tga": 8.0, "tiff": 5.0, "sgi": 8.0,
    "jpg": 0.4, "webp": 0.4, "avif": 0.3, "heic": 0.4, "jp2": 0.8, "qoi": 2.5,
    "gif": 1.5, "ico": 0.05, "icns": 0.1,
    "txt": 0.4, "md": 0.5, "html": 1.2, "pdf": 2.0, "svg": 1.2,
    "wav": 8.0, "flac": 4.0, "aiff": 8.0, "mp3": 0.8, "m4a": 0.8, "aac": 0.8,
    "ogg": 0.8, "opus": 0.6, "wma": 0.9, "ac3": 1.0,
    "docx": 0.8,
}

_BYTES_PER_PAGE = {"png": 350_000, "jpg": 120_000, "webp": 90_000,
                   "tiff": 1_200_000, "svg": 60_000, "pdf": 90_000}

_WORK_BY_TARGET = {
    "mp4": 2.0, "webm": 2.4, "mkv": 2.0, "mov": 2.0, "avi": 1.6,
    "apng": 1.8, "gif": 1.5, "avif": 1.8, "heic": 1.3,
}
_WORK_BY_CATEGORY = {

    (formats.DOCUMENT, "pdf"): 1.4, (formats.DOCUMENT, "png"): 1.4,
    (formats.DOCUMENT, "jpg"): 1.4, (formats.DOCUMENT, "webp"): 1.4,
    (formats.DOCUMENT, "tiff"): 1.5, (formats.DOCUMENT, "svg"): 1.4,
    (formats.DOCUMENT, "docx"): 1.4,
    # LibreOffice starts afresh for every conversion, which costs a few seconds whatever the size.
    (formats.DOCUMENT, "odt"): 1.6, (formats.DOCUMENT, "doc"): 1.6, (formats.DOCUMENT, "rtf"): 1.6,
    (formats.DOCUMENT, "pptx"): 2.0, (formats.DOCUMENT, "odp"): 2.0,
    **{(formats.PRESENTATION, target): 1.8 for target in ("pdf", "pptx", "ppt", "odp", "txt")},
    (formats.PRESENTATION, "png"): 2.0, (formats.PRESENTATION, "jpg"): 2.0,
    (formats.DATA, "ods"): 1.4, (formats.DATA, "xls"): 1.4,

    (formats.VIDEO, "png"): 1.0, (formats.VIDEO, "jpg"): 1.0,
    (formats.VIDEO, "mp3"): 1.1, (formats.VIDEO, "m4a"): 1.1,

    (formats.ARCHIVE, "zip"): 1.4, (formats.ARCHIVE, "tgz"): 1.5, (formats.ARCHIVE, "tbz2"): 2.2,
    (formats.ARCHIVE, "txz"): 2.6, (formats.ARCHIVE, "7z"): 2.6, (formats.ARCHIVE, "tar"): 1.1,
}

RAW_WORK_FACTOR = 2.0

def work_factor(src_ext: str, target_ext: str) -> float:
    """How much hardware this pair costs for its size, as a multiplier."""
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    category = formats.CATEGORY_OF.get(src_ext)
    if src_ext in formats.RAW_FORMATS:

        return RAW_WORK_FACTOR * _WORK_BY_TARGET.get(target_ext, 1.0)
    if (category, target_ext) in _WORK_BY_CATEGORY:
        return _WORK_BY_CATEGORY[(category, target_ext)]
    return _WORK_BY_TARGET.get(target_ext, 1.0)

def estimate_output_bytes(src_ext: str, target_ext: str, in_bytes: int,
                          pages: "int | None" = None) -> int:
    """About how big the result will be. Never exact, and never presented as exact -- see the note above."""
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    if pages and target_ext in _BYTES_PER_PAGE and \
            formats.CATEGORY_OF.get(src_ext) == formats.DOCUMENT:
        return max(1, int(pages * _BYTES_PER_PAGE[target_ext]))
    category = formats.CATEGORY_OF.get(src_ext)
    ratio = _RAW_RATIO.get(target_ext) if src_ext in formats.RAW_FORMATS else None
    if ratio is None:
        ratio = _RATIO_BY_PAIR.get((src_ext, target_ext))
    if ratio is None:
        ratio = _RATIO_BY_CATEGORY.get((category, target_ext))
    if ratio is None:
        ratio = _RATIO_BY_TARGET.get(target_ext, 1.0)
    return max(1, int(in_bytes * ratio))

def billable_bytes(in_bytes: int, out_bytes: int) -> int:
    """What the price is charged on. See BILLABLE."""
    return max(in_bytes, out_bytes) if BILLABLE == "max" else in_bytes + out_bytes

def ocr_job_pages(src_ext: str, target_ext: str, ocr_pages: int = 0, files: int = 1) -> int:
    """How many pages a conversion reads as text (ocr_convert.py): 0 when it reads none, so it is not a text-recognition job at all."""
    import ocr_convert
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    if target_ext not in ocr_convert.WRITES or files > 1:
        return 0
    if src_ext == "pdf":
        counted = max(0, int(ocr_pages or 0))
        return counted if counted <= ocr_convert.OCR_MAX_PAGES else 0
    if src_ext in formats.RAW_FORMATS or src_ext == "svg":
        return 0
    return 1 if formats.category_of(src_ext, False) == formats.IMAGE else 0

_OCR_TEXT_BYTES_PER_PAGE = 4096
_OCR_LAYER_BYTES_PER_PAGE = 10 * 1024

def ocr_limit(src_ext: str, target_ext: str, in_bytes: int, out_bytes: int, read_pages: int,
              paid: bool, pages: "int | None" = None) -> int:
    """The time limit of a job that reads `read_pages` pages as text, from what the quote knows: the file, its estimated result, the pair and the PDF's page count."""
    import jobs
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    if src_ext == "pdf" and target_ext == "txt":
        out_bytes = max(out_bytes, estimate_output_bytes(src_ext, target_ext, in_bytes, pages))
    return jobs.ocr_time_limit(read_pages, paid, billable_bytes(in_bytes, out_bytes),
                               work_factor(src_ext, target_ext))

def _ocr_price(src_ext: str, target_ext: str, in_bytes: int, pages: "int | None",
               read_pages: int) -> tuple:
    """(credits, estimated output bytes) for a conversion that reads text."""
    import jobs
    import ocr_convert
    import pricing
    if target_ext == "txt":
        out_bytes = _OCR_TEXT_BYTES_PER_PAGE * max(pages or 0, read_pages)
    elif src_ext == "pdf":
        out_bytes = in_bytes + _OCR_LAYER_BYTES_PER_PAGE * read_pages
    else:
        out_bytes = int(in_bytes * 1.2) + _OCR_LAYER_BYTES_PER_PAGE
    if billable_bytes(in_bytes, out_bytes) < FREE_UNDER_MB * _MB and read_pages <= ocr_convert.OCR_FREE_PAGES:
        return 0, out_bytes
    return pricing.price(pricing.cost(ocr_limit(src_ext, target_ext, in_bytes, out_bytes, read_pages, True, pages),
                                      jobs.big_send_limit(out_bytes or in_bytes))), out_bytes

def price_for_job(src_ext: str, target_ext: str, in_bytes: int,
                  pages: "int | None" = None, ocr_pages: int = 0, files: int = 1) -> tuple:
    """(credits, estimated output bytes) for one conversion."""
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    reading = ocr_job_pages(src_ext, target_ext, ocr_pages, files)
    if reading:
        return _ocr_price(src_ext, target_ext, in_bytes, pages, reading)
    out_bytes = estimate_output_bytes(src_ext, target_ext, in_bytes, pages)
    return _price(in_bytes, out_bytes, work_factor(src_ext, target_ext)), out_bytes

def _price(in_bytes: int, out_bytes: int, work: float) -> int:
    import jobs
    import pricing
    billable = billable_bytes(in_bytes, out_bytes)
    if billable < FREE_UNDER_MB * _MB:
        return 0
    return pricing.price(pricing.cost(jobs.time_limit_for(billable, work, paid=True),
                                      jobs.big_send_limit(out_bytes or in_bytes)))

def document_pages(path, src_ext: str) -> "int | None":
    """How many pages a document has, read from its index rather than by rendering it."""
    if formats.CATEGORY_OF.get(formats.normalise(src_ext)) != formats.DOCUMENT:
        return None
    try:
        import pymupdf
    except ImportError:
        return None
    try:
        with pymupdf.open(path) as doc:
            return int(doc.page_count)
    except Exception:
        return None

def least_paid_price() -> int:
    """What the cheapest paid conversion costs: the shortest time a paid job is given and the least it may send back."""
    import jobs
    import pricing
    return pricing.price(pricing.cost(jobs.TIME_BASE_S, jobs.SEND_LIMIT_BYTES))

def price_tiers_text(lang: str = "en") -> str:
    """The price list: free under FREE_UNDER_MB, the least a paid conversion costs, one worked example, and the most anything can -- every number worked out by the same rule a quote is."""
    import i18n
    import jobs
    import pricing

    example_mb = min(100, MAX_FILE_MB)
    example, _ = price_for_job("mp4", "mp4", example_mb * _MB)
    most = pricing.price(pricing.cost(jobs.TIME_LIMIT_S, jobs.big_send_limit(MAX_FILE_MB * _MB)))
    lines = [
        "  " + i18n.t(lang, "price_free_upto", mb=FREE_UNDER_MB) + i18n.t(lang, "price_free"),
        "  " + i18n.t(lang, "price_from", price=least_paid_price()),
        "  " + i18n.t(lang, "price_example", mb=example_mb, price=example),
        "  " + i18n.t(lang, "price_at_most", mb=MAX_FILE_MB, price=most),
    ]
    note = "" if BIG_FILES else " " + i18n.t(lang, "price_cloud_api_note")
    lines.append("  " + i18n.t(lang, "price_over", mb=MAX_FILE_MB) + i18n.t(lang, "price_not_supported") + note)
    lines.append("  " + i18n.t(lang, "price_quoted_first"))
    return "\n".join(lines)

_OPENERS_REGISTERED = False

def register_openers() -> None:
    """Teach Pillow the formats that arrive as a plugin."""
    global _OPENERS_REGISTERED
    if _OPENERS_REGISTERED:
        return
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    _OPENERS_REGISTERED = True

_EXIF_ORIENTATION = 0x0112

_ORIENTED_BY_CONTAINER = {"HEIF", "AVIF"}

def upright(img: Image.Image) -> Image.Image:
    """The picture the way up it was taken."""
    if img.format in _ORIENTED_BY_CONTAINER:
        return img
    try:
        orientation = img.getexif().get(_EXIF_ORIENTATION, 1)
    except Exception:
        return img
    if orientation not in (2, 3, 4, 5, 6, 7, 8):
        return img
    from PIL import ImageOps
    turned = ImageOps.exif_transpose(img)
    if turned is not img:
        img.close()
    return turned

def _open_image(path) -> Image.Image:
    register_openers()
    try:
        img = Image.open(path)
        img.load()
        return upright(img)
    except Exception as exc:
        raise ConversionError(f"Couldn't read that as an image: {exc}") from exc

def gif_is_animated(path) -> bool:
    """Whether a GIF, WEBP or APNG actually has more than one frame."""
    try:
        register_openers()
        with Image.open(path) as img:
            return getattr(img, "n_frames", 1) > 1
    except Exception:
        return False

_IMAGE_TARGETS = {
    "png":  ("RGBA", "PNG", {}),
    "jpg":  ("RGB", "JPEG", {"quality": 92}),
    "webp": ("RGBA", "WEBP", {"quality": 92}),
    "bmp":  ("RGB", "BMP", {}),
    "tiff": ("RGB", "TIFF", {"compression": "tiff_lzw"}),
    "avif": ("RGBA", "AVIF", {"quality": 80}),
    "heic": ("RGB", "HEIF", {"quality": 80}),
    "jp2":  ("RGB", "JPEG2000", {"quality_mode": "rates", "quality_layers": [20]}),
    "tga":  ("RGB", "TGA", {}),
    "ppm":  ("RGB", "PPM", {}),
    "qoi":  ("RGB", "QOI", {}),
    "gif":  ("P", "GIF", {}),

    "ico":  ("RGBA", "ICO", {"sizes": [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]}),
    "icns": ("RGBA", "ICNS", {}),
}

def _flatten_onto_white(img: Image.Image) -> Image.Image:
    """A transparent PNG saved as JPEG has to become *something* where it was see-through, and black is the one answer nobody wants."""
    background = Image.new("RGB", img.size, (255, 255, 255))
    rgba = img.convert("RGBA")
    background.paste(rgba, mask=rgba.split()[-1])
    return background

def convert_image(in_path, target_ext: str, out_path) -> None:
    target_ext = formats.normalise(target_ext)
    if target_ext not in _IMAGE_TARGETS:
        raise ConversionError(f"Unsupported image target format: {target_ext}")
    save_image(_open_image(in_path), target_ext, out_path)

def save_image(img: Image.Image, target_ext: str, out_path) -> None:
    """Write a picture that is already open as `target_ext`, by the table above, and close it."""
    target_ext = formats.normalise(target_ext)
    spec = _IMAGE_TARGETS.get(target_ext)
    if spec is None:
        img.close()
        raise ConversionError(f"Unsupported image target format: {target_ext}")
    mode, pillow_format, kwargs = spec
    register_openers()

    try:
        if mode == "RGB" and img.mode in ("RGBA", "LA", "P"):
            img = _flatten_onto_white(img)
        elif mode == "P":
            img = img.convert("RGB").convert("P", palette=Image.ADAPTIVE)
        else:
            img = img.convert(mode)
        if target_ext == "icns":

            img = img.convert("RGBA").resize((1024, 1024))
        img.save(out_path, format=pillow_format, **kwargs)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Image conversion failed: {exc}") from exc
    finally:
        img.close()

def images_to_pdf(in_paths, out_path) -> int:
    """Every picture given, in order, one to a page."""
    pages: list[Image.Image] = []
    try:
        for path in in_paths:
            img = _open_image(path)
            try:

                if img.mode in ("RGBA", "LA", "P"):
                    pages.append(_flatten_onto_white(img))
                else:
                    pages.append(img.convert("RGB"))
            finally:

                img.close()
        if not pages:
            raise ConversionError("No images to put in the PDF.")
        pages[0].save(
            out_path, format="PDF", save_all=True, append_images=pages[1:],
            resolution=PAGE_DPI,
        )
        return len(pages)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't build the PDF: {exc}") from exc
    finally:
        for page in pages:
            try:
                page.close()
            except Exception:
                pass

FFMPEG_TIMEOUT_S = int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "600"))
FFMPEG_THREADS = os.environ.get("FFMPEG_THREADS", "2")
FFMPEG_CAP_IN = ["-threads", FFMPEG_THREADS, "-filter_threads", FFMPEG_THREADS,
                 "-filter_complex_threads", FFMPEG_THREADS]
FFMPEG_CAP_OUT = ["-threads", FFMPEG_THREADS]

_EVEN = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
_H264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-vf", _EVEN, "-c:a", "aac"]

_FFMPEG_ARGS = {
    "mp4":  _H264 + ["-movflags", "+faststart"],
    "mov":  _H264,
    "mkv":  _H264,
    "avi":  ["-c:v", "mpeg4", "-qscale:v", "5", "-vf", _EVEN, "-c:a", "libmp3lame", "-q:a", "4"],

    "webm": ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-row-mt", "1",
             "-pix_fmt", "yuv420p", "-vf", _EVEN, "-c:a", "libopus"],

    "gif":  ["-vf", "fps=15,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", "-loop", "0"],
    "webp": ["-c:v", "libwebp", "-vf", "fps=15,scale=480:-1:flags=lanczos", "-loop", "0", "-q:v", "70", "-an"],
    "apng": ["-c:v", "apng", "-vf", "fps=15,scale=480:-1:flags=lanczos", "-plays", "0", "-an"],

    "mp3":  ["-vn", "-c:a", "libmp3lame", "-q:a", "2"],
    "wav":  ["-vn", "-c:a", "pcm_s16le"],
    "aiff": ["-vn", "-c:a", "pcm_s16be"],
    "ogg":  ["-vn", "-c:a", "libvorbis", "-q:a", "5"],
    "opus": ["-vn", "-c:a", "libopus", "-b:a", "128k"],
    "m4a":  ["-vn", "-c:a", "aac", "-b:a", "192k"],
    "aac":  ["-vn", "-c:a", "aac", "-b:a", "192k"],
    "flac": ["-vn", "-c:a", "flac"],
    "wma":  ["-vn", "-c:a", "wmav2", "-b:a", "192k"],
    "ac3":  ["-vn", "-c:a", "ac3", "-b:a", "192k"],
    "srt":  ["-c:s", "srt"],
    "vtt":  ["-c:s", "webvtt"],
    "ass":  ["-c:s", "ass"],

    "png":  ["-frames:v", "1", "-an"],
    "jpg":  ["-frames:v", "1", "-q:v", "2", "-an"],
}

def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

_HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
_TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
_SDR_VIDEO = {"mp4", "mov", "mkv", "avi", "webm"}
_SDR_TARGETS = _SDR_VIDEO | {"gif", "webp", "apng", "png", "jpg"}
_ANIMATED_SCALE = "fps=15,scale=480:-1:flags=lanczos"
_filters_seen: "dict[str, bool]" = {}

def _ffmpeg_has_filters(*names: str) -> bool:
    """Whether this ffmpeg was built with every one of these filters. Asked once per process."""
    if not _filters_seen:
        try:
            listing = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True,
                                     text=True, timeout=20).stdout
        except Exception:
            listing = ""
        for line in listing.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                _filters_seen[parts[1]] = True
        _filters_seen.setdefault("", False)
    return all(_filters_seen.get(name) for name in names)

def _is_hdr(in_path) -> bool:
    """Whether the first video stream is on an HDR curve, from ffprobe."""
    if shutil.which("ffprobe") is None:
        return False
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
             "-of", "default=noprint_wrappers=1:nokey=1", str(in_path)],
            capture_output=True, text=True, timeout=20)
    except Exception:
        return False
    return (probe.stdout or "").strip().lower() in _HDR_TRANSFERS

def _tonemapped(args: list, target_ext: str) -> list:
    """The same arguments, with the tonemap in the video filter -- after the downscale for the small animated targets, where it costs a fraction of what it would at 4K, and first everywhere else -- and the result labelled as the BT.709 it now is."""
    args = list(args)
    if "-vf" in args:
        at = args.index("-vf") + 1
        chain = args[at]
        if chain.startswith(_ANIMATED_SCALE):
            args[at] = _ANIMATED_SCALE + "," + _TONEMAP + chain[len(_ANIMATED_SCALE):]
        else:
            args[at] = _TONEMAP + "," + chain
    else:
        args = ["-vf", _TONEMAP] + args
    if target_ext in _SDR_VIDEO:
        args += ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    return args

FIT_PIXELS = int(os.environ.get("CONVERT_VIDEO_FIT_PIXELS") or 2_900_000)
HUGE_PIXELS = 3840 * 2160
FIT_BOX = 1920
_FIT_FILTER = (f"scale={FIT_BOX}:{FIT_BOX}:force_original_aspect_ratio=decrease:"
               "force_divisible_by=2:flags=bicubic")

def _quarter_turn(stream: dict) -> bool:
    """Whether the player turns this stream a quarter (90 or 270 degrees) before showing it, which swaps its width and its height."""
    turn = None
    for data in stream.get("side_data_list") or ():
        if isinstance(data, dict) and "rotation" in data:
            turn = data["rotation"]
            break
    if turn is None:
        turn = (stream.get("tags") or {}).get("rotate")
    try:
        turn = float(turn)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(turn):
        return False
    return round(turn / 90) % 2 == 1

def video_geometry(in_path) -> "tuple[int, int, bool] | None":
    """(width, height, is HDR) of the first video stream, from one ffprobe call -- or None for no video stream, no ffprobe, or an answer that makes no sense."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", str(in_path)],
            capture_output=True, text=True, timeout=20)
        stream = json.loads(probe.stdout or "{}")["streams"][0]
        width, height = int(stream["width"]), int(stream["height"])
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    if _quarter_turn(stream):
        width, height = height, width
    return width, height, str(stream.get("color_transfer") or "").lower() in _HDR_TRANSFERS

def video_needs_fit(width: int, height: int, hdr: bool, target_ext: str) -> bool:
    """Whether this video is brought down to the 1920x1920 box for this target. Pure."""
    if not FIT_PIXELS or width * height <= FIT_PIXELS:
        return False
    target_ext = formats.normalise(target_ext)
    if target_ext not in _SDR_VIDEO:
        return False
    return hdr or target_ext == "webm" or width * height > HUGE_PIXELS

def fitted_size(width: int, height: int) -> "tuple[int, int]":
    """What the box makes of this size: never larger, even numbers, same shape."""
    scale = min(1.0, FIT_BOX / width, FIT_BOX / height)
    return max(2, int(width * scale) // 2 * 2), max(2, int(height * scale) // 2 * 2)

def _fitted(args: list) -> list:
    """The same arguments with the fit in front of whatever video filter they already have -- before the tonemap, because that is the expensive part."""
    args = list(args)
    if "-vf" in args:
        at = args.index("-vf") + 1
        args[at] = _FIT_FILTER + "," + args[at]
        return args
    return ["-vf", _FIT_FILTER] + args

def video_fit_note(in_path) -> "tuple[str, int, int, int, int] | None":
    """What to tell somebody about a video before they pay: None, or (which, width, height, fitted width, fitted height) with `which` being "hdr" (HDR: every video target is brought down), "huge" (not HDR, but bigger than 4K: every video target is brought down) or "big" (only WEBM is)."""
    geometry = video_geometry(in_path)
    if geometry is None:
        return None
    width, height, hdr = geometry
    if not FIT_PIXELS or width * height <= FIT_PIXELS:
        return None
    fw, fh = fitted_size(width, height)
    which = "hdr" if hdr else ("huge" if width * height > HUGE_PIXELS else "big")
    return (which, width, height, fw, fh)

def convert_media_ffmpeg(in_path, target_ext: str, out_path) -> None:
    target_ext = formats.normalise(target_ext)
    args = _FFMPEG_ARGS.get(target_ext)
    if args is None:
        raise ConversionError(f"Unsupported target format: {target_ext}")
    if not _ffmpeg_available():
        raise ConversionError(
            "ffmpeg isn't installed on this host, so video, audio and subtitle "
            "conversion isn't available."
        )
    if not os.path.getsize(in_path):
        raise ConversionError("That file came through empty -- try sending it again.")
    hdr = target_ext in _SDR_TARGETS and _is_hdr(in_path)
    if hdr and _ffmpeg_has_filters("zscale", "tonemap"):
        args = _tonemapped(args, target_ext)
    if target_ext in _SDR_VIDEO and FIT_PIXELS:
        geometry = video_geometry(in_path)
        if geometry and video_needs_fit(geometry[0], geometry[1], hdr or geometry[2], target_ext):
            args = _fitted(args)

    duration = _media_duration(in_path) if PROGRESS is not None else None
    if duration:
        _ffmpeg_with_progress(in_path, args, out_path, duration)
        return

    cmd = ["ffmpeg", "-nostdin", "-y", *FFMPEG_CAP_IN, "-i", str(in_path)]
    cmd += args + FFMPEG_CAP_OUT
    cmd.append(str(out_path))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise ConversionError(
            f"Conversion took longer than {FFMPEG_TIMEOUT_S}s and was stopped. "
            "Try a shorter or smaller file."
        ) from None
    if _killed(proc.returncode):
        raise OutOfMemory(f"ffmpeg was killed (exit {proc.returncode}), for memory: "
                          f"{(proc.stderr or '').strip()[-300:]}")
    if proc.returncode != 0 or not os.path.exists(out_path):
        note = (proc.stderr or "").strip()[-500:] or "ffmpeg failed with no output"
        raise ConversionError(f"Conversion failed: {note}")

def _media_duration(in_path) -> "float | None":
    """How long the file plays, in seconds, from ffprobe -- or None, and the progress bar simply does not appear."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(in_path)],
            capture_output=True, text=True, timeout=20)
        seconds = float((probe.stdout or "").strip().splitlines()[0])
    except Exception:
        return None
    return seconds if seconds > 0 else None

def _ffmpeg_with_progress(in_path, args, out_path, duration: float) -> None:
    """The same ffmpeg run, reading its -progress output as it goes."""
    import tempfile
    import time
    cmd = ["ffmpeg", "-nostdin", "-y", *FFMPEG_CAP_IN, "-progress", "pipe:1", "-nostats",
           "-i", str(in_path)]
    cmd += args + FFMPEG_CAP_OUT
    cmd.append(str(out_path))
    deadline = time.monotonic() + FFMPEG_TIMEOUT_S
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errors, text=True)
        try:
            for line in proc.stdout:
                key, _, value = line.strip().partition("=")
                if key in ("out_time_us", "out_time_ms") and value.isdigit():
                    report(int(value) / 1_000_000, duration)
                if time.monotonic() > deadline:
                    proc.kill()
                    proc.wait()
                    raise ConversionError(
                        f"Conversion took longer than {FFMPEG_TIMEOUT_S}s and was stopped. "
                        "Try a shorter or smaller file.")
            proc.wait(timeout=max(1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise ConversionError(
                f"Conversion took longer than {FFMPEG_TIMEOUT_S}s and was stopped. "
                "Try a shorter or smaller file.") from None
        if proc.returncode != 0 or not os.path.exists(out_path):
            errors.seek(0)
            note = errors.read().decode("utf-8", "replace").strip()[-500:] or "ffmpeg failed with no output"
            if _killed(proc.returncode):
                raise OutOfMemory(f"ffmpeg was killed (exit {proc.returncode}), for memory: {note[-300:]}")
            raise ConversionError(f"Conversion failed: {note}")

def _reject_overlong_animation(in_path, src_ext: str) -> None:
    """An animation with more frames than MAX_FRAMES is refused up front."""
    if src_ext not in ("gif", "apng", "webp"):
        return
    try:
        register_openers()
        with Image.open(in_path) as img:
            frames = getattr(img, "n_frames", 1)
    except Exception:
        return
    if frames > MAX_FRAMES:
        raise ConversionError(
            f"That animation has {frames} frames, over the {MAX_FRAMES}-frame "
            "limit. Try a shorter clip."
        )

def zip_files(paths, out_path) -> None:
    """One page per entry, deflated."""
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in paths:
                archive.write(path, arcname=Path(path).name)
    except Exception as exc:
        raise ConversionError(f"Couldn't package the results: {exc}") from exc

def _out(work_dir, stem: str, ext: str) -> Path:
    return Path(work_dir) / f"{stem}.{ext}"

def convert(in_paths, src_ext: str, target_ext: str, work_dir, stem: str = "converted",
            ocr_lang: str = "", ocr_pages: int = 0) -> Result:
    """Everything the bot converts, dispatched by what the source is."""
    in_paths = [str(path) for path in in_paths]
    if not in_paths:
        raise ConversionError("Nothing to convert.")
    src_ext = formats.normalise(src_ext)
    target_ext = formats.normalise(target_ext)
    category = formats.category_of(src_ext)
    work_dir = Path(work_dir)

    import ocr_convert
    if len(in_paths) > 1:
        if target_ext in ocr_convert.WRITES and (target_ext == "ocrpdf" or category == formats.IMAGE):

            raise ConversionError("Text is read from one picture or PDF at a time, not from an album.")
        return _convert_batch(in_paths, src_ext, target_ext, work_dir, stem)

    in_path = in_paths[0]
    out_path = _out(work_dir, stem, target_ext)

    if src_ext in formats.ANIMATED_CAPABLE:
        category = formats.category_of(src_ext, gif_is_animated(in_path))

    if target_ext in ocr_convert.WRITES:

        reading = ocr_job_pages(src_ext, target_ext, ocr_pages, len(in_paths))
        picture = category == formats.IMAGE and src_ext not in formats.RAW_FORMATS and src_ext != "svg"
        if picture or (src_ext == "pdf" and (reading or target_ext == "ocrpdf")):
            return ocr_convert.convert(in_path, src_ext, target_ext, work_dir, stem,
                                       lang=ocr_lang, max_scanned=reading)
        if target_ext == "ocrpdf":
            raise ConversionError(f"A .{src_ext} file can't be turned into a searchable PDF.")

    import office_convert
    if office_convert.handles(src_ext, target_ext):
        return office_convert.convert(in_path, src_ext, target_ext, work_dir, stem)

    if category == formats.IMAGE and src_ext in formats.RAW_FORMATS:
        import raw_convert
        raw_convert.convert(in_path, src_ext, target_ext, out_path)
        return Result(out_path)

    if category == formats.IMAGE and src_ext != "svg":
        if target_ext == "pdf":
            images_to_pdf([in_path], out_path)
        elif target_ext in _IMAGE_TARGETS:
            convert_image(in_path, target_ext, out_path)
        else:

            convert_media_ffmpeg(in_path, target_ext, out_path)
        return Result(out_path)

    if category in (formats.VIDEO, formats.AUDIO, formats.SUBTITLE):
        _reject_overlong_animation(in_path, src_ext)
        if category == formats.SUBTITLE and target_ext == "txt":
            import data_convert
            data_convert.subtitle_to_text(in_path, src_ext, out_path)
            return Result(out_path)
        convert_media_ffmpeg(in_path, target_ext, out_path)
        return Result(out_path)

    if category == formats.DOCUMENT or src_ext == "svg":
        import doc_convert
        return doc_convert.convert(in_path, src_ext, target_ext, work_dir, stem)

    if category == formats.DATA:
        import data_convert
        return data_convert.convert(in_path, src_ext, target_ext, work_dir, stem)

    if category == formats.ARCHIVE:
        import archive_convert
        return archive_convert.convert(in_path, src_ext, target_ext, work_dir, stem)

    raise ConversionError(f"Nothing here converts a .{src_ext} file.")

def _convert_batch(in_paths, src_ext, target_ext, work_dir, stem) -> Result:
    """Several files at once: one PDF, or one zip of individual results."""
    if len(in_paths) > formats.MAX_BATCH:
        raise ConversionError(
            f"That is {len(in_paths)} files, over the {formats.MAX_BATCH}-file "
            "limit for one conversion."
        )
    if target_ext == "pdf" and formats.category_of(src_ext) == formats.IMAGE:
        out_path = _out(work_dir, stem, "pdf")
        pages = images_to_pdf(in_paths, out_path)
        return Result(out_path, items=pages)

    produced = []
    for index, path in enumerate(in_paths, start=1):
        report(index - 1, len(in_paths))
        one = convert([path], src_ext, target_ext, work_dir, f"{stem}-{index:02d}")
        produced.append(one.path)
    report(len(in_paths), len(in_paths))
    out_path = _out(work_dir, stem, "zip")
    zip_files(produced, out_path)
    for path in produced:
        Path(path).unlink(missing_ok=True)
    return Result(out_path, items=len(produced), zipped=True)

# ─── module: convert_bot.data_convert ────────────────────────────────────────
"""Structured data: CSV, TSV, JSON, YAML, XLSX and XML -- and the plain-text form of a subtitle file, which has nowhere better to live."""
from __future__ import annotations

import csv
import html as html_module
import io
import json
import re
from pathlib import Path
from typing import NamedTuple

import formats
from convert_utils import Result, ConversionError, zip_files

class Table(NamedTuple):
    headers: list[str]
    rows: list[list]

WRITES = frozenset({"json", "yaml", "xlsx", "csv", "tsv", "md", "html", "pdf", "txt"})

_DELIMITERS = {"csv": ",", "tsv": "\t"}

def _read_text(in_path) -> str:
    try:
        return Path(in_path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        raise ConversionError(f"Couldn't read that file: {exc}") from exc

def _check_size(rows: int, columns: int) -> None:
    if rows > formats.MAX_ROWS:
        raise ConversionError(
            f"That is {rows:,} rows, over the {formats.MAX_ROWS:,}-row limit "
            "for one conversion."
        )
    if rows * max(columns, 1) > formats.MAX_CELLS:
        raise ConversionError(
            f"That is about {rows * columns:,} cells, over the "
            f"{formats.MAX_CELLS:,}-cell limit for one conversion."
        )

class _Budget:
    """What has been read so far, checked as it is read."""

    def __init__(self):
        self.rows = 0
        self.cells = 0

    def add(self, row) -> None:
        self.rows += 1
        self.cells += len(row)
        if self.rows > formats.MAX_ROWS + 1:
            raise ConversionError(
                f"That is over the {formats.MAX_ROWS:,}-row limit for one conversion.")
        if self.cells > formats.MAX_CELLS:
            raise ConversionError(
                f"That is over the {formats.MAX_CELLS:,}-cell limit for one conversion.")

def _read_delimited(in_path, src_ext: str) -> Table:
    text = _read_text(in_path)
    reader = csv.reader(io.StringIO(text), delimiter=_DELIMITERS[src_ext])
    rows = []
    budget = _Budget()
    try:
        for row in reader:
            budget.add(row)
            rows.append(row)
    except csv.Error as exc:

        raise ConversionError(f"That isn't a CSV this can read: {exc}.") from exc
    if not rows:
        raise ConversionError("That file is empty.")
    headers = [str(cell) for cell in rows[0]]
    _check_size(len(rows) - 1, len(headers))
    return Table(headers, rows[1:])

def _read_xlsx(in_path) -> list[tuple[str, Table]]:
    """Every sheet in the workbook, named."""
    try:
        import openpyxl
    except ImportError as exc:
        raise ConversionError("Spreadsheets aren't supported on this host.") from exc
    try:

        book = openpyxl.load_workbook(in_path, read_only=True, data_only=True)
    except Exception as exc:
        raise ConversionError(f"Couldn't read that spreadsheet: {exc}") from exc
    sheets = []
    try:
        for sheet in book.worksheets:

            rows = []
            budget = _Budget()
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    budget.add(row)
                    rows.append(list(row))
            if not rows:
                continue
            headers = ["" if cell is None else str(cell) for cell in rows[0]]
            _check_size(len(rows) - 1, len(headers))
            sheets.append((sheet.title, Table(headers, rows[1:])))
    finally:
        book.close()
    if not sheets:
        raise ConversionError("That spreadsheet has no data in it.")
    return sheets

def _read_json(in_path):
    try:
        return json.loads(_read_text(in_path))
    except json.JSONDecodeError as exc:
        raise ConversionError(f"That isn't valid JSON: line {exc.lineno}, {exc.msg}.") from exc
    except RecursionError as exc:
        raise ConversionError("That JSON is nested too deeply to convert.") from exc

def _refuse_expansion(obj) -> None:
    """Refuse a YAML document that is small on disk and enormous once read."""
    seen = 0
    stack = [obj]
    while stack:
        node = stack.pop()
        seen += 1
        if seen > formats.MAX_CELLS:
            raise ConversionError(
                "That YAML repeats itself through anchors and aliases until it "
                f"would come to more than {formats.MAX_CELLS:,} values, which is "
                "over the limit for one conversion.")
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, (list, tuple)):
            stack.extend(node)

def _read_yaml(in_path):
    try:
        import yaml
    except ImportError as exc:
        raise ConversionError("YAML isn't supported on this host.") from exc
    try:

        obj = yaml.safe_load(_read_text(in_path))
    except Exception as exc:
        raise ConversionError(f"That isn't valid YAML: {exc}") from exc
    _refuse_expansion(obj)
    return obj

def _element_to_object(element):
    """An XML element as dicts and lists, attributes prefixed with `@`."""
    node = {}
    for name, value in element.attrib.items():
        node[f"@{name}"] = value
    for child in element:
        value = _element_to_object(child)
        if child.tag in node:
            if not isinstance(node[child.tag], list):
                node[child.tag] = [node[child.tag]]
            node[child.tag].append(value)
        else:
            node[child.tag] = value
    text = (element.text or "").strip()
    if text:
        if node:
            node["#text"] = text
        else:
            return text
    return node or None

def _read_xml(in_path):
    try:
        from defusedxml.ElementTree import parse
    except ImportError as exc:
        raise ConversionError("XML isn't supported on this host.") from exc
    try:
        root = parse(str(in_path)).getroot()
    except Exception as exc:
        raise ConversionError(f"That isn't XML this can read: {exc}") from exc
    try:
        return {root.tag: _element_to_object(root)}
    except RecursionError as exc:
        raise ConversionError("That XML is nested too deeply to convert.") from exc

def _load(in_path, src_ext: str):
    """(object, sheets) -- one of the two is always None."""
    if src_ext in _DELIMITERS:
        return None, [("", _read_delimited(in_path, src_ext))]
    if src_ext == "xlsx":
        return None, _read_xlsx(in_path)
    if src_ext == "json":
        return _read_json(in_path), None
    if src_ext == "yaml":
        return _read_yaml(in_path), None
    if src_ext == "xml":
        return _read_xml(in_path), None
    raise ConversionError(f"Nothing here reads a .{src_ext} file.")

def _cell(value):
    """What a nested value looks like in a cell that can only hold a string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value

def as_table(obj) -> Table:
    """A nested object as one table, or a refusal that says why not."""
    if isinstance(obj, list) and obj and all(isinstance(item, dict) for item in obj):
        headers: list[str] = []
        for item in obj:
            for key in item:
                if key not in headers:
                    headers.append(key)
        _check_size(len(obj), len(headers))
        return Table(headers, [[_cell(item.get(key)) for key in headers] for item in obj])

    if isinstance(obj, list) and obj and all(isinstance(item, (list, tuple)) for item in obj):
        width = max(len(row) for row in obj)
        _check_size(len(obj), width)
        headers = [f"column {index + 1}" for index in range(width)]
        return Table(headers, [[_cell(cell) for cell in row] + [""] * (width - len(row))
                               for row in obj])

    if isinstance(obj, dict):

        lists = [value for value in obj.values()
                 if isinstance(value, list) and value and all(isinstance(item, dict) for item in value)]
        if len(lists) == 1:
            return as_table(lists[0])
        _check_size(len(obj), 2)
        return Table(["key", "value"], [[key, _cell(value)] for key, value in obj.items()])

    raise ConversionError(
        "That file isn't shaped like a table -- it has no list of records in "
        "it to make rows out of. JSON, YAML and XML will still convert to "
        "each other, or to PDF."
    )

def _table_to_object(table: Table) -> list[dict]:
    return [dict(zip(table.headers, row)) for row in table.rows]

def _object_of(obj, sheets) -> object:
    """Whatever was loaded, as a nested object."""
    if obj is not None:
        return obj
    if len(sheets) == 1:
        return _table_to_object(sheets[0][1])
    return {name or f"sheet {index + 1}": _table_to_object(table)
            for index, (name, table) in enumerate(sheets)}

def _tables_of(obj, sheets) -> list[tuple[str, Table]]:
    """Whatever was loaded, as one or more tables."""
    if sheets is not None:
        return sheets
    return [("", as_table(obj))]

def _write_delimited(table: Table, out_path, target_ext: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=_DELIMITERS[target_ext])
        writer.writerow(table.headers)
        writer.writerows(table.rows)

def _write_xlsx(sheets: list[tuple[str, Table]], out_path) -> None:
    try:
        import openpyxl
    except ImportError as exc:
        raise ConversionError("Spreadsheets aren't supported on this host.") from exc
    book = openpyxl.Workbook()
    book.remove(book.active)
    for index, (name, table) in enumerate(sheets):

        title = re.sub(r"[:\\/?*\[\]]", "-", name or f"Sheet{index + 1}")[:31]
        sheet = book.create_sheet(title=title)
        sheet.append(table.headers)
        for row in table.rows:
            sheet.append([_cell(value) for value in row])
    book.save(out_path)

def _markdown_table(table: Table) -> str:
    def escape(value):
        return str("" if value is None else value).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(escape(head) for head in table.headers) + " |",
             "| " + " | ".join("---" for _ in table.headers) + " |"]
    for row in table.rows:
        cells = [escape(value) for value in row]
        cells += [""] * (len(table.headers) - len(cells))
        lines.append("| " + " | ".join(cells[:len(table.headers)]) + " |")
    return "\n".join(lines)

def _html_table(table: Table) -> str:
    def cell(value, tag):
        return f"<{tag}>{html_module.escape(str('' if value is None else value))}</{tag}>"

    head = "<tr>" + "".join(cell(head, "th") for head in table.headers) + "</tr>"
    body = "".join(
        "<tr>" + "".join(cell(value, "td") for value in row) + "</tr>" for row in table.rows
    )
    return f"<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\">\n{head}\n{body}\n</table>"

def _write_yaml(obj, out_path) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise ConversionError("YAML isn't supported on this host.") from exc
    with open(out_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(obj, handle, allow_unicode=True, sort_keys=False, default_flow_style=False)

def convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str = "converted") -> Result:
    try:
        return _convert(in_path, src_ext, target_ext, work_dir, stem)
    except RecursionError as exc:

        raise ConversionError("That file is nested too deeply to convert.") from exc

def _convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str) -> Result:
    src_ext = formats.normalise(src_ext)
    target_ext = formats.normalise(target_ext)
    work_dir = Path(work_dir)
    out_path = work_dir / f"{stem}.{target_ext}"
    obj, sheets = _load(in_path, src_ext)

    if target_ext == "json":
        out_path.write_text(
            json.dumps(_object_of(obj, sheets), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return Result(out_path)

    if target_ext == "yaml":
        _write_yaml(json.loads(json.dumps(_object_of(obj, sheets), default=str)), out_path)
        return Result(out_path)

    if target_ext == "xlsx":
        _write_xlsx(_tables_of(obj, sheets), out_path)
        return Result(out_path)

    if target_ext in _DELIMITERS:
        tables = _tables_of(obj, sheets)
        if len(tables) == 1:
            _write_delimited(tables[0][1], out_path, target_ext)
            return Result(out_path)

        produced = []
        for index, (name, table) in enumerate(tables, start=1):
            safe = re.sub(r"[^\w.-]", "_", name) or f"sheet{index}"
            path = work_dir / f"{safe}.{target_ext}"
            _write_delimited(table, path, target_ext)
            produced.append(path)
        archive = work_dir / f"{stem}.zip"
        zip_files(produced, archive)
        for path in produced:
            path.unlink(missing_ok=True)
        return Result(archive, items=len(produced), zipped=True)

    if target_ext in ("md", "html", "pdf"):
        tables = _tables_of(obj, sheets)
        if target_ext == "md":
            parts = []
            for name, table in tables:
                parts.append(f"## {name}\n" if name and len(tables) > 1 else "")
                parts.append(_markdown_table(table))
            out_path.write_text("\n".join(part for part in parts if part), encoding="utf-8")
            return Result(out_path)
        body = "\n".join(
            (f"<h2>{html_module.escape(name)}</h2>" if name and len(tables) > 1 else "")
            + _html_table(table)
            for name, table in tables
        )
        if target_ext == "html":
            out_path.write_text("<!doctype html>\n<meta charset=\"utf-8\">\n" + body, encoding="utf-8")
            return Result(out_path)
        import doc_convert
        doc_convert.html_to_pdf(body, out_path)
        return Result(out_path)

    if target_ext == "txt":
        out_path.write_text(
            json.dumps(_object_of(obj, sheets), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return Result(out_path)

    raise ConversionError(f"Nothing here converts a .{src_ext} to .{target_ext}.")

_TAG_RE = re.compile(r"<[^>]+>|\{[^}]*\}")
_TIMING_RE = re.compile(r"^\s*[\d:.,]+\s*-->\s*[\d:.,]+")
_INDEX_RE = re.compile(r"^\s*\d+\s*$")
_ASS_EVENT_RE = re.compile(r"^Dialogue:\s*(?:[^,]*,){9}(.*)$")

def subtitle_to_text(in_path, src_ext: str, out_path) -> None:
    source = _read_text(in_path)
    lines: list[str] = []
    if formats.normalise(src_ext) == "ass":
        for line in source.splitlines():
            match = _ASS_EVENT_RE.match(line.strip())
            if match:

                lines.append(_TAG_RE.sub("", match.group(1)).replace("\\N", " ").strip())
    else:
        for line in source.splitlines():
            stripped = line.strip()
            if (not stripped or _INDEX_RE.match(stripped) or _TIMING_RE.match(stripped)
                    or stripped.upper().startswith(("WEBVTT", "NOTE ", "STYLE"))):
                continue
            lines.append(_TAG_RE.sub("", stripped).strip())
    text = "\n".join(line for line in lines if line)
    if not text:
        raise ConversionError("There were no subtitle lines in that file.")
    Path(out_path).write_text(text, encoding="utf-8")

# ─── module: convert_bot.doc_convert ─────────────────────────────────────────
"""Documents: PDF, EPUB, MOBI, FB2, CBZ, XPS, DOCX, Markdown, HTML, plain text -- and SVG, which is a document in every way that matters here."""
from __future__ import annotations

import html as html_module
import io
from pathlib import Path

import formats
from convert_utils import Result, ConversionError, PAGE_DPI, convert_image, report, zip_files

_MUPDF_NATIVE = ("pdf", "epub", "mobi", "fb2", "cbz", "xps", "svg", "html", "txt")

WRITES = frozenset({"pdf", "png", "jpg", "webp", "tiff", "svg", "txt", "html", "md", "docx"})

_PAGE = "a4"
_MARGIN = 40

def _fitz():
    try:
        import pymupdf
        return pymupdf
    except ImportError as exc:
        raise ConversionError(
            "The document engine isn't installed on this host, so PDF and "
            "e-book conversion isn't available."
        ) from exc

def _open(in_path, src_ext: str):
    """The source as a PyMuPDF document, whatever it started as."""
    pymupdf = _fitz()
    if src_ext in _MUPDF_NATIVE:
        try:
            return pymupdf.open(in_path)
        except Exception as exc:
            raise ConversionError(f"Couldn't read that {src_ext.upper()}: {exc}") from exc

    pdf_bytes = _to_pdf_bytes(in_path, src_ext)
    return pymupdf.open(stream=pdf_bytes, filetype="pdf")

def _page_count(doc) -> int:
    count = doc.page_count
    if count > formats.MAX_PAGES:
        raise ConversionError(
            f"That document is {count} pages, over the {formats.MAX_PAGES}-page "
            "limit for one conversion. Split it and send the part you need."
        )
    return count

def _check_page_sizes(doc, pages: int) -> None:
    """Refuse a document with a page too big to draw, before drawing any."""
    for index in range(pages):
        rect = doc[index].rect
        megapixels = (rect.width * PAGE_DPI / 72) * (rect.height * PAGE_DPI / 72) / 1_000_000
        if megapixels > formats.MAX_PAGE_MEGAPIXELS:
            raise ConversionError(
                f"Page {index + 1} is {rect.width / 72:.0f} by {rect.height / 72:.0f} inches, "
                f"which would be {megapixels:,.0f} megapixels as a picture -- over the "
                f"{formats.MAX_PAGE_MEGAPIXELS}-megapixel limit for one page."
            )

def _docx_to_html(in_path) -> str:
    try:
        import mammoth
    except ImportError as exc:
        raise ConversionError("Word documents aren't supported on this host.") from exc
    try:
        with open(in_path, "rb") as handle:
            return mammoth.convert_to_html(handle).value
    except Exception as exc:
        raise ConversionError(f"Couldn't read that .docx: {exc}") from exc

def _md_to_html(in_path) -> str:
    try:
        import markdown
    except ImportError as exc:
        raise ConversionError("Markdown isn't supported on this host.") from exc
    try:
        text = Path(in_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ConversionError(f"Couldn't read that file: {exc}") from exc
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])

def _source_html(in_path, src_ext: str) -> str:
    if src_ext == "docx":
        return _docx_to_html(in_path)
    if src_ext == "md":
        return _md_to_html(in_path)
    if src_ext == "html":
        return Path(in_path).read_text(encoding="utf-8", errors="replace")
    if src_ext == "txt":
        body = html_module.escape(Path(in_path).read_text(encoding="utf-8", errors="replace"))
        return f"<pre>{body}</pre>"

    doc = _open(in_path, src_ext)
    try:
        pages = _page_count(doc)
        return "\n".join(doc[index].get_text("html") for index in range(pages))
    finally:
        doc.close()

def html_to_pdf(source_html: str, out_path) -> None:
    """Lay HTML out onto pages and write a PDF."""
    pymupdf = _fitz()
    try:
        story = pymupdf.Story(html=f"<html><body>{source_html}</body></html>")
        page_rect = pymupdf.paper_rect(_PAGE)
        frame = page_rect + (_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)

        writer = pymupdf.DocumentWriter(out_path if hasattr(out_path, "write") else str(out_path))
        more = 1
        pages = 0
        while more:
            device = writer.begin_page(page_rect)
            more, _ = story.place(frame)
            story.draw(device)
            writer.end_page()
            pages += 1
            if pages > formats.MAX_PAGES:
                writer.close()
                raise ConversionError(
                    f"That comes to more than {formats.MAX_PAGES} pages, which is "
                    "over the limit for one conversion."
                )
        writer.close()
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't lay that out as a PDF: {exc}") from exc

def _to_pdf_bytes(in_path, src_ext: str) -> bytes:
    """A PDF of the source, in memory."""
    _fitz()
    if src_ext in _MUPDF_NATIVE:
        doc = _open(in_path, src_ext)
        try:
            _page_count(doc)
            if src_ext == "pdf":
                return doc.tobytes()
            return doc.convert_to_pdf()
        finally:
            doc.close()
    buffer = io.BytesIO()
    html_to_pdf(_source_html(in_path, src_ext), buffer)
    return buffer.getvalue()

def _to_pdf(in_path, src_ext: str, out_path) -> None:
    if src_ext in ("docx", "md"):
        html_to_pdf(_source_html(in_path, src_ext), out_path)
        return
    doc = _open(in_path, src_ext)
    try:
        _page_count(doc)
        Path(out_path).write_bytes(doc.convert_to_pdf())
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't write that as a PDF: {exc}") from exc
    finally:
        doc.close()

def _render_pages(in_path, src_ext: str, target_ext: str, work_dir, stem: str) -> list[Path]:
    """One picture per page, at PAGE_DPI."""
    doc = _open(in_path, src_ext)
    produced: list[Path] = []
    try:
        pages = _page_count(doc)
        _check_page_sizes(doc, pages)
        for index in range(pages):
            report(index, pages)
            pixmap = doc[index].get_pixmap(dpi=PAGE_DPI)
            png_path = Path(work_dir) / f"{stem}-page{index + 1:03d}.png"
            pixmap.save(str(png_path))
            if target_ext == "png":
                produced.append(png_path)
                continue
            out_path = png_path.with_suffix(f".{target_ext}")
            try:
                convert_image(png_path, target_ext, out_path)
            finally:
                png_path.unlink(missing_ok=True)
            produced.append(out_path)
    except ConversionError:
        for path in produced:
            path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        for path in produced:
            path.unlink(missing_ok=True)
        raise ConversionError(f"Couldn't render that document: {exc}") from exc
    finally:
        doc.close()
    return produced

def _page_svgs(in_path, src_ext: str, work_dir, stem: str) -> list[Path]:
    """A PDF page as SVG keeps its vectors, which is the whole reason to ask for one rather than a PNG."""
    doc = _open(in_path, src_ext)
    produced: list[Path] = []
    try:
        pages = _page_count(doc)
        for index in range(pages):
            report(index, pages)
            path = Path(work_dir) / f"{stem}-page{index + 1:03d}.svg"
            path.write_text(doc[index].get_svg_image(), encoding="utf-8")
            produced.append(path)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't write that page as SVG: {exc}") from exc
    finally:
        doc.close()
    return produced

def _pack(produced: list[Path], target_ext: str, work_dir, stem: str) -> Result:
    """One page comes back as itself; many come back as a zip."""
    if not produced:
        raise ConversionError("That document had no pages in it.")
    if len(produced) == 1:
        final = Path(work_dir) / f"{stem}.{target_ext}"
        produced[0].replace(final)
        return Result(final, items=1)
    archive = Path(work_dir) / f"{stem}.zip"
    zip_files(produced, archive)
    for path in produced:
        path.unlink(missing_ok=True)
    return Result(archive, items=len(produced), zipped=True)

def _to_text(in_path, src_ext: str) -> str:
    if src_ext == "docx":
        try:
            import mammoth
            with open(in_path, "rb") as handle:
                return mammoth.extract_raw_text(handle).value
        except ImportError as exc:
            raise ConversionError("Word documents aren't supported on this host.") from exc
        except Exception as exc:
            raise ConversionError(f"Couldn't read that .docx: {exc}") from exc
    if src_ext == "md":

        doc = _open(in_path, src_ext)
        try:
            return "\n".join(doc[index].get_text() for index in range(_page_count(doc)))
        finally:
            doc.close()
    doc = _open(in_path, src_ext)
    try:
        return "\n".join(doc[index].get_text() for index in range(_page_count(doc)))
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't extract the text: {exc}") from exc
    finally:
        doc.close()

_HEADING_RATIO = 1.25
_HEADING_2_RATIO = 1.6

_MIN_IMAGE_PIXELS = 64 * 64

_MAX_IMAGE_PIXELS = 50_000_000
_DOCX_PAGE_WIDTH_INCHES = 6.0

def _docx():
    try:
        import docx
        return docx
    except ImportError as exc:
        raise ConversionError(
            "The Word writer isn't installed on this host, so converting to "
            "DOCX isn't available."
        ) from exc

def _body_size(doc) -> float:
    """The size most of this document's text is set in, which is what makes 'larger than the body' a question with an answer."""
    sizes: dict = {}
    for page in doc:
        for block in page.get_text("dict").get("blocks", ()):
            for line in block.get("lines", ()):
                for span in line.get("spans", ()):
                    text = (span.get("text") or "").strip()
                    if not text:
                        continue
                    size = round(float(span.get("size") or 0), 1)
                    sizes[size] = sizes.get(size, 0) + len(text)
    if not sizes:
        return 0.0
    return max(sizes.items(), key=lambda pair: pair[1])[0]

def _line_text(line) -> str:
    return "".join(span.get("text") or "" for span in line.get("spans", ())).strip()

def _to_docx(in_path, src_ext: str, out_path, work_dir) -> None:
    """Everything the PDF actually says, as a Word document. See above for what that does and does not include."""
    docx = _docx()
    pymupdf = _fitz()
    document = docx.Document()
    with _open(in_path, src_ext) as doc:
        _page_count(doc)
        body_size = _body_size(doc)
        wrote_anything = False
        for index, page in enumerate(doc):
            report(index, len(doc))
            if index:
                document.add_page_break()
            for block in sorted(page.get_text("dict").get("blocks", ()),
                                key=lambda b: (round(b.get("bbox", (0, 0, 0, 0))[1]),
                                               round(b.get("bbox", (0, 0, 0, 0))[0]))):
                for line in block.get("lines", ()):
                    text = _line_text(line)
                    if not text:
                        continue
                    spans = [span for span in line.get("spans", ()) if (span.get("text") or "").strip()]
                    size = max((float(span.get("size") or 0) for span in spans), default=body_size)

                    bold = any(int(span.get("flags") or 0) & (1 << 4) for span in spans)
                    if body_size and size >= body_size * _HEADING_2_RATIO:
                        document.add_heading(text, level=1)
                    elif body_size and size >= body_size * _HEADING_RATIO:
                        document.add_heading(text, level=2)
                    else:
                        paragraph = document.add_paragraph()
                        run = paragraph.add_run(text)
                        run.bold = bold
                    wrote_anything = True
            _add_page_images(document, doc, page, pymupdf, work_dir)
    if not wrote_anything:
        raise ConversionError(
            "There is nothing in that file to put into a Word document -- it "
            "looks like scanned pages rather than text. Converting it to PNG "
            "or JPG will give you the pages themselves."
        )
    document.save(str(out_path))

def _add_page_images(document, doc, page, pymupdf, work_dir) -> None:
    """The pictures on one page, in the order the page lists them."""
    import io
    from PIL import Image as PILImage
    try:
        listed = page.get_images(full=True)
    except Exception:
        return
    for number, info in enumerate(listed):
        try:
            data = doc.extract_image(info[0])
            raw, width, height = data["image"], data.get("width", 0), data.get("height", 0)
            if width * height < _MIN_IMAGE_PIXELS or width * height > _MAX_IMAGE_PIXELS:
                continue

            picture = PILImage.open(io.BytesIO(raw))
            if picture.mode not in ("RGB", "L"):
                picture = picture.convert("RGB")
            buffer = io.BytesIO()
            picture.save(buffer, format="PNG")
            buffer.seek(0)
            inches = min(_DOCX_PAGE_WIDTH_INCHES, max(1.0, width / 96))
            from docx.shared import Inches
            document.add_picture(buffer, width=Inches(inches))
        except Exception:
            continue

def convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str = "converted") -> Result:
    src_ext = formats.normalise(src_ext)
    target_ext = formats.normalise(target_ext)
    work_dir = Path(work_dir)
    out_path = work_dir / f"{stem}.{target_ext}"

    if target_ext == "pdf":
        _to_pdf(in_path, src_ext, out_path)
        return Result(out_path)

    if target_ext == "docx":
        _to_docx(in_path, src_ext, out_path, work_dir)
        return Result(out_path)

    if target_ext in ("png", "jpg", "webp", "tiff"):
        return _pack(_render_pages(in_path, src_ext, target_ext, work_dir, stem),
                     target_ext, work_dir, stem)

    if target_ext == "svg":
        return _pack(_page_svgs(in_path, src_ext, work_dir, stem), "svg", work_dir, stem)

    if target_ext == "txt":
        text = _to_text(in_path, src_ext)
        if not text.strip():
            raise ConversionError(
                "There is no text in that file to extract -- it looks like "
                "scanned pages rather than a document. Converting it to PNG "
                "or JPG will give you the pages themselves."
            )
        out_path.write_text(text, encoding="utf-8")
        return Result(out_path)

    if target_ext == "html":
        out_path.write_text(
            "<!doctype html>\n<meta charset=\"utf-8\">\n" + _source_html(in_path, src_ext),
            encoding="utf-8",
        )
        return Result(out_path)

    if target_ext == "md":
        if src_ext != "docx":
            raise ConversionError(f"Nothing here turns a .{src_ext} into Markdown.")
        try:
            import mammoth
            with open(in_path, "rb") as handle:
                out_path.write_text(mammoth.convert_to_markdown(handle).value, encoding="utf-8")
        except ImportError as exc:
            raise ConversionError("Word documents aren't supported on this host.") from exc
        except Exception as exc:
            raise ConversionError(f"Couldn't read that .docx: {exc}") from exc
        return Result(out_path)

    raise ConversionError(f"Nothing here converts a .{src_ext} to .{target_ext}.")

# ─── module: convert_bot.office_convert ──────────────────────────────────────
"""Office files -- PowerPoint, Word, Excel and their OpenDocument twins -- through LibreOffice, run headless, one fresh process and one fresh profile per conversion.

What LibreOffice writes directly: a deck as PPTX, PPT, ODP or PDF; a text document as DOCX, DOC, ODT, RTF or PDF; a spreadsheet as XLSX, XLS, ODS or PDF; and a PDF as an editable PPTX or ODP (its PDF import makes text boxes and shapes, not pictures). Everything else goes through one of those: a deck's pictures and text come from its PDF (doc_convert), an old spreadsheet's CSV or JSON from its XLSX (data_convert).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import formats
from convert_utils import Result, ConversionError, report

PRESENTATIONS = ("pptx", "ppt", "odp")
TEXT_DOCUMENTS = ("doc", "odt", "rtf")
SPREADSHEETS = ("xls", "ods")

# What LibreOffice writes itself, by the kind of file it opened.
_DIRECT = {
    "impress": ("pdf", "pptx", "ppt", "odp"),
    "writer": ("pdf", "docx", "doc", "odt", "rtf"),
    "calc": ("pdf", "xlsx", "xls", "ods"),
    "pdf": ("pptx", "odp"),
}

# Targets only LibreOffice writes: any conversion into one of these comes here.
ONLY_HERE = ("pptx", "ppt", "odp", "doc", "odt", "rtf", "xls", "ods")

# The export filter by name where the bare extension would pick a less compatible one.
_FILTERS = {
    "pptx": "pptx:Impress MS PowerPoint 2007 XML",
    "docx": "docx:MS Word 2007 XML",
    "xlsx": "xlsx:Calc MS Excel 2007 XML",
}

SOFFICE_TIMEOUT_S = int(os.environ.get("CONVERT_OFFICE_TIMEOUT_SECONDS") or 600)

# Exit status of a first start on a new profile: it was made, start again.
_RESTART = 81

# A new profile with macros off and nothing fetched from outside: whatever arrives in a
# document stays inert. Written before the first start, so it is in force from the start.
_PROFILE_SETTINGS = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="BlockUntrustedRefererLinks" oor:op="fuse"><value>true</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="UseOpenCL" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop></item>
</oor:items>
"""


def soffice_path() -> "str | None":
    """LibreOffice's own program, soffice.bin, where it can be found: started directly it is one process, which a timeout can stop, where the `soffice` launcher would leave it running."""
    explicit = os.environ.get("CBOT_SOFFICE")
    candidates = [explicit] if explicit else []
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates += ["/usr/lib/libreoffice/program/soffice", "/opt/libreoffice/program/soffice"]
    for candidate in candidates:
        if not candidate or not os.path.exists(candidate):
            continue
        real = Path(os.path.realpath(candidate))
        if real.name == "soffice.bin":
            return str(real)
        binary = real.parent / "soffice.bin"
        if binary.is_file():
            return str(binary)
    return None


def has_pdf_import() -> bool:
    """Whether this LibreOffice can open a PDF as slides (its pdfimport library is a separate part on some systems)."""
    binary = soffice_path()
    if not binary:
        return False
    program = Path(binary).parent
    return any(program.glob("libpdfimportlo.so")) or any(program.glob("pdfimport*.dll")) \
        or any(program.glob("libpdfimport*"))


def family_of(src_ext: str) -> "str | None":
    src_ext = formats.normalise(src_ext)
    if src_ext in PRESENTATIONS:
        return "impress"
    if src_ext in TEXT_DOCUMENTS or src_ext == "docx":
        return "writer"
    if src_ext in SPREADSHEETS or src_ext == "xlsx":
        return "calc"
    if src_ext == "pdf":
        return "pdf"
    return None


def handles(src_ext: str, target_ext: str) -> bool:
    """Whether this conversion is LibreOffice's to do."""
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    if src_ext in PRESENTATIONS or src_ext in TEXT_DOCUMENTS or src_ext in SPREADSHEETS:
        return True
    if target_ext in ONLY_HERE:
        return family_of(src_ext) is not None
    # A Word document's PDF -- and its pages as pictures -- keep the layout only when Word's own
    # rules lay it out; without LibreOffice doc_convert re-flows it.
    return src_ext == "docx" and target_ext in ("pdf", "png", "jpg") and formats.met("office")


def _run(binary: str, source: Path, target_ext: str, out_dir: Path, profile: Path,
         infilter: "str | None" = None) -> None:
    command = [binary, "--headless", "--invisible", "--norestore", "--nolockcheck", "--nodefault",
               "--nologo", "--nofirststartwizard", f"-env:UserInstallation={profile.as_uri()}"]
    if infilter:
        command.append(f"--infilter={infilter}")
    command += ["--convert-to", _FILTERS.get(target_ext, target_ext), "--outdir", str(out_dir), str(source)]
    # Only what it needs: none of the bots' tokens or database addresses reach a program that is
    # opening somebody else's document.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(profile),
           "TMPDIR": str(profile), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "SAL_USE_VCLPLUGIN": "svp"}
    for attempt in range(2):
        try:
            proc = subprocess.run(command, capture_output=True, text=True, env=env,
                                  timeout=SOFFICE_TIMEOUT_S, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            raise ConversionError(
                f"LibreOffice was still working on that after {SOFFICE_TIMEOUT_S // 60} minutes, so I stopped it."
            ) from None
        except OSError as exc:
            raise ConversionError(f"LibreOffice couldn't be started here: {exc}") from None
        if proc.returncode == _RESTART and attempt == 0:
            continue
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or [""]
            raise ConversionError(
                f"LibreOffice couldn't convert that file (exit {proc.returncode}). {tail[0][:200]}".strip()
            )
        return


def soffice(in_path, src_ext: str, target_ext: str, work_dir, infilter: "str | None" = None) -> Path:
    """`in_path` written as `target_ext` by LibreOffice; the path of what it wrote, inside work_dir."""
    binary = soffice_path()
    if not binary:
        raise ConversionError("Office documents can't be converted on this host: LibreOffice isn't installed.")
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    room = Path(work_dir) / f"office-{os.getpid()}-{target_ext}"
    shutil.rmtree(room, ignore_errors=True)
    profile, inbox, outbox = room / "profile", room / "in", room / "out"
    for folder in (profile / "user", inbox, outbox):
        folder.mkdir(parents=True, exist_ok=True)
    (profile / "user" / "registrymodifications.xcu").write_text(_PROFILE_SETTINGS, encoding="utf-8")
    # A plain name: the result is named after the source, and a user's file name stays out of argv.
    source = inbox / f"source.{src_ext}"
    shutil.copyfile(in_path, source)
    _run(binary, source, target_ext, outbox, profile, infilter)
    produced = outbox / f"source.{target_ext}"
    if not produced.is_file() or produced.stat().st_size == 0:
        # LibreOffice says nothing and exits 0 when it can't open a file at all.
        raise ConversionError(
            f"LibreOffice couldn't open that .{src_ext}. It may be damaged, password-protected, "
            "or not really a ." + src_ext + " file."
        )
    kept = Path(work_dir) / f"{room.name}.{target_ext}"
    produced.replace(kept)
    shutil.rmtree(room, ignore_errors=True)
    return kept


def convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str = "converted") -> Result:
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    work_dir = Path(work_dir)
    family = family_of(src_ext)
    if family is None:
        raise ConversionError(f"Nothing here converts a .{src_ext} to .{target_ext}.")
    out_path = work_dir / f"{stem}.{target_ext}"
    report(0, 2)

    if target_ext in _DIRECT[family]:
        infilter = "impress_pdf_import" if family == "pdf" else None
        written = soffice(in_path, src_ext, target_ext, work_dir, infilter)
        written.replace(out_path)
        report(2, 2)
        return Result(out_path)

    if family in ("impress", "writer"):
        # Pictures, text and HTML of a deck or a document come from its PDF.
        import doc_convert
        pdf = soffice(in_path, src_ext, "pdf", work_dir)
        report(1, 2)
        try:
            return doc_convert.convert(pdf, "pdf", target_ext, work_dir, stem)
        finally:
            pdf.unlink(missing_ok=True)

    if family == "calc":
        import data_convert
        xlsx = soffice(in_path, src_ext, "xlsx", work_dir)
        report(1, 2)
        try:
            return data_convert.convert(xlsx, "xlsx", target_ext, work_dir, stem)
        finally:
            xlsx.unlink(missing_ok=True)

    raise ConversionError(f"Nothing here converts a .{src_ext} to .{target_ext}.")


def selftest() -> None:
    """A two-page PDF opened as slides, saved as PPTX, then as PDF again, and its text read back: main.py --check runs it, so an image whose LibreOffice can't do the conversions offered fails the build. SystemExit on failure."""
    import tempfile
    import pymupdf
    with tempfile.TemporaryDirectory(prefix="office-check-") as folder:
        folder = Path(folder)
        doc = pymupdf.open()
        for number in (1, 2):
            page = doc.new_page(width=960, height=540)
            page.insert_text((60, 120), f"Office check slide {number}", fontsize=36)
        doc.save(folder / "check.pdf")
        doc.close()
        try:
            deck = convert(folder / "check.pdf", "pdf", "pptx", folder, "deck").path
            old = convert(deck, "pptx", "ppt", folder, "old").path
            back = convert(old, "ppt", "pdf", folder, "back").path
            with pymupdf.open(back) as again:
                text = " ".join(page.get_text() for page in again)
                pages = again.page_count
        except ConversionError as exc:
            print(f"  FAIL  LibreOffice: {exc}")
            raise SystemExit(1) from None
        if pages != 2 or "Office check slide 2" not in text:
            print(f"  FAIL  LibreOffice: the round trip came back as {pages} page(s): {text[:120]!r}")
            raise SystemExit(1)
        # Writer and Calc are packages of their own: one document and one spreadsheet each way.
        (folder / "check.html").write_text("<p>Office check document</p>", encoding="utf-8")
        (folder / "check.csv").write_text("name,score\nOffice check,1\n", encoding="utf-8")
        try:
            odt = soffice(folder / "check.html", "html", "odt", folder)
            doc = convert(odt, "odt", "doc", folder, "doc").path
            docx = convert(doc, "doc", "docx", folder, "docx").path
            text = Path(convert(docx, "docx", "pdf", folder, "docpdf").path)
            ods = soffice(folder / "check.csv", "csv", "ods", folder)
            xls = convert(ods, "ods", "xls", folder, "xls").path
            csv = convert(xls, "xls", "csv", folder, "csv").path.read_text(encoding="utf-8")
        except ConversionError as exc:
            print(f"  FAIL  LibreOffice (Writer or Calc): {exc}")
            raise SystemExit(1) from None
        with pymupdf.open(text) as again:
            document = " ".join(page.get_text() for page in again)
        if "Office check document" not in document or "Office check,1" not in csv:
            print(f"  FAIL  LibreOffice: Writer gave {document[:80]!r}, Calc gave {csv[:80]!r}")
            raise SystemExit(1)

# ─── module: convert_bot.archive_convert ─────────────────────────────────────
"""Archives: ZIP, TAR, TAR.GZ, TAR.BZ2, TAR.XZ and 7z -- and RAR, which is read and never written."""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
import zipfile
from pathlib import Path

import formats
from convert_utils import ConversionError, Result, remove_tree, report
from formats import bsdtar_path

WRITES = frozenset({"zip", "tar", "tgz", "tbz2", "txz", "7z"})

TAR_READ_MODES = {"tar": "r:", "tgz": "r:gz", "tbz2": "r:bz2", "txz": "r:xz"}
TAR_WRITE_MODES = {"tar": "w:", "tgz": "w:gz", "tbz2": "w:bz2", "txz": "w:xz"}

MAX_ENTRIES = int(os.environ.get("CONVERT_MAX_ARCHIVE_ENTRIES") or 10_000)

MAX_EXPANDED_MB = int(os.environ.get("CONVERT_MAX_ARCHIVE_EXPANDED_MB") or 300)

MAX_RATIO = int(os.environ.get("CONVERT_MAX_ARCHIVE_RATIO") or 200)
MAX_NAME_BYTES = 1024
MAX_PART_BYTES = 255

MAX_HEADER_BYTES = 1024 * 1024
BSDTAR_TIMEOUT_S = 900.0

_STDERR_TAIL = 64 * 1024

_WINDOWS_NAMES = os.name == "nt"

WATCH_INTERVAL_S = 0.25
_stats = {"watcher_killed": 0}

_MB = 1024 * 1024
_CHUNK = 1024 * 256
_DEVICE_NAMES = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                           *(f"lpt{i}" for i in range(1, 10))})
_DRIVE = re.compile(r"^[A-Za-z]:")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_NOT_FILES = frozenset({stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK})
_PASSWORD_WORDS = ("passphrase", "encrypted", "password", "incorrect pass")

def _limit_bytes() -> int:
    return MAX_EXPANDED_MB * _MB

def _safe_name(raw: str) -> "str | None":
    """The entry's path as a clean relative POSIX path, or None for an entry that is just the folder itself ("./", ".")."""
    if raw is None or _CONTROL.search(raw):
        raise ConversionError("That archive has a file name with control characters in it, "
                              "so it was not opened.")
    name = raw.replace("\\", "/")
    if name.startswith("/") or _DRIVE.match(name):
        raise ConversionError("That archive has a file whose path starts at the root of a disk "
                              "instead of inside the archive, so it was not opened.")
    parts = []
    for part in name.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ConversionError("That archive has a file whose path climbs out of the archive "
                                  "(a `..`), so it was not opened.")
        if len(part.encode("utf-8", "replace")) > MAX_PART_BYTES:
            raise ConversionError("That archive has a file name longer than a file system takes, "
                                  "so it was not opened.")
        if _WINDOWS_NAMES and part.split(".")[0].lower() in _DEVICE_NAMES:
            raise ConversionError("That archive has a file named like a device (CON, NUL, ...), "
                                  "so it was not opened.")
        parts.append(part)
    if not parts:
        return None
    clean = "/".join(parts)
    if len(clean.encode("utf-8", "replace")) > MAX_NAME_BYTES:
        raise ConversionError("That archive has a path longer than a file system takes, "
                              "so it was not opened.")
    return clean

def _under(root: Path, relative: str) -> Path:
    """root/relative, and proof it is still inside root once symlinks are resolved -- a belt for the braces above."""
    target = (root / relative)
    resolved = target.resolve()
    if os.path.commonpath([str(root.resolve()), str(resolved)]) != str(root.resolve()):
        raise ConversionError("That archive would write outside its own folder, so it was not opened.")
    return target

class _Budget:
    """What may still be written. Counted on the bytes that are written, not on what an index says they will be."""

    def __init__(self):
        self.entries = 0
        self.files = 0
        self.bytes = 0
        self.skipped = 0

    def entry(self) -> None:
        self.entries += 1
        if self.entries > MAX_ENTRIES:
            raise ConversionError(f"That archive has more than {MAX_ENTRIES:,} entries, "
                                  "which is more than one conversion takes.")

    def add(self, count: int) -> None:
        self.bytes += count
        if self.bytes > _limit_bytes():
            raise ConversionError(f"That archive expands to more than {MAX_EXPANDED_MB:,} MB, "
                                  "which is more than one conversion takes.")

_CLASH = "That archive has a file and a folder with the same name, so it was not opened."

def _make_folder(path: Path) -> None:
    """mkdir -p, where a FILE already in the way is a refusal, not a crash."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, NotADirectoryError):
        raise ConversionError(_CLASH) from None

def _copy_capped(source, destination: Path, budget: _Budget) -> None:
    _make_folder(destination.parent)
    if destination.is_dir():
        raise ConversionError(_CLASH)
    with open(destination, "wb") as out:
        while True:
            chunk = source.read(_CHUNK)
            if not chunk:
                break
            budget.add(len(chunk))
            out.write(chunk)
    budget.files += 1

def _extract_zip(in_path: str, root: Path, budget: _Budget) -> None:
    try:
        archive = zipfile.ZipFile(in_path)
    except UnicodeDecodeError:

        raise ConversionError("That archive's file names aren't readable text, so it was not opened.") from None
    except (zipfile.BadZipFile, OSError, NotImplementedError, EOFError) as exc:
        raise ConversionError(f"Couldn't read that ZIP: {exc}") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ConversionError(f"That archive has {len(infos):,} entries, over the "
                                  f"{MAX_ENTRIES:,} one conversion takes.")
        declared = 0
        for info in infos:
            if info.flag_bits & 0x1:
                raise ConversionError("That ZIP is password-protected. Nothing was charged -- "
                                      "this bot never asks for a password.")
            declared += info.file_size
            if info.file_size > _MB and (info.compress_size == 0
                                         or info.file_size / max(1, info.compress_size) > MAX_RATIO):
                raise ConversionError(f"That ZIP has a file that expands more than {MAX_RATIO}-fold, "
                                      "which is how a zip bomb is built, so it was not opened.")
        if declared > _limit_bytes():
            raise ConversionError(f"That archive expands to {declared // _MB:,} MB, over the "
                                  f"{MAX_EXPANDED_MB:,} MB one conversion takes.")
        for info in infos:
            budget.entry()
            name = _safe_name(info.filename)
            if name is None:
                continue

            if stat.S_IFMT(info.external_attr >> 16) in _NOT_FILES:
                budget.skipped += 1
                continue
            if info.is_dir():
                _make_folder(_under(root, name))
                continue
            try:
                with archive.open(info) as source:
                    _copy_capped(source, _under(root, name), budget)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, OSError, ValueError) as exc:
                raise ConversionError(f"Couldn't read '{name}' inside that ZIP: {exc}") from exc

_HEADER_TOO_BIG = "a header in the archive is larger than the limit"

class _HeaderReads:
    """A tar file's byte stream for the length of one header, handing over no more than MAX_HEADER_BYTES in all."""

    def __init__(self, fileobj):
        self._fileobj = fileobj
        self._left = MAX_HEADER_BYTES

    def read(self, size=-1):
        if size is None or size < 0 or size > self._left:
            raise tarfile.HeaderError(_HEADER_TOO_BIG)
        self._left -= size
        return self._fileobj.read(size)

    def __getattr__(self, name):
        return getattr(self._fileobj, name)

class _CappedTarInfo(tarfile.TarInfo):
    """tarfile's header reader, refusing a header larger than any name needs."""

    def _within_allowance(self, parent, tar, check_size):
        if check_size and self.size > MAX_HEADER_BYTES:
            raise tarfile.HeaderError(_HEADER_TOO_BIG)
        if isinstance(tar.fileobj, _HeaderReads):
            return parent(tar)
        real = tar.fileobj
        tar.fileobj = _HeaderReads(real)
        try:
            return parent(tar)
        finally:
            tar.fileobj = real

    def _proc_gnulong(self, tar):
        return self._within_allowance(super()._proc_gnulong, tar, True)

    def _proc_pax(self, tar):
        return self._within_allowance(super()._proc_pax, tar, True)

    def _proc_sparse(self, tar):

        return self._within_allowance(super()._proc_sparse, tar, False)

def _tar_refusal(exc: Exception) -> ConversionError:
    if _HEADER_TOO_BIG in str(exc):

        return ConversionError("That archive has a header far larger than any file name, "
                               "so it was not opened.")
    return ConversionError(f"Couldn't read that archive: {exc}")

def _extract_tar(in_path: str, src_ext: str, root: Path, budget: _Budget) -> None:
    try:
        archive = tarfile.open(in_path, mode=TAR_READ_MODES[src_ext], tarinfo=_CappedTarInfo)
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise _tar_refusal(exc) from exc
    except MemoryError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't read that archive: {type(exc).__name__}") from exc
    try:
        with archive:
            for member in archive:
                budget.entry()
                name = _safe_name(member.name)
                if name is None:
                    continue
                if member.isdir():
                    _make_folder(_under(root, name))
                    continue
                if not member.isreg():
                    budget.skipped += 1
                    continue
                source = archive.extractfile(member)
                if source is None:
                    budget.skipped += 1
                    continue
                with source:
                    _copy_capped(source, _under(root, name), budget)
    except ConversionError:
        raise
    except (tarfile.TarError, EOFError, OSError, ValueError) as exc:
        raise _tar_refusal(exc) from exc
    except MemoryError:
        raise
    except Exception as exc:
        raise ConversionError(f"That archive is damaged ({type(exc).__name__}).") from exc

_MAGIC = {"rar": b"Rar!\x1a\x07", "7z": b"7z\xbc\xaf\x27\x1c"}
_PADDING = 20 * 1024

def _padded_copy(in_path: str, src_ext: str, work_dir: Path, stem: str) -> Path:
    with open(in_path, "rb") as source:
        if not source.read(8).startswith(_MAGIC[src_ext]):
            raise ConversionError(f"That file is not a {src_ext.upper()} archive, whatever it is called.")
    copy = work_dir / f"{stem}-source.{src_ext}"
    shutil.copyfile(in_path, copy)
    with open(copy, "ab") as out:
        out.write(b"\0" * _PADDING)
    return copy

def _walk_failed(exc: OSError):
    """os.walk's onerror, for every walk over what an archive unpacked."""
    raise ConversionError("Some of that archive's files couldn't be read, so it was not opened.") from exc

def _tree_size(root: Path, strict: bool = False) -> int:
    """Bytes under root."""
    total = 0
    for current, _dirs, files in os.walk(root, onerror=_walk_failed if strict else None):
        for name in files:
            try:
                total += os.lstat(os.path.join(current, name)).st_size
            except OSError as exc:
                if strict:
                    _walk_failed(exc)
    return total

def _opened_mode(mode: int, is_dir: bool) -> int:
    """A mode with the owner able to read and write (and, for a folder, to enter and list), the setuid, setgid and sticky bits gone, and everything else as it was."""
    return (mode | (0o700 if is_dir else 0o600)) & 0o777

def _open_up(root: Path) -> None:
    """Make everything bsdtar unpacked readable and writable by us, top down."""
    try:
        os.chmod(root, _opened_mode(os.lstat(root).st_mode, True))
        for current, dirs, files in os.walk(root, onerror=_walk_failed):
            for name in dirs + files:
                path = os.path.join(current, name)
                mode = os.lstat(path).st_mode
                if stat.S_ISDIR(mode):
                    os.chmod(path, _opened_mode(mode, True))
                elif stat.S_ISREG(mode):
                    os.chmod(path, _opened_mode(mode, False))
    except OSError as exc:
        _walk_failed(exc)

def _tail(handle, limit: int = _STDERR_TAIL) -> str:
    """The last `limit` bytes of a file bsdtar wrote its complaints to."""
    try:
        size = handle.seek(0, os.SEEK_END)
        handle.seek(max(0, size - limit))
        return handle.read(limit).decode("utf-8", "replace")
    except (OSError, ValueError):
        return ""

def _too_big() -> ConversionError:
    return ConversionError(f"That archive expands to more than {MAX_EXPANDED_MB:,} MB, "
                           "which is more than one conversion takes.")

def _extract_with_bsdtar(in_path: str, root: Path, budget: _Budget) -> None:
    tar = bsdtar_path()
    if tar is None:
        raise ConversionError("7z and RAR archives aren't supported on this host.")

    with tempfile.TemporaryFile() as listing_errors:
        listing = subprocess.Popen([tar, "-tf", in_path], stdout=subprocess.PIPE, stderr=listing_errors)
        names = []
        try:
            for line in listing.stdout:
                names.append(line.decode("utf-8", "replace").rstrip("\r\n"))
                if len(names) > MAX_ENTRIES:
                    listing.kill()
                    raise ConversionError(f"That archive has more than {MAX_ENTRIES:,} entries, "
                                          "which is more than one conversion takes.")
            listing.wait(timeout=60)
        except subprocess.TimeoutExpired:
            listing.kill()
            raise ConversionError("Reading that archive's index took too long, so it was not opened.") from None
        finally:
            if listing.poll() is None:
                listing.kill()
            listing.wait()
            listing.stdout.close()
        errors = _tail(listing_errors)
    if listing.returncode not in (0, None) and not names:
        _refuse_bsdtar(errors)
    for name in names:
        _safe_name(name)

    with tempfile.TemporaryFile() as extract_errors:
        proc = subprocess.Popen(
            [tar, "-xpf", in_path, "-C", str(root), "--no-same-owner",
             "--no-acls", "--no-xattrs", "--no-fflags"],
            stdout=subprocess.DEVNULL, stderr=extract_errors)
        over = threading.Event()
        done = threading.Event()

        def watch():
            while not done.wait(WATCH_INTERVAL_S):
                if _tree_size(root) > _limit_bytes():
                    over.set()
                    _stats["watcher_killed"] += 1
                    proc.kill()
                    return

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            proc.wait(timeout=BSDTAR_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise ConversionError("Opening that archive took too long, so it was stopped.") from None
        finally:
            done.set()
            watcher.join(2)
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        err = _tail(extract_errors)
    if over.is_set():
        raise _too_big()
    if proc.returncode != 0:
        if _tree_size(root) > _limit_bytes():
            raise _too_big()
        if proc.returncode < 0:
            raise MemoryError("the archive reader was stopped by the system")
        _refuse_bsdtar(err)

    _open_up(root)

    os.utime(root)
    if _tree_size(root, strict=True) > _limit_bytes():
        raise _too_big()
    _drop_non_files(root, budget)
    _count_files(root, budget)

def _count_files(root: Path, budget: _Budget) -> None:
    """What bsdtar wrote, counted against the same budget as the other readers."""
    for current, _dirs, files in os.walk(root, onerror=_walk_failed):
        for name in files:
            budget.entry()
            budget.add(os.lstat(os.path.join(current, name)).st_size)
            budget.files += 1

def _drop_non_files(root: Path, budget: _Budget) -> None:
    """Whatever bsdtar made that is not a plain file or a folder goes: links (which it creates as links), devices, fifos."""
    for current, dirs, files in os.walk(root, followlinks=False, onerror=_walk_failed):
        for name in list(dirs) + list(files):
            path = os.path.join(current, name)
            mode = os.lstat(path).st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                os.unlink(path)
                budget.skipped += 1
                if name in dirs:
                    dirs.remove(name)

def _refuse_bsdtar(message: str) -> None:
    lowered = message.lower()
    if any(word in lowered for word in _PASSWORD_WORDS):
        raise ConversionError("That archive is password-protected. Nothing was charged -- "
                              "this bot never asks for a password.")
    raise ConversionError("Couldn't read that archive: " + (message.strip().splitlines() or ["unknown error"])[-1][:200])

def _entries(root: Path):
    """(relative path, absolute path, is a directory), directories first within each level, in a stable order -- so the same input is the same output."""
    for current, dirs, files in os.walk(root, onerror=_walk_failed):
        dirs.sort()
        here = Path(current)
        for name in sorted(files):
            yield (here / name).relative_to(root).as_posix(), here / name, False
        if not dirs and not files and here != root:
            yield here.relative_to(root).as_posix(), here, True

def _require_text_names(entries, label: str) -> None:
    """A ZIP or a 7z stores names as text, so a name that is not text cannot go into one."""
    for name, _path, _is_dir in entries:
        try:
            name.encode("utf-8")
        except UnicodeEncodeError:
            raise ConversionError("That archive's file names aren't readable text, so it can't be "
                                  f"made into a {label}.") from None

def _write_zip(root: Path, out_path: Path) -> int:
    count = 0
    entries = list(_entries(root))
    _require_text_names(entries, "ZIP")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6, strict_timestamps=False) as archive:
        for index, (name, path, is_dir) in enumerate(entries):
            report(index, len(entries))
            if is_dir:
                archive.writestr(name + "/", b"")
            else:
                archive.write(path, arcname=name)
                count += 1
    report(len(entries), len(entries))
    return count

def _normalised(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Nobody's user id, nobody's name, and permissions that mean the same on any machine: what was on the sender's disk is not the recipient's business."""
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mode = 0o755 if info.isdir() else 0o644
    return info

def _write_tar(root: Path, target_ext: str, out_path: Path) -> int:
    count = 0
    entries = list(_entries(root))
    with tarfile.open(out_path, mode=TAR_WRITE_MODES[target_ext]) as archive:
        for index, (name, path, is_dir) in enumerate(entries):
            report(index, len(entries))
            archive.add(path, arcname=name, recursive=False, filter=_normalised)
            count += 0 if is_dir else 1
    report(len(entries), len(entries))
    return count

def _write_7z(root: Path, out_path: Path) -> int:
    tar = bsdtar_path()
    if tar is None:
        raise ConversionError("7z archives can't be made on this host.")
    entries = list(_entries(root))
    _require_text_names(entries, "7Z")
    count = sum(1 for _, _, is_dir in entries if not is_dir)
    try:
        proc = subprocess.run(
            [tar, "--format", "7zip", "--options", "7zip:compression=lzma2", "-cf", str(out_path), "-C", str(root), "."],
            capture_output=True, timeout=BSDTAR_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise ConversionError("Making that 7z took too long, so it was stopped.") from None
    if proc.returncode != 0 or not out_path.exists():
        out_path.unlink(missing_ok=True)
        detail = (proc.stderr.decode("utf-8", "replace").strip().splitlines() or [""])[-1][:160]

        raise ConversionError("Couldn't make a 7z out of this one" + (f" ({detail})" if detail else "")
                              + ". A ZIP or TAR.XZ will work.")
    return count

def convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str = "converted") -> Result:
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    if target_ext not in WRITES:
        raise ConversionError(f"Nothing here makes a .{target_ext} archive.")
    work_dir = Path(work_dir)
    out_path = work_dir / f"{stem}.{target_ext}"
    root = work_dir / f"{stem}-contents"
    if root.exists():
        remove_tree(root)
    root.mkdir(parents=True)
    budget = _Budget()
    try:
        if src_ext == "zip":
            _extract_zip(str(in_path), root, budget)
        elif src_ext in TAR_READ_MODES:
            _extract_tar(str(in_path), src_ext, root, budget)
        elif src_ext in ("7z", "rar"):
            padded = _padded_copy(str(in_path), src_ext, work_dir, stem)
            try:
                _extract_with_bsdtar(str(padded), root, budget)
            finally:
                padded.unlink(missing_ok=True)
        else:
            raise ConversionError(f"Nothing here opens a .{src_ext} archive.")
        if budget.files == 0:
            raise ConversionError("That archive has no files in it." + (
                " Links, devices and other things that are not plain files are never carried over."
                if budget.skipped else ""))
        if target_ext == "zip":
            files = _write_zip(root, out_path)
        elif target_ext in TAR_WRITE_MODES:
            files = _write_tar(root, target_ext, out_path)
        else:
            files = _write_7z(root, out_path)
    except BaseException:
        out_path.unlink(missing_ok=True)
        raise
    finally:
        remove_tree(root)
    return Result(out_path, items=max(1, files))

# ─── module: convert_bot.raw_convert ─────────────────────────────────────────
"""Camera RAW: CR2, CR3, NEF, ARW, DNG, RAF, ORF and RW2 to JPG, PNG, WEBP, AVIF, HEIC or TIFF."""
from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import NamedTuple

import formats
from convert_utils import ConversionError, OutOfMemory, save_image

FORMATS = formats.RAW_FORMATS
FULL_MP = float(os.environ.get("CONVERT_RAW_FULL_MP") or 40)
MAX_MP = float(os.environ.get("CONVERT_RAW_MAX_MP") or 110)

WRITES = frozenset({"jpg", "png", "webp", "avif", "heic", "tiff"})

class RawInfo(NamedTuple):
    width: int
    height: int
    megapixels: float
    half: bool
    out_width: int
    out_height: int
    out_megapixels: float

def _rawpy():
    try:
        import rawpy
        return rawpy
    except ImportError as exc:
        raise ConversionError("Camera raw photos aren't supported on this host.") from exc

def _open(path, src_ext: str, unpack: bool = True):
    """The file opened by LibRaw."""
    rawpy = _rawpy()
    try:
        if not unpack:
            raw = rawpy.RawPy()
            raw.open_file(str(path))
            return raw
        return rawpy.imread(str(path))
    except MemoryError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't read that {src_ext.upper()} as a camera raw photo: "
                              f"{_tidy(exc)}") from exc

def _mp(value: float) -> str:
    """A megapixel count for a sentence: whole numbers for photos, two places for the small ones a test or a thumbnail can be."""
    return f"{value:.0f}" if value >= 10 else f"{value:.2f}"

def _tidy(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:160] or type(exc).__name__

def _sizes(raw) -> "tuple[int, int]":
    """The picture's own width and height, after the camera's turn."""
    width, height = int(raw.sizes.width), int(raw.sizes.height)
    if int(getattr(raw.sizes, "flip", 0) or 0) in (5, 6):
        width, height = height, width
    return width, height

def inspect(path, src_ext: str = "dng") -> RawInfo:
    """Size and plan from the file's header, without decoding a pixel."""
    with _open(path, src_ext, unpack=False) as raw:
        width, height = _sizes(raw)
    megapixels = width * height / 1_000_000
    half = megapixels > FULL_MP
    out_w, out_h = (width // 2, height // 2) if half else (width, height)
    return RawInfo(width, height, megapixels, half, out_w, out_h, out_w * out_h / 1_000_000)

def megapixels(path, src_ext: str) -> "float | None":
    """The size the way jobs.describe_image gives it for a picture -- None for anything that cannot be read -- but the OUTPUT size, because that is what the estimates of what comes out are about."""
    try:
        return inspect(path, src_ext).out_megapixels
    except ConversionError:
        return None

def convert(in_path, src_ext: str, target_ext: str, out_path) -> None:
    src_ext, target_ext = formats.normalise(src_ext), formats.normalise(target_ext)
    if target_ext not in WRITES:
        raise ConversionError(f"A camera raw photo doesn't convert to .{target_ext}.")
    rawpy = _rawpy()
    with _open(in_path, src_ext) as raw:
        width, height = _sizes(raw)
        megapixels_ = width * height / 1_000_000
        if megapixels_ > MAX_MP:
            raise ConversionError(
                f"That photo is {_mp(megapixels_)} megapixels. This server converts camera raw photos up to "
                f"{_mp(MAX_MP)}: past that even the half-size decode needs more memory than it has.")
        bits = 16 if target_ext == "tiff" else 8
        try:
            rgb = raw.postprocess(
                use_camera_wb=True, no_auto_bright=True, output_bps=bits,
                output_color=rawpy.ColorSpace.sRGB,
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                half_size=megapixels_ > FULL_MP)
        except MemoryError:
            raise OutOfMemory("decoding that raw photo ran out of memory") from None
        except Exception as exc:
            raise ConversionError(f"Couldn't develop that raw photo: {_tidy(exc)}") from exc
    if target_ext == "tiff":
        _write_tiff16(rgb, out_path)
        return
    from PIL import Image
    try:
        picture = Image.fromarray(rgb)
        del rgb
        save_image(picture, target_ext, out_path)
    except ConversionError:
        raise
    except MemoryError:
        raise OutOfMemory("saving that raw photo ran out of memory") from None
    except Exception as exc:
        raise ConversionError(f"Image conversion failed: {exc}") from exc

def _srgb_profile() -> "bytes | None":
    """Pillow carries lcms; with it the TIFF says which colours its numbers are, which is what an editor asks about an untagged 16-bit file."""
    try:
        from PIL import ImageCms
        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    except Exception:
        return None

def _write_tiff16(rgb, out_path) -> None:
    """An uncompressed baseline TIFF of an (height, width, 3) uint16 array: one strip, little-endian, written without making a second copy of the pixels."""
    import numpy as np
    height, width, channels = rgb.shape
    if channels != 3 or rgb.dtype != np.uint16:
        raise ConversionError("The developed picture was not 16-bit RGB, so no TIFF was made.")
    data_bytes = width * height * 6
    if data_bytes >= 2 ** 32 - 1024:
        raise ConversionError("That picture is too big for one TIFF strip.")
    profile = _srgb_profile()
    rgb = np.ascontiguousarray(rgb.astype("<u2", copy=False))

    SHORT, LONG, RATIONAL, UNDEFINED = 3, 4, 5, 7
    tags = [
        (256, LONG, 1, width), (257, LONG, 1, height),
        (258, SHORT, 3, struct.pack("<3H", 16, 16, 16)),
        (259, SHORT, 1, 1), (262, SHORT, 1, 2),
        (273, LONG, 1, None),
        (277, SHORT, 1, 3), (278, LONG, 1, height), (279, LONG, 1, data_bytes),
        (282, RATIONAL, 1, struct.pack("<II", 72, 1)), (283, RATIONAL, 1, struct.pack("<II", 72, 1)),
        (284, SHORT, 1, 1), (296, SHORT, 1, 2),
    ]
    if profile:
        tags.append((34675, UNDEFINED, len(profile), profile))
    tags.sort(key=lambda t: t[0])
    ifd_size = 2 + len(tags) * 12 + 4
    extra_at = 8 + ifd_size
    extra = bytearray()
    placed = []
    for tag, typ, count, value in tags:
        if isinstance(value, bytes) and len(value) > 4:
            placed.append((tag, typ, count, extra_at + len(extra)))
            extra += value + (b"\0" if len(value) % 2 else b"")
        elif isinstance(value, bytes):
            placed.append((tag, typ, count, int.from_bytes(value.ljust(4, b"\0"), "little")))
        else:
            placed.append((tag, typ, count, value))
    data_at = extra_at + len(extra)
    with open(out_path, "wb") as out:
        out.write(b"II*\0" + struct.pack("<I", 8) + struct.pack("<H", len(tags)))
        for tag, typ, count, value in placed:
            if tag == 273:
                value = data_at
            out.write(struct.pack("<HHII", tag, typ, count, value))
        out.write(struct.pack("<I", 0))
        out.write(extra)
        rgb.tofile(out)

def describe(path, src_ext: str) -> "RawInfo | None":
    """inspect(), or None for a file that cannot be read -- for the menu, which would rather say nothing than refuse a file the converter might still take."""
    try:
        return inspect(Path(path), src_ext)
    except ConversionError:
        return None

# ─── module: convert_bot.ocr_convert ─────────────────────────────────────────
"""Text from pictures and scanned PDFs, recognised on this machine."""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import convert_utils
import formats
from convert_utils import ConversionError, OutOfMemory, Result, report

OCR_MAX_PIXELS = int(os.environ.get("CONVERT_OCR_MAX_PIXELS") or 12_000_000)

OCR_PAGE_S = int(os.environ.get("CONVERT_OCR_PAGE_SECONDS") or 15)

OCR_MAX_PAGES = int(os.environ.get("CONVERT_OCR_MAX_PAGES") or 30)

OCR_DESCRIBE_SECONDS = float(os.environ.get("CONVERT_OCR_DESCRIBE_SECONDS") or 5)

OCR_FREE_PAGES = int(os.environ.get("CONVERT_OCR_FREE_PAGES") or 1)

OCR_MIN_TEXT_CHARS = int(os.environ.get("CONVERT_OCR_MIN_TEXT_CHARS") or 20)

OCR_MIN_DPI = int(os.environ.get("CONVERT_OCR_MIN_DPI") or 50)

OCR_MAX_DECODE_PIXELS = int(os.environ.get("CONVERT_OCR_MAX_DECODE_PIXELS") or 64_000_000)
MAX_DPI = 300

WRITES = frozenset({"txt", "ocrpdf"})

LANGS = {"eng": "eng", "rus": "rus", "uzb": "uzb+uzb_cyrl"}
CHOICES = tuple(LANGS)

DEFAULT_CHOICE = {"en": "eng", "ru": "rus", "uz": "uzb"}

_TRAINEDDATA = ("eng", "rus", "uzb", "uzb_cyrl")

def tesseract_language(choice) -> str:
    """The language string for a choice."""
    return LANGS.get(choice or "", LANGS["eng"])

def default_choice(lang) -> str:
    """The text language a person gets before they have chosen one."""
    return DEFAULT_CHOICE.get(lang or "", "eng")

def tessdata_dir() -> "str | None":
    """TESSDATA_PREFIX when it holds all four language files, else None."""
    folder = os.environ.get("TESSDATA_PREFIX") or ""
    if folder and all(os.path.isfile(os.path.join(folder, f"{name}.traineddata")) for name in _TRAINEDDATA):
        return folder
    return None

def available() -> bool:
    """Whether this host can recognise text: PyMuPDF with the engine in it, and the language data."""
    try:
        import pymupdf
        if not (hasattr(pymupdf.Pixmap, "pdfocr_tobytes") and hasattr(pymupdf.Page, "delete_image")
                and hasattr(pymupdf.TOOLS, "store_shrink")):
            return False
    except Exception:
        return False
    return tessdata_dir() is not None

def _pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError as exc:
        raise ConversionError("Text recognition isn't available on this host.") from exc

def _tidy(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:160] or type(exc).__name__

def ocr_dpi(width_pt, height_pt) -> "int | None":
    """The dpi to draw a page of this size at for the engine: 300 where that stays under OCR_MAX_PIXELS, less where it does not (an A0 poster comes out at 87 or so)."""
    try:
        width, height = float(width_pt), float(height_pt)
    except (TypeError, ValueError):
        return None
    if not (width > 0 and height > 0):
        return None
    dpi = min(MAX_DPI, math.floor(72 * math.sqrt(OCR_MAX_PIXELS / (width * height)) + 1e-6))
    while dpi >= OCR_MIN_DPI and ((math.ceil(width * dpi / 72) + 1)
                                  * (math.ceil(height * dpi / 72) + 1)) > OCR_MAX_PIXELS:
        dpi -= 1
    return dpi if dpi >= OCR_MIN_DPI else None

def is_scanned(page) -> bool:
    """A page that is a picture of text: there is a picture on it, it has too little text of its own, and it can be drawn at a size the engine can read."""
    if not page.get_images():
        return False
    rect = page.rect
    if ocr_dpi(rect.width, rect.height) is None:
        return False
    return len("".join(page.get_text("text").split())) < OCR_MIN_TEXT_CHARS

def _open_pdf(path):
    pymupdf = _pymupdf()
    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise ConversionError(f"Couldn't read that PDF: {_tidy(exc)}") from exc
    if not doc.is_pdf:
        doc.close()
        raise ConversionError("Couldn't read that as a PDF.")
    if doc.needs_pass:
        doc.close()
        raise ConversionError("That PDF is password-protected, so its pages can't be read.")
    return doc

def count_scanned(path, on_pages=None, scan: bool = True, stop_after: "int | None" = None) -> dict:
    """{"pages": n, "scanned": m} for a PDF: its page count, and how many of its first formats.MAX_PAGES pages are scanned."""
    doc = _open_pdf(path)
    try:
        pages = int(doc.page_count)
        if on_pages is not None:
            on_pages(pages)
        if not scan:
            return {"pages": pages, "scanned": None}
        scanned = 0
        for index in range(min(pages, formats.MAX_PAGES)):
            page = doc.load_page(index)
            if is_scanned(page):
                scanned += 1
            del page
            if stop_after is not None and scanned > stop_after:
                break
        return {"pages": pages, "scanned": scanned}
    except ConversionError:
        raise
    except MemoryError:
        raise OutOfMemory("reading that PDF ran out of memory") from None
    except Exception as exc:
        raise ConversionError(f"Couldn't read that PDF: {_tidy(exc)}") from exc
    finally:
        doc.close()

def _recognise(pymupdf, page, language: str, tessdata: str, layer: bool) -> str:
    """The text on one scanned page."""
    dpi = ocr_dpi(page.rect.width, page.rect.height)
    if dpi is None:
        return ""
    pix = page.get_pixmap(dpi=dpi)
    try:
        data = pix.pdfocr_tobytes(compress=True, language=language, tessdata=tessdata)
    finally:
        del pix
    ocr = pymupdf.open("pdf", data)
    del data
    try:
        text = ocr[0].get_text()
        if layer and text.strip():
            for item in ocr[0].get_images(full=True):
                ocr[0].delete_image(item[0])

            rotation = page.rotation
            page.set_rotation(0)
            try:
                page.show_pdf_page(page.rect, ocr, 0, overlay=True, rotate=rotation)
            finally:
                page.set_rotation(rotation)
    finally:
        ocr.close()

        pymupdf.TOOLS.store_shrink(100)
    return text

def _pdf(in_path, target_ext: str, out_path: Path, language: str, tessdata: str,
         max_scanned: "int | None" = None) -> None:
    import doc_convert
    pymupdf = _pymupdf()
    doc = _open_pdf(in_path)
    try:
        pages = doc_convert._page_count(doc)
        if not pages:
            raise ConversionError("That document had no pages in it.")
        scanned = []
        for index in range(pages):
            page = doc.load_page(index)
            if is_scanned(page):
                scanned.append(index)
            del page
        if len(scanned) > OCR_MAX_PAGES:
            raise ConversionError(
                f"{len(scanned)} pages of that PDF are pictures without text. Text is recognised on at "
                f"most {OCR_MAX_PAGES} such pages in one conversion. Split it and send the part you need.")
        if max_scanned is not None and len(scanned) > max_scanned:

            raise ConversionError(
                f"{len(scanned)} pages of that PDF are pictures without text, more than the {max_scanned} "
                "this conversion was priced for. Send the PDF again.")
        if target_ext == "ocrpdf" and not scanned:
            raise ConversionError("Every page of that PDF has its text already, so there is nothing to recognise.")

        wanted = set(scanned)
        texts = []
        found = False
        done = 0

        for index in (range(pages) if target_ext == "txt" else scanned):
            page = doc.load_page(index)
            if index in wanted:
                report(done, len(scanned))
                text = _recognise(pymupdf, page, language, tessdata, layer=target_ext == "ocrpdf")
                done += 1
            else:
                text = page.get_text()
            found = found or bool(text.strip())
            del page
            if target_ext == "txt":
                texts.append(text)
        report(len(scanned), len(scanned))

        if not found:
            raise ConversionError("No text was found in that PDF.")
        if target_ext == "txt":

            out_path.write_text("\n".join(texts), encoding="utf-8")
        else:
            doc.save(str(out_path), garbage=3, deflate=True)
    finally:
        doc.close()

_EXIF_ORIENTATION = 0x0112

def _too_large(pixels: float = 0) -> ConversionError:
    size = f"{pixels / 1_000_000:.0f} megapixels" if pixels else "too big"
    return ConversionError(
        f"That picture is {size}. Text is read from pictures up to "
        f"{OCR_MAX_DECODE_PIXELS // 1_000_000} megapixels here, or from a JPEG of any size the bot takes. "
        "Send a smaller copy.")

_GREY_16_TO_8 = [value >> 8 for value in range(65536)]

_GREY_BAND_PIXELS = 1_000_000

def _eight_bit(im):
    """The picture as L, RGB or RGBA, which is what a resize and a JPEG can take."""
    from PIL import Image
    mode = im.mode
    if mode in ("L", "RGB", "RGBA"):
        return im
    if mode == "1":
        return im.convert("L")
    if mode == "I":

        return im.point(_GREY_16_TO_8, "L")
    if mode.startswith("I;16"):

        width, height = im.size
        rows = max(1, _GREY_BAND_PIXELS // max(1, width))
        grey = Image.new("L", im.size)
        for top in range(0, height, rows):
            band = im.crop((0, top, width, min(height, top + rows)))
            grey.paste(band.convert("I").point(_GREY_16_TO_8, "L"), (0, top))
        return grey
    if mode in ("LA", "PA") or (mode == "P" and "transparency" in im.info):
        return im.convert("RGBA")
    return im.convert("RGB")

def _tiff_pages(im) -> int:
    """How many pages (directories) an opened TIFF holds, counted from the file's headers and without decoding a pixel."""
    try:
        im.seek(1)
    except Exception:
        return 1
    try:
        return max(2, int(im.n_frames))
    except Exception:
        return 2
    finally:
        try:
            im.seek(0)
        except Exception:
            pass

def _picture(in_path):
    """A picture ready to be a PDF page: (bytes, format name, width, height)."""
    import io
    from PIL import Image
    convert_utils.register_openers()
    try:
        im = Image.open(in_path)
    except Image.DecompressionBombError as exc:
        raise _too_large() from exc
    except MemoryError:
        raise
    except Exception as exc:
        raise ConversionError(f"Couldn't read that as an image: {_tidy(exc)}") from exc
    try:
        source_format = im.format
        pages = _tiff_pages(im) if source_format == "TIFF" else 1
        if pages > 1:

            raise ConversionError(
                f"That TIFF holds {pages} pages. Text is read from a one-page picture: "
                "convert the TIFF to PDF first, then choose TXT or Searchable PDF.")
        width, height = im.size
        if width * height > OCR_MAX_PIXELS:
            scale = math.sqrt(OCR_MAX_PIXELS / (width * height))
            im.draft("RGB", (max(1, math.ceil(width * scale)), max(1, math.ceil(height * scale))))

        if im.size[0] * im.size[1] > OCR_MAX_DECODE_PIXELS:
            raise _too_large(width * height)
        try:
            im.load()
        except MemoryError:
            raise OutOfMemory("decoding that picture ran out of memory") from None
        except Exception as exc:
            raise ConversionError(f"Couldn't read that as an image: {_tidy(exc)}") from exc

        orientation = 1
        if source_format not in convert_utils._ORIENTED_BY_CONTAINER:
            try:
                orientation = im.getexif().get(_EXIF_ORIENTATION, 1)
            except Exception:
                orientation = 1
        picture = _eight_bit(im)
        if picture is not im:
            im.close()
        if picture.size[0] * picture.size[1] > OCR_MAX_PIXELS:
            scale = math.sqrt(OCR_MAX_PIXELS / (picture.size[0] * picture.size[1]))
            smaller = picture.resize((max(1, math.floor(picture.size[0] * scale)),
                                      max(1, math.floor(picture.size[1] * scale))), Image.LANCZOS)
            picture.close()
            picture = smaller
        if picture.mode == "RGBA":
            flat = convert_utils._flatten_onto_white(picture)
            picture.close()
            picture = flat
        if orientation in (2, 3, 4, 5, 6, 7, 8):
            turn = Image.Transpose
            turned = picture.transpose({2: turn.FLIP_LEFT_RIGHT, 3: turn.ROTATE_180, 4: turn.FLIP_TOP_BOTTOM,
                                        5: turn.TRANSPOSE, 6: turn.ROTATE_270, 7: turn.TRANSVERSE,
                                        8: turn.ROTATE_90}[orientation])
            picture.close()
            picture = turned
        out = io.BytesIO()
        try:
            if source_format == "PNG":
                picture.save(out, format="PNG")
            else:
                picture.save(out, format="JPEG", quality=90)
        except MemoryError:
            raise OutOfMemory("saving that picture ran out of memory") from None
        except Exception as exc:
            raise ConversionError(f"Couldn't read that as an image: {_tidy(exc)}") from exc
        result = (out.getvalue(), picture.size[0], picture.size[1])
        picture.close()
        return result
    finally:
        im.close()

def _image(in_path, src_ext: str, target_ext: str, out_path: Path, language: str, tessdata: str) -> None:
    pymupdf = _pymupdf()
    data, width, height = _picture(in_path)

    doc = pymupdf.open()
    try:
        page = doc.new_page(width=max(width, 1) * 72 / MAX_DPI, height=max(height, 1) * 72 / MAX_DPI)
        page.insert_image(page.rect, stream=data)
        del data
        report(0, 1)
        text = _recognise(pymupdf, page, language, tessdata, layer=target_ext == "ocrpdf")
        report(1, 1)
        if not text.strip():
            raise ConversionError("No text was found in that picture.")
        if target_ext == "txt":
            out_path.write_text(text, encoding="utf-8")
        else:
            doc.save(str(out_path), garbage=3, deflate=True)
    finally:
        doc.close()

def convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str = "converted",
            lang: str = "eng", max_scanned: "int | None" = None) -> Result:
    """Text from a picture or a PDF as `target_ext`: "txt", or "ocrpdf" (a searchable PDF, written as `<stem>.pdf`)."""
    src_ext = formats.normalise(src_ext)
    target_ext = formats.normalise(target_ext)
    if target_ext not in WRITES:
        raise ConversionError(f"Text isn't recognised into .{target_ext}.")

    animated = convert_utils.gif_is_animated(in_path) if src_ext in formats.ANIMATED_CAPABLE else None
    if animated:
        raise ConversionError("Text isn't recognised in an animation.")
    is_picture = (formats.category_of(src_ext, animated) == formats.IMAGE
                  and src_ext not in formats.RAW_FORMATS and src_ext != "svg")
    if src_ext != "pdf" and not is_picture:
        raise ConversionError(f"Text can't be recognised in a .{src_ext} file.")
    if src_ext != "pdf" and max_scanned is not None and max_scanned < 1:
        raise ConversionError("That conversion was not priced for reading any page.")
    tessdata = tessdata_dir()
    if tessdata is None:
        raise ConversionError("Text recognition isn't available on this host.")
    out_path = Path(work_dir) / f"{stem}.{'txt' if target_ext == 'txt' else 'pdf'}"
    if os.path.realpath(in_path) == os.path.realpath(out_path):
        raise ConversionError("The result would overwrite the original.")
    language = tesseract_language(lang)
    try:
        if src_ext == "pdf":
            _pdf(in_path, target_ext, out_path, language, tessdata, max_scanned)
        else:
            _image(in_path, src_ext, target_ext, out_path, language, tessdata)
    except ConversionError:
        out_path.unlink(missing_ok=True)
        raise
    except MemoryError:
        out_path.unlink(missing_ok=True)
        raise OutOfMemory("recognising the text ran out of memory") from None
    except Exception as exc:
        out_path.unlink(missing_ok=True)
        raise ConversionError(f"Couldn't recognise the text: {_tidy(exc)}") from exc
    return Result(out_path)

def selftest() -> None:
    """Exits 1 with a one-line reason unless the language data is there and the engine reads a line of English and a line of Russian back."""
    def fail(reason: str):
        sys.stderr.write(f"OCR self-test failed: {reason}\n")
        raise SystemExit(1)

    folder = os.environ.get("TESSDATA_PREFIX") or ""
    missing = [name for name in _TRAINEDDATA if not os.path.isfile(os.path.join(folder, f"{name}.traineddata"))]
    if missing:
        fail(f"no language data for {', '.join(missing)} in TESSDATA_PREFIX={folder!r}")
    try:
        import pymupdf
    except ImportError:
        fail("PyMuPDF is not installed")
    if not hasattr(pymupdf.Pixmap, "pdfocr_tobytes"):
        fail("this PyMuPDF has no text recognition (Pixmap.pdfocr_tobytes)")
    font = pymupdf.Font("helv")
    for language, line, words in (("eng", "MumuBots OCR 2026", ("MumuBots", "OCR", "2026")),
                                  ("rus", "Проверка текста", ("Проверка", "текста"))):
        try:
            doc = pymupdf.open()
            page = doc.new_page(width=520, height=120)
            writer = pymupdf.TextWriter(page.rect)
            writer.append((20, 70), line, font=font, fontsize=36)
            writer.write_text(page)
            recognised = pymupdf.open("pdf", page.get_pixmap(dpi=200).pdfocr_tobytes(
                compress=True, language=language, tessdata=folder))[0].get_text()
        except Exception as exc:
            fail(f"reading {language} failed: {_tidy(exc)}")
        for word in words:
            if word not in recognised:
                fail(f"read {line!r} ({language}) as {' '.join(recognised.split())!r}")

# ─── module: convert_bot.convert_worker ──────────────────────────────────────
"""One conversion, in a process of its own."""
import json
import os
import sys
import traceback
import warnings


PROGRESS_EVERY_S = 1.0

def _emit(ok: bool, **fields) -> None:
    fields["ok"] = ok
    sys.stdout.write("\n" + json.dumps(fields) + "\n")
    sys.stdout.flush()

def _cap_memory(max_memory_mb: int) -> None:
    """Give the worker a MemoryError instead of letting the kernel pick a victim."""
    if not max_memory_mb or os.name != "posix":
        return
    try:
        import resource
        limit = int(max_memory_mb) * 1024 * 1024
        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
    except Exception:
        pass

def _describe_raw(job: dict) -> int:
    """Read a camera raw photo's size without decoding it (raw_convert.inspect) and say it as JSON."""
    try:
        import convert_utils
        import raw_convert
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"could not load the converters: {exc}")
        return 1
    try:
        info = raw_convert.inspect(job["path"], job.get("src_ext") or "dng")
    except MemoryError:
        _emit(False, kind="no_memory", message="reading the raw photo ran out of memory")
        return 2
    except convert_utils.ConversionError as exc:
        _emit(False, kind="refused", message=str(exc))
        return 2
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"{type(exc).__name__}: {exc}")
        return 1
    _emit(True, info=info._asdict())
    return 0

def _describe_image(job: dict) -> int:
    """A picture's width and height from Pillow's header read, as JSON (jobs.describe_image)."""
    try:
        import convert_utils
        from PIL import Image
        convert_utils.register_openers()
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(job["path"]) as img:
            width, height = img.size
    except MemoryError:
        _emit(False, kind="no_memory", message="reading the picture's size ran out of memory")
        return 2
    except Exception as exc:
        _emit(False, kind="refused", message=type(exc).__name__)
        return 2
    _emit(True, width=int(width), height=int(height))
    return 0

def _describe_pdf(job: dict) -> int:
    """A PDF's page count and how many pages are pictures without text (ocr_convert.count_scanned), as JSON (jobs.describe_pdf)."""
    try:
        import convert_utils
        import ocr_convert
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"could not load the converters: {exc}")
        return 1

    def say_pages(pages: int) -> None:
        sys.stdout.write(json.dumps({"pages": int(pages)}) + "\n")
        sys.stdout.flush()

    try:
        counted = ocr_convert.count_scanned(job["path"], on_pages=say_pages, scan=ocr_convert.available(),
                                            stop_after=ocr_convert.OCR_MAX_PAGES)
    except MemoryError:
        _emit(False, kind="no_memory", message="reading the PDF ran out of memory")
        return 2
    except convert_utils.OutOfMemory as exc:
        _emit(False, kind="no_memory", message=str(exc))
        return 2
    except convert_utils.ConversionError as exc:
        _emit(False, kind="refused", message=str(exc))
        return 2
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"{type(exc).__name__}: {exc}")
        return 1
    scanned = counted["scanned"]
    _emit(True, pages=int(counted["pages"]), scanned=None if scanned is None else int(scanned))
    return 0

def main(argv) -> int:
    if len(argv) < 2:
        _emit(False, kind="crash", message="no job was given to the worker")
        return 1
    try:
        job = json.loads(argv[1])
    except ValueError as exc:
        _emit(False, kind="crash", message=f"the job was not valid JSON: {exc}")
        return 1

    _cap_memory(job.get("max_memory_mb") or 0)

    warnings.simplefilter("ignore")

    if job.get("kind") == "describe_raw":
        return _describe_raw(job)
    if job.get("kind") == "describe_image":
        return _describe_image(job)
    if job.get("kind") == "describe_pdf":
        return _describe_pdf(job)

    try:
        import convert_utils
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"could not load the converters: {exc}")
        return 1

    import time
    last = [0.0]

    def progress(done, total):
        now = time.monotonic()
        if now - last[0] >= PROGRESS_EVERY_S or done >= total:
            last[0] = now
            sys.stdout.write(json.dumps({"progress": [round(float(done), 3), round(float(total), 3)]}) + "\n")
            sys.stdout.flush()

    convert_utils.PROGRESS = progress

    try:
        from PIL import Image
        if job.get("max_pixels"):
            Image.MAX_IMAGE_PIXELS = int(job["max_pixels"])
    except Exception:
        pass

    try:
        result = convert_utils.convert(
            job["in_paths"], job["src_ext"], job["target_ext"],
            job["work_dir"], job.get("stem") or "converted",
            ocr_lang=job.get("ocr_lang") or "", ocr_pages=int(job.get("ocr_pages") or 0),
        )
    except convert_utils.OutOfMemory as exc:
        _emit(False, kind="no_memory", message=str(exc))
        return 2
    except convert_utils.ConversionError as exc:
        _emit(False, kind="refused", message=str(exc))
        return 2
    except MemoryError:
        _emit(False, kind="no_memory", message="the conversion ran out of memory (MemoryError)")
        return 2
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"{type(exc).__name__}: {exc}")
        return 1

    path = str(result.path)
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        _emit(False, kind="crash", message=f"the converter reported a file that is not there: {exc}")
        return 1
    _emit(True, path=path, zipped=bool(getattr(result, "zipped", False)),
          items=int(getattr(result, "items", 1) or 1), bytes=size)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

# ─── module: convert_bot.jobs ────────────────────────────────────────────────
"""The conversion queue, and what happens to the credit."""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import math
import os
import shutil
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import big_files

logger = logging.getLogger(__name__)

HERE = Path(__spec__.origin if __spec__ else __file__).resolve().parent
WORKER = HERE / "main.py"
WORKER_ARGS = ("--module", "convert_bot.convert_worker")

LOCAL_BOT_API = bool(os.environ.get("LOCAL_BOT_API_URL"))

MAX_CONCURRENT = max(1, int(os.environ.get("CONVERT_MAX_CONCURRENT") or 1))

TIME_LIMIT_S = int(os.environ.get("CONVERT_TIME_LIMIT_SECONDS") or 600)

FREE_TIME_LIMIT_S = int(os.environ.get("CONVERT_FREE_TIME_LIMIT_SECONDS") or 60)

TIME_BASE_S = int(os.environ.get("CONVERT_TIME_BASE_SECONDS") or 120)
TIME_PER_MB_S = float(os.environ.get("CONVERT_TIME_PER_MB_SECONDS") or 1.0)

def time_limit_for(billable_bytes: int, work: float = 1.0, paid: bool = True) -> int:
    """How long a conversion may run, in seconds."""
    if not paid:
        return FREE_TIME_LIMIT_S
    wanted = TIME_BASE_S + TIME_PER_MB_S * work * billable_bytes / (1024 * 1024)
    return int(min(TIME_LIMIT_S, max(TIME_BASE_S, wanted)))

def ocr_time_limit(ocr_pages: int, paid: bool, billable: int = 0, work: float = 1.0) -> int:
    """How long a job that recognises text may run: what any conversion of that file is given (time_limit_for: TIME_BASE_S, and a second more for every megabyte of work in the file and its result), and OCR_PAGE_S more for every page it reads, up to TIME_LIMIT_S."""
    if not paid:
        return FREE_TIME_LIMIT_S
    import ocr_convert
    return int(min(TIME_LIMIT_S, time_limit_for(billable, work, True) + max(0, ocr_pages) * ocr_convert.OCR_PAGE_S))

def job_limit(job: "Job") -> int:
    """The limit this job runs under: its own, or for a job made before it had one, the flat limit of its kind."""
    return job.time_limit or (TIME_LIMIT_S if job.price > 0 else FREE_TIME_LIMIT_S)

PROJECT_AFTER_S = 30
PROJECT_MARGIN = 1.2

PROGRESS_MARKS_S = (120, 300)

MAX_QUEUED_PER_USER = max(1, int(os.environ.get("CONVERT_MAX_QUEUED_PER_USER") or 5))

def _default_user_storage_mb() -> int:
    try:
        import convert_utils
        import formats
        album = formats.MAX_BATCH * convert_utils.MAX_FILE_MB
        return min(album, max(2000, 2 * convert_utils.MAX_FILE_MB)) + 50
    except Exception:
        return 450

USER_STORAGE_MB = int(os.environ.get("CONVERT_USER_STORAGE_MB") or max(120, _default_user_storage_mb()))
STORAGE_MB = int(os.environ.get("CONVERT_STORAGE_MB") or max(1024, USER_STORAGE_MB + 200))
MIN_FREE_MB = int(os.environ.get("CONVERT_MIN_FREE_MB") or 300)

MAX_MEGAPIXELS = int(os.environ.get("CONVERT_MAX_MEGAPIXELS") or 210)

CARD_EVERY_S = 3.0

HOLD_TOUCH_S = 30
HOLD_STALE_S = 120

WORKER_MAX_MEMORY_MB = int(os.environ.get("CONVERT_WORKER_MAX_MEMORY_MB") or 0)

SEND_LIMIT_MB = big_files.BOT_API_SEND_BYTES // (1024 * 1024)
SEND_LIMIT_BYTES = SEND_LIMIT_MB * 1024 * 1024

BIG_SEND_MAX_BYTES = big_files.MTPROTO_MAX_BYTES
SEND_HEADROOM = 3

def big_sends(chat_id: int) -> bool:
    """Whether a result over 50 MB can reach this chat at all."""
    return LOCAL_BOT_API or big_files.usable(chat_id)

def big_send_limit(out_estimate: int) -> int:
    """The largest result a conversion estimated at `out_estimate` bytes may send where big sends can reach, which is what its price covers."""
    return min(BIG_SEND_MAX_BYTES, max(SEND_LIMIT_BYTES, SEND_HEADROOM * max(0, out_estimate or 0)))

def send_limit_for(in_bytes: int, out_estimate: int | None, chat_id: int) -> int:
    """The largest result this conversion may send back, in bytes."""
    if not big_sends(chat_id):
        return SEND_LIMIT_BYTES
    return big_send_limit(out_estimate if out_estimate else in_bytes)

def send_ceiling_mb(chat_id: int) -> int:
    """The most any result could be sent at in this chat, for sentences about a format that is off the menu for being too big."""
    return (BIG_SEND_MAX_BYTES if big_sends(chat_id) else SEND_LIMIT_BYTES) // (1024 * 1024)

LOSSLESS_BYTES_PER_PIXEL = {
    "bmp": 3.0,
    "ppm": 3.0,
    "tga": 3.0,
    "tiff": 0.6,
    "png": 0.5,
    "qoi": 0.5,
}

RAW_LOSSLESS_BYTES_PER_PIXEL = {"tiff": 6.0}

TARGET_MAX_MEGAPIXELS = {
    "heic": 142.6,
}

USER_CANCELLED = "user_cancelled"
NO_CREDIT = "no_credit"
REFUSED = "refused"
TIMEOUT = "timeout"

TOO_SLOW = "too_slow"
CRASH = "crash"

NO_MEMORY = "no_memory"
TOO_LARGE = "too_large"
SEND_FAILED = "send_failed"
INTERRUPTED = "interrupted"

PAUSED = "paused"

REFUNDED = frozenset({REFUSED, TIMEOUT, TOO_SLOW, CRASH, NO_MEMORY, TOO_LARGE, SEND_FAILED, INTERRUPTED})

ALERTED = frozenset({TIMEOUT, CRASH, TOO_LARGE, SEND_FAILED, INTERRUPTED})

_sequence = itertools.count()

@dataclass
class Job:
    user_id: int
    chat_id: int
    paths: list
    src_ext: str
    target_ext: str
    size: int
    price: int
    lang: str
    username: str | None = None
    keep_file: bool = False

    send_limit: int = SEND_LIMIT_BYTES

    time_limit: int = 0

    ocr_lang: str = ""
    ocr_pages: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    state: str = "queued"
    charged: bool = False
    user_cancelled: bool = False
    task: asyncio.Task | None = None
    proc: object | None = None
    queued_at: float = field(default_factory=time.monotonic)
    seq: int = field(default_factory=lambda: next(_sequence))
    started_at: float | None = None
    extra: dict = field(default_factory=dict)

@dataclass
class Outcome:
    ok: bool
    kind: str | None = None
    message: str = ""
    path: str | None = None
    zipped: bool = False
    items: int = 1
    bytes: int = 0

_jobs: dict[str, Job] = {}
_user_locks: dict[int, asyncio.Lock] = {}
_slots: asyncio.Semaphore | None = None

def reset() -> None:
    """For tests, which run each scenario on a fresh event loop: asyncio primitives belong to the loop they were first used on."""
    global _slots
    _jobs.clear()
    _user_locks.clear()
    _slots = None

def _global_slots() -> asyncio.Semaphore:
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(MAX_CONCURRENT)
    return _slots

def get(job_id: str) -> Job | None:
    return _jobs.get(job_id)

def jobs_for(user_id: int) -> list[Job]:
    return sorted((job for job in _jobs.values() if job.user_id == user_id),
                  key=lambda job: job.seq)

def ahead_of(job: Job) -> int:
    """How many jobs will start before this one, across everybody."""
    return sum(1 for other in _jobs.values()
               if other is not job and other.state in ("queued", "running")
               and other.seq < job.seq)

def active_paths() -> set[str]:
    """Every staged file a queued or running job still needs."""
    return {str(path) for job in _jobs.values() for path in job.paths}

def active_stems() -> set[str]:
    """The stems (job_stem) of every queued or running job: what the files and folders a job makes for itself in the work directory are named after."""
    return {job_stem(job) for job in _jobs.values()}

def uncharged_total(user_id: int) -> int:
    """Credit this person's queued jobs will need when they start."""
    return sum(job.price for job in _jobs.values()
               if job.user_id == user_id and not job.charged)

def storage_problem(user_id: int, incoming_bytes: int, upload_dir) -> tuple[str, int, int] | None:
    """None if there is room for `incoming_bytes` more; otherwise which limit stops it -- "user", "global" or "disk" -- with the MB used and the limit."""
    upload_dir = Path(upload_dir)
    mb = 1024 * 1024
    used_all = used_user = 0
    prefix = f"{user_id}-"
    if upload_dir.is_dir():
        for path in upload_dir.iterdir():
            try:
                if path.is_file():
                    size = path.stat().st_size
                    used_all += size
                    if path.name.startswith(prefix):
                        used_user += size
            except OSError:
                continue
    if USER_STORAGE_MB and used_user + incoming_bytes > USER_STORAGE_MB * mb:
        return ("user", used_user // mb, USER_STORAGE_MB)
    if STORAGE_MB and used_all + incoming_bytes > STORAGE_MB * mb:
        return ("global", used_all // mb, STORAGE_MB)
    try:
        probe = upload_dir if upload_dir.is_dir() else upload_dir.parent
        free = shutil.disk_usage(probe).free
    except OSError:
        free = None
    if free is not None and MIN_FREE_MB and free - incoming_bytes < MIN_FREE_MB * mb:
        return ("disk", free // mb, MIN_FREE_MB)
    return None

def estimate_output_bytes(megapixels: float | None, target_ext: str, raw: bool = False) -> int | None:
    ratio = (RAW_LOSSLESS_BYTES_PER_PIXEL.get(target_ext) if raw else None) or LOSSLESS_BYTES_PER_PIXEL.get(target_ext)
    if megapixels is None or ratio is None:
        return None
    return int(megapixels * 1_000_000 * ratio)

def unsendable_targets(megapixels: float | None, targets, in_bytes: int = 0,
                       chat_id: int = 0, raw: bool = False) -> list[str]:
    """The formats that would certainly come out too big to send, or that the encoder itself cannot produce at this size."""
    out = []
    for target in targets:
        ceiling = TARGET_MAX_MEGAPIXELS.get(target)
        if megapixels is not None and ceiling is not None and megapixels > ceiling:
            out.append(target)
            continue
        estimate = estimate_output_bytes(megapixels, target, raw)
        if estimate is not None and estimate > send_limit_for(in_bytes, estimate, chat_id):
            out.append(target)
    return out

_OWN_GROUP = {} if sys.platform == "win32" else {"start_new_session": True}

async def _kill(proc) -> None:
    if proc is None or proc.returncode is not None:
        return
    try:
        if sys.platform == "win32":
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/T", "/PID", str(proc.pid),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await killer.wait()
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception:
        logger.debug("Could not kill the conversion worker's group", exc_info=True)
    if proc.returncode is None:
        try:
            proc.kill()
        except ProcessLookupError:
            return
        except Exception:
            logger.debug("Could not kill conversion worker", exc_info=True)
    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
    except Exception:
        logger.debug("Conversion worker did not exit after kill", exc_info=True)

def _parse(returncode, out: bytes, err: bytes) -> Outcome:
    lines = [line for line in (out or b"").decode("utf-8", "replace").splitlines() if line.strip()]
    if lines:
        try:
            data = json.loads(lines[-1])
        except ValueError:
            data = None
        if isinstance(data, dict):
            if data.get("ok"):
                return Outcome(True, None, "", data.get("path"), bool(data.get("zipped")),
                               int(data.get("items") or 1), int(data.get("bytes") or 0))
            return Outcome(False, data.get("kind") or CRASH, str(data.get("message") or ""))
    tail = (err or b"").decode("utf-8", "replace").strip()[-400:]
    if returncode is not None and (returncode < 0 or returncode == 137):
        return Outcome(False, CRASH,
                       f"the worker was killed (exit {returncode}), most likely for memory. {tail}".strip())
    return Outcome(False, CRASH, f"the worker exited {returncode} without a result. {tail}".strip())

async def _start_worker(payload: dict):
    """The one place a child process is started: convert_worker.py, handed its job as a single JSON argument."""
    return await asyncio.create_subprocess_exec(
        sys.executable, "-u", str(WORKER), *WORKER_ARGS, json.dumps(payload),
        cwd=str(HERE), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **_OWN_GROUP,
    )

def job_stem(job: Job) -> str:
    """What a job's own files in the work directory are named after."""
    return f"{job.user_id}-{job.id}-out"

async def run_worker(job: Job, work_dir, stem: str, time_limit: int) -> Outcome:
    payload = {
        "in_paths": [str(path) for path in job.paths],
        "src_ext": job.src_ext,
        "target_ext": job.target_ext,
        "work_dir": str(work_dir),
        "stem": stem,
        "max_pixels": MAX_MEGAPIXELS * 1_000_000,
        "max_memory_mb": WORKER_MAX_MEMORY_MB,
        "ocr_lang": job.ocr_lang,
        "ocr_pages": job.ocr_pages,
    }
    proc = await _start_worker(payload)
    job.proc = proc
    kept: list[bytes] = []
    errors = bytearray()

    async def follow():

        async def drain():
            while chunk := await proc.stderr.read(65536):
                errors.extend(chunk)
                del errors[:-8000]
        draining = asyncio.ensure_future(drain())
        while True:
            try:
                line = await proc.stdout.readline()
            except ValueError:
                continue
            if not line:
                break
            try:
                data = json.loads(line) if line.startswith(b'{"progress"') else None
            except ValueError:
                data = None
            if data is not None:
                done, total = data["progress"]
                job.extra["progress"] = (done, total)
                elapsed = time.monotonic() - started
                if (elapsed >= PROJECT_AFTER_S and total and done > 0 and "projected_s" not in job.extra
                        and elapsed * total / done > time_limit * PROJECT_MARGIN):

                    job.extra["projected_s"] = elapsed * total / done
                    await _kill(proc)
            else:
                kept.append(line)
        await proc.wait()
        await draining

    started = time.monotonic()
    try:
        await asyncio.wait_for(follow(), timeout=time_limit)
        if "projected_s" in job.extra:
            return Outcome(False, TOO_SLOW, f"on course for {job.extra['projected_s']:.0f}s against a "
                                            f"{time_limit}s limit, stopped after {time.monotonic() - started:.0f}s")
        out, err = b"".join(kept), bytes(errors)
    except asyncio.TimeoutError:
        await _kill(proc)
        return Outcome(False, TIMEOUT, f"ran past the {time_limit}s limit")
    except asyncio.CancelledError:
        await asyncio.shield(_kill(proc))
        raise
    finally:
        job.proc = None
    return _parse(proc.returncode, out, err)

DESCRIBE_TIMEOUT_S = 30

def _raw_info(answer: bytes):
    """(the RawInfo in the child's last line of output, "") or (None, why) for anything that is not exactly that."""
    import raw_convert
    lines = [line for line in (answer or b"").decode("utf-8", "replace").splitlines() if line.strip()]
    if not lines:
        return None, "no answer"
    try:
        data = json.loads(lines[-1])
    except ValueError:
        return None, "an answer that is not JSON"
    if not isinstance(data, dict):
        return None, "an answer that is not an object"
    if not data.get("ok"):
        return None, str(data.get("kind") or "crash")
    try:
        fields = data["info"]
        sizes = [fields[name] for name in ("width", "height", "out_width", "out_height")]
        sizes_mp = [fields["megapixels"], fields["out_megapixels"]]
        half = fields["half"]
        if (not isinstance(half, bool) or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in sizes)
                or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n <= 0
                       for n in sizes_mp)):
            return None, "an answer that makes no sense"
        width, height, out_width, out_height = sizes
        megapixels, out_megapixels = (float(n) for n in sizes_mp)
        if (not math.isclose(megapixels, width * height / 1_000_000, rel_tol=1e-9)
                or not math.isclose(out_megapixels, out_width * out_height / 1_000_000, rel_tol=1e-9)):
            return None, "an answer that makes no sense"
    except (KeyError, TypeError):
        return None, "an answer that makes no sense"
    return raw_convert.RawInfo(width, height, megapixels, half, out_width, out_height, out_megapixels), ""

async def describe_raw(path, src_ext: str, timeout: float = DESCRIBE_TIMEOUT_S):
    """raw_convert.describe(), in a child process: the RawInfo of a camera raw photo, or None for one that cannot be read -- which includes a child that crashed, ran past `timeout` (it is killed) or answered nonsense."""
    payload = {"kind": "describe_raw", "path": str(path), "src_ext": src_ext,
               "max_memory_mb": WORKER_MAX_MEMORY_MB}
    answered = await _ask_child(payload, timeout, "a raw photo's size")
    if answered is None:
        return None
    out, returncode = answered
    info, why = _raw_info(out)
    if info is None:

        if why != "refused":
            logger.warning("Reading a raw photo's size failed (%s, exit %s)", why, returncode)
        return None
    return info

async def _ask_child(payload: dict, timeout: float, what: str):
    """Run one describe job in a child (see _start_worker): (its stdout, its exit code), or None -- logged -- when it could not be run or overran `timeout` and was killed."""
    async with _describe_slots:
        return await _ask_child_now(payload, timeout, what)

DESCRIBE_AT_ONCE = 2
_describe_slots = asyncio.Semaphore(DESCRIBE_AT_ONCE)

async def _ask_child_now(payload: dict, timeout: float, what: str):
    proc = None
    try:
        proc = await _start_worker(payload)
        out, _err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        await _kill(proc)
        logger.warning("Reading %s took over %.0f s and was stopped", what, timeout)
        return None
    except asyncio.CancelledError:
        await asyncio.shield(_kill(proc))
        raise
    except Exception as exc:
        await _kill(proc)
        logger.warning("Reading %s failed to run (%s)", what, type(exc).__name__)
        return None
    return out, proc.returncode

def _image_size(answer: bytes) -> "float | None":
    """Megapixels from a describe_image child's last line, or None."""
    lines = [line for line in (answer or b"").decode("utf-8", "replace").splitlines() if line.strip()]
    try:
        data = json.loads(lines[-1])
        width, height = data["width"], data["height"]
    except (IndexError, ValueError, TypeError, KeyError):
        return None
    if not data.get("ok") or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0
                                 for n in (width, height)):
        return None
    return (width * height) / 1_000_000

async def describe_image(path, timeout: float = DESCRIBE_TIMEOUT_S) -> "float | None":
    """A picture's size in megapixels from its header, read in a child process from its header, or None for one that cannot be read."""
    answered = await _ask_child({"kind": "describe_image", "path": str(path),
                                 "max_memory_mb": WORKER_MAX_MEMORY_MB}, timeout, "a picture's size")
    return None if answered is None else _image_size(answered[0])

def _count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def _pdf_info(answer: bytes) -> "dict | None":
    """{"pages": n, "scanned": m} from a describe_pdf child's answer, or None for anything that is not exactly that."""
    lines = [line for line in (answer or b"").decode("utf-8", "replace").splitlines() if line.strip()]
    try:
        last = json.loads(lines[-1])
    except (IndexError, ValueError):
        last = None
    if isinstance(last, dict) and last.get("ok"):
        pages, scanned = last.get("pages"), last.get("scanned", False)
        if not _count(pages) or not (scanned is None or (_count(scanned) and scanned <= pages)):
            return None
        return {"pages": pages, "scanned": scanned}
    for line in lines:
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, dict) and "ok" not in data and _count(data.get("pages")):
            return {"pages": data["pages"], "scanned": None}
    return None

async def _ask_child_partial(payload: dict, timeout: float, what: str):
    """_ask_child, for a child whose first lines are worth having even when the rest is not: (what it wrote, its exit code) -- the exit code None when it overran `timeout` and was killed, with what it had written by then -- or None when it could not be run at all."""
    async with _describe_slots:
        proc = None
        written: list[bytes] = []
        try:
            proc = await _start_worker(payload)

            async def read_out():
                while chunk := await proc.stdout.read(65536):
                    written.append(chunk)
                await proc.wait()

            async def drain_err():
                while await proc.stderr.read(65536):
                    pass
            await asyncio.wait_for(asyncio.gather(read_out(), drain_err()), timeout=timeout)
        except asyncio.TimeoutError:
            await _kill(proc)
            logger.warning("Reading %s took over %.0f s and was stopped", what, timeout)
            return b"".join(written), None
        except asyncio.CancelledError:
            await asyncio.shield(_kill(proc))
            raise
        except Exception as exc:
            await _kill(proc)
            logger.warning("Reading %s failed to run (%s)", what, type(exc).__name__)
            return None
        return b"".join(written), proc.returncode

async def describe_pdf(path, timeout: "float | None" = None) -> "dict | None":
    """How many pages a PDF has and how many of them are pictures without text ({"pages": n, "scanned": m}, ocr_convert.count_scanned), read in a child process, or None for a PDF that cannot be read -- which includes a child that crashed or answered nonsense before it knew the page count."""
    if timeout is None:
        import ocr_convert
        timeout = ocr_convert.OCR_DESCRIBE_SECONDS
    answered = await _ask_child_partial({"kind": "describe_pdf", "path": str(path),
                                         "max_memory_mb": WORKER_MAX_MEMORY_MB}, timeout, "a PDF's pages")
    if answered is None:
        return None
    out, returncode = answered
    info = _pdf_info(out)
    if info is None and returncode not in (0, 2, None):
        logger.warning("Reading a PDF's pages failed (exit %s)", returncode)
    return info

class Runner:
    """What bot.py provides. None of these may raise, except `deliver`, whose exception is the send failure."""

    def work_dir(self) -> Path:
        raise NotImplementedError

    async def refuse_start(self, job: Job) -> bool:
        return False

    async def charge(self, job: Job) -> int | None:
        raise NotImplementedError

    async def started(self, job: Job, balance: int) -> None:
        return None

    async def progress(self, job: Job, stage: int, stages: int, elapsed_s: float,
                       next_s: float | None, limit_s: int) -> None:
        """Still running at `elapsed_s`."""
        return None

    async def deliver(self, job: Job, outcome: Outcome) -> None:
        raise NotImplementedError

    async def succeeded(self, job: Job, outcome: Outcome) -> None:
        return None

    async def refund(self, job: Job, kind: str) -> int:
        raise NotImplementedError

    async def queued(self, job: Job, ahead: int) -> None:
        """Still waiting, with `ahead` jobs in front of it -- called when that changes."""
        return None

    async def card(self, job: Job) -> None:
        """Redraw the status while it runs; called every CARD_EVERY_S."""
        return None

    async def hold(self, job: Job) -> None:
        """A paid conversion has started: record it, so a hard kill cannot keep its credit."""
        return None

    async def release(self, job: Job) -> str:
        """It ended here: "held", "recovered" (already refunded elsewhere) or "absent"."""
        return "absent"

    async def failed(self, job: Job, kind: str, detail: str, refunded_to: int | None) -> None:
        return None

    async def alert(self, job: Job, kind: str, detail: str, elapsed: float,
                    refunded_to: int | None) -> None:
        return None

async def _safe(awaitable):
    try:
        return await awaitable
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("A conversion job hook failed")
        return None

def _unlink(path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        logger.debug("Could not remove %s", path, exc_info=True)

def remove_job_leftovers(work_dir, stem: str) -> int:
    """Remove what a conversion named `stem` leaves in `work_dir` when it is killed: the folder `<stem>-contents` an archive was unpacked into and the padded copy `<stem>-source.<ext>` bsdtar reads."""
    if not stem or stem in (".", "..") or any(sep in stem for sep in ("/", "\\", os.sep)):
        return 0
    try:
        entries = list(os.scandir(work_dir))
        base = os.path.normcase(os.path.realpath(work_dir))
    except OSError:
        return 0
    import convert_utils
    removed = 0
    for entry in entries:
        try:
            contents = entry.name == f"{stem}-contents"
            if not (contents or entry.name.startswith(f"{stem}-source.")):
                continue
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                os.unlink(entry.path)
            elif contents:
                if os.path.normcase(os.path.dirname(os.path.realpath(entry.path))) != base:
                    logger.warning("Not removing %s: it does not resolve inside the work directory", entry.name)
                    continue
                convert_utils.remove_tree(entry.path)
                if os.path.lexists(entry.path):
                    continue
            else:
                continue
            removed += 1
        except OSError:
            logger.debug("Could not remove %s", entry.path, exc_info=True)
    return removed

async def _finish(job: Job, runner: Runner, kind: str | None, detail: str,
                  outcome: Outcome | None) -> None:
    try:
        elapsed = time.monotonic() - job.started_at if job.started_at else 0.0
        held = await _safe(runner.release(job)) if job.charged else None
        if kind is None:
            await _safe(runner.succeeded(job, outcome))
            return
        refunded_to = None
        if job.charged and kind in REFUNDED and held == "recovered":

            logger.warning("Conversion %s ended %s after it had been refunded as lost", job.id, kind)
            job.charged = False
        if job.charged and kind in REFUNDED:
            try:
                refunded_to = await runner.refund(job, kind)
                job.charged = False
            except Exception:
                logger.exception("Refunding conversion %s failed", job.id)
        await _safe(runner.failed(job, kind, detail, refunded_to))
        if kind in ALERTED:
            await _safe(runner.alert(job, kind, detail, elapsed, refunded_to))
    finally:
        _jobs.pop(job.id, None)
        job.state = "done"
        if outcome is not None and outcome.path:
            _unlink(outcome.path)
        if not job.keep_file:
            still_needed = active_paths()
            for path in job.paths:
                if str(path) not in still_needed:
                    _unlink(path)
        lock = _user_locks.get(job.user_id)
        if lock is not None and not lock.locked() and not getattr(lock, "_waiters", None):
            _user_locks.pop(job.user_id, None)
        if job.started_at is not None:

            try:
                await asyncio.to_thread(remove_job_leftovers, runner.work_dir(), job_stem(job))
            except Exception:
                logger.debug("Could not clean up after conversion %s", job.id, exc_info=True)

async def _watch_progress(job: Job, runner: Runner, limit: int) -> None:
    marks = [mark for mark in PROGRESS_MARKS_S if mark < limit]
    started = time.monotonic()
    for index, mark in enumerate(marks):
        await asyncio.sleep(max(0.0, mark - (time.monotonic() - started)))
        following = marks[index + 1] if index + 1 < len(marks) else None
        await _safe(runner.progress(job, index + 1, len(marks), mark, following, limit))

async def _watch_queue(job: Job, runner: Runner) -> None:
    shown = ahead_of(job)
    while True:
        await asyncio.sleep(CARD_EVERY_S)
        now = ahead_of(job)
        if now != shown:
            shown = now
            await _safe(runner.queued(job, now))

async def _watch_card(job: Job, runner: Runner) -> None:
    while True:
        await asyncio.sleep(CARD_EVERY_S)
        await _safe(runner.card(job))

async def _run(job: Job, runner: Runner) -> None:
    lock = _user_locks.setdefault(job.user_id, asyncio.Lock())
    kind: str | None = None
    detail = ""
    outcome: Outcome | None = None
    queue_watcher = asyncio.ensure_future(_watch_queue(job, runner))
    card_watcher = None
    try:
        async with lock:
            async with _global_slots():
                queue_watcher.cancel()
                if job.user_cancelled:
                    raise asyncio.CancelledError
                job.state = "running"
                job.started_at = time.monotonic()
                if await _safe(runner.refuse_start(job)):
                    kind, detail = PAUSED, "paused for an update before it could start"
                else:
                    balance = await runner.charge(job)
                    if balance is None:
                        kind = NO_CREDIT
                    else:
                        job.charged = job.price > 0
                        if job.charged:
                            await _safe(runner.hold(job))
                        job.extra.update(stage="converting", stage_started=time.monotonic(),
                                         progress=None, balance_after=balance)
                        await _safe(runner.started(job, balance))
                        limit = job_limit(job)
                        watcher = asyncio.ensure_future(_watch_progress(job, runner, limit))
                        card_watcher = asyncio.ensure_future(_watch_card(job, runner))
                        try:
                            outcome = await run_worker(job, runner.work_dir(), job_stem(job), limit)
                        finally:
                            watcher.cancel()
                        if not outcome.ok:
                            kind, detail = outcome.kind or CRASH, outcome.message
                        elif outcome.bytes > job.send_limit:
                            kind = TOO_LARGE
                            detail = f"{outcome.bytes / 1024 / 1024:.0f} MB"
                        else:
                            job.extra.update(stage="sending", stage_started=time.monotonic(), progress=None)
                            await _safe(runner.card(job))
                            try:
                                await runner.deliver(job, outcome)
                            except asyncio.CancelledError:
                                raise
                            except Exception as exc:
                                kind, detail = SEND_FAILED, f"{type(exc).__name__}: {exc}"
    except asyncio.CancelledError:
        queue_watcher.cancel()
        if card_watcher is not None:
            card_watcher.cancel()
        kind = USER_CANCELLED if job.user_cancelled else INTERRUPTED
        detail = ("stopped by the person who asked for it" if job.user_cancelled
                  else "the bot was stopped in the middle of it")
        await asyncio.shield(_finish(job, runner, kind, detail, outcome))
        if not job.user_cancelled:
            raise
        return
    except Exception as exc:
        logger.exception("Conversion job %s failed unexpectedly", job.id)
        kind, detail = CRASH, f"{type(exc).__name__}: {exc}"
    queue_watcher.cancel()
    if card_watcher is not None:
        card_watcher.cancel()
    job.extra["stage"] = "done"
    await _finish(job, runner, kind, detail, outcome)

def submit(application, job: Job, runner: Runner) -> Job:
    """Queue a job and start its task. Returns the job, whose `ahead_of` the caller can use to say where it stands."""
    _jobs[job.id] = job
    coroutine = _run(job, runner)
    if application is not None and hasattr(application, "create_task"):
        job.task = application.create_task(coroutine)
    else:
        job.task = asyncio.get_running_loop().create_task(coroutine)
    return job

def cancel(job_id: str, user_id: int | None = None) -> Job | None:
    """Stop a job at the request of the person it belongs to."""
    job = _jobs.get(job_id)
    if job is None or (user_id is not None and job.user_id != user_id):
        return None
    job.user_cancelled = True
    if job.task is not None and not job.task.done():
        job.task.cancel()
    return job

# ─── module: convert_bot.convert_runner ──────────────────────────────────────
"""The Telegram side of a conversion job."""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import big_files
import db
import family_link
import formats
import i18n
import jobs
import lifecycle
import live_message
import problems
from live_message import LiveMessage
from shared_features import emit_event, note_job, note_stat, report_markup

logger = logging.getLogger(__name__)

BOT_LABEL = os.environ.get("FAMILY_LABEL") or "ConvertBot"

PROCESS_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"

def _upper(ext: str) -> str:
    return (ext or "?").upper()

def _target(job: jobs.Job, lang: str | None = None) -> str:
    """The job's target as the person is told it: PNG, or "Searchable PDF" for the pseudo-target ocrpdf, never the pseudo-extension itself."""
    return i18n.target_label(lang or job.lang, job.target_ext)

def _pair(job: jobs.Job) -> str:
    """"png->pdf", for the credit ledger and the in-flight record, which the person can read in /balance: the pseudo-target ocrpdf is written out."""
    target = "searchable-pdf" if job.target_ext == "ocrpdf" else job.target_ext
    return f"{job.src_ext}->{target}"

BAR_CELLS = 10

def progress_bar(fraction: float) -> str:
    """Ten cells and the percentage."""
    fraction = max(0.0, min(fraction, 0.99))
    filled = int(fraction * BAR_CELLS + 0.5)
    return "🟩" * filled + "⬜" * (BAR_CELLS - filled) + f" {int(fraction * 100)}%"

def clock(seconds: float) -> str:
    """0:07, 1:42, 12:05 -- a waiting time somebody can read at a glance."""
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"

def time_left(done: float, total: float, elapsed: float) -> float | None:
    """Seconds still to go, from the rate so far -- or None until there is a rate worth believing: a guess from the first second is noise, and a number that swings wildly is worse than no number."""
    if not total or done <= 0 or elapsed < 3:
        return None
    fraction = done / total
    if fraction < 0.03 or fraction >= 1:
        return None
    return elapsed * (1 - fraction) / fraction

def status_card(lang: str, job: jobs.Job, now: float | None = None) -> str:
    now = time.monotonic() if now is None else now
    stage = job.extra.get("stage") or "converting"
    lines = [f"🔄 {_upper(job.src_ext)} → {_target(job, lang)}",
             i18n.t(lang, "card_sending" if stage == "sending" else "card_converting")]
    progress = job.extra.get("progress")
    stage_started = job.extra.get("stage_started") or job.started_at or now
    timing = i18n.t(lang, "card_elapsed", elapsed=clock(now - (job.started_at or stage_started)))
    if progress and progress[1]:
        done, total = progress
        lines.append(progress_bar(done / total))
        left = time_left(done, total, now - stage_started)
        if left is not None:
            timing += " · " + i18n.t(lang, "card_left", left=clock(left))
    lines.append(timing)
    if job.price:
        lines.append(i18n.t(lang, "card_paid", price=job.price,
                            balance=job.extra.get("balance_after", "?")))
    else:
        lines.append(i18n.t(lang, "card_free"))
    return "\n".join(lines)

def download_card(lang: str, done: int, total: int, elapsed: float) -> str:
    """The same card for a file arriving, before there is a conversion."""
    lines = [i18n.t(lang, "card_downloading")]
    if total:
        lines.append(progress_bar(done / total))
        sizes = i18n.t(lang, "card_download_sizes", done=_megabytes(done), total=_megabytes(total))
        left = time_left(done, total, elapsed)
        if left is not None:
            sizes += " · " + i18n.t(lang, "card_left", left=clock(left))
        lines.append(sizes)
    return "\n".join(lines)

def _megabytes(size: int) -> str:
    return f"{size / 1024 / 1024:.1f} MB"

def result_filename(path) -> str:
    """What the converted file is called when it arrives."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"converted_{stamp}{Path(path).suffix}"

class ConvertRunner(jobs.Runner):
    def __init__(self, application, admin_ids, upload_dir, caption_for):
        self.application = application
        self.admin_ids = sorted(admin_ids or ())
        self.upload_dir = Path(upload_dir)
        self.caption_for = caption_for

    @property
    def bot(self):
        return self.application.bot

    def work_dir(self):
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        return self.upload_dir

    def stop_keyboard(self, job: jobs.Job) -> InlineKeyboardMarkup:
        key = "job_stop_button" if job.state == "running" else "job_stop_button_queued"
        return InlineKeyboardMarkup([[InlineKeyboardButton(
            i18n.t(job.lang, key), callback_data=f"convstop:{job.id}")]])

    async def _status(self, job: jobs.Job, text: str, markup=None) -> None:
        """Rewrite the conversion's one status message."""
        live = job.extra.get("status_live")
        if live is None and job.extra.get("status_message") is not None:
            live = LiveMessage.adopt(job.extra["status_message"])
        try:
            if live is None:
                sent = await self.bot.send_message(chat_id=job.chat_id, text=text, reply_markup=markup)
                job.extra["status_message"] = sent
                job.extra["status_live"] = LiveMessage.adopt(sent)
                return
            before = live.message_id
            await live.set(self.bot, text, reply_markup=markup)
            job.extra["status_live"] = live
            if live.message_id != before:
                try:
                    await self.bot.delete_message(chat_id=live.chat_id, message_id=before)
                except Exception:
                    logger.debug("Could not remove the old status of conversion %s", job.id, exc_info=True)
        except Exception:
            logger.debug("Could not update the status of conversion %s", job.id, exc_info=True)

    async def refuse_start(self, job: jobs.Job) -> bool:
        return lifecycle.is_paused()

    async def charge(self, job: jobs.Job) -> int | None:
        if job.price <= 0:
            return await asyncio.to_thread(family_link.star_balance, job.user_id)
        return await asyncio.to_thread(
            family_link.spend_stars, job.user_id, job.price, "spend",
            f"{_pair(job)} conversion, {job.size / 1024:.0f} KB")

    async def started(self, job: jobs.Job, balance: int) -> None:
        await self.card(job)

    async def queued(self, job: jobs.Job, ahead: int) -> None:
        if ahead:
            text = i18n.t(job.lang, "job_queued", src=_upper(job.src_ext), target=_target(job),
                          ahead=ahead, price=job.price)
        else:
            text = i18n.t(job.lang, "job_starting", src=_upper(job.src_ext), target=_target(job))
        await self._status(job, text, self.stop_keyboard(job))

    async def card(self, job: jobs.Job) -> None:
        """The live status, redrawn only when what it says has changed."""
        text = status_card(job.lang, job)
        if text == job.extra.get("card_text"):
            return
        job.extra["card_text"] = text
        stopping = job.extra.get("stage") != "sending"
        await self._status(job, text, self.stop_keyboard(job) if stopping else None)

    async def progress(self, job: jobs.Job, stage: int, stages: int, elapsed_s: float,
                       next_s, limit_s: int) -> None:
        """A new message, not an edit: an edit arrives silently, and the point is that somebody who has waited two minutes hears about it."""
        def minutes(seconds: float) -> int:
            return max(1, round(seconds / 60))

        if next_s is not None:
            text = i18n.t(job.lang, "job_progress", elapsed=minutes(elapsed_s),
                          next=minutes(next_s - elapsed_s), last=minutes(limit_s - elapsed_s))
        else:
            text = i18n.t(job.lang, "job_progress_last", elapsed=minutes(elapsed_s),
                          last=minutes(limit_s - elapsed_s))
        try:

            sent = await self.bot.send_message(chat_id=job.chat_id, text=text)
            live_message.bump(sent.chat_id, sent.message_id)
        except Exception:
            logger.debug("Could not send a progress update for conversion %s", job.id, exc_info=True)

    async def deliver(self, job: jobs.Job, outcome: jobs.Outcome) -> None:
        caption = self.caption_for(job.lang, outcome, job.src_ext, job.target_ext, job.price)
        if job.price:
            balance = await asyncio.to_thread(family_link.star_balance, job.user_id)
            caption += "\n\n" + i18n.t(job.lang, "balance_left_line", balance=balance)
        if outcome.bytes > jobs.SEND_LIMIT_BYTES and not jobs.LOCAL_BOT_API:

            def sending(done, total):
                job.extra["progress"] = (done, total)
            await big_files.send_document(job.chat_id, outcome.path,
                                          result_filename(outcome.path), caption, progress=sending)
            return

        with open(outcome.path, "rb") as handle:
            await self.bot.send_document(
                chat_id=job.chat_id, document=handle, filename=result_filename(outcome.path),
                caption=caption, read_timeout=300, write_timeout=300)

    async def succeeded(self, job: jobs.Job, outcome: jobs.Outcome) -> None:
        note_job(True)
        await self._status(job, i18n.t(job.lang, "job_done", src=_upper(job.src_ext),
                                       target=_target(job)))
        # After the person's line, and never in its way: a statistic must not cost them their result.
        try:
            note_stat("conversion", f"{formats.normalise(job.src_ext)}>{formats.normalise(job.target_ext)}")
        except Exception:
            logger.debug("Conversion not counted", exc_info=True)

    async def refund(self, job: jobs.Job, kind: str) -> int:
        return await asyncio.to_thread(
            family_link.move_stars, job.user_id, job.price, "refund",
            f"{_pair(job)} conversion ended: {kind}")

    async def hold(self, job: jobs.Job) -> None:
        await asyncio.to_thread(db.hold_conversion, job.id, job.user_id, job.chat_id, job.price,
                                job.lang, _pair(job), PROCESS_ID)

    async def release(self, job: jobs.Job) -> str:
        return await asyncio.to_thread(db.release_conversion, job.id)

    async def keep_alive_and_recover(self) -> int:
        """Stamp this process's paid conversions, and give back the credit of any whose process was killed before it could."""
        await asyncio.to_thread(db.touch_conversions, PROCESS_ID)
        lost = await asyncio.to_thread(db.claim_orphaned_conversions, PROCESS_ID, jobs.HOLD_STALE_S)
        for row in lost:
            try:
                balance = await asyncio.to_thread(
                    family_link.move_stars, row["user_id"], row["price"], "refund",
                    f"{row['pair']} conversion ended: the bot was stopped before it finished")
            except Exception:
                logger.exception("Could not refund conversion %s, lost to a restart", row["job_id"])
                emit_event("error", "conversion",
                           f"⚠️ {BOT_LABEL}: a conversion lost to a restart could NOT be refunded "
                           f"({row['price']} ⚡, job {row['job_id']}). Refund it by hand.")
                continue
            lang = row["lang"] or "en"
            incident = problems.new_incident()
            text = (i18n.t(lang, "job_reason_interrupted") + "\n\n"
                    + i18n.t(lang, "job_refunded_line", price=row["price"], balance=balance)
                    + problems.code_line("CV-RESTARTED"))
            logger.info("Conversion %s was lost to a restart (CV-RESTARTED, incident %s); %s ⚡ refunded",
                        row["job_id"], incident, row["price"])
            try:
                await self.bot.send_message(chat_id=row["chat_id"], text=text,
                                            reply_markup=report_markup(lang, "CV-RESTARTED", incident))
            except Exception:
                logger.debug("Could not tell anyone about lost conversion %s", row["job_id"], exc_info=True)
            emit_event("warning", "conversion",
                       f"⚠️ {BOT_LABEL}: a conversion was lost to a restart and refunded "
                       f"({row['pair']}, {row['price']} ⚡ back). Incident {incident}.")
        return len(lost)

    async def failed(self, job: jobs.Job, kind: str, detail: str, refunded_to) -> None:
        lang = job.lang
        if kind == jobs.USER_CANCELLED:
            if job.started_at is None:
                text = i18n.t(lang, "job_removed_from_queue")
            elif job.price and job.charged:
                text = i18n.t(lang, "job_user_stopped", price=job.price)
            else:
                text = i18n.t(lang, "job_user_stopped_free")
            await self._status(job, text)
            return
        if kind == jobs.PAUSED:
            await self._status(job, i18n.t(lang, "update_soon_try_later_soon"))
            return
        if kind == jobs.NO_CREDIT:
            balance = await asyncio.to_thread(family_link.star_balance, job.user_id)
            await self._status(job, i18n.t(lang, "job_no_credit", price=job.price, balance=balance))
            return

        if kind in (jobs.TIMEOUT, jobs.CRASH, jobs.SEND_FAILED):
            note_job(False)
        limit = jobs.job_limit(job)
        reasons = {
            jobs.REFUSED: ("job_reason_refused", {"detail": detail}),
            jobs.TIMEOUT: ("job_reason_timeout", {"minutes": max(1, round(limit / 60))}),
            jobs.TOO_SLOW: ("job_reason_too_slow", {"minutes": max(2, round(job.extra.get("projected_s", 0) / 60)),
                                                    "limit": max(1, round(limit / 60))}),
            jobs.CRASH: ("job_reason_crash", {}),
            jobs.NO_MEMORY: ("job_reason_no_memory", {}),
            jobs.TOO_LARGE: ("job_reason_too_large", {"target": _target(job),
                                                      "mb": detail.split()[0] if detail else "?",
                                                      "limit": job.send_limit // (1024 * 1024)}),
            jobs.SEND_FAILED: ("job_reason_send_failed", {}),
            jobs.INTERRUPTED: ("job_reason_interrupted", {}),
        }
        key, fields = reasons.get(kind, ("job_reason_crash", {}))
        text = i18n.t(lang, key, **fields)
        if refunded_to is not None:
            text += "\n\n" + i18n.t(lang, "job_refunded_line", price=job.price, balance=refunded_to)

        code = problems.JOB_ENDINGS.get(kind, "CV-CRASH")
        incident = job.extra.setdefault("incident", problems.new_incident())
        logger.info("Conversion %s ended %s (%s, incident %s): %s", job.id, kind, code, incident, detail)
        await self._status(job, text + problems.code_line(code),
                           report_markup(lang, code, incident, chat_id=job.chat_id))

    async def alert(self, job: jobs.Job, kind: str, detail: str, elapsed: float, refunded_to) -> None:
        """Straight to the owner, from this bot, in English."""
        limit = jobs.job_limit(job)

        credit = (f"{job.price} ⚡ back to the balance" if refunded_to is not None
                  else ("free conversion, nothing to refund" if not job.price else "not refunded"))
        text = (f"⚠️ {BOT_LABEL}: a conversion failed ({kind})\n"
                f"File: {job.size / 1024 / 1024:.1f} MB {_upper(job.src_ext)} → {_target(job, 'en')}\n"
                f"Ran: {elapsed:.0f}s of a {limit}s limit\n"
                f"Detail: {detail or '-'}\n"
                f"Code: {problems.JOB_ENDINGS.get(kind, 'CV-CRASH')} · incident {job.extra.get('incident', '-')}\n"
                f"Credit: {credit}")
        delivered = 0
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(chat_id=admin_id, text=text)
                delivered += 1
            except Exception:
                logger.debug("Could not alert admin %s", admin_id, exc_info=True)
        emit_event("info" if delivered else "warning", "conversion", text)
