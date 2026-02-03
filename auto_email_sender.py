#!/usr/bin/env python3
"""Auto email sender.

Sends email via SMTP using environment variables for credentials.
Supports optional scheduling via a fixed interval loop.
"""

from __future__ import annotations

import argparse
import email.utils
import logging
import mimetypes
import os
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


LOG = logging.getLogger(__name__)


def _split_addresses(value: str | None) -> list[str]:
    if not value:
        return []
    return [addr.strip() for addr in value.split(",") if addr.strip()]


def _add_attachments(message: EmailMessage, attachments: Iterable[Path]) -> None:
    for attachment in attachments:
        if not attachment.exists():
            raise FileNotFoundError(f"Attachment not found: {attachment}")
        mime_type, encoding = mimetypes.guess_type(attachment)
        if mime_type is None or encoding is not None:
            mime_type = "application/octet-stream"
        maintype, subtype = mime_type.split("/", 1)
        with attachment.open("rb") as handle:
            message.add_attachment(
                handle.read(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment.name,
            )


def build_message(
    *,
    sender: str,
    to_addrs: list[str],
    cc_addrs: list[str],
    bcc_addrs: list[str],
    subject: str,
    body: str,
    html_body: str | None,
    attachments: Iterable[Path],
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(to_addrs)
    if cc_addrs:
        message["Cc"] = ", ".join(cc_addrs)
    message["Subject"] = subject
    message["Date"] = email.utils.formatdate(localtime=True)

    if html_body:
        message.set_content(body)
        message.add_alternative(html_body, subtype="html")
    else:
        message.set_content(body)

    _add_attachments(message, attachments)
    return message


def send_email(
    message: EmailMessage,
    *,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    use_tls: bool,
) -> None:
    context = ssl.create_default_context()
    if use_tls:
        LOG.debug("Connecting with STARTTLS to %s:%s", smtp_host, smtp_port)
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(username, password)
            server.send_message(message)
    else:
        LOG.debug("Connecting with SSL to %s:%s", smtp_host, smtp_port)
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(username, password)
            server.send_message(message)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send automated emails via SMTP.")
    parser.add_argument("--to", required=True, help="Comma-separated recipient emails")
    parser.add_argument("--cc", default="", help="Comma-separated CC emails")
    parser.add_argument("--bcc", default="", help="Comma-separated BCC emails")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument(
        "--body",
        required=True,
        help="Plain text body or @/path/to/file.txt to read content",
    )
    parser.add_argument(
        "--html",
        default=None,
        help="HTML body string or @/path/to/file.html",
    )
    parser.add_argument(
        "--attachment",
        action="append",
        default=[],
        help="Attachment path (can be repeated)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help="If set, send on a fixed interval in seconds",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of emails to send (default 1). Use 0 for infinite.",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args(argv)


def _load_content(value: str) -> str:
    if value.startswith("@"):
        path = Path(value[1:]).expanduser()
        return path.read_text(encoding="utf-8")
    return value


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(levelname)s %(message)s")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_SENDER") or smtp_user
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}

    missing = [
        name
        for name, value in {
            "SMTP_HOST": smtp_host,
            "SMTP_USERNAME": smtp_user,
            "SMTP_PASSWORD": smtp_password,
        }.items()
        if not value
    ]
    if missing:
        LOG.error("Missing environment variables: %s", ", ".join(missing))
        return 1

    if not sender:
        LOG.error("SMTP_SENDER is required when SMTP_USERNAME is empty")
        return 1

    to_addrs = _split_addresses(args.to)
    cc_addrs = _split_addresses(args.cc)
    bcc_addrs = _split_addresses(args.bcc)

    if not to_addrs:
        LOG.error("At least one recipient is required")
        return 1

    body = _load_content(args.body)
    html_body = _load_content(args.html) if args.html else None
    attachments = [Path(path).expanduser() for path in args.attachment]

    total = args.count
    interval = args.interval_seconds
    iteration = 0

    while total == 0 or iteration < total:
        iteration += 1
        LOG.info("Sending email %s", iteration)
        message = build_message(
            sender=sender,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            bcc_addrs=bcc_addrs,
            subject=args.subject,
            body=body,
            html_body=html_body,
            attachments=attachments,
        )
        all_recipients = to_addrs + cc_addrs + bcc_addrs
        message["To"] = ", ".join(to_addrs)
        if cc_addrs:
            message["Cc"] = ", ".join(cc_addrs)
        if bcc_addrs:
            message["Bcc"] = ", ".join(bcc_addrs)

        send_email(
            message,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            use_tls=use_tls,
        )
        LOG.info("Email sent to %s", ", ".join(all_recipients))

        if interval <= 0:
            break
        if total == 0 or iteration < total:
            LOG.info("Sleeping for %s seconds", interval)
            time.sleep(interval)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
