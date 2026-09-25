"""One conversion, in a process of its own.

ConvertBot used to run convert() on a thread inside the bot's own process.
Three things go wrong with that, and a 200-megapixel photo found all of them
at once:

  it cannot be stopped. Python has no way to kill a thread, so a time limit on
  a threaded conversion only stops *waiting* for it -- the work goes on,
  holding a core and a gigabyte, after everybody has given up on it;
  it does not give memory back. Decoding a photo that size takes the process
  past a gigabyte, and CPython's allocator returns little of that to the
  operating system afterwards, so the bot idles fat until it is restarted --
  on a host that bills resident memory by the second;
  it is not isolated. A crash in a C decoder, or the kernel's OOM killer
  choosing a victim, takes the whole bot down with everybody's pending work.

A child process fixes all three for the price of starting one. jobs.py gives
it a deadline and kills it when the deadline passes; the operating system
takes the memory back the moment it exits; and if it dies, it dies alone.

The protocol is deliberately plain. The job arrives as one JSON argument and
the outcome leaves as one JSON line -- the last non-empty line on stdout.
Anything a library prints along the way is ignored.

    {"ok": true,  "path": "...", "zipped": false, "items": 1, "bytes": 123}
    {"ok": false, "kind": "refused", "message": "..."}   a ConversionError
    {"ok": false, "kind": "crash",   "message": "..."}   anything else

"refused" means the file could not be converted and saying so is the bot
working; "crash" means the bot failed. jobs.py refunds both and tells the
owner only about the second.
"""
import json
import os
import sys
import traceback
import warnings


def _emit(ok: bool, **fields) -> None:
    fields["ok"] = ok
    sys.stdout.write("\n" + json.dumps(fields) + "\n")
    sys.stdout.flush()


def _cap_memory(max_memory_mb: int) -> None:
    """Give the worker a MemoryError instead of letting the kernel pick a
    victim. POSIX only, and only when asked: the OOM killer on a container
    chooses the largest process, which is normally this one, but "normally"
    is not the guarantee a shared container deserves."""
    if not max_memory_mb or os.name != "posix":
        return
    try:
        import resource
        limit = int(max_memory_mb) * 1024 * 1024
        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
    except Exception:
        pass


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
    # The size policy is decided by the parent, before anything is charged.
    # A DecompressionBombWarning here would only be noise on stderr.
    warnings.simplefilter("ignore")

    try:
        import convert_utils
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(False, kind="crash", message=f"could not load the converters: {exc}")
        return 1

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
        )
    except convert_utils.ConversionError as exc:
        _emit(False, kind="refused", message=str(exc))
        return 2
    except MemoryError:
        _emit(False, kind="crash", message="the conversion ran out of memory")
        return 1
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
