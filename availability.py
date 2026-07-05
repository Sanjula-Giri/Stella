"""
Picks the right calendar backend for a business (fake vs. Google) and
formats slots into caller-friendly speech.
"""
from __future__ import annotations

from datetime import datetime

from config.schema import BusinessConfig, CalendarProvider

from .client import GoogleCalendarClient
from .fake_calendar import FakeCalendar


def build_calendar(cfg: BusinessConfig):
    """Returns a calendar object with get_available_slots/book/find_by_phone/
    cancel/reschedule — either FakeCalendar or GoogleCalendarClient,
    depending on config. Returns None if this vertical doesn't book at all.
    """
    if cfg.calendar.provider == CalendarProvider.NONE:
        return None
    if cfg.calendar.provider == CalendarProvider.FAKE:
        return FakeCalendar(
            slot_minutes=cfg.calendar.appointment_duration_minutes,
            business_hours=cfg.business_hours.model_dump(),
        )
    if cfg.calendar.provider == CalendarProvider.GOOGLE:
        return GoogleCalendarClient(
            calendar_id=cfg.calendar.calendar_id,
            credentials_path=cfg.calendar.credentials_path,
            slot_minutes=cfg.calendar.appointment_duration_minutes,
        )
    raise ValueError(f"Unknown calendar provider: {cfg.calendar.provider}")


def format_slots_for_speech(slots: list[datetime]) -> str:
    """Turn a list of datetimes into something natural to say aloud, e.g.
    'I have 2pm, 2:30pm, or 3pm' rather than reading ISO timestamps."""
    if not slots:
        return "I don't have any openings that day."

    def _fmt(dt: datetime) -> str:
        return dt.strftime("%-I:%M%p").lower().replace(":00", "")

    spoken = [_fmt(s) for s in slots]
    if len(spoken) == 1:
        return f"I have {spoken[0]} available."
    return f"I have {', '.join(spoken[:-1])}, or {spoken[-1]} available."
