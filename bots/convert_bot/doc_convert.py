"""Documents: PDF, EPUB, MOBI, FB2, CBZ, XPS, DOCX, Markdown, HTML, plain
text -- and SVG, which is a document in every way that matters here.

Three libraries, all optional, all imported inside the functions that need
them so that a host without one still starts and simply does not offer those
formats (`formats.probe()` is what notices):

  PyMuPDF   opens all of the above except DOCX and Markdown, renders pages to
            pictures, extracts their text, and writes a PDF from HTML.
  mammoth   turns a .docx into semantic HTML -- headings, lists, bold, tables
            -- which PyMuPDF then lays out.
  markdown  the same trick for Markdown.
  docx      python-docx, which writes the .docx that _to_docx below builds.

## What "docx to PDF" means here, and what it does not

There is no LibreOffice in this image, so a .docx is not rendered the way
Word would render it: page breaks, columns, headers and footers, and exact
kerning are not preserved. What is preserved is the document -- its
headings, its emphasis, its lists and its tables -- reflowed onto A4. That
is the honest description and it is what the caption says, because a user who
expects a pixel-identical page and gets a reflowed one has been misled even
though the conversion "worked".

Adding LibreOffice would fix that and cost about a gigabyte of image and a
much slower cold start on every deploy, for one format pair. It is written up
in `CHANGES_v1.5.0.md` under *Not done yet* rather than done quietly.
"""
from __future__ import annotations

import html as html_module
import io
from pathlib import Path

import formats
from convert_utils import Result, ConversionError, PAGE_DPI, convert_image, zip_files

# Formats PyMuPDF opens directly, by extension. Everything else here has to
# be turned into HTML or into a PDF first.
_MUPDF_NATIVE = ("pdf", "epub", "mobi", "fb2", "cbz", "xps", "svg", "html", "txt")

# What convert() below can write. Declared rather than inferred so that
# tests/test_conversions.py can check the whole matrix in formats.py against
# the three backends that have to implement it -- a target advertised with no
# branch to produce it is otherwise only found by a user picking it.
WRITES = frozenset({"pdf", "png", "jpg", "webp", "tiff", "svg", "txt", "html", "md", "docx"})

# The page a reflowed document is laid out on. A4 rather than US Letter: the
# bot's users are not in the United States.
_PAGE = "a4"
_MARGIN = 40


def _fitz():
    try:
        import pymupdf
        return pymupdf
    except ImportError as exc:      # pragma: no cover - formats.py gates this
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
    # docx and md have to become a PDF before there are pages to look at.
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


# ---------- getting to HTML ----------

def _docx_to_html(in_path) -> str:
    try:
        import mammoth
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError("Word documents aren't supported on this host.") from exc
    try:
        with open(in_path, "rb") as handle:
            return mammoth.convert_to_html(handle).value
    except Exception as exc:
        raise ConversionError(f"Couldn't read that .docx: {exc}") from exc


def _md_to_html(in_path) -> str:
    try:
        import markdown
    except ImportError as exc:      # pragma: no cover - formats.py gates this
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
    # A page of a PDF or an e-book already has a layout; MuPDF's own HTML is
    # the closest thing to it that a browser can open.
    doc = _open(in_path, src_ext)
    try:
        pages = _page_count(doc)
        return "\n".join(doc[index].get_text("html") for index in range(pages))
    finally:
        doc.close()


# ---------- HTML to a laid-out PDF ----------

def html_to_pdf(source_html: str, out_path) -> None:
    """Lay HTML out onto pages and write a PDF.

    `Story` is MuPDF's own flow layout: it is given a rectangle at a time and
    says whether it has more to place, which is exactly the loop below. It
    understands the subset of HTML and CSS that documents are actually made
    of -- headings, paragraphs, emphasis, lists, tables, images -- and
    ignores the rest rather than failing on it.
    """
    pymupdf = _fitz()
    try:
        story = pymupdf.Story(html=f"<html><body>{source_html}</body></html>")
        page_rect = pymupdf.paper_rect(_PAGE)
        frame = page_rect + (_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)
        # DocumentWriter takes a path or a file object; _to_pdf_bytes hands it
        # a buffer, because a docx on its way to being rendered as pictures
        # never needs to exist on disk as a PDF.
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
    """A PDF of the source, in memory. Only used as a stepping stone -- when
    the PDF is the answer, `_to_pdf` writes it straight to disk instead."""
    _fitz()          # a clear refusal now rather than an ImportError later
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


# ---------- pages as pictures ----------

def _render_pages(in_path, src_ext: str, target_ext: str, work_dir, stem: str) -> list[Path]:
    """One picture per page, at PAGE_DPI.

    PNG comes straight out of MuPDF; everything else is that PNG handed to
    Pillow, because there is no second encoder here worth having and the
    intermediate is one file on disk rather than a second decode of the
    document.
    """
    doc = _open(in_path, src_ext)
    produced: list[Path] = []
    try:
        pages = _page_count(doc)
        for index in range(pages):
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
    """A PDF page as SVG keeps its vectors, which is the whole reason to ask
    for one rather than a PNG."""
    doc = _open(in_path, src_ext)
    produced: list[Path] = []
    try:
        for index in range(_page_count(doc)):
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


# ---------- text ----------

def _to_text(in_path, src_ext: str) -> str:
    if src_ext == "docx":
        try:
            import mammoth
            with open(in_path, "rb") as handle:
                return mammoth.extract_raw_text(handle).value
        except ImportError as exc:  # pragma: no cover - formats.py gates this
            raise ConversionError("Word documents aren't supported on this host.") from exc
        except Exception as exc:
            raise ConversionError(f"Couldn't read that .docx: {exc}") from exc
    if src_ext == "md":
        # The Markdown *source* is already text, so the useful answer is the
        # text it renders to -- headings without their hashes, links without
        # their brackets.
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


# ---------- the dispatcher ----------

# ---------------------------------------------------------------------------
# ...and back out to Word
# ---------------------------------------------------------------------------
# The owner: "Is it possible to add conversion from pdf to word? at least the
# bare minimum with text and some images, idk."
#
# It is, and "the bare minimum" is the honest ceiling rather than a first
# step towards something better. A PDF is a description of marks on a page:
# glyphs at coordinates, with no paragraphs, no headings, no lists and no
# tables in it. Anything that hands you a Word document with those things in
# has *inferred* them, and every library that does it well -- pdf2docx and
# the commercial engines -- carries a computer-vision stack to do the
# inferring. pdf2docx alone pulls in OpenCV and NumPy, which is most of a
# hundred megabytes of image for one format pair.
#
# So this does the part that is not guesswork: PyMuPDF already groups glyphs
# into lines and blocks and reports each span's font, size and weight, and
# that is enough to write real paragraphs, bold where the PDF says bold, and
# a heading where a line is markedly larger than the page's body text. The
# pictures come out as pictures, in the order they appear. What does not
# survive is the page layout itself: columns become sequential paragraphs,
# tables become their text, headers and footers become paragraphs like any
# other, and the page breaks are the PDF's rather than Word's.
#
# The caption says all of that, because a Word document that looks nothing
# like the PDF is a bad surprise and a Word document described as a reflow is
# exactly what was asked for.

# A line whose text is this much larger than the document's usual size is
# treated as a heading. 1.25 is deliberately shy: over-calling headings in a
# long document is worse than under-calling them, because Word's navigation
# pane then fills with sentences.
_HEADING_RATIO = 1.25
_HEADING_2_RATIO = 1.6
# Images smaller than this are page furniture -- rules, bullets, logos in a
# footer -- and putting them in costs more than it gives.
_MIN_IMAGE_PIXELS = 64 * 64
_DOCX_PAGE_WIDTH_INCHES = 6.0


def _docx():
    try:
        import docx
        return docx
    except ImportError as exc:      # pragma: no cover - formats.py gates this
        raise ConversionError(
            "The Word writer isn't installed on this host, so converting to "
            "DOCX isn't available."
        ) from exc


def _body_size(doc) -> float:
    """The size most of this document's text is set in, which is what makes
    'larger than the body' a question with an answer. The mode rather than
    the mean: an average is dragged up by one big title on a short document,
    and then nothing is a heading."""
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
    """Everything the PDF actually says, as a Word document. See above for
    what that does and does not include."""
    docx = _docx()
    pymupdf = _fitz()
    document = docx.Document()
    with _open(in_path, src_ext) as doc:
        _page_count(doc)
        body_size = _body_size(doc)
        wrote_anything = False
        for index, page in enumerate(doc):
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
                    # Bit 4 of PyMuPDF's span flags is the bold bit.
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
    """The pictures on one page, in the order the page lists them.

    Extracted rather than re-rendered, so a photograph comes out as the
    photograph rather than as a screenshot of it. Anything the writer refuses
    -- an exotic colour space, a mask, a CMYK JPEG -- is skipped rather than
    failing the conversion: a Word document missing one decoration is worth
    having and an exception instead of a document is not.
    """
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
            if width * height < _MIN_IMAGE_PIXELS:
                continue
            # Through Pillow, because python-docx only takes the handful of
            # formats Word understands and a PDF can hold any of a dozen.
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
        except ImportError as exc:  # pragma: no cover - formats.py gates this
            raise ConversionError("Word documents aren't supported on this host.") from exc
        except Exception as exc:
            raise ConversionError(f"Couldn't read that .docx: {exc}") from exc
        return Result(out_path)

    raise ConversionError(f"Nothing here converts a .{src_ext} to .{target_ext}.")
