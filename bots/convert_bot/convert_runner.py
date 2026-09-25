"""The Telegram side of a conversion job.

jobs.py decides what happens -- when credit is taken, when it goes back, who
is told. This file is how it is said: the status message a person watches,
the file they receive, the sentence that explains a failure, and the message
the owner gets when the bot is at fault.

Kept out of bot.py for two reasons. bot.py is already the file every handler
lives in, and this is not a handler: it runs in a background task long after
the button that started it was answered. And it takes its dependencies in
its constructor -- the application, the admin ids, the caption builder --
so nothing here imports bot.py and nothing can go round in a circle.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import family_link
import i18n
import jobs
import lifecycle
import live_message
import problems
from live_message import edit_in_place
from shared_features import emit_event, note_job, report_markup

logger = logging.getLogger(__name__)

BOT_LABEL = os.environ.get("FAMILY_LABEL") or "ConvertBot"


def _upper(ext: str) -> str:
    return (ext or "?").upper()


def result_filename(path) -> str:
    """What the converted file is called when it arrives.

    Every result used to be `converted.pdf`. Convert three documents and a
    phone downloads `converted.pdf`, `converted (1).pdf`, `converted (2).pdf`
    -- or, on a client that overwrites rather than numbering, one file three
    times. The owner: "The converted result file's name should be unique,
    maybe by naming it with date and time of conversion might help."

    So it carries the moment it was made, to the second, in an order that
    sorts: `converted_2026-09-13_235812.pdf`. UTC, because the container has
    no idea what time it is where the person reading the name is, and a name
    that claims a local time it guessed is worse than one that does not
    claim one.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"converted_{stamp}{Path(path).suffix}"


class ConvertRunner(jobs.Runner):
    def __init__(self, application, admin_ids, upload_dir, caption_for):
        self.application = application
        self.admin_ids = sorted(admin_ids or ())
        self.upload_dir = Path(upload_dir)
        self.caption_for = caption_for

    @property
    def bot(self):
        return self.application.bot

    def work_dir(self):
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        return self.upload_dir

    # ---- the status message --------------------------------------------

    def stop_keyboard(self, job: jobs.Job) -> InlineKeyboardMarkup:
        key = "job_stop_button" if job.state == "running" else "job_stop_button_queued"
        return InlineKeyboardMarkup([[InlineKeyboardButton(
            i18n.t(job.lang, key), callback_data=f"convstop:{job.id}")]])

    async def _status(self, job: jobs.Job, text: str, markup=None) -> None:
        message = job.extra.get("status_message")
        try:
            if message is not None:
                await edit_in_place(message, self.bot, text, reply_markup=markup)
                return
            job.extra["status_message"] = await self.bot.send_message(
                chat_id=job.chat_id, text=text, reply_markup=markup)
        except Exception:
            logger.debug("Could not update the status of conversion %s", job.id, exc_info=True)

    # ---- the policy's hooks --------------------------------------------

    async def refuse_start(self, job: jobs.Job) -> bool:
        return lifecycle.is_paused()

    async def charge(self, job: jobs.Job) -> int | None:
        if job.price <= 0:
            return await asyncio.to_thread(family_link.star_balance, job.user_id)
        return await asyncio.to_thread(
            family_link.spend_stars, job.user_id, job.price, "spend",
            f"{job.src_ext}->{job.target_ext} conversion, {job.size / 1024:.0f} KB")

    async def started(self, job: jobs.Job, balance: int) -> None:
        if job.price:
            text = i18n.t(job.lang, "job_started", src=_upper(job.src_ext),
                          target=_upper(job.target_ext), price=job.price, balance=balance)
        else:
            text = i18n.t(job.lang, "job_started_free", src=_upper(job.src_ext),
                          target=_upper(job.target_ext))
        await self._status(job, text, self.stop_keyboard(job))

    async def progress(self, job: jobs.Job, stage: int, stages: int, elapsed_s: float,
                       next_s, limit_s: int) -> None:
        """A new message, not an edit: an edit arrives silently, and the point
        is that somebody who has waited two minutes hears about it. Sent under
        the status line, which is then moved below it for the ending."""
        def minutes(seconds: float) -> int:
            return max(1, round(seconds / 60))

        if next_s is not None:
            text = i18n.t(job.lang, "job_progress", elapsed=minutes(elapsed_s),
                          next=minutes(next_s - elapsed_s), last=minutes(limit_s - elapsed_s))
        else:
            text = i18n.t(job.lang, "job_progress_last", elapsed=minutes(elapsed_s),
                          last=minutes(limit_s - elapsed_s))
        status = job.extra.get("status_message")
        try:
            sent = await self.bot.send_message(
                chat_id=job.chat_id, text=text,
                reply_to_message_id=getattr(status, "message_id", None),
                allow_sending_without_reply=True)
            live_message.bump(sent.chat_id, sent.message_id)
        except Exception:
            logger.debug("Could not send a progress update for conversion %s", job.id, exc_info=True)

    async def deliver(self, job: jobs.Job, outcome: jobs.Outcome) -> None:
        caption = self.caption_for(job.lang, outcome, job.src_ext, job.target_ext, job.price)
        if job.price:
            balance = await asyncio.to_thread(family_link.star_balance, job.user_id)
            caption += "\n\n" + i18n.t(job.lang, "balance_left_line", balance=balance)
        # Streamed from disk rather than read into memory: the result of a
        # large conversion should never have to exist in the bot's process.
        with open(outcome.path, "rb") as handle:
            await self.bot.send_document(
                chat_id=job.chat_id, document=handle, filename=result_filename(outcome.path),
                caption=caption, read_timeout=300, write_timeout=300)

    async def succeeded(self, job: jobs.Job, outcome: jobs.Outcome) -> None:
        note_job(True)
        await self._status(job, i18n.t(job.lang, "job_done", src=_upper(job.src_ext),
                                       target=_upper(job.target_ext)))

    async def refund(self, job: jobs.Job, kind: str) -> int:
        return await asyncio.to_thread(
            family_link.move_stars, job.user_id, job.price, "refund",
            f"{job.src_ext}->{job.target_ext} conversion ended: {kind}")

    async def failed(self, job: jobs.Job, kind: str, detail: str, refunded_to) -> None:
        lang = job.lang
        if kind == jobs.USER_CANCELLED:
            if job.started_at is None:
                text = i18n.t(lang, "job_removed_from_queue")
            elif job.price and job.charged:
                text = i18n.t(lang, "job_user_stopped", price=job.price)
            else:
                text = i18n.t(lang, "job_user_stopped_free")
            await self._status(job, text)
            return
        if kind == jobs.PAUSED:
            await self._status(job, i18n.t(lang, "update_soon_try_later_soon"))
            return
        if kind == jobs.NO_CREDIT:
            balance = await asyncio.to_thread(family_link.star_balance, job.user_id)
            await self._status(job, i18n.t(lang, "job_no_credit", price=job.price, balance=balance))
            return

        if kind in (jobs.TIMEOUT, jobs.CRASH, jobs.SEND_FAILED):
            note_job(False)
        limit = jobs.TIME_LIMIT_S if job.price else jobs.FREE_TIME_LIMIT_S
        reasons = {
            jobs.REFUSED: ("job_reason_refused", {"detail": detail}),
            jobs.TIMEOUT: ("job_reason_timeout", {"minutes": max(1, round(limit / 60))}),
            jobs.CRASH: ("job_reason_crash", {}),
            jobs.TOO_LARGE: ("job_reason_too_large", {"target": _upper(job.target_ext),
                                                      "mb": detail.split()[0] if detail else "?",
                                                      "limit": jobs.SEND_LIMIT_MB}),
            jobs.SEND_FAILED: ("job_reason_send_failed", {}),
            jobs.INTERRUPTED: ("job_reason_interrupted", {}),
        }
        key, fields = reasons.get(kind, ("job_reason_crash", {}))
        text = i18n.t(lang, key, **fields)
        if refunded_to is not None:
            text += "\n\n" + i18n.t(lang, "job_refunded_line", price=job.price, balance=refunded_to)
        # The code, and an incident the owner's alert and this log line carry
        # too, so a report from this person meets both.
        code = problems.JOB_ENDINGS.get(kind, "CV-CRASH")
        incident = job.extra.setdefault("incident", problems.new_incident())
        logger.info("Conversion %s ended %s (%s, incident %s): %s", job.id, kind, code, incident, detail)
        await self._status(job, text + problems.code_line(code), report_markup(lang, code, incident))

    async def alert(self, job: jobs.Job, kind: str, detail: str, elapsed: float, refunded_to) -> None:
        """Straight to the owner, from this bot, in English.

        Sent directly rather than only through family.events, because the
        family log is read by ManagerBot from the shared database and a
        TestBot on a laptop writes to a local one -- so an event alone would
        reach nobody from exactly the place the owner tests. It is still
        recorded as an info event, which ManagerBot does not forward, so in
        production the owner gets one message rather than two; if no admin
        can be reached directly it is raised as a warning instead, which
        ManagerBot does forward.
        """
        limit = jobs.TIME_LIMIT_S if job.price else jobs.FREE_TIME_LIMIT_S
        # What failed and what it cost to run -- never who it happened to.
        # The owner does not want user details in anything sent to them: no
        # id, no username, and no person's balance.
        credit = (f"{job.price} ⚡ back to the balance" if refunded_to is not None
                  else ("free conversion, nothing to refund" if not job.price else "not refunded"))
        text = (f"⚠️ {BOT_LABEL}: a conversion failed ({kind})\n"
                f"File: {job.size / 1024 / 1024:.1f} MB {_upper(job.src_ext)} → {_upper(job.target_ext)}\n"
                f"Ran: {elapsed:.0f}s of a {limit}s limit\n"
                f"Detail: {detail or '-'}\n"
                f"Code: {problems.JOB_ENDINGS.get(kind, 'CV-CRASH')} · incident {job.extra.get('incident', '-')}\n"
                f"Credit: {credit}")
        delivered = 0
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(chat_id=admin_id, text=text)
                delivered += 1
            except Exception:
                logger.debug("Could not alert admin %s", admin_id, exc_info=True)
        emit_event("info" if delivered else "warning", "conversion", text)
