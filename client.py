"""
Real Google Calendar client. OAuth/service-account wiring is left as a TODO
since it needs your own credentials — the method signatures match
`fake_calendar.FakeCalendar` so `agent.py` can use either interchangeably
based on `calendar.provider` in the business config.
"""
from __future__ import annotations

from datetime import datetime, timedelta


class GoogleCalendarClient:
    def __init__(self, calendar_id: str, credentials_path: str, slot_minutes: int = 30):
        self.calendar_id = calendar_id
        self.credentials_path = credentials_path
        self.slot_minutes = slot_minutes
        self._service = self._build_service()

    def _build_service(self):
        # TODO: build the real Google API client, e.g.:
        #
        #   from google.oauth2 import service_account
        #   from googleapiclient.discovery import build
        #
        #   creds = service_account.Credentials.from_service_account_file(
        #       self.credentials_path,
        #       scopes=["https://www.googleapis.com/auth/calendar"],
        #   )
        #   return build("calendar", "v3", credentials=creds)
        #
        # Left unimplemented here since it requires real credentials per
        # business. Decide OAuth (per-business consent) vs. service account
        # (single shared calendar identity) before filling this in — see
        # TRD's "Environment/secrets" section.
        raise NotImplementedError(
            "GoogleCalendarClient requires real credentials. Fill in "
            "_build_service() once you've chosen OAuth vs. service account, "
            "or use `calendar.provider: fake` in the business config to "
            "prototype without Google Calendar."
        )

    def get_available_slots(self, day: datetime, count: int = 3) -> list[datetime]:
        # TODO: call self._service.freebusy().query(...) or events().list(...)
        # for `self.calendar_id` on `day`, then diff against business hours
        # using the same slot-generation logic as FakeCalendar.
        raise NotImplementedError

    def book(self, caller_phone: str, start_time: datetime, notes: str = ""):
        # TODO: self._service.events().insert(calendarId=self.calendar_id, body=...)
        raise NotImplementedError

    def find_by_phone(self, caller_phone: str):
        # TODO: query events with a caller_phone match in extendedProperties
        raise NotImplementedError

    def cancel(self, appointment_id: str) -> bool:
        # TODO: self._service.events().delete(...)
        raise NotImplementedError

    def reschedule(self, appointment_id: str, new_start_time: datetime):
        # TODO: self._service.events().patch(...)
        raise NotImplementedError
