#!/usr/bin/env python3
"""Every bot in the family, in one process.

    python main.py                  run every bot that has a token set
    python main.py sticker anon     run only these (same as BOTS=sticker,anon)
    python main.py --check          load every bot, prove they are kept apart, run one conversion, exit
    python main.py --list           which bots exist and which have a token
    python main.py --module KEY ... run one section as a program of its own (the conversion
                                    worker and the big-file transfer are started this way)

Each bot is loaded as a package of its own, so `import db` inside it means its
own db. The code is eight files, one per thing it does (core.py, bots.py,
storage.py, text.py, stickers.py, convert.py, download.py, anon.py), each made
of sections: `# ─── module: convert_bot.jobs` is ConvertBot's `jobs`, and a
section named without a bot -- `# ─── module: family_link` -- is one every bot
has a copy of. sections() reads them; a bot's modules are the sections named
for it.
"""
from __future__ import annotations

import asyncio
import builtins
import contextlib
import contextvars
import gc
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import inspect
import json
import logging
import os
import re
import signal
import sys
import time
import types
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent

DRAIN_SECONDS = float(os.environ.get("UNIFIED_DRAIN_SECONDS") or 30)

STATUS_MINUTES = float(os.environ.get("UNIFIED_STATUS_MINUTES") or 30)

WORKER_THREADS = int(os.environ.get("WORKER_THREADS") or 8)

STARTUP_REPORT_SECONDS = 300

PER_BOT_ONLY = ("DB_SCHEMA", "FAMILY_BOT_ID", "FAMILY_LABEL", "PRIVACY_URL", "TERMS_URL")
PER_BOT_ONLY_PREFIXES = ("PAYMENT_PROVIDER_TOKEN_",)

NOT_OVERRIDES = {"TOKEN", "USERNAME", "ADMIN_ID"}

POLICY_DOCUMENTS = {"PRIVACY_URL": "privacy", "TERMS_URL": "terms"}
LEGAL_URL = "https://github.com/MukhtorovMurodbek/MumuCombined/blob/main/LEGAL.md"

BOTS = (
    ("sticker_bot", "StickerBot", "SBOT"),
    ("convert_bot", "ConvertBot", "CBOT"),
    ("downloader_bot", "DownloaderBot", "DBOT"),
    ("anon_bot", "AnonBot", "ABOT"),
    ("manager_bot", "ManagerBot", "MBOT"),
)
# ManagerBot is private: no donations, no /cancel, no translations.
NOT_FOR = {"manager_bot": {"shared_features"}}

MARKER = re.compile(r"^# ─── module: ([\w.]+) ─*$")
_SECTIONS: dict[str, tuple[Path, int, str]] = {}


def sections() -> dict[str, tuple[Path, int, str]]:
    """Every section of every code file: {key: (file, lines before it, its source)}."""
    if not _SECTIONS:
        for path in sorted(ROOT.glob("*.py")):
            if path.name == "main.py":
                continue
            lines = path.read_text(encoding="utf-8").split("\n")
            key, start = None, 0
            for number, line in enumerate(lines):
                found = MARKER.match(line)
                if found:
                    if key:
                        _SECTIONS[key] = (path, start, "\n".join(lines[start:number]))
                    key, start = found.group(1), number + 1
            if key:
                _SECTIONS[key] = (path, start, "\n".join(lines[start:]))
    return _SECTIONS


def compiled(key: str):
    """A section's code, compiled as the file it is in, at its own lines -- so a
    traceback points at the right line of the right file."""
    path, start, source = sections()[key]
    return compile("\n" * start + source, str(path), "exec")

ALIASES = {"parent": "manager_bot", "parentbot": "manager_bot", "chat": "anon_bot"}

log = logging.getLogger("family")

@dataclass(eq=False)
class Bot:
    folder: str
    name: str
    prefix: str
    directory: Path
    shared: tuple = ()
    files: dict = field(default_factory=dict)
    local: frozenset = frozenset()
    import_table: dict | None = None
    dotenv: dict = field(default_factory=dict)
    handlers: list = field(default_factory=list)
    initialized: bool = False
    module: types.ModuleType | None = None
    app: object | None = None
    polling: dict = field(default_factory=dict)
    context: contextvars.Context | None = None
    task: asyncio.Task | None = None
    state: str = "new"
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
        """Run from the development tree, each bot folder has a .env of its own, and what is in it is that bot's alone -- including the names that would otherwise be ignored process-wide, like DB_SCHEMA."""
        env_file = self.directory / ".env"
        if env_file.is_file():
            try:
                from dotenv import dotenv_values
            except ImportError:
                log.warning("%s has a .env but python-dotenv is not installed -- ignoring it.", self.name)
                return
            self.dotenv = {key: value for key, value in dotenv_values(env_file).items() if value}

def discover() -> tuple[list[Bot], Path | None, str]:
    """The five bots. data/<folder>/ is each one's home: its logs, and its own .env if it has one."""
    shared = [key for key in sections() if "." not in key]
    bots = [Bot(folder=folder, name=name, prefix=prefix, directory=ROOT / "data" / folder,
                files={key.split(".", 1)[1]: key for key in sections() if key.startswith(folder + ".")},
                shared=tuple(key for key in shared if key not in NOT_FOR.get(folder, ())))
            for folder, name, prefix in BOTS]
    found = re.search(r'VERSION = os.environ.get\("FAMILY_VERSION", "([^"]+)"\)', sections()["family_link"][2])
    return bots, None, found.group(1) if found else "?"

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

def _per_bot_only(key: str) -> bool:
    return key in PER_BOT_ONLY or key.startswith(PER_BOT_ONLY_PREFIXES)

def setting(bot: Bot, key: str) -> str | None:
    """The value of `key` as `bot` sees it, or None. Empty counts as unset."""
    env, own = os.environ, bot.dotenv

    if key.startswith(bot.prefix + "_"):

        value = env.get(key) or own.get(key)
        if not value and key == f"{bot.prefix}_ADMIN_ID":
            value = env.get("ADMIN_ID") or own.get("ADMIN_ID")
        if value and key == f"{bot.prefix}_USERNAME":
            value = value.strip().lstrip("@")
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
        legal = (env.get("LEGAL_URL") or LEGAL_URL).strip()
        if key in POLICY_DOCUMENTS and legal and bot.folder != "manager_bot":
            return f"{legal}#{bot.name.lower()}-{POLICY_DOCUMENTS[key]}"
        return None

    return env.get(key) or own.get(key) or None

class BotEnviron(MutableMapping):
    """os.environ as one bot sees it."""

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

_PACKAGES: dict[str, Bot] = {}
_SHARED_DIR: Path | None = None
_CURRENT: contextvars.ContextVar[Bot | None] = contextvars.ContextVar("family_bot", default=None)

class _BotFinder:
    """Finds `<bot>.<module>` for the packages registered below, and nothing else, so no other import in the process can be affected by it."""

    @staticmethod
    def find_spec(fullname, path=None, target=None):
        package, dot, name = fullname.partition(".")
        bot = _PACKAGES.get(package)
        if bot is None or not dot or "." in name:
            return None
        key = bot.files.get(name) or (name if name in bot.shared else None)
        if key is None:
            return None
        loader = _SectionLoader(key, bot, str(bot.directory / f"{name}.py"))
        spec = importlib.util.spec_from_loader(fullname, loader, origin=str(sections()[key][0]))
        spec.has_location = True
        return spec

class _SectionLoader(importlib.abc.Loader):
    """One section, as a module of one bot's."""

    def __init__(self, key, bot, seen_as):
        self.key, self.bot, self.seen_as = key, bot, seen_as

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__builtins__ = self.bot.import_table
        module.__file__ = self.seen_as
        exec(compiled(self.key), module.__dict__)

class _BotImportlib(types.ModuleType):
    """`importlib` as a bot's modules see it."""

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
    names = set(bot.files) | set(bot.shared)
    bot.local = frozenset(names)
    bot.import_table = _builtins_for(bot)
    package = types.ModuleType(bot.folder)
    package.__path__ = []
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
    """Whatever a bot writes into the real environment while it loads -- its own load_dotenv() does, in the development tree -- is undone afterwards, so the next bot does not inherit it."""
    saved = dict(os.environ)
    try:
        yield
    finally:
        if dict(os.environ) != saved:
            os.environ.clear()
            os.environ.update(saved)

_FORMAT = "%(asctime)s %(bot)-13s %(levelname)-7s %(where)s: %(message)s"

def _install_log_tagging() -> None:
    """Stamp every record with the bot it came from: by logger name when the logger belongs to a bot package, otherwise by the bot whose task or thread wrote it -- which is how python-telegram-bot's and psycopg's own lines get attributed."""
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
    """While a bot loads, every handler it attaches to the root or `problems` logger is filtered down to that bot's own records -- so its /logs and its log files are its own -- and its console handler is dropped, because this process already prints one line per record for everybody."""
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
    """Information to stdout, warnings and errors to stderr: hosts like Railway mark a line's level by the stream it came on, so this is what makes an error show as an error in their log viewer."""
    _install_log_tagging()
    formatter = logging.Formatter(_FORMAT)
    ordinary = logging.StreamHandler(sys.stdout)
    ordinary.addFilter(lambda record: record.levelno < logging.WARNING)
    alarming = logging.StreamHandler(sys.stderr)
    alarming.setLevel(logging.WARNING)
    root = logging.getLogger()
    for handler in (ordinary, alarming):
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    for noisy in ("httpx", "httpcore", "telegram.ext.Updater", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.captureWarnings(True)

PLACEHOLDER = re.compile(r"<[^<>\s]*>")

DB_WAIT_SECONDS = float(os.environ.get("UNIFIED_DB_WAIT_SECONDS") or 120)

def _where(dsn: str) -> str:
    try:
        parts = urlsplit(dsn)
        return f"{parts.hostname or '?'}:{parts.port or 5432}"
    except ValueError:
        return "?"

def _database_problem(dsn: str) -> str | None:
    """None when the database answers; otherwise why not, in a sentence."""
    import psycopg

    where = _where(dsn)
    deadline = time.monotonic() + DB_WAIT_SECONDS
    while True:
        try:
            with psycopg.connect(dsn, connect_timeout=10) as connection:
                connection.execute("SELECT 1")
            return None
        except Exception as exc:
            first = (str(exc).strip().splitlines() or [type(exc).__name__])[0]
            said = first.lower()
            if "resolve host" in said or "name or service not known" in said or "nodename nor servname" in said:
                return (f"the database host in DATABASE_URL does not exist ({where}). "
                        f"The connection string was cut short or mistyped.")
            if "password authentication failed" in said:
                return (f"the database at {where} refused the password in DATABASE_URL. "
                        f"Characters like @ : / ? # and spaces in a password have to be "
                        f"percent-encoded (@ is %40).")
            if "tenant or user not found" in said:
                return (f"the pooler at {where} does not know the user in DATABASE_URL. "
                        f"Supabase's pooler wants postgres.<project ref> as the user.")
            if time.monotonic() >= deadline:
                return f"the database at {where} has not answered for {DB_WAIT_SECONDS:.0f}s ({first})."
            log.warning("The database at %s is not answering yet (%s) -- trying again in 10s.", where, first)
            time.sleep(10)

def preflight(bots: list[Bot]) -> str | None:
    """Everything wrong with the settings these bots depend on, or None."""
    problems: list[str] = []

    def problem(text):
        if text not in problems:
            problems.append(text)

    for bot in bots:
        for key in (f"{bot.prefix}_TOKEN", f"{bot.prefix}_USERNAME", f"{bot.prefix}_ADMIN_ID"):
            value = setting(bot, key) or ""
            name = "ADMIN_ID" if key.endswith("_ADMIN_ID") and not (
                os.environ.get(key) or bot.dotenv.get(key)) else key
            if PLACEHOLDER.search(value):
                problem(f"{name} still holds an example value from .env.example")
            elif value and (value != value.strip() or value[0] in "\"'"):
                problem(f"{name} has spaces or quotes around it")
        admins = setting(bot, f"{bot.prefix}_ADMIN_ID")
        if admins and not PLACEHOLDER.search(admins) and not all(
                part.strip().isdigit() for part in admins.split(",") if part.strip()):
            problem("ADMIN_ID must be numeric Telegram user ids, comma-separated -- "
                    "not usernames (@userinfobot shows the number)")

    urls = {setting(bot, "DATABASE_URL") for bot in bots}
    if None in urls:
        problem("DATABASE_URL is not set. Nothing runs without it: the Supabase connection "
                "string, from Project Settings -> Database -> Session pooler (port 5432)")
    for dsn in sorted(url for url in urls if url):
        if PLACEHOLDER.search(dsn):
            problem("DATABASE_URL is still the example from .env.example -- <ref>, <password> "
                    "and <region> are meant to be replaced. Paste the real one from Supabase: "
                    "Project Settings -> Database -> Session pooler (port 5432)")
        elif not dsn.startswith(("postgresql://", "postgres://")):
            problem("DATABASE_URL should start with postgresql://")
    if problems:
        return "; ".join(problems) + "."

    for dsn in sorted(url for url in urls if url):
        found = _database_problem(dsn)
        if found:
            return found[0].upper() + found[1:]
    return None

def _libc():
    if sys.platform != "linux":
        return None
    try:
        import ctypes
        return ctypes.CDLL("libc.so.6")
    except OSError:
        return None

_LIBC = _libc()

def cap_malloc_arenas() -> None:
    """glibc gives a threaded process up to 8 x cpu_count malloc arenas, and cpu_count in a container is the host's."""
    if _LIBC is not None and "MALLOC_ARENA_MAX" not in os.environ:
        with contextlib.suppress(Exception):
            _LIBC.mallopt(-8, 2)

def give_back_memory() -> None:
    """Return freed heap pages to the kernel."""
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

_ORIGINAL_RUN_POLLING = None

def _capture_run_polling(self, *args, **kwargs):
    """Each bot's main() ends in app.run_polling(), which would take the event loop for itself and never return."""
    bot = _CURRENT.get()
    if bot is None:
        return _ORIGINAL_RUN_POLLING(self, *args, **kwargs)
    arguments = inspect.signature(_ORIGINAL_RUN_POLLING).bind(self, *args, **kwargs).arguments
    arguments.pop("self", None)
    bot.app, bot.polling = self, dict(arguments)

def load(bot: Bot, wire: bool = True) -> bool:
    """Import the bot and run its main() as far as run_polling."""
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
    except SystemExit as exc:
        bot.state, bot.problem = "skipped", str(exc)
        log.warning("%s is not running: %s", bot.name, exc)
    except Exception as exc:
        bot.state, bot.problem = "failed", f"{type(exc).__name__}: {exc}"
        log.exception("%s could not be loaded", bot.name)
    finally:
        _CURRENT.reset(token)
    forget(bot)
    return False

def one_memory_reporter(bots: list[Bot]) -> None:
    """Every bot records what its process holds, for ManagerBot's /usage and the memory alarm."""
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

    def take_signals(self) -> None:
        loop = self.loop
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.on_signal, sig)
            except (NotImplementedError, RuntimeError, ValueError):

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
                bot.task.cancel()
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
        """Application.stop_running(), as this process understands it."""
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

    async def _initialize(self, bot: Bot) -> None:
        """app.initialize() is where the bot first talks to Telegram and reads its saved state."""
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

    async def teardown(self, bot: Bot) -> None:
        """Everything run_polling does on its way out, in the same order."""
        app = bot.app
        steps = []
        if app.updater is not None and app.updater.running:
            steps.append(app.updater.stop)
        if app.running:
            steps.append(app.stop)
        if bot.initialized:

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

            close = getattr(sys.modules.get(f"{bot.folder}.db"), "close_pool", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(close)

    async def stop_one(self, bot: Bot) -> None:
        await self.teardown(bot)
        bot.state = "stopped"
        if not any(other.state in ("running", "starting") for other in self.bots):
            self.stop_event.set()

    def _take_executor(self) -> None:
        self.loop.set_default_executor(
            ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="worker"))

        def keep_the_shared_one(executor):

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

            await asyncio.wait({starting, stopped}, timeout=STARTUP_REPORT_SECONDS,
                               return_when=asyncio.FIRST_COMPLETED)
            if not stopped.done():

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
    """SIBLING_BOTS -- how the public bots point at each other -- is nothing but their usernames, which are already set once each."""
    if os.environ.get("SIBLING_BOTS"):
        return
    entries = [f"{bot.name.lower()}:{bot.name}:{setting(bot, f'{bot.prefix}_USERNAME')}"
               for bot in bots
               if bot.folder != "manager_bot" and setting(bot, f"{bot.prefix}_USERNAME")]
    if entries:
        os.environ["SIBLING_BOTS"] = ",".join(entries)

def _worker_problem(jobs) -> str | None:
    """One real conversion through the worker process, the way jobs.py starts it."""
    import subprocess
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as work:
        source = Path(work) / "check.png"
        Image.new("RGB", (8, 8), (200, 40, 40)).save(source)
        job = {"in_paths": [str(source)], "src_ext": "png", "target_ext": "jpg", "work_dir": work,
               "stem": "check", "max_pixels": 1_000_000, "max_memory_mb": 0}
        done = subprocess.run([sys.executable, "-u", str(jobs.WORKER), *jobs.WORKER_ARGS, json.dumps(job)],
                              cwd=str(jobs.HERE), capture_output=True, timeout=120)
        outcome = jobs._parse(done.returncode, done.stdout, done.stderr)
        if not outcome.ok:
            return outcome.message or outcome.kind
        return None if outcome.bytes > 0 and Path(outcome.path).is_file() else "no file came out"


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
    leaked = sorted(name for bot in loaded for name in bot.local
                    if getattr(sys.modules.get(name), "__file__", None)
                    and ROOT in Path(sys.modules[name].__file__).resolve().parents)
    expect(f"no bot module loaded under its bare name ({', '.join(leaked)})", not leaked)
    jobs = sys.modules.get("convert_bot.jobs")
    if jobs is not None:
        problem = _worker_problem(jobs)
        expect(f"ConvertBot's worker converts a picture ({problem})", problem is None)
        if problem is None:
            print("  ok    ConvertBot: the conversion worker ran, as", " ".join(jobs.WORKER_ARGS))
    give_back_memory()
    print(f"\n{len(loaded)} bot(s) loaded in {seconds:.1f}s; {footprint()}")
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("All checks passed.")
    return 0

def run_section(key: str, args: list[str]) -> int:
    """`main.py --module KEY ...`: one section as a program of its own, for the
    processes the bots start -- ConvertBot's worker, and the big-file transfer.
    A bot's section runs with that bot's modules and settings, as it would
    inside the bot; a shared one with nothing but itself."""
    if key not in sections():
        raise SystemExit(f"No section {key!r}.")
    sys.argv = [key, *args]
    path = sections()[key][0]
    names = {"__name__": "__main__", "__spec__": None, "__file__": str(path)}
    if "." in key:
        folder, name = key.split(".", 1)
        bot = next((b for b in discover()[0] if b.folder == folder), None)
        if bot is None:
            raise SystemExit(f"No bot {folder!r}.")
        bot.read_own_env_file()
        sys.meta_path.insert(0, _BotFinder)
        register(bot)
        names.update(__builtins__=bot.import_table, __file__=str(bot.directory / f"{name}.py"))
    exec(compiled(key), names)
    return 0


def main(argv: list[str]) -> int:
    global _SHARED_DIR
    if argv[:1] == ["--module"] and len(argv) > 1:
        return run_section(argv[1], argv[2:])
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

    log.info("Bot family %s, one process: %s", version, ", ".join(bot.name for bot in bots))
    tokens: dict[str, Bot] = {}
    wanted = []
    for bot in bots:
        if not bot.token_set():
            bot.state, bot.problem = "skipped", f"no {bot.prefix}_TOKEN"
            log.info("%s skipped: %s is not set.", bot.name, f"{bot.prefix}_TOKEN")
            continue
        token = setting(bot, f"{bot.prefix}_TOKEN")
        if token in tokens:
            bot.state, bot.problem = "skipped", f"same token as {tokens[token].name}"
            log.error("%s skipped: it has the same token as %s, and two pollers on one "
                      "token split its updates between them.", bot.name, tokens[token].name)
            continue
        tokens[token] = bot
        wanted.append(bot)
    if not wanted:
        log.error("Nothing to run: no bot has a token. Set at least one of %s.",
                  ", ".join(f"{bot.prefix}_TOKEN" for bot in bots))
        return 1

    problem = preflight(wanted)
    if problem:
        log.error("Not starting: %s", problem)
        return 1

    family_holder: list[Family] = []
    patch_python_telegram_bot(family_holder)
    runnable = [bot for bot in wanted if load(bot)]
    if not runnable:
        reasons = sorted({bot.problem for bot in wanted if bot.problem})
        log.error("No bot could be loaded: %s", " / ".join(reasons) or "see the errors above")
        return 1
    one_memory_reporter(runnable)

    family = Family(runnable)
    family_holder.append(family)
    return asyncio.run(family.run())

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
