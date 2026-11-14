# Every bot in one container, one process. Builds the same on Railway,
# Render, Fly.io or a plain `docker build`.
FROM python:3.11-slim-bookworm

# StickerBot, ConvertBot and DownloaderBot shell out to ffmpeg; ConvertBot also to bsdtar
# (libarchive's tar: it reads 7z and RAR and writes 7z -- without it those two are
# simply not offered). The four tesseract-ocr-* packages are language DATA for reading
# text from pictures and scanned PDFs (English, Russian, Uzbek in Latin and Cyrillic);
# the engine is inside PyMuPDF, so --no-install-recommends keeps them from pulling in
# the tesseract program, which nothing uses.
# LibreOffice, in its -nogui build (no X11 or GTK), does ConvertBot's PowerPoint, Word and
# Excel files: PPT/PPTX/ODP, DOC/ODT/RTF, XLS/ODS, and a PDF opened as slides (the PDF
# import is in libreoffice-core-nogui). The fonts are what decks and documents are laid out
# in: Carlito and Caladea measure the same as Calibri and Cambria, Liberation as Arial,
# Times New Roman and Courier New, so the text breaks where it did in Office; DejaVu covers
# Cyrillic and Noto CJK Korean, Chinese and Japanese, which would otherwise come out as boxes.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libarchive-tools \
    tesseract-ocr-eng tesseract-ocr-rus tesseract-ocr-uzb tesseract-ocr-uzb-cyrl \
    libreoffice-impress-nogui libreoffice-writer-nogui libreoffice-calc-nogui \
    fonts-crosextra-carlito fonts-crosextra-caladea fonts-liberation2 fonts-dejavu-core fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

# MALLOC_ARENA_MAX keeps glibc from holding freed memory in one arena per
# core; resident memory is what a usage-billed host charges for.
# LOG_TO_FILES=0: a container's log is its stdout; /logs reads from memory.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MALLOC_ARENA_MAX=2 \
    LOG_TO_FILES=0 \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata \
    MUMU_CHECK_OFFICE=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# The runner's bytecode once, here (the sections are compiled as they load).
# Then every bot is loaded, one conversion is run, a test page's text is read and a PDF goes
# through LibreOffice as slides and back, so an image in which a bot cannot load, cannot read
# text or cannot convert an office file never gets as far as a deploy.
RUN python -m compileall -q main.py \
 && python main.py --check \
 && useradd --create-home --uid 10001 bots \
 && mkdir -p data && chown -R bots /app
USER bots

CMD ["python", "main.py"]
