"""ManagerBot's own logging / crash tracking / activity tracking.

This is the monitoring half of the other four bots' shared_features.py,
copied here without the halves ManagerBot has no use for (donations, the
sibling-bot cross-promotion, i18n -- ManagerBot has exactly one user and
speaks one language). family_link.py looks for a module named either
`shared_features` or `monitoring` and uses whichever it finds, which is why
this file keeps the same function names.

Keeping ManagerBot on the same vocabulary matters: a bot that watches the
others should be watched by exactly the same machinery, so "ManagerBot has
been quietly crashing" is as visible as it would be for any of them.
"""
import asyncio
import gc
import logging
import os
import socket
import sys
import time
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from telegram.error import BadRequest, NetworkError, RetryAfter

import db
import family_link
import live_message

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

_recent_errors: deque[tuple[str, str]] = deque(maxlen=10)
_error_count = 0

# Set by family_link.attach(); see shared_features.py in any of the other
# bots for the same hook.
_event_hook = None


def set_event_hook(fn) -> None:
    global _event_hook
    _event_hook = fn


def emit_event(level: str, kind: str, message: str, details: str | None = None) -> None:
    if _event_hook is None:
        return
    try:
        _event_hook(level, kind, message, details)
    except Exception:
        logging.getLogger(__name__).debug("Family event hook failed", exc_info=True)


def _log_to_files() -> bool:
    """Files on a laptop, stdout only in the cloud -- see the identical
    reasoning in the other four bots' shared_features.py."""
    override = os.environ.get("LOG_TO_FILES")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes", "on")
    return not (os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT"))


def setup_logging(bot_file: str) -> None:
    fmt = logging.Formatter(_LOG_FORMAT)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    for noisy in ("httpx", "httpcore", "telegram.ext.Updater", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not _log_to_files():
        return

    log_dir = os.path.join(os.path.dirname(os.path.abspath(bot_file)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    info_file = RotatingFileHandler(
        os.path.join(log_dir, "bot.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    info_file.setFormatter(fmt)
    root.addHandler(info_file)

    error_file = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    error_file.setLevel(logging.WARNING)
    error_file.setFormatter(fmt)
    root.addHandler(error_file)


# ---------------------------------------------------------------------------
# Transient network conditions vs. actual faults
# ---------------------------------------------------------------------------
# A long poll losing its connection, a read timing out, Telegram asking us to
# slow down: PTB retries all of these itself and the bot keeps working, so
# waking the owner with a traceback for each one is noise that trains you to
# ignore the channel that also carries real crashes.
#
# The catch is PTB's class hierarchy: BadRequest *subclasses* NetworkError,
# and a BadRequest is a genuine fault -- a malformed API call, our bug -- so a
# plain `isinstance(exc, NetworkError)` would swallow exactly the errors most
# worth hearing about. It has to be excluded explicitly.

TRANSIENT_NETWORK_ERRORS = (NetworkError, RetryAfter)

# How many blips in a row before saying something. Reset by any update that
# arrives, since one arriving proves the connection is working again. Roughly
# a few minutes of a dead link at a 30-second poll.
NETWORK_ALERT_AFTER = int(os.environ.get("NETWORK_ALERT_AFTER", "20"))

_network_blips = 0        # consecutive, since the last update actually arrived
_network_blips_total = 0  # since this process started
_network_alerted = False


# PTB raises Telegram's HTTP 413 -- "Request Entity Too Large" -- as a plain
# NetworkError, so it matched the tuple above and was filed as a flaky
# connection. It is the opposite: permanent, and the same upload fails every
# time. That is how two successful ConvertBot conversions of a 200 MP photo
# vanished -- result converted, upload refused, error handler said "retried
# by PTB", user told nothing, credit kept. Anything whose text says the
# payload is too big is a real failure, whatever class it arrived as.
PERMANENT_NETWORK_MESSAGES = ("entity too large", "file is too big", "too big", "too large")


def is_transient_network_error(exc: BaseException) -> bool:
    if not isinstance(exc, TRANSIENT_NETWORK_ERRORS) or isinstance(exc, BadRequest):
        return False
    text = str(exc).lower()
    return not any(marker in text for marker in PERMANENT_NETWORK_MESSAGES)


def note_network_blip(exc: BaseException) -> None:
    """Counted and logged, never reported as a crash -- until there have been
    enough in a row to mean the connection is gone rather than flaky, which is
    worth exactly one message."""
    global _network_blips, _network_blips_total, _network_alerted
    _network_blips += 1
    _network_blips_total += 1
    logging.getLogger(__name__).warning(
        "Transient network error (%s): %s -- retried by PTB, %s in a row",
        type(exc).__name__, exc, _network_blips,
    )
    if _network_blips >= NETWORK_ALERT_AFTER and not _network_alerted:
        _network_alerted = True
        emit_event(
            "warning", "network",
            f"{_network_blips} network errors in a row -- this bot may not be "
            f"reaching Telegram. Latest: {type(exc).__name__}: {exc}",
        )


def note_network_ok() -> None:
    """An update arrived, so the connection works. Called from track_activity,
    which runs before every other handler."""
    global _network_blips, _network_alerted
    if _network_blips and _network_alerted:
        emit_event("info", "network", "Telegram is reachable again.")
    _network_blips = 0
    _network_alerted = False


def record_error(exc: BaseException) -> None:
    global _error_count
    _error_count += 1
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    _recent_errors.append((stamp, repr(exc)))
    emit_event(
        "error", "crash", f"ManagerBot itself hit an unhandled {type(exc).__name__}: {exc}",
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )


def error_summary() -> str:
    blips = (
        f"\n\U0001f310 {_network_blips_total} transient network error(s) -- retried, not crashes."
        if _network_blips_total else ""
    )
    if _error_count == 0:
        return "✅ No errors since this instance started." + blips
    lines = [f"⚠️ {_error_count} error(s) since start:"]
    lines.extend(f"  {stamp} — {msg}" for stamp, msg in _recent_errors)
    if _error_count > len(_recent_errors):
        lines.append(f"  (+{_error_count - len(_recent_errors)} earlier, see logs/errors.log)")
    return "\n".join(lines) + blips


async def error_handler(update, context) -> None:
    """Register with Application.add_error_handler in each bot's main() --
    this is PTB's global hook for exceptions that escape a handler callback
    uncaught (i.e. actual crashes, not the try/except'd, user-facing errors
    already handled inline elsewhere).

    A dropped long poll reaches here too, and is not a crash -- see
    is_transient_network_error above."""
    # Only a failure with no update behind it is the long poll. A network
    # error raised while handling somebody's message means that person asked
    # for something and did not get it, and that is not a blip however
    # transient its cause: it is counted, logged with its traceback, and
    # reported like any other failure.
    if update is None and is_transient_network_error(context.error):
        note_network_blip(context.error)
        return
    logging.getLogger(__name__).error("Unhandled exception while processing an update", exc_info=context.error)
    record_error(context.error)


# ---------------------------------------------------------------------------
# Active-user tracking, buffered -- see shared_features.py for the reasoning
# ---------------------------------------------------------------------------
# ManagerBot has one user, so the saving here is small in absolute terms. It is
# kept identical anyway: the whole point of this file is that ManagerBot is
# measured by exactly the same machinery as the bots it watches, and a
# divergence here is a divergence in what /status means.
ACTIVITY_FLUSH_SECONDS = int(os.environ.get("ACTIVITY_FLUSH_SECONDS", "60"))

_activity_buffer: set[int] = set()


def _flush_activity_now() -> int:
    global _activity_buffer
    if not _activity_buffer:
        return 0
    batch, _activity_buffer = _activity_buffer, set()
    try:
        db.record_activity_batch(batch)
    except Exception:
        _activity_buffer |= batch
        raise
    return len(batch)


async def _flush_activity_job(context) -> None:
    try:
        await asyncio.to_thread(_flush_activity_now)
    except Exception:
        logging.getLogger(__name__).debug("Activity flush failed; will retry", exc_info=True)


async def track_activity(update, context) -> None:
    note_network_ok()
    # See shared_features: this is what lets an evolving message tell whether
    # it is still the last thing in the chat.
    live_message.note_update(update)
    user = update.effective_user
    if not user:
        return
    _activity_buffer.add(user.id)
    note_usage_update(user.id)


WORKER_THREADS = int(os.environ.get("WORKER_THREADS", "4"))
GC_THRESHOLD = int(os.environ.get("GC_GEN0_THRESHOLD", "5000"))


async def tune_runtime(application) -> None:
    """Call from post_init -- see shared_features.py for why the default
    executor is worth capping, why everything imported at startup is worth
    freezing out of the garbage collector's reach, and why an idle process
    should not be sweeping its heap every few seconds."""
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="worker")
    )
    gc.collect()
    gc.freeze()
    gc.set_threshold(GC_THRESHOLD, 20, 20)


def attach_maintenance(app) -> None:
    """One line in ManagerBot's main(). ManagerBot refuses to start without a
    job queue at all (see bot.py), so there is no degraded path here."""
    app.job_queue.run_repeating(
        _flush_activity_job, interval=ACTIVITY_FLUSH_SECONDS, first=ACTIVITY_FLUSH_SECONDS
    )
    app.job_queue.run_repeating(
        _usage_sample_job, interval=USAGE_SAMPLE_MINUTES * 60,
        first=USAGE_SAMPLE_MINUTES * 60 + 60,
    )


async def flush_on_shutdown(application) -> None:
    """Register as Application.post_stop."""
    try:
        await asyncio.to_thread(_flush_activity_now)
    except Exception:
        logging.getLogger(__name__).debug("Final activity flush failed", exc_info=True)
    try:
        await asyncio.to_thread(db.close_pool)
    except Exception:
        logging.getLogger(__name__).debug("Closing the connection pool failed", exc_info=True)


def detect_host_environment() -> str:
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT")
    if railway_env:
        project = os.environ.get("RAILWAY_PROJECT_NAME", "?")
        service = os.environ.get("RAILWAY_SERVICE_NAME", "?")
        return f"☁️ Cloud (Railway -- project \"{project}\", service \"{service}\", env \"{railway_env}\")"
    return f"💻 Local ({socket.gethostname()})"


# ---------------------------------------------------------------------------
# What this process actually costs to run
# ---------------------------------------------------------------------------
# A usage-billed host charges for resident memory and CPU seconds, and until
# this was on /status there was no way to tell whether a change to either had
# helped, hurt, or done nothing. Every number here is read from the kernel,
# free, and only when someone asks.

def _read_first_int(path: str, key: str | None = None) -> int | None:
    try:
        with open(path) as handle:
            if key is None:
                text = handle.read().strip()
                return int(text) if text.isdigit() else None
            for line in handle:
                if line.startswith(key):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _memory_ceiling_bytes() -> int | None:
    """What the container is allowed, rather than what the host has. cgroup
    v2 first (every current Linux container runtime), then v1."""
    for path, scale in (("/sys/fs/cgroup/memory.max", 1),
                        ("/sys/fs/cgroup/memory/memory.limit_in_bytes", 1)):
        value = _read_first_int(path)
        # An unset cgroup limit is reported as a number near 2^63, which is
        # "the whole machine" and worth nothing as a denominator.
        if value and value < (1 << 62):
            return value * scale
    return None


def footprint_numbers() -> dict:
    """The same four readings process_footprint() prints, as numbers.

    Separated out because a sentence is what a person wants and a number is
    what a threshold and a database row want, and building the sentence twice
    to parse it back would be the kind of thing that breaks silently in one
    language and not another.

    Any of them may be None: /proc is Linux, the cgroup file is a container,
    and `resource` is not on Windows. A missing number means "not measurable
    here", never zero -- zero would read as "free" to every caller.
    """
    resident = _read_first_int("/proc/self/status", "VmRSS:")
    peak = _read_first_int("/proc/self/status", "VmHWM:")
    ceiling = _memory_ceiling_bytes()
    cpu = None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        cpu = usage.ru_utime + usage.ru_stime
        if resident is None:
            # ru_maxrss is kilobytes on Linux and bytes on macOS/BSD, and it
            # is a high-water mark rather than a live reading -- so it stands
            # in for the peak, and there is no live number to report.
            scale = 1 if sys.platform == "darwin" else 1024
            peak = usage.ru_maxrss * scale // 1024
    except Exception:
        pass
    return {
        "rss_mb": None if resident is None else resident // 1024,
        "peak_rss_mb": None if peak is None else peak // 1024,
        "ceiling_mb": None if ceiling is None else ceiling // (1024 * 1024),
        "cpu_seconds": None if cpu is None else int(cpu),
    }


def process_footprint() -> str:
    """One line: resident memory, its high-water mark, and CPU seconds burned
    since startup. Read /proc where it exists (Linux, which is what the
    deployed containers are) and fall back to getrusage elsewhere."""
    numbers = footprint_numbers()
    parts = []
    if numbers["rss_mb"] is not None:
        line = f"Memory: {numbers['rss_mb']} MB resident"
        if numbers["peak_rss_mb"]:
            line += f" (peak {numbers['peak_rss_mb']} MB)"
        if numbers["ceiling_mb"]:
            line += f" of {numbers['ceiling_mb']} MB allowed"
        parts.append(line)
    elif numbers["peak_rss_mb"] is not None:
        parts.append(f"Memory: peak {numbers['peak_rss_mb']} MB")
    if numbers["cpu_seconds"] is not None:
        parts.append(f"CPU: {numbers['cpu_seconds']}s used since start")
    trend = usage_trend_line()
    if trend:
        parts.append(trend)
    return " · ".join(parts) or "Footprint: not readable on this host"


# ---------------------------------------------------------------------------
# What it costs over time, and when that stops being normal
# ---------------------------------------------------------------------------
# /status answers "what is this process using right now", which on its own
# tells nobody whether right now is unusual. This keeps a rolling window --
# updates handled, distinct people, and the four kernel readings -- writes one
# row per window into family.usage_samples, and raises an event when a window
# is far enough from the others to be worth a message at 3am.
#
# Three things are worth being told about, and they are different questions:
#
#   memory headroom   the container is close to the limit it will be killed
#                     for crossing. The only one of the three that is an
#                     emergency.
#   an activity spike a window with far more updates than the recent norm.
#                     Could be a launch, could be one script. Either way the
#                     owner would rather hear it from the bot than from the
#                     bill.
#   monthly reach     how many distinct people used it in thirty days, which
#                     is the number that decides whether the plan it is on is
#                     still the right one. Slow-moving, so it is checked once
#                     a day and only ever mentioned when it crosses.
#
# Everything here is a count. No user ids, no chat ids, no text.

# How long a bot has to be quiet before that quiet could have been sleep.
# The same name and the same default as shared_features.py in the four public
# bots, because /idle's arithmetic compares this against the sleepable seconds
# those bots measured with it -- two different numbers would make the answer
# quietly wrong rather than loudly broken.
SLEEP_AFTER_SECONDS = int(os.environ.get("SLEEP_AFTER_SECONDS") or 300)

USAGE_SAMPLE_MINUTES = int(os.environ.get("USAGE_SAMPLE_MINUTES") or 15)
# How full the container has to be before it is worth saying so. 0.85 rather
# than 0.95: the point is to arrive before the OOM kill, not with it.
USAGE_MEMORY_WARN_RATIO = float(os.environ.get("USAGE_MEMORY_WARN_RATIO") or 0.85)
# A window counts as a spike when it is this many times the median of the
# recent ones AND clears the floor. The floor is what stops "2 updates, then
# 12" from being an incident on a quiet bot -- which, on a bot this quiet, is
# most of the time.
USAGE_SPIKE_FACTOR = float(os.environ.get("USAGE_SPIKE_FACTOR") or 6.0)
USAGE_SPIKE_FLOOR = int(os.environ.get("USAGE_SPIKE_FLOOR") or 60)
# Distinct people in thirty days, past which the owner is told once. Not a
# limit and nothing is refused; it is the number that means "the smallest
# plan that fits may no longer be the smallest plan that fits".
USAGE_MONTHLY_USERS_WARN = int(os.environ.get("USAGE_MONTHLY_USERS_WARN") or 400)
# How long a host waits for silence before it stops charging for a container.
# Railway sleeps a service after roughly five minutes with no *outbound*
# traffic, so a gap between updates is only worth anything from the five-minute
# mark onwards -- which is why this is subtracted from every gap rather than
# the gaps simply being added up. Nothing in the bots sleeps yet; this measures
# what sleeping *would* have saved, so the decision is made on this family's
# own traffic rather than on a guess.
SLEEP_AFTER_SECONDS = int(os.environ.get("SLEEP_AFTER_SECONDS") or 300)
# A window where more than this fraction of the jobs failed is worth being told
# about -- a job being a conversion, a download, a pack edit: whatever the bot
# is for. The floor is again what stops one failure out of one being an
# outage.
USAGE_FAILURE_WARN_RATIO = float(os.environ.get("USAGE_FAILURE_WARN_RATIO") or 0.5)
USAGE_FAILURE_FLOOR = int(os.environ.get("USAGE_FAILURE_FLOOR") or 4)
# How many recent windows the spike test compares against, and how long an
# alarm of one kind stays quiet after firing.
_USAGE_WINDOW_MEMORY = 24
_ALARM_QUIET_SECONDS = {"memory": 3600, "spike": 3600, "monthly_users": 86400,
                        "failures": 1800}

_usage_updates = 0
_usage_users: set[int] = set()
_usage_recent: "deque[int]" = deque(maxlen=_USAGE_WINDOW_MEMORY)
_usage_alarmed: dict[str, float] = {}
# The gap clock. monotonic() rather than time(): this measures a duration, and
# a clock that can be stepped by NTP would make one negative.
_usage_last_update = time.monotonic()
_usage_sleepable = 0.0
_usage_max_gap = 0.0
_usage_jobs_ok = 0
_usage_jobs_failed = 0


def note_usage_update(user_id: int | None) -> None:
    """One update happened. Called from track_activity, so it is on the path
    of every update there is -- it adds an int to a set and increments a
    couple of counters, and must never do anything more expensive than that."""
    global _usage_updates, _usage_last_update, _usage_sleepable, _usage_max_gap
    _usage_updates += 1
    now = time.monotonic()
    gap = now - _usage_last_update
    _usage_last_update = now
    _usage_max_gap = max(_usage_max_gap, gap)
    _usage_sleepable += max(0.0, gap - SLEEP_AFTER_SECONDS)
    if user_id is not None and len(_usage_users) < 10000:
        _usage_users.add(user_id)


def note_job(ok: bool) -> None:
    """One unit of the thing this bot is for finished -- a conversion, a
    download, a pack edit. Two counters and nothing else.

    What is deliberately NOT here: what was converted, which link, whose it
    was, or why it failed. The question this answers is "is the bot still
    working", and that needs a ratio, not a record. Per-route detail already
    lives where it belongs -- DownloaderBot's provider health, and every
    bot's error log."""
    global _usage_jobs_ok, _usage_jobs_failed
    if ok:
        _usage_jobs_ok += 1
    else:
        _usage_jobs_failed += 1


def _alarm_due(kind: str) -> bool:
    now = time.time()
    if now - _usage_alarmed.get(kind, 0) < _ALARM_QUIET_SECONDS.get(kind, 3600):
        return False
    _usage_alarmed[kind] = now
    return True


def _median(values) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def usage_trend_line() -> str:
    """One line for /status: what the recent windows looked like, so the
    number above it has something to be compared with."""
    if not _usage_recent:
        return ""
    quiet = int(time.monotonic() - _usage_last_update)
    return (f"Recent: {sum(_usage_recent)} update(s) over the last "
            f"{len(_usage_recent)} window(s) of {USAGE_SAMPLE_MINUTES} min · "
            f"quiet for {quiet // 60}m {quiet % 60}s")


def _monthly_users() -> int | None:
    """Distinct people in the last thirty days, if this bot's db can say."""
    counter = getattr(db, "count_active_users_since", None)
    if counter is None:
        return None
    try:
        return counter(datetime.now(timezone.utc) - timedelta(days=30))
    except Exception:
        return None


def _check_usage_alarms(numbers: dict, updates: int, users: int,
                        jobs_ok: int = 0, jobs_failed: int = 0) -> None:
    """Blocking; runs in the same thread as the sample write."""
    jobs = jobs_ok + jobs_failed
    if (jobs >= USAGE_FAILURE_FLOOR
            and jobs_failed / jobs >= USAGE_FAILURE_WARN_RATIO
            and _alarm_due("failures")):
        family_link.report_event(
            "warning" if jobs_ok else "error", "job_failures",
            f"{jobs_failed} of {jobs} job(s) failed in the last "
            f"{USAGE_SAMPLE_MINUTES} min"
            + ("." if jobs_ok else " -- none succeeded."),
            "A job is whatever this bot is for: a conversion, a download, a pack "
            "edit. All of them failing usually means something outside the bot "
            "stopped answering rather than something inside it breaking.",
        )
    ceiling = numbers.get("ceiling_mb")
    peak = numbers.get("peak_rss_mb")
    if ceiling and peak and peak >= ceiling * USAGE_MEMORY_WARN_RATIO and _alarm_due("memory"):
        family_link.report_event(
            "warning", "memory_headroom",
            f"Memory peaked at {peak} MB of {ceiling} MB allowed "
            f"({peak / ceiling:.0%} of the limit).",
            "Crossing the limit is an out-of-memory kill rather than a slow reply. "
            "Either something is holding more than it should, or this service has "
            "outgrown its plan.",
        )

    baseline = _median(_usage_recent)
    if (updates >= USAGE_SPIKE_FLOOR and baseline > 0
            and updates >= baseline * USAGE_SPIKE_FACTOR and _alarm_due("spike")):
        family_link.report_event(
            "warning", "activity_spike",
            f"{updates} updates from {users} person(s) in {USAGE_SAMPLE_MINUTES} min, "
            f"against a recent median of {baseline:.0f}.",
            "Could be a launch and could be one script. /status and the usage table "
            "have the shape of it.",
        )

    monthly = _monthly_users()
    if monthly is not None and monthly >= USAGE_MONTHLY_USERS_WARN and _alarm_due("monthly_users"):
        family_link.report_event(
            "warning", "monthly_users",
            f"{monthly} distinct people used this bot in the last 30 days, "
            f"past the {USAGE_MONTHLY_USERS_WARN} mark.",
            "Nothing is refused and nothing is broken. It is the number that decides "
            "whether the plan this runs on is still the right one.",
        )


def _sample_usage_now() -> None:
    """One window: write the row, then decide whether to say anything.

    The counters are taken and reset first, so a slow database cannot make
    the next window count this one's updates twice."""
    global _usage_updates, _usage_users
    updates, users = _usage_updates, len(_usage_users)
    _usage_updates, _usage_users = 0, set()
    numbers = footprint_numbers()
    global _usage_sleepable, _usage_max_gap, _usage_jobs_ok, _usage_jobs_failed
    # The window ends with a gap in progress. Counting it now, and starting the
    # next window's clock from here, is what stops a bot that was quiet for six
    # hours reporting six hours of sleepable time in one window and none in the
    # twenty-three before it.
    global _usage_last_update
    now = time.monotonic()
    trailing = now - _usage_last_update
    sleepable = int(_usage_sleepable + max(0.0, trailing - SLEEP_AFTER_SECONDS))
    max_gap = int(max(_usage_max_gap, trailing))
    jobs_ok, jobs_failed = _usage_jobs_ok, _usage_jobs_failed
    _usage_sleepable, _usage_max_gap = 0.0, 0.0
    _usage_jobs_ok, _usage_jobs_failed = 0, 0
    _usage_last_update = now
    try:
        family_link.record_usage(
            USAGE_SAMPLE_MINUTES, numbers["rss_mb"], numbers["peak_rss_mb"],
            numbers["ceiling_mb"], numbers["cpu_seconds"], updates, users,
            sleepable, max_gap, jobs_ok, jobs_failed,
        )
    except Exception:
        logging.getLogger(__name__).debug("Usage sample not written", exc_info=True)
    try:
        _check_usage_alarms(numbers, updates, users, jobs_ok, jobs_failed)
    except Exception:
        logging.getLogger(__name__).debug("Usage alarm check failed", exc_info=True)
    _usage_recent.append(updates)


async def _usage_sample_job(context) -> None:
    await asyncio.to_thread(_sample_usage_now)
def build_status_text(start_time: datetime, users_last_hour: int, users_since_start: int) -> str:
    now = datetime.now(timezone.utc)
    uptime = now - start_time
    days, rem = divmod(int(uptime.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"
    return "\n".join([
        "📊 Status",
        f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ({uptime_str} ago)",
        f"Hosted: {detect_host_environment()}",
        f"Active users (last hour): {users_last_hour}",
        f"Active users (since this start): {users_since_start}",
        process_footprint(),
        "",
        error_summary(),
    ])
