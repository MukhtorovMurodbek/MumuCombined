"""Convert arbitrary GIFs/videos (and already-valid Telegram video stickers,
re-encoded for safety) into Telegram-compliant video stickers.

Telegram's rule for video stickers: WEBM container, VP9 codec, no audio
track, one side exactly 512px (the other <=512px), <=3 seconds, <=30 FPS,
<=256 KB.

Hitting 256 KB is the hard part, and no single quality setting does it for
every clip. This used to walk a fixed ladder of eight increasingly
aggressive CRF values, re-encoding from scratch each time -- up to eight
full VP9 encodes of the same clip, which on a small shared vCPU is the
single most expensive thing this bot family does, and it happened most often
for exactly the busy clips that were slowest to encode.

Instead this now *measures*: the first attempt reports how far off it was,
and the next CRF is derived from that ratio rather than from a fixed step.
Two attempts cover almost everything, four is the ceiling, and the encoder
itself is capped to a couple of threads so one user's sticker cannot take
the whole container's CPU away from everyone else's messages.

Requires ffmpeg (with libvpx-vp9) on PATH.
"""
import os
import shutil
import subprocess
import tempfile

import i18n

STICKER_SIDE = 512
MAX_DURATION_S = 3
MAX_FPS = 30
MAX_BYTES = 256 * 1024

# VP9's CRF scale is 0 (best) to 63 (worst). 34 lands inside the limit for
# most ordinary clips; the loop below moves from there based on what the
# encode actually produced.
_FIRST_CRF = 34
_MIN_CRF, _MAX_CRF = 20, 63
_MAX_ATTEMPTS = int(os.environ.get("STICKER_ENCODE_ATTEMPTS", "4"))

# Wall-clock ceiling per ffmpeg run. Without one, a pathological input can
# leave a process pinning a core until the container is restarted -- and the
# user, meanwhile, sees nothing at all.
_TIMEOUT_S = int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", "120"))

# libvpx-vp9 will happily use every core it can see. On a shared host that is
# the host's core count, not this container's share, so it buys nothing and
# costs everyone else their latency. Two threads plus row-based multi-
# threading is the sweet spot for a 512px clip.
_THREADS = os.environ.get("FFMPEG_THREADS", "2")

# Picks 512 for whichever side is larger and scales the other proportionally
# (-2 keeps it even, which libvpx-vp9 requires) -- computed by ffmpeg itself
# from the input's actual width/height, so no separate probing step is needed.
_SCALE_FILTER = (
    f"scale=w='if(gte(iw,ih),{STICKER_SIDE},-2)':h='if(gte(iw,ih),-2,{STICKER_SIDE})'"
)


class ConversionError(Exception):
    """Raised when ffmpeg is missing or the clip can't be made to fit."""


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _next_crf(crf: int, size: int, fps: int) -> tuple[int, int]:
    """Given an attempt that came out `size` bytes at `crf`, guess the CRF
    that lands under the limit -- and drop the frame rate once CRF alone has
    run out of room.

    VP9's bitrate falls off roughly geometrically in CRF: about 6 points of
    CRF halves it. So overshooting by 2x asks for +6, by 4x for +12, and a
    near miss only nudges. That is the whole trick -- the old ladder spent
    its attempts stepping past clips it had already measured."""
    overshoot = size / MAX_BYTES
    step = 6
    while overshoot > 2 and step < 24:
        overshoot /= 2
        step += 6
    target = crf + step
    if target <= _MAX_CRF:
        return target, fps
    # Out of quality headroom: keep the worst CRF and thin the frames out
    # instead. 24 then 15 fps, both well inside Telegram's "up to 30".
    return _MAX_CRF, 15 if fps <= 24 else 24


def _encode(in_path: str, out_path: str, crf: int, fps: int) -> subprocess.CompletedProcess:
    cmd = [
        "ffmpeg", "-nostdin", "-y",
        "-i", in_path,
        "-t", str(MAX_DURATION_S),
        "-an",  # video stickers must have no audio track
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
    """Takes raw bytes of a GIF, video, or video sticker and returns bytes
    of a compliant WEBM/VP9 video sticker. Raises ConversionError on failure.

    Runs synchronously (shells out to ffmpeg) -- call via asyncio.to_thread
    from async code so it doesn't block the event loop. `lang` only affects
    the text of any ConversionError raised (this function itself has no
    other user-facing output).
    """
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
                # A failed encode says nothing about size, so there is no
                # measurement to steer by -- stop rather than burn the
                # remaining attempts on the same error.
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
                break  # nowhere left to go; another identical encode is waste

        raise ConversionError(i18n.t(lang, "video_convert_too_big", note=last_note))
