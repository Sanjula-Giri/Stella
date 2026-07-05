"""
A minimal in-memory calendar so you can validate the voice pipeline and
booking conversation flow before wiring up real Google Calendar credentials.

Matches the interface `booking/client.py` will expose for the real
Google-backed implementation, so swapping one for the other later is a
one-line change in `agent.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Appointment:
    id: str
    caller_phone: str
    start_time: datetime
    end_time: datetime
    notes: str = ""
    status: str = "booked"  # booked | cancelled | rescheduled


class FakeCalendar:
    """Same shape as the real Google-backed client — swap-in compatible."""

    def __init__(self, slot_minutes: int = 30, business_hours: dict | None = None):
        self.slot_minutes = slot_minutes
        self.business_hours = business_hours or {}
        self._appointments: dict[str, Appointment] = {}
        self._next_id = 1

    def _new_id(self) -> str:
        appt_id = f"appt_{self._next_id}"
        self._next_id += 1
        return appt_id

    def get_available_slots(self, day: datetime, count: int = 3) -> list[datetime]:
        """Return up to `count` open slots on the given day, 9am-5pm placeholder hours."""
        start_of_day = day.replace(hour=9, minute=0, second=0, microsecond=0)
        end_of_day = day.replace(hour=17, minute=0, second=0, microsecond=0)

        booked_starts = {
            a.start_time
            for a in self._appointments.values()
            if a.status == "booked" and a.start_time.date() == day.date()
        }

        slots = []
        cursor = start_of_day
        while cursor + timedelta(minutes=self.slot_minutes) <= end_of_day and len(slots) < count:
            if cursor not in booked_starts:
                slots.append(cursor)
            cursor += timedelta(minutes=self.slot_minutes)
        return slots

    def book(self, caller_phone: str, start_time: datetime, notes: str = "") -> Appointment:
        end_time = start_time + timedelta(minutes=self.slot_minutes)
        appt = Appointment(
            id=self._new_id(),
            caller_phone=caller_phone,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
        )
        self._appointments[appt.id] = appt
        return appt

    def find_by_phone(self, caller_phone: str) -> list[Appointment]:
        return [
            a
            for a in self._appointments.values()
            if a.caller_phone == caller_phone and a.status == "booked"
        ]

    def cancel(self, appointment_id: str) -> bool:
        appt = self._appointments.get(appointment_id)
        if not appt:
            return False
        appt.status = "cancelled"
        return True

    def reschedule(self, appointment_id: str, new_start_time: datetime) -> Appointment | None:
        appt = self._appointments.get(appointment_id)
        if not appt:
            return None
        appt.start_time = new_start_time
        appt.end_time = new_start_time + timedelta(minutes=self.slot_minutes)
        # Stays "booked" (not a separate "rescheduled" status) so it still
        # shows up in find_by_phone for a later reschedule/cancel in the
        # same call.
        appt.status = "booked"
        return appt
