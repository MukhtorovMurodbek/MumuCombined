# Every bot in one container, one process. Builds the same on Railway,
# Render, Fly.io or a plain `docker build`.
FROM python:3.11-slim-bookworm

# StickerBot, ConvertBot and DownloaderBot shell out to ffmpeg.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# DownloaderBot's yt-dlp needs a JavaScript runtime for YouTube. Without one,
# current yt-dlp skips every YouTube client that has to solve the player's
# challenge and asks with the one client left, which is the one a datacenter
# address is told to sign in on. Deno is the runtime yt-dlp looks for by
# default, and its solver scripts come with yt-dlp[default].
COPY --from=denoland/deno:bin-2.9.7 /deno /usr/local/bin/deno

# MALLOC_ARENA_MAX: glibc would otherwise keep up to 8 x (host cores) malloc
# arenas for a threaded process, each holding freed memory it never returns.
# Resident memory is what a usage-billed host charges for.
# LOG_TO_FILES=0: a container's log is its stdout; /logs reads from memory.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MALLOC_ARENA_MAX=2 \
    LOG_TO_FILES=0

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Bytecode is compiled here, once, rather than on every start. Then every bot
# is loaded and checked for isolation, so an image in which a bot cannot even
# be imported never gets as far as a deploy.
RUN python -m compileall -q bot.py bots shared \
 && python bot.py --check \
 && useradd --create-home --uid 10001 bots \
 && chown -R bots /app
USER bots

CMD ["python", "bot.py"]
