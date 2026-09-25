#!/usr/bin/env python3
"""Every bot in the family, in one process.

    python bot.py                  run every bot that has a token set
    python bot.py sticker anon     run only these two (same as BOTS=sticker,anon)
    python bot.py --check          load every bot, prove they are kept apart, exit
    python bot.py --list           which bots exist and which have a token

WHAT THIS IS FOR
    The family normally runs as five services: one process, one repository
    and one deployment per bot. That is still the default and still the right
    shape -- see "What it costs" below. This file is the other shape, for when
    memory is the constraint: one interpreter and one event loop running all
    five `Application`s side by side.

    Almost all of an idle bot's memory is the interpreter and its libraries:
    Python itself, python-telegram-bot, httpx, psycopg, Pillow. Five
    processes load all of that five times. One process loads it once, and
    each bot adds only its own code and its own users' state on top.

HOW THE BOTS STAY SEPARATE
    Every bot folder is written as if it were the whole program: `import db`
    means *its* db, `import i18n` *its* translations, and the modules shared
    across the family (family_link, lifecycle, ...) keep per-bot state in
    module globals. So each bot is loaded as a package of its own --
    `sticker_bot.db`, `anon_bot.db` -- and inside a bot's modules, a bare
    `import db` resolves to that bot's copy. That is done by giving each
    bot's modules their own `__import__` (through their `__builtins__`), not
    by patching the interpreter's: libraries and every other bot are
    untouched.

    A shared module that lives once in shared/ is still instantiated once per
    bot, from the same file, and sees `__file__` as if it sat in that bot's
    folder -- which is where the bot's own copy would have been.

SETTINGS
    There is one environment, and each bot's modules see it through a view
    of their own (their `os.environ`), at load time and every time after:

      - <PREFIX>_<NAME> is <NAME> for that bot only: SBOT_POLL_TIMEOUT=50.
      - Some names only ever mean one bot -- DB_SCHEMA, PRIVACY_URL,
        TERMS_URL, PAYMENT_PROVIDER_TOKEN_*. For those the process-wide
        value is ignored (with a warning); only the prefixed one counts.
        DB_SCHEMA defaults to the bot's folder name, and PRIVACY_URL /
        TERMS_URL to POLICY_BASE_URL/<folder>/PRIVACY.md when that is set.
      - ADMIN_ID stands in for every <PREFIX>_ADMIN_ID that is not set: one
        owner, one line.
      - SIBLING_BOTS, when not set, is written from the public bots'
        <PREFIX>_USERNAME values.
      - An empty value counts as not set, so a blank line in a pasted
        settings file means "the default", not a crash.

WHAT IT COSTS
    Everything the five-process shape exists to prevent:
      - one out-of-memory kill takes all five bots down, not one;
      - one deploy restarts all five, and `/run <bot> restart` from
        ManagerBot restarts all five (it exits the process);
      - a bot cannot be held back from a release.
    A handler that raises is still caught per bot, as it always was, and a
    bot that cannot start is logged and left out while the others run.

Nothing in the bots' own code knows which shape it is running in.
"""
from __future__ import annotations

import asyncio
import builtins
import contextlib
import contextvars
import gc
import importlib
import importlib.machinery
import importlib.util
import inspect
import json
import logging
import os
import signal
import sys
import time
import types
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# How long a SIGTERM waits for every bot to tell its users what was
# interrupted before the process stops anyway. Railway's own draining window
# is longer; this only has to cover a few sendMessage calls.
DRAIN_SECONDS = float(os.environ.get("UNIFIED_DRAIN_SECONDS") or 30)
# A one-line summary in the log every this many minutes -- which bots are up
# and what the process is holding. 0 turns it off.
STATUS_MINUTES = float(os.environ.get("UNIFIED_STATUS_MINUTES") or 30)
# One thread pool for all five. Each bot sizes its own at 4 when it runs
# alone; five bots sharing four would let two slow downloads hold up every
# other bot's database calls. Threads are started only when needed, so an
# idle process pays for none of them.
WORKER_THREADS = int(os.environ.get("WORKER_THREADS") or 8)
# The "N/5 polling" line is written once every bot has started or this many
# seconds have passed, whichever is first.
STARTUP_REPORT_SECONDS = 300

# Settings that only ever mean one bot. Given process-wide they would
# re-point, rename or bill all five at once, so only the prefixed form counts.
PER_BOT_ONLY = ("DB_SCHEMA", "FAMILY_BOT_ID", "FAMILY_LABEL", "PRIVACY_URL", "TERMS_URL")
PER_BOT_ONLY_PREFIXES = ("PAYMENT_PROVIDER_TOKEN_",)   # one per currency; a provider token belongs to one bot
# <PREFIX>_<NAME> is <NAME> for that bot -- except these, which the bots
# already read under their prefixed names.
NOT_OVERRIDES = {"TOKEN", "USERNAME", "ADMIN_ID"}
# Where each bot's PRIVACY.md and TERMS.md are published, as
# <base>/<folder>/PRIVACY.md -- one line instead of eight.
POLICY_DOCUMENTS = {"PRIVACY_URL": "PRIVACY.md", "TERMS_URL": "TERMS.md"}
# Words that read naturally for a bot but are not derived from its folder.
ALIASES = {"parent": "manager_bot", "parentbot": "manager_bot", "chat": "anon_bot"}

log = logging.getLogger("family")


# ---------------------------------------------------------------------------
# Which bots there are
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class Bot:
    folder: str                      # sticker_bot -- package name and Postgres schema
    name: str                        # StickerBot
    prefix: str                      # SBOT
    directory: Path
    shared: tuple = ()               # modules taken from the shared folder
    local: frozenset = frozenset()   # every bare name that means "this bot's module"
    import_table: dict | None = None
    dotenv: dict = field(default_factory=dict)   # the bot's own .env, in the development tree
    handlers: list = field(default_factory=list)
    initialized: bool = False
    module: types.ModuleType | None = None
    app: object | None = None
    polling: dict = field(default_factory=dict)
    context: contextvars.Context | None = None
    task: asyncio.Task | None = None
    state: str = "new"               # loaded, starting, running, stopped, failed, skipped
    problem: str = ""

    @property
    def names(self) -> set[str]:
        role = self.folder.removesuffix("_bot")
        found = {self.folder, role, self.name.lower(), self.prefix.lower()}
        found |= {alias for alias, folder in ALIASES.items() if folder == self.folder}
        return found

    def token_set(self) -> bool:
        return bool(setting(self, f"{self.prefix}_TOKEN"))

    def read_own_env_file(self) -> None:
        """Run from the development tree, each bot folder has a .env of its
        own, and what is in it is that bot's alone -- including the names
        that would otherwise be ignored process-wide, like DB_SCHEMA."""
        env_file = self.directory / ".env"
        if env_file.is_file():
            try:
                from dotenv import dotenv_values
            except ImportError:
                log.warning("%s has a .env but python-dotenv is not installed -- ignoring it.", self.name)
                return
            self.dotenv = {key: value for key, value in dotenv_values(env_file).items() if value}


def _family_name(folder: str) -> str:
    return "".join(part.title() for part in folder.split("_"))


def discover() -> tuple[list[Bot], Path | None, str]:
    """The bots next to this file.

    Two layouts. The published one is bots/<folder>/ with the family's shared
    modules once, in shared/, and bots/bots.json saying which bot uses which.
    The development one is the monorepo itself -- this file in unified/, each
    bot folder beside it carrying its own copies -- so a change can be tried
    in one process without building anything first."""
    manifest = ROOT / "bots" / "bots.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        bots = [Bot(folder=entry["folder"], name=entry["name"], prefix=entry["prefix"],
                    directory=ROOT / "bots" / entry["folder"], shared=tuple(entry["shared"]))
                for entry in data["bots"]]
        return bots, ROOT / "shared", data.get("version", "?")
    parent = ROOT.parent
    bots = [Bot(folder=path.parent.name, name=_family_name(path.parent.name),
                prefix=path.parent.name[0].upper() + "BOT", directory=path.parent)
            for path in sorted(parent.glob("*_bot/bot.py"))]
    return bots, None, "development tree"


def select(bots: list[Bot], wanted: list[str]) -> list[Bot]:
    if not wanted or wanted == ["all"]:
        return bots
    chosen, unknown = [], []
    for word in wanted:
        match = next((bot for bot in bots if word.lower().lstrip("@") in bot.names), None)
        if match is None:
            unknown.append(word)
        elif match not in chosen:
            chosen.append(match)
    if unknown:
        known = ", ".join(bot.folder.removesuffix("_bot") for bot in bots)
        raise SystemExit(f"Unknown bot(s): {', '.join(unknown)}. Known: {known}.")
    return chosen


# ---------------------------------------------------------------------------
# One environment, a view of it per bot
# ---------------------------------------------------------------------------
# Every bot reads its settings from os.environ, some when it loads and some
# (a payment token, a feature flag) every time it needs them. In one process
# there is one os.environ, so each bot's modules are given their own view of
# it instead -- through `import os`, the same way `import db` is theirs --
# and every rule about which value a bot sees lives in setting() below.

def _per_bot_only(key: str) -> bool:
    return key in PER_BOT_ONLY or key.startswith(PER_BOT_ONLY_PREFIXES)


def setting(bot: Bot, key: str) -> str | None:
    """The value of `key` as `bot` sees it, or None. Empty counts as unset."""
    env, own = os.environ, bot.dotenv

    if key.startswith(bot.prefix + "_"):
        # A name the bot reads under its own prefix already: SBOT_TOKEN.
        value = env.get(key) or own.get(key)
        if not value and key == f"{bot.prefix}_ADMIN_ID":
            value = env.get("ADMIN_ID") or own.get("ADMIN_ID")
        return value or None

    if key not in NOT_OVERRIDES:
        value = env.get(f"{bot.prefix}_{key}")
        if value:
            return value

    if _per_bot_only(key):
        if own.get(key):
            return own[key]
        if key == "DB_SCHEMA":
            return bot.folder
        base = (env.get("POLICY_BASE_URL") or "").rstrip("/")
        if key in POLICY_DOCUMENTS and base:
            return f"{base}/{bot.folder}/{POLICY_DOCUMENTS[key]}"
        return None

    return env.get(key) or own.get(key) or None


class BotEnviron(MutableMapping):
    """os.environ as one bot sees it. Reads go through setting(); writes go
    to the real environment, as they always would."""

    def __init__(self, bot: Bot):
        self._bot = bot

    def __getitem__(self, key):
        value = setting(self._bot, key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        os.environ[key] = value

    def __delitem__(self, key):
        del os.environ[key]

    def _names(self):
        names = set(os.environ) | set(self._bot.dotenv) | {"DB_SCHEMA"}
        for key in os.environ:
            if key.startswith(self._bot.prefix + "_"):
                names.add(key[len(self._bot.prefix) + 1:])
        return names

    def __iter__(self):
        return iter(sorted(name for name in self._names() if setting(self._bot, name) is not None))

    def __len__(self):
        return sum(1 for _ in self)

    def copy(self) -> dict:
        return dict(self)

    def __repr__(self):
        return f"<environment as {self._bot.name} sees it>"


class _BotOs(types.ModuleType):
    """`os` as a bot's modules see it: the real one, except its environment."""

    def __init__(self, bot: Bot):
        super().__init__("os", os.__doc__)
        self.environ = BotEnviron(bot)

    def __getattr__(self, attribute):
        return getattr(os, attribute)

    def getenv(self, key, default=None):
        return self.environ.get(key, default)


# ---------------------------------------------------------------------------
# One package per bot
# ---------------------------------------------------------------------------

_PACKAGES: dict[str, Bot] = {}
_SHARED_DIR: Path | None = None
_CURRENT: contextvars.ContextVar[Bot | None] = contextvars.ContextVar("family_bot", default=None)


class _BotFinder:
    """Finds `<bot>.<module>` for the packages registered below, and nothing
    else, so no other import in the process can be affected by it."""

    @staticmethod
    def find_spec(fullname, path=None, target=None):
        package, dot, name = fullname.partition(".")
        bot = _PACKAGES.get(package)
        if bot is None or not dot or "." in name:
            return None
        own = bot.directory / f"{name}.py"
        if own.is_file():
            real = own
        elif name in bot.shared and _SHARED_DIR is not None:
            real = _SHARED_DIR / f"{name}.py"
        else:
            return None
        loader = _BotLoader(fullname, str(real), bot, str(own))
        return importlib.util.spec_from_file_location(fullname, str(real), loader=loader)


class _BotLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname, path, bot, seen_as):
        super().__init__(fullname, path)
        self.bot, self.seen_as = bot, seen_as

    def exec_module(self, module):
        module.__builtins__ = self.bot.import_table
        # Where the bot's own copy would have been: logs/ and anything else a
        # module finds relative to itself stays inside that bot's folder.
        module.__file__ = self.seen_as
        super().exec_module(module)


class _BotImportlib(types.ModuleType):
    """`importlib` as a bot's modules see it. family_link looks up its
    sibling modules by name at run time -- importlib.import_module("i18n") --
    and that has to find the calling bot's i18n, not fail and quietly fall
    back to English."""

    def __init__(self, bot: Bot):
        super().__init__("importlib", importlib.__doc__)
        self._bot = bot

    def __getattr__(self, attribute):
        return getattr(importlib, attribute)

    def import_module(self, name, package=None):
        if name in self._bot.local:
            return importlib.import_module(f"{self._bot.folder}.{name}")
        return importlib.import_module(name, package)


def _builtins_for(bot: Bot) -> dict:
    real_import = builtins.__import__
    proxies = {"importlib": _BotImportlib(bot), "os": _BotOs(bot)}

    def bot_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0:
            if name in bot.local:
                return importlib.import_module(f"{bot.folder}.{name}")
            top = name.partition(".")[0]
            if top in proxies and (name == top or not fromlist):
                real_import(name, globals, locals, fromlist, level)
                return proxies[top]
        return real_import(name, globals, locals, fromlist, level)

    table = dict(vars(builtins))
    table["__import__"] = bot_import
    return table


def register(bot: Bot) -> None:
    names = {path.stem for path in bot.directory.glob("*.py")} | set(bot.shared)
    bot.local = frozenset(names)
    bot.import_table = _builtins_for(bot)
    package = types.ModuleType(bot.folder)
    package.__path__ = []          # members are found by _BotFinder, never by path
    package.__package__ = bot.folder
    sys.modules[bot.folder] = package
    _PACKAGES[bot.folder] = bot


def forget(bot: Bot) -> None:
    """Drop a bot that will not run, so what it loaded can be freed."""
    db = sys.modules.get(f"{bot.folder}.db")
    close = getattr(db, "close_pool", None)
    if callable(close):
        with contextlib.suppress(Exception):
            close()
    for logger, handler in bot.handlers:
        logger.removeHandler(handler)
        with contextlib.suppress(Exception):
            handler.close()
    bot.handlers.clear()
    for name in [name for name in sys.modules if name == bot.folder or name.startswith(bot.folder + ".")]:
        del sys.modules[name]
    bot.module = bot.app = None


@contextlib.contextmanager
def bot_environment(bot: Bot):
    """Whatever a bot writes into the real environment while it loads -- its
    own load_dotenv() does, in the development tree -- is undone afterwards,
    so the next bot does not inherit it. What the bot *reads* comes through
    its own view (BotEnviron) and needs nothing here."""
    saved = dict(os.environ)
    try:
        yield
    finally:
        if dict(os.environ) != saved:
            os.environ.clear()
            os.environ.update(saved)


# ---------------------------------------------------------------------------
# One log, with every line saying whose it is
# ---------------------------------------------------------------------------

_FORMAT = "%(asctime)s %(bot)-13s %(levelname)-7s %(where)s: %(message)s"


def _install_log_tagging() -> None:
    """Stamp every record with the bot it came from: by logger name when the
    logger belongs to a bot package, otherwise by the bot whose task or thread
    wrote it -- which is how python-telegram-bot's and psycopg's own lines get
    attributed."""
    base = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = base(*args, **kwargs)
        package, _, rest = record.name.partition(".")
        bot = _PACKAGES.get(package)
        if bot is not None:
            record.where = rest or package
        else:
            bot = _CURRENT.get()
            record.where = record.name
        record.bot = bot.name if bot is not None else "family"
        return record

    logging.setLogRecordFactory(factory)


class _OnlyBot(logging.Filter):
    def __init__(self, name: str):
        super().__init__()
        self.bot_name = name

    def filter(self, record) -> bool:
        return getattr(record, "bot", None) == self.bot_name


@contextlib.contextmanager
def adopting_handlers(bot: Bot):
    """While a bot loads, every handler it attaches to the root or `problems`
    logger is filtered down to that bot's own records -- so its /logs and its
    log files are its own -- and its console handler is dropped, because this
    process already prints one line per record for everybody."""
    root, problems = logging.getLogger(), logging.getLogger("problems")

    def adopt(logger):
        original = logger.addHandler

        def add(handler):
            if logger is root and type(handler) is logging.StreamHandler:
                return
            handler.addFilter(_OnlyBot(bot.name))
            bot.handlers.append((logger, handler))
            original(handler)
        logger.addHandler = add

    adopt(root)
    adopt(problems)
    try:
        yield
    finally:
        for logger in (root, problems):
            with contextlib.suppress(AttributeError):
                del logger.addHandler


def setup_logging() -> None:
    _install_log_tagging()
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger()
    root.addHandler(console)
    root.setLevel(logging.INFO)
    for noisy in ("httpx", "httpcore", "telegram.ext.Updater", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # Python's own warnings (python-telegram-bot has a few at startup) into
    # the same log, attributed like everything else, instead of raw stderr.
    logging.captureWarnings(True)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def _libc():
    if sys.platform != "linux":
        return None
    try:
        import ctypes
        return ctypes.CDLL("libc.so.6")
    except OSError:
        return None     # not glibc (Alpine's musl, say): nothing to tune


_LIBC = _libc()


def cap_malloc_arenas() -> None:
    """glibc gives a threaded process up to 8 x cpu_count malloc arenas, and
    cpu_count in a container is the host's. MALLOC_ARENA_MAX in the image
    does this before Python starts; this covers a host that did not set it.
    Must run before the first worker thread exists."""
    if _LIBC is not None and "MALLOC_ARENA_MAX" not in os.environ:
        with contextlib.suppress(Exception):
            _LIBC.mallopt(-8, 2)   # M_ARENA_MAX


def give_back_memory() -> None:
    """Return freed heap pages to the kernel. Loading five bots allocates and
    drops a lot along the way, and glibc keeps what it freed unless asked."""
    gc.collect()
    if _LIBC is not None:
        with contextlib.suppress(Exception):
            _LIBC.malloc_trim(0)


def footprint() -> str:
    numbers = {}
    with contextlib.suppress(OSError):
        with open("/proc/self/status") as status:
            for line in status:
                key, _, value = line.partition(":")
                if key in ("VmRSS", "VmHWM", "Threads"):
                    numbers[key] = int(value.split()[0])
    if "VmRSS" not in numbers:
        return "memory not readable here"
    return (f"{numbers['VmRSS'] // 1024} MB resident (peak {numbers.get('VmHWM', 0) // 1024} MB), "
            f"{numbers.get('Threads', '?')} threads")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_ORIGINAL_RUN_POLLING = None


def _capture_run_polling(self, *args, **kwargs):
    """Each bot's main() ends in app.run_polling(), which would take the event
    loop for itself and never return. Here it only records the arguments;
    the bots are started together further down."""
    bot = _CURRENT.get()
    if bot is None:
        return _ORIGINAL_RUN_POLLING(self, *args, **kwargs)
    arguments = inspect.signature(_ORIGINAL_RUN_POLLING).bind(self, *args, **kwargs).arguments
    arguments.pop("self", None)
    bot.app, bot.polling = self, dict(arguments)


def load(bot: Bot, wire: bool = True) -> bool:
    """Import the bot and run its main() as far as run_polling. False, with
    bot.state and bot.problem saying why, if it cannot run."""
    token = _CURRENT.set(bot)
    try:
        with bot_environment(bot), adopting_handlers(bot):
            bot.module = importlib.import_module(f"{bot.folder}.bot")
            if wire:
                bot.module.main()
                if bot.app is None:
                    raise RuntimeError("main() returned without starting to poll")
        bot.state = "loaded"
        return True
    except SystemExit as exc:       # the bot's own "set X first" refusals
        bot.state, bot.problem = "skipped", str(exc)
        log.warning("%s is not running: %s", bot.name, exc)
    except Exception as exc:
        bot.state, bot.problem = "failed", f"{type(exc).__name__}: {exc}"
        log.exception("%s could not be loaded -- the others carry on without it", bot.name)
    finally:
        _CURRENT.reset(token)
    forget(bot)
    return False


def one_memory_reporter(bots: list[Bot]) -> None:
    """Every bot records what its process holds, for ManagerBot's /usage and
    the memory alarm. Here all five would record the same process, and
    ManagerBot would add it up five times and raise the same alarm five
    times. One bot -- ManagerBot when it is here -- keeps reporting memory;
    the others report their traffic and jobs as before and memory as
    "not measured", which is what None means to both readers."""
    loaded = [bot for bot in bots if bot.state == "loaded"]
    if len(loaded) < 2:
        return
    reporter = next((bot for bot in loaded if bot.folder == "manager_bot"), loaded[0])
    for bot in loaded:
        if bot is reporter:
            continue
        link = sys.modules.get(f"{bot.folder}.family_link")
        monitor = (sys.modules.get(f"{bot.folder}.shared_features")
                   or sys.modules.get(f"{bot.folder}.monitoring"))
        if not (hasattr(link, "record_usage") and hasattr(monitor, "_check_usage_alarms")):
            log.warning("%s: could not route memory reports through %s -- /usage will "
                        "count this process more than once", bot.name, reporter.name)
            continue
        record, alarms = link.record_usage, monitor._check_usage_alarms

        def record_usage(window, rss, peak, ceiling, cpu, *rest, _record=record, **named):
            return _record(window, None, None, None, None, *rest, **named)

        def check_alarms(numbers, *rest, _alarms=alarms, **named):
            quiet = dict(numbers, rss_mb=None, peak_rss_mb=None, ceiling_mb=None)
            return _alarms(quiet, *rest, **named)

        link.record_usage = record_usage
        monitor._check_usage_alarms = check_alarms


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

class Family:
    def __init__(self, bots: list[Bot]):
        self.bots = bots
        self.by_app = {id(bot.app): bot for bot in bots}
        self.stopping = False
        self.waiting: set[Bot] = set()
        self.signal_handlers: dict[int, list] = {}
        self.stop_event: asyncio.Event | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.exit_code = 0

    # -- signals ------------------------------------------------------------
    # lifecycle.py takes SIGTERM so that a redeploy can tell whoever is
    # mid-conversion what happened. It does that with
    # loop.add_signal_handler(), and a loop has one handler per signal: five
    # bots registering in turn would leave only the last one hearing it. So
    # this process owns the signals and hands each one to every bot.

    def take_signals(self) -> None:
        loop = self.loop
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.on_signal, sig)
            except (NotImplementedError, RuntimeError, ValueError):
                # Windows: no loop signal handlers. Ctrl-C still arrives.
                with contextlib.suppress(ValueError, OSError):
                    signal.signal(sig, lambda number, frame: loop.call_soon_threadsafe(self.on_signal, number))
        loop.add_signal_handler = self._register_signal
        loop.remove_signal_handler = self._unregister_signal

    def _register_signal(self, sig, callback, *args) -> None:
        self.signal_handlers.setdefault(int(sig), []).append((_CURRENT.get(), callback, args))

    def _unregister_signal(self, sig) -> bool:
        bot = _CURRENT.get()
        kept = [entry for entry in self.signal_handlers.get(int(sig), []) if entry[0] is not bot]
        self.signal_handlers[int(sig)] = kept
        return True

    def on_signal(self, sig: int) -> None:
        try:
            name = signal.Signals(sig).name
        except ValueError:
            name = f"signal {sig}"
        if self.stopping:
            log.warning("%s again -- stopping without waiting for the bots to finish.", name)
            self.stop_event.set()
            return
        self.stopping = True
        running = [bot for bot in self.bots if bot.state == "running"]
        log.info("%s -- stopping %d bot(s).", name, len(running))
        for bot in self.bots:
            if bot.task is not None and not bot.task.done():
                bot.task.cancel()      # still starting: nothing to drain
        handlers = [entry for entry in self.signal_handlers.get(sig, [])
                    if entry[0] is None or entry[0].state == "running"]
        self.waiting = {bot for bot, _, _ in handlers if bot is not None}
        for bot, callback, args in handlers:
            try:
                (bot.context.run(callback, *args) if bot is not None else callback(*args))
            except Exception:
                log.exception("%s: stop handler failed", bot.name if bot else "?")
        if not self.waiting:
            self.stop_event.set()
        else:
            self.loop.call_later(DRAIN_SECONDS, self.stop_event.set)

    def on_stop_running(self, app) -> None:
        """Application.stop_running(), as this process understands it. Alone,
        a bot calls it to end its process; here it means that bot is done
        draining -- and, outside a shutdown, that that one bot stops."""
        bot = self.by_app.get(id(app))
        if bot is None:
            return
        if self.stopping:
            self.waiting.discard(bot)
            if not self.waiting:
                self.stop_event.set()
            return
        log.info("%s asked to stop; the other bots carry on.", bot.name)
        self.loop.create_task(self.stop_one(bot), context=bot.context)

    # -- starting -------------------------------------------------------------

    async def _initialize(self, bot: Bot) -> None:
        """app.initialize() is where the bot first talks to Telegram and reads
        its saved state. Run alone, a failure here ends the process and the
        platform restarts it; here, a network failure is waited out instead,
        so one bot's bad minute does not become every bot's restart."""
        from telegram.error import InvalidToken, NetworkError
        delay, attempt = 5, 0
        while True:
            try:
                await bot.app.initialize()
                return
            except InvalidToken:
                raise
            except Exception as exc:
                attempt += 1
                if not isinstance(exc, NetworkError) and attempt >= 6:
                    raise
                log.warning("Could not start yet (%s: %s) -- trying again in %ss.",
                            type(exc).__name__, exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 120)

    def _polling_arguments(self, bot: Bot) -> dict:
        app = bot.app
        wanted = ("poll_interval", "timeout", "bootstrap_retries", "allowed_updates",
                  "drop_pending_updates")
        arguments = {key: value for key, value in bot.polling.items() if key in wanted}
        if not arguments.get("bootstrap_retries"):
            arguments["bootstrap_retries"] = -1

        def error_callback(exc):
            app.create_task(app.process_error(error=exc, update=None))

        arguments["error_callback"] = error_callback
        return arguments

    async def start(self, bot: Bot) -> None:
        app = bot.app
        bot.state = "starting"
        try:
            await self._initialize(bot)
            bot.initialized = True
            if app.post_init:
                await app.post_init(app)
            await app.updater.start_polling(**self._polling_arguments(bot))
            await app.start()
        except asyncio.CancelledError:
            bot.state = "stopped"
            await self.teardown(bot)
            raise
        except Exception as exc:
            bot.state, bot.problem = "failed", f"{type(exc).__name__}: {exc}"
            others = any(other.state in ("running", "starting") for other in self.bots)
            log.exception("Could not start%s.", " -- the other bots carry on without it" if others else "")
            await self.teardown(bot)
            if not any(other.state in ("running", "starting") for other in self.bots):
                self.exit_code = 1
                self.stop_event.set()
            return
        bot.state = "running"
        log.info("Polling as @%s.", app.bot.username)

    # -- stopping -------------------------------------------------------------

    async def teardown(self, bot: Bot) -> None:
        """Everything run_polling does on its way out, in the same order."""
        app = bot.app
        steps = []
        if app.updater is not None and app.updater.running:
            steps.append(app.updater.stop)
        if app.running:
            steps.append(app.stop)
        if bot.initialized:
            # Also for a bot that failed after initialising: post_stop is what
            # saves its state, releases its poll lease and closes its pool.
            if app.post_stop:
                steps.append(lambda: app.post_stop(app))
            steps.append(app.shutdown)
            if app.post_shutdown:
                steps.append(lambda: app.post_shutdown(app))
        for step in steps:
            try:
                await step()
            except Exception:
                log.exception("Error while stopping")
        if not bot.initialized:
            # Never reached Telegram, so none of the above had anything to
            # undo -- except the pool main() opened.
            close = getattr(sys.modules.get(f"{bot.folder}.db"), "close_pool", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(close)

    async def stop_one(self, bot: Bot) -> None:
        await self.teardown(bot)
        bot.state = "stopped"
        if not any(other.state in ("running", "starting") for other in self.bots):
            self.stop_event.set()

    # -- the whole run --------------------------------------------------------

    def _take_executor(self) -> None:
        self.loop.set_default_executor(
            ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="worker"))

        def keep_the_shared_one(executor):
            # Every bot's tune_runtime() installs a pool sized for itself alone.
            executor.shutdown(wait=False)

        self.loop.set_default_executor = keep_the_shared_one

    async def _spectate(self) -> None:
        while True:
            await asyncio.sleep(STATUS_MINUTES * 60)
            give_back_memory()
            log.info("%s · %s", self.board(), footprint())

    def board(self) -> str:
        up = [bot.name for bot in self.bots if bot.state == "running"]
        down = [f"{bot.name} {bot.state}" for bot in self.bots if bot.state != "running"]
        return f"{len(up)}/{len(self.bots)} polling" + (f" (not: {', '.join(down)})" if down else "")

    async def run(self) -> int:
        self.loop = asyncio.get_running_loop()
        self.stop_event = asyncio.Event()
        self.take_signals()
        self._take_executor()

        for bot in self.bots:
            bot.context = contextvars.copy_context()
            bot.context.run(_CURRENT.set, bot)
            bot.task = self.loop.create_task(self.start(bot), context=bot.context)
        starting = asyncio.gather(*(bot.task for bot in self.bots), return_exceptions=True)
        stopped = self.loop.create_task(self.stop_event.wait())
        spectator = None
        try:
            # Usually every bot is polling within seconds. One waiting out a
            # network problem, or an old container's poll lease, must not
            # hold up the report on the rest.
            await asyncio.wait({starting, stopped}, timeout=STARTUP_REPORT_SECONDS,
                               return_when=asyncio.FIRST_COMPLETED)
            if not stopped.done():
                # Everything imported and started is here for the life of the
                # process: out of the collector's sight, and the churn of
                # getting here handed back to the kernel.
                give_back_memory()
                gc.freeze()
                log.info("%s · %s", self.board(), footprint())
                if STATUS_MINUTES > 0:
                    spectator = self.loop.create_task(self._spectate())
                await stopped
        finally:
            if spectator is not None:
                spectator.cancel()
            await asyncio.gather(starting, return_exceptions=True)
            stopped.cancel()
            await asyncio.gather(*(self._stop_in_context(bot) for bot in self.bots
                                   if bot.state == "running"))
            log.info("Stopped.")
        if self.exit_code:
            log.error("No bot could start.")
        return self.exit_code

    async def _stop_in_context(self, bot: Bot) -> None:
        task = self.loop.create_task(self.stop_one(bot), context=bot.context)
        await task


def patch_python_telegram_bot(family_holder: list) -> None:
    """The two places where python-telegram-bot assumes it owns the process."""
    global _ORIGINAL_RUN_POLLING
    from telegram.ext import Application

    _ORIGINAL_RUN_POLLING = Application.run_polling
    Application.run_polling = _capture_run_polling

    def stop_running(self):
        if family_holder:
            family_holder[0].on_stop_running(self)
    Application.stop_running = stop_running


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if env_file.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file, override=False)
        except ImportError:
            log.warning(".env found but python-dotenv is not installed -- ignoring it.")


def _clear_per_bot_settings() -> None:
    for key in [key for key in os.environ if _per_bot_only(key)]:
        if os.environ[key]:
            shown = "<set>" if key.startswith(PER_BOT_ONLY_PREFIXES) else os.environ[key]
            log.warning("Ignoring %s=%s: in one process it would apply to every bot. "
                        "Give it to one bot with its prefix, e.g. SBOT_%s.", key, shown, key)
        del os.environ[key]


def derive_siblings(bots: list[Bot]) -> None:
    """SIBLING_BOTS -- how the public bots point at each other -- is nothing
    but their usernames, which are already set once each. Written from them
    unless it was given."""
    if os.environ.get("SIBLING_BOTS"):
        return
    entries = [f"{bot.name.lower()}:{bot.name}:{setting(bot, f'{bot.prefix}_USERNAME')}"
               for bot in bots
               if bot.folder != "manager_bot" and setting(bot, f"{bot.prefix}_USERNAME")]
    if entries:
        os.environ["SIBLING_BOTS"] = ",".join(entries)


def check(bots: list[Bot]) -> int:
    """Load every bot without starting any, and prove each got its own modules."""
    failures = []

    def expect(what, ok):
        if not ok:
            failures.append(what)
            print(f"  FAIL  {what}")

    started = time.monotonic()
    loaded = [bot for bot in bots if load(bot, wire=False)]
    seconds = time.monotonic() - started
    expect("every bot loads", len(loaded) == len(bots))
    for bot in loaded:
        package = bot.folder
        mine = {name: module for name, module in sys.modules.items() if name.startswith(package + ".")}
        db = mine.get(f"{package}.db")
        link = mine.get(f"{package}.family_link")
        expect(f"{bot.name}: db.DB_SCHEMA is {package}", getattr(db, "DB_SCHEMA", None) == package)
        expect(f"{bot.name}: family_link uses its own db", getattr(link, "db", None) is db)
        if hasattr(link, "_i18n"):
            expect(f"{bot.name}: family_link finds its own translations",
                   link._i18n() is mine.get(f"{package}.i18n"))
        if hasattr(link, "_monitoring"):
            expect(f"{bot.name}: family_link finds its own monitoring",
                   link._monitoring() in (mine.get(f"{package}.shared_features"),
                                          mine.get(f"{package}.monitoring")))
        for name in bot.shared:
            module = mine.get(f"{package}.{name}")
            if module is not None:
                expect(f"{bot.name}: {name} sees itself in its bot's folder",
                       Path(module.__file__).parent == bot.directory)
        # Settings, read the way the bot reads them -- through its own `os`.
        view = getattr(db, "os", None)
        expect(f"{bot.name}: reads settings through its own view", isinstance(view, _BotOs))
        if isinstance(view, _BotOs):
            expect(f"{bot.name}: sees DB_SCHEMA={package} after loading too",
                   view.environ.get("DB_SCHEMA") == package)
            for key, value in os.environ.items():
                other = next((b for b in bots if key.startswith(b.prefix + "_")), None)
                name = key.split("_", 1)[1] if other else None
                if not value or name in NOT_OVERRIDES or name is None:
                    continue
                if other is bot:
                    expect(f"{bot.name}: {key} reaches it as {name}", view.environ.get(name) == value)
                elif _per_bot_only(name):
                    expect(f"{bot.name}: {key} does not leak into it", view.environ.get(name) != value)
        admins = os.environ.get("ADMIN_ID")
        own_admins = f"{bot.prefix}_ADMIN_ID"
        if (admins and hasattr(bot.module, "ADMIN_IDS")
                and not (os.environ.get(own_admins) or bot.dotenv.get(own_admins))):
            expect(f"{bot.name}: ADMIN_ID is its admin list",
                   bot.module.ADMIN_IDS == {int(x) for x in admins.split(",") if x.strip()})
        print(f"  ok    {bot.name}: {len(mine)} modules, schema {getattr(db, 'DB_SCHEMA', '?')}")
    links = [sys.modules.get(f"{bot.folder}.family_link") for bot in loaded]
    expect("no two bots share a family_link", len({id(link) for link in links}) == len(links))
    homes = {bot.directory.resolve() for bot in bots} | ({_SHARED_DIR.resolve()} if _SHARED_DIR else set())
    leaked = sorted(name for bot in loaded for name in bot.local
                    if getattr(sys.modules.get(name), "__file__", None)
                    and Path(sys.modules[name].__file__).resolve().parent in homes)
    expect(f"no bot module loaded under its bare name ({', '.join(leaked)})", not leaked)
    give_back_memory()
    print(f"\n{len(loaded)} bot(s) loaded in {seconds:.1f}s; {footprint()}")
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("All checks passed.")
    return 0


def main(argv: list[str]) -> int:
    global _SHARED_DIR
    cap_malloc_arenas()
    setup_logging()
    _load_dotenv()
    _clear_per_bot_settings()

    flags = {arg for arg in argv if arg.startswith("-")}
    words = [arg for arg in argv if not arg.startswith("-")]
    if not words and os.environ.get("BOTS"):
        words = [word.strip() for word in os.environ["BOTS"].split(",") if word.strip()]

    everything, _SHARED_DIR, version = discover()
    if not everything:
        raise SystemExit(f"No bots found next to {ROOT}.")
    for bot in everything:
        bot.read_own_env_file()
    derive_siblings(everything)
    bots = select(everything, words)

    if "--list" in flags:
        for bot in everything:
            mark = "token set" if bot.token_set() else f"no {bot.prefix}_TOKEN"
            print(f"  {bot.folder.removesuffix('_bot'):<11} {bot.name:<14} {mark}")
        return 0

    sys.meta_path.insert(0, _BotFinder)
    for bot in bots:
        register(bot)
    if "--check" in flags:
        return check(bots)

    family_holder: list[Family] = []
    patch_python_telegram_bot(family_holder)
    log.info("Bot family %s, one process: %s", version, ", ".join(bot.name for bot in bots))
    tokens: dict[str, Bot] = {}
    runnable = []
    for bot in bots:
        if not bot.token_set():
            bot.state, bot.problem = "skipped", f"no {bot.prefix}_TOKEN"
            log.info("%s skipped: %s is not set.", bot.name, f"{bot.prefix}_TOKEN")
            continue
        token = setting(bot, f"{bot.prefix}_TOKEN")
        if token and token in tokens:
            bot.state, bot.problem = "skipped", f"same token as {tokens[token].name}"
            log.error("%s skipped: it has the same token as %s, and two pollers on one "
                      "token split its updates between them.", bot.name, tokens[token].name)
            continue
        if token:
            tokens[token] = bot
        if load(bot):
            runnable.append(bot)
    if not runnable:
        log.error("Nothing to run. Each bot needs its token, e.g. SBOT_TOKEN for StickerBot.")
        return 1
    one_memory_reporter(runnable)

    family = Family(runnable)
    family_holder.append(family)
    return asyncio.run(family.run())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
