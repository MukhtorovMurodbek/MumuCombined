"""Structured data: CSV, TSV, JSON, YAML, XLSX and XML -- and the plain-text
form of a subtitle file, which has nowhere better to live.

This is the corner of the bot that no general-purpose converter bothers with,
and it is cheap: everything here is the standard library plus `openpyxl`,
`PyYAML` and `defusedxml`, all pure wheels. Somebody who has a CSV and needs
a spreadsheet, or a JSON export and needs a table they can read, currently
opens a website and pastes their data into it. They should not have to.

## One intermediate, two shapes

Every format here is read into an ordinary Python object -- lists, dicts,
strings, numbers -- and written out of one. That is enough for the pairs
where both sides are nested (JSON, YAML, XML).

The other five formats are *tables* and cannot hold a nested object, so
`as_table()` is the narrow place where a nested thing either flattens or is
refused with a sentence saying why. Silently writing `[object Object]` into a
cell, which is what most converters do, is worse than not converting.

## XML is parsed with defusedxml and nothing else

The standard library's XML parsers will expand entities, which makes a
fourteen-line file into gigabytes of memory ("billion laughs") and can be
pointed at a local file or a URL ("XXE"). Neither is theoretical and both
arrive as an ordinary-looking upload from a stranger. `defusedxml` refuses
all of it, and `formats.py` does not offer XML at all when it is missing.
"""
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


# What convert() below can write -- see doc_convert.WRITES.
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


# ---------- reading ----------

def _read_delimited(in_path, src_ext: str) -> Table:
    text = _read_text(in_path)
    reader = csv.reader(io.StringIO(text), delimiter=_DELIMITERS[src_ext])
    rows = [row for row in reader]
    if not rows:
        raise ConversionError("That file is empty.")
    headers = [str(cell) for cell in rows[0]]
    _check_size(len(rows) - 1, len(headers))
    return Table(headers, rows[1:])


def _read_xlsx(in_path) -> list[tuple[str, Table]]:
    """Every sheet in the workbook, named.

    All of them rather than the first: a workbook with three sheets converted
    to "a CSV" would silently be a third of the answer, and which third would
    depend on which tab happened to be open when it was saved.
    """
    try:
        import openpyxl
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError("Spreadsheets aren't supported on this host.") from exc
    try:
        # read_only streams the sheet rather than building the whole object
        # model; data_only hands back what a formula evaluated to last time it
        # was calculated, which is the number the user can see in the cell.
        book = openpyxl.load_workbook(in_path, read_only=True, data_only=True)
    except Exception as exc:
        raise ConversionError(f"Couldn't read that spreadsheet: {exc}") from exc
    sheets = []
    try:
        for sheet in book.worksheets:
            rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            rows = [row for row in rows if any(cell is not None for cell in row)]
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


def _read_yaml(in_path):
    try:
        import yaml
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError("YAML isn't supported on this host.") from exc
    try:
        # safe_load and never load(): the full loader constructs arbitrary
        # Python objects named in the document, which from a stranger's file
        # is remote code execution.
        return yaml.safe_load(_read_text(in_path))
    except Exception as exc:
        raise ConversionError(f"That isn't valid YAML: {exc}") from exc


def _element_to_object(element):
    """An XML element as dicts and lists, attributes prefixed with `@`.

    The same shape `xmltodict` produces, which is the one most people expect
    when they ask for XML as JSON: repeated children become a list, an
    element with only text becomes that text.
    """
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
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError("XML isn't supported on this host.") from exc
    try:
        root = parse(str(in_path)).getroot()
    except Exception as exc:
        raise ConversionError(f"That isn't XML this can read: {exc}") from exc
    return {root.tag: _element_to_object(root)}


# ---------- the two shapes ----------

def _load(in_path, src_ext: str):
    """(object, sheets) -- one of the two is always None.

    A spreadsheet is the only source that can be several tables at once, and
    keeping that in the return type is what stops the rest of this file from
    having to know about worksheets.
    """
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
    """A nested object as one table, or a refusal that says why not.

    Three shapes flatten honestly and the rest do not:

      a list of objects   the ordinary shape of an export -- one row each,
                          columns being the union of the keys, in the order
                          they were first seen.
      a list of lists     already a table; the columns get numbers.
      an object           two columns, key and value.

    Anything else -- a bare number, a list of lists of objects -- has no
    table in it, and saying so is more useful than inventing one.
    """
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
        # A single object with one list of objects inside it is what almost
        # every API export looks like: {"items": [...]}. Use the list.
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


# ---------- writing ----------

def _write_delimited(table: Table, out_path, target_ext: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=_DELIMITERS[target_ext])
        writer.writerow(table.headers)
        writer.writerows(table.rows)


def _write_xlsx(sheets: list[tuple[str, Table]], out_path) -> None:
    try:
        import openpyxl
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError("Spreadsheets aren't supported on this host.") from exc
    book = openpyxl.Workbook()
    book.remove(book.active)
    for index, (name, table) in enumerate(sheets):
        # Excel's own rules, and it rejects the file rather than the sheet
        # name: 31 characters, and none of : \ / ? * [ ].
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
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError("YAML isn't supported on this host.") from exc
    with open(out_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(obj, handle, allow_unicode=True, sort_keys=False, default_flow_style=False)


# ---------- the dispatcher ----------

def convert(in_path, src_ext: str, target_ext: str, work_dir, stem: str = "converted") -> Result:
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
        # A workbook is several tables and a CSV is one. Every sheet, named,
        # in a zip -- rather than picking one and not saying which.
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


# ---------- subtitles, as plain text ----------
# ffmpeg converts between the subtitle formats themselves; this is the one
# subtitle target it has no encoder for, because "the words with none of the
# timings" is not a subtitle format. It is, however, the thing people most
# often want out of a subtitle file: a transcript.

_TAG_RE = re.compile(r"<[^>]+>|\{[^}]*\}")           # <i>, {\an8}
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
                # ASS puts hard line breaks in the text itself.
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
