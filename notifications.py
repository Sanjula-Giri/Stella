"""
Pluggable message channels. `file` works out of the box (zero setup) so the
prototype is fully testable without any external service. `email` and
`webhook` are stubbed with a clear TODO — plug in your own SMTP/Resend/
webhook target rather than us guessing your provider.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from config.schema import BusinessConfig, MessageChannel


def _write_file_notification(cfg: BusinessConfig, payload: dict) -> None:
    directory = os.path.join("data", "notifications", cfg.slug)
    os.makedirs(directory, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    path = os.path.join(directory, f"{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _send_email_notification(cfg: BusinessConfig, payload: dict) -> None:
    # TODO: wire up SMTP or Resend here using cfg.notifications.email_to /
    # cfg.notifications.smtp_password. Left stubbed since it needs a real
    # provider + credentials.
    print(f"[stub] would email {cfg.notifications.email_to}: {payload}")


def _send_webhook_notification(cfg: BusinessConfig, payload: dict) -> None:
    # TODO: POST `payload` to cfg.notifications.webhook_url with
    # Authorization: Bearer {cfg.notifications.webhook_token}
    print(f"[stub] would POST to {cfg.notifications.webhook_url}: {payload}")


def notify(cfg: BusinessConfig, kind: str, payload: dict) -> None:
    """kind: 'message' | 'booking' | 'intake' | 'reschedule' | 'cancel'"""
    full_payload = {"kind": kind, "business": cfg.slug, **payload}

    for channel in cfg.notifications.channels:
        if channel == MessageChannel.FILE:
            _write_file_notification(cfg, full_payload)
        elif channel == MessageChannel.EMAIL:
            _send_email_notification(cfg, full_payload)
        elif channel == MessageChannel.WEBHOOK:
            _send_webhook_notification(cfg, full_payload)
