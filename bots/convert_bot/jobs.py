"""The conversion queue, and what happens to the credit.

A conversion used to run inside the handler the format button called. Every
bot in this family has python-telegram-bot process updates one at a time --
on purpose: album batching depends on the parts of an album being handled in
the order they arrive -- so a four-minute conversion of a 200-megapixel photo
held the whole bot for four minutes. Nobody else's button did anything, and
the next tap failed outright with "query is too old", because Telegram gives
a button fifteen seconds to be answered.

So the handler now decides and enqueues, and the work happens here, in a task
of its own:

  one conversion at a time per person, in the order they asked;
  MAX_CONCURRENT across the whole bot, because the container is sized for
  one heavy job rather than for everyone's at once;
  each one in a child process (convert_worker.py) under a time limit that is
  actually enforced, because a process can be killed and a thread cannot.

What happens to the credit is decided here too, in one place, because it is
the part that has to be right every time:

  it is taken when the conversion STARTS, not when it is queued, so removing
  a queued job costs nothing and no job waits in a queue holding somebody's
  money;
  it is not refunded if the person stops a running conversion themselves;
  it is refunded, and the person told why, whenever the conversion ends for a
  reason that is the bot's rather than theirs;
  and the owner is told as well whenever that reason is a fault -- a
  timeout, a crash, a result too big to send, a send that failed, a restart
  -- rather than a file the bot declined.

This module knows nothing about Telegram. bot.py hands it a Runner that does
the talking, and that seam is what lets tests/test_jobs.py drive the whole
policy with a fake worker and no network.
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
WORKER = HERE / "convert_worker.py"

LOCAL_BOT_API = bool(os.environ.get("LOCAL_BOT_API_URL"))

# How many conversions run at once across the whole bot. One: the container is
# sized for the idle bot plus one heavy job, and a 200 MP photo is a heavy job.
# Everybody else waits in order rather than two jobs racing each other into an
# out-of-memory kill.
MAX_CONCURRENT = max(1, int(os.environ.get("CONVERT_MAX_CONCURRENT") or 1))

# How long one conversion may run before it is stopped and refunded. Ten
# minutes is the ceiling ffmpeg already had; the Pillow path had none at all,
# which is how a conversion could be waited on for twenty minutes.
TIME_LIMIT_S = int(os.environ.get("CONVERT_TIME_LIMIT_SECONDS") or 600)

# Free conversions (under 3 MB) get a much shorter one. Nothing that small
# megabyte needs a minute, and a free job that runs to the paid limit costs
# real hosting for no revenue at all -- the one case where the pricing could
# not "at least cover the hardware".
FREE_TIME_LIMIT_S = int(os.environ.get("CONVERT_FREE_TIME_LIMIT_SECONDS") or 60)

# Updates while a long conversion runs. The owner: "Maybe 10 minutes is too
# long to go with no context. Implement warnings after 2 minute of doing work
# ... that there will be 2 more warnings, 3 minutes and 8 minutes later. the
# last warning (that triggers after 10 minutes of work) should say it failed
# or whatever happened." So a note at two minutes, another at five, and at the
# time limit the ending itself -- which the ending already is. A mark at or
# past a job's own limit is dropped, so a free conversion sends none.
PROGRESS_MARKS_S = (120, 300)

# How many conversions one person may have waiting or running at once.
MAX_QUEUED_PER_USER = max(1, int(os.environ.get("CONVERT_MAX_QUEUED_PER_USER") or 5))

# Temporary storage, per person and for the whole bot, plus the free disk
# that must remain afterwards. Checked before a file is downloaded, against
# the size Telegram declares, so a full disk refuses an upload with a sentence
# instead of failing half-way through writing it.
#
# The per-person default is sized from the batch limits rather than picked:
# an album may hold MAX_BATCH files of MAX_FILE_MB each, and a smaller share
# refused the ninth and tenth scans of a ten-page PDF while it was still
# arriving, so the PDF quietly came out short.
def _largest_batch_mb() -> int:
    try:
        import convert_utils
        import formats
        return formats.MAX_BATCH * convert_utils.MAX_FILE_MB
    except Exception:
        return 400


USER_STORAGE_MB = int(os.environ.get("CONVERT_USER_STORAGE_MB") or max(120, _largest_batch_mb() + 50))
STORAGE_MB = int(os.environ.get("CONVERT_STORAGE_MB") or max(1024, USER_STORAGE_MB + 200))
MIN_FREE_MB = int(os.environ.get("CONVERT_MIN_FREE_MB") or 300)

# The largest picture converted at all. 210 covers the 200 MP sensors in
# current flagship phones -- the owner's own Galaxy S23 Ultra among them --
# which is exactly the professional case worth supporting. Above it a single
# decode needs more memory than a small container has.
MAX_MEGAPIXELS = int(os.environ.get("CONVERT_MAX_MEGAPIXELS") or 210)

# Optional hard memory cap on the worker process (POSIX). 0 leaves it to the
# container. See convert_worker._cap_memory.
WORKER_MAX_MEMORY_MB = int(os.environ.get("CONVERT_WORKER_MAX_MEMORY_MB") or 0)

# What a bot may send back. The cloud Bot API refuses a document over 50 MB
# with "Request Entity Too Large" -- which is what the owner's two 200 MP
# conversions ran into, after converting successfully. A local Bot API server
# raises it to 2 GB.
SEND_LIMIT_MB = 2000 if LOCAL_BOT_API else 50
SEND_LIMIT_BYTES = SEND_LIMIT_MB * 1024 * 1024

# Bytes per pixel a lossless picture comes out at. Only formats whose size is
# predictable from the pixel count are listed; everything lossy is left to the
# result-size check after the conversion, because a JPEG's size depends on
# what is in the picture rather than how many pixels it has.
#
# Deliberately on the LOW side of what a photo produces, so a format is only
# kept off the menu when it is clearly going to be over the limit. A format
# that slips through is caught after converting, refunded, and reported --
# the estimate saves somebody a wait, the check is what keeps it honest.
#
# Calibrated against a 149.8 MP photo (the owner's S23 Ultra at 16:9): PNG
# came out at 163 MB and QOI at 150 MB, about 1.0-1.1 bytes a pixel, on a
# test image noisier than a real photo. Half that is used here, which still
# keeps both off the menu above roughly 100 MP -- where they are certain to
# be over 50 MB -- without hiding them from pictures that might fit.
LOSSLESS_BYTES_PER_PIXEL = {
    "bmp": 3.0,
    "ppm": 3.0,
    "tga": 3.0,
    "tiff": 0.6,
    "png": 0.5,
    "qoi": 0.5,
}

# Encoders with a hard ceiling of their own, in megapixels. x265 refuses more
# than 142,606,336 luma samples (HEVC level 6.2), so HEIC of a 150 MP photo
# fails a few seconds in with an encoder error. Leaving it off the menu is
# better than charging, failing and refunding.
TARGET_MAX_MEGAPIXELS = {
    "heic": 142.6,
}

# How a job can end, other than with a delivered file.
USER_CANCELLED = "user_cancelled"
NO_CREDIT = "no_credit"
REFUSED = "refused"
TIMEOUT = "timeout"
CRASH = "crash"
TOO_LARGE = "too_large"
SEND_FAILED = "send_failed"
INTERRUPTED = "interrupted"
# Reached the front while the owner had paused the bot for an update. Nothing
# started and nothing was charged, so it is neither refunded nor reported --
# before this it was INTERRUPTED, which paged the owner once per queued job
# and told each person the bot had restarted in the middle of their file.
PAUSED = "paused"

# Refunded when the job had been charged: every ending except the person
# stopping it themselves. NO_CREDIT is never charged in the first place.
REFUNDED = frozenset({REFUSED, TIMEOUT, CRASH, TOO_LARGE, SEND_FAILED, INTERRUPTED})

# Worth the owner's attention: the bot's own faults. A file the bot declined
# (REFUSED) is the bot working as designed, and an alert for every unreadable
# upload would bury the failures that matter.
ALERTED = frozenset({TIMEOUT, CRASH, TOO_LARGE, SEND_FAILED, INTERRUPTED})


# Queue order comes from a counter, not a clock. time.monotonic() ticks about
# every 16 ms on Windows, so two jobs queued back to back got the same
# timestamp and "how many are ahead of me" answered none -- the lock ran
# them in the right order, but the sentence telling people so was wrong.
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
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    state: str = "queued"          # queued | running | done
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
    """For tests, which run each scenario on a fresh event loop: asyncio
    primitives belong to the loop they were first used on."""
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
    """Every staged file a queued or running job still needs. The sweeper and
    _discard_pending skip these: a file must not be deleted out from under a
    conversion that is about to read it."""
    return {str(path) for job in _jobs.values() for path in job.paths}


def uncharged_total(user_id: int) -> int:
    """Credit this person's queued jobs will need when they start. Checked at
    enqueue so a queue cannot be built that the balance will not cover."""
    return sum(job.price for job in _jobs.values()
               if job.user_id == user_id and not job.charged)


# ---------------------------------------------------------------------------
# Before anything is downloaded or charged
# ---------------------------------------------------------------------------

def storage_problem(user_id: int, incoming_bytes: int, upload_dir) -> tuple[str, int, int] | None:
    """None if there is room for `incoming_bytes` more; otherwise which limit
    stops it -- "user", "global" or "disk" -- with the MB used and the limit.

    Scans the staging directory rather than keeping a running total, because a
    running total has to be right about every crash and restart, and a
    directory listing of a handful of files cannot be wrong."""
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


def image_megapixels(path) -> float | None:
    """The size of a picture, read from its header without decoding it.

    Pillow's own decompression-bomb ceiling is switched off for the length of
    the read, because opening a header is not the dangerous part and this is
    the function that decides what the ceiling is. None for anything that is
    not a picture Pillow can read."""
    try:
        from PIL import Image
    except Exception:
        return None
    previous = getattr(Image, "MAX_IMAGE_PIXELS", None)
    try:
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(path) as img:
            width, height = img.size
        return (width * height) / 1_000_000
    except Exception:
        return None
    finally:
        try:
            Image.MAX_IMAGE_PIXELS = previous
        except Exception:
            pass


def estimate_output_bytes(megapixels: float | None, target_ext: str) -> int | None:
    ratio = LOSSLESS_BYTES_PER_PIXEL.get(target_ext)
    if megapixels is None or ratio is None:
        return None
    return int(megapixels * 1_000_000 * ratio)


def unsendable_targets(megapixels: float | None, targets) -> list[str]:
    """The formats that would certainly come out too big to send, or that
    the encoder itself cannot produce at this size."""
    out = []
    for target in targets:
        ceiling = TARGET_MAX_MEGAPIXELS.get(target)
        if megapixels is not None and ceiling is not None and megapixels > ceiling:
            out.append(target)
            continue
        estimate = estimate_output_bytes(megapixels, target)
        if estimate is not None and estimate > SEND_LIMIT_BYTES:
            out.append(target)
    return out


# ---------------------------------------------------------------------------
# The worker
# ---------------------------------------------------------------------------

async def _kill(proc) -> None:
    if proc is None or proc.returncode is not None:
        return
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


async def run_worker(job: Job, work_dir, stem: str, time_limit: int) -> Outcome:
    payload = {
        "in_paths": [str(path) for path in job.paths],
        "src_ext": job.src_ext,
        "target_ext": job.target_ext,
        "work_dir": str(work_dir),
        "stem": stem,
        "max_pixels": MAX_MEGAPIXELS * 1_000_000,
        "max_memory_mb": WORKER_MAX_MEMORY_MB,
    }
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-u", str(WORKER), json.dumps(payload),
        cwd=str(HERE), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    job.proc = proc
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=time_limit)
    except asyncio.TimeoutError:
        await _kill(proc)
        return Outcome(False, TIMEOUT, f"ran past the {time_limit}s limit")
    except asyncio.CancelledError:
        await asyncio.shield(_kill(proc))
        raise
    finally:
        job.proc = None
    return _parse(proc.returncode, out, err)


# ---------------------------------------------------------------------------
# Running a job
# ---------------------------------------------------------------------------

class Runner:
    """What bot.py provides. None of these may raise, except `deliver`, whose
    exception is the send failure."""

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
        """Still running at `elapsed_s`. `next_s` is when the next update
        comes, or None if the next thing is the ending at `limit_s`."""
        return None

    async def deliver(self, job: Job, outcome: Outcome) -> None:
        raise NotImplementedError

    async def succeeded(self, job: Job, outcome: Outcome) -> None:
        return None

    async def refund(self, job: Job, kind: str) -> int:
        raise NotImplementedError

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


async def _finish(job: Job, runner: Runner, kind: str | None, detail: str,
                  outcome: Outcome | None) -> None:
    try:
        elapsed = time.monotonic() - job.started_at if job.started_at else 0.0
        if kind is None:
            await _safe(runner.succeeded(job, outcome))
            return
        refunded_to = None
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


async def _watch_progress(job: Job, runner: Runner, limit: int) -> None:
    marks = [mark for mark in PROGRESS_MARKS_S if mark < limit]
    started = time.monotonic()
    for index, mark in enumerate(marks):
        await asyncio.sleep(max(0.0, mark - (time.monotonic() - started)))
        following = marks[index + 1] if index + 1 < len(marks) else None
        await _safe(runner.progress(job, index + 1, len(marks), mark, following, limit))


async def _run(job: Job, runner: Runner) -> None:
    lock = _user_locks.setdefault(job.user_id, asyncio.Lock())
    kind: str | None = None
    detail = ""
    outcome: Outcome | None = None
    try:
        async with lock:
            async with _global_slots():
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
                        await _safe(runner.started(job, balance))
                        limit = TIME_LIMIT_S if job.price > 0 else FREE_TIME_LIMIT_S
                        watcher = asyncio.ensure_future(_watch_progress(job, runner, limit))
                        try:
                            outcome = await run_worker(job, runner.work_dir(),
                                                       f"{job.user_id}-{job.id}-out", limit)
                        finally:
                            watcher.cancel()
                        if not outcome.ok:
                            kind, detail = outcome.kind or CRASH, outcome.message
                        elif outcome.bytes > SEND_LIMIT_BYTES:
                            kind = TOO_LARGE
                            detail = f"{outcome.bytes / 1024 / 1024:.0f} MB"
                        else:
                            try:
                                await runner.deliver(job, outcome)
                            except asyncio.CancelledError:
                                raise
                            except Exception as exc:
                                kind, detail = SEND_FAILED, f"{type(exc).__name__}: {exc}"
    except asyncio.CancelledError:
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
    await _finish(job, runner, kind, detail, outcome)


def submit(application, job: Job, runner: Runner) -> Job:
    """Queue a job and start its task. Returns the job, whose `ahead_of` the
    caller can use to say where it stands."""
    _jobs[job.id] = job
    coroutine = _run(job, runner)
    if application is not None and hasattr(application, "create_task"):
        job.task = application.create_task(coroutine)
    else:
        job.task = asyncio.get_running_loop().create_task(coroutine)
    return job


def cancel(job_id: str, user_id: int | None = None) -> Job | None:
    """Stop a job at the request of the person it belongs to. Returns the job,
    or None if there is no such job or it is somebody else's."""
    job = _jobs.get(job_id)
    if job is None or (user_id is not None and job.user_id != user_id):
        return None
    job.user_cancelled = True
    if job.task is not None and not job.task.done():
        job.task.cancel()
    return job
