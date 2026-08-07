"""Outbound-mail seam (same shape as the llm_client / speech_gateway seams).

SmtpMailer speaks stdlib smtplib with STARTTLS and runs each send in a thread
executor so the SMTP round-trip never blocks the event loop. ConsoleMailer is
the dev/test double: it logs the message and keeps it in memory so tests (and
the SAUTI_FAKE_AI-only /__test__/last-mail endpoint) can read the link back.

Selection lives in main.create_app: SAUTI_FAKE_AI=1 or missing SMTP creds
means ConsoleMailer; otherwise SmtpMailer with the settings' credentials.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Protocol

log = logging.getLogger("sauti.mail")


@dataclass
class SentMail:
    to: str
    subject: str
    text: str
    html: str | None = None


class Mailer(Protocol):
    async def send(
        self, to: str, subject: str, text: str, html: str | None = None
    ) -> None: ...


class ConsoleMailer:
    """Dev/test mailer: logs the message and captures it for assertions."""

    def __init__(self) -> None:
        self.sent: list[SentMail] = []

    async def send(
        self, to: str, subject: str, text: str, html: str | None = None
    ) -> None:
        self.sent.append(SentMail(to=to, subject=subject, text=text, html=html))
        log.info("ConsoleMailer captured mail to=%s subject=%r\n%s", to, subject, text)

    def last_for(self, to: str) -> SentMail | None:
        for mail in reversed(self.sent):
            if mail.to == to:
                return mail
        return None


class SmtpMailer:
    """Real SMTP (STARTTLS + auth). Sends run via asyncio.to_thread."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        mail_from: str,
        starttls: bool = True,
        timeout: float = 20.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mail_from = mail_from
        self.starttls = starttls
        self.timeout = timeout

    def _send_sync(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
            smtp.ehlo()
            if self.starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if self.username:
                smtp.login(self.username, self.password)
            refused = smtp.send_message(msg)
            if refused:  # partial refusal: send_message only raises when ALL fail
                raise smtplib.SMTPRecipientsRefused(refused)

    async def send(
        self, to: str, subject: str, text: str, html: str | None = None
    ) -> None:
        msg = EmailMessage()
        msg["From"] = self.mail_from
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
        await asyncio.to_thread(self._send_sync, msg)
        log.info("SMTP accepted mail to=%s subject=%r", to, subject)


async def send_mail_safely(
    mailer: Mailer, *, to: str, subject: str, text: str, html: str | None = None
) -> None:
    """Background-task wrapper: a mail failure must never fail the request
    that queued it (registration already returned 201, forgot-password must
    stay a uniform 200)."""
    try:
        await mailer.send(to, subject, text, html)
    except Exception:
        log.exception("Failed to send mail to=%s subject=%r", to, subject)
