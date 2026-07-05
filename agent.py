"""
The Receptionist Agent — one class, fixed tool surface, used for every
vertical. What differs per business is entirely the config (system prompt,
calendar, intake case types, dtmf routes) — never this code.

Built against the livekit-agents Agent/function_tool pattern. If your
installed livekit-agents version's decorator names differ slightly, adjust
the imports below — the tool bodies themselves don't depend on the exact
decorator API.
"""
from __future__ import annotations

from datetime import datetime

from livekit.agents import Agent, function_tool

from config.schema import BusinessConfig
from app.booking.availability import build_calendar, format_slots_for_speech
from app.intakes.engine import start_intake_session
from app.notifications import notify
from app.prompts import build_system_prompt


class Receptionist(Agent):
    def __init__(self, cfg: BusinessConfig, call_id: str):
        super().__init__(instructions=build_system_prompt(cfg))
        self.cfg = cfg
        self.call_id = call_id
        self.calendar = build_calendar(cfg)
        self._intake_session = None  # set by start_intake tool
        self._pending_transfer_target: str | None = None

    # ---- Appointment tools ------------------------------------------------

    @function_tool
    async def check_availability(self, date_iso: str) -> str:
        """Look up open appointment slots on a given date (YYYY-MM-DD)."""
        if self.calendar is None:
            return "This business doesn't take phone bookings — offer to transfer or take a message."
        day = datetime.fromisoformat(date_iso)
        slots = self.calendar.get_available_slots(day)
        return format_slots_for_speech(slots)

    @function_tool
    async def book_appointment(self, caller_phone: str, start_time_iso: str, notes: str = "") -> str:
        """Book an appointment for the caller at the given ISO start time."""
        if self.calendar is None:
            return "This business doesn't take phone bookings."
        start_time = datetime.fromisoformat(start_time_iso)
        appt = self.calendar.book(caller_phone, start_time, notes)
        notify(
            self.cfg,
            kind="booking",
            payload={
                "appointment_id": appt.id,
                "caller_phone": caller_phone,
                "start_time": start_time.isoformat(),
            },
        )
        return f"Booked. Confirmation id {appt.id} at {start_time.strftime('%A %I:%M %p')}."

    @function_tool
    async def reschedule_appointment(self, caller_phone: str, new_start_time_iso: str) -> str:
        """Reschedule the caller's existing appointment to a new time.

        NOTE: this closes the gap flagged in the original plan (Phase 5),
        where reschedule/cancel had no tool and fell back to take_message.
        """
        if self.calendar is None:
            return "This business doesn't take phone bookings."
        existing = self.calendar.find_by_phone(caller_phone)
        if not existing:
            return "I couldn't find an existing appointment under that number — offer to take a message."
        appt = existing[0]
        new_start = datetime.fromisoformat(new_start_time_iso)
        updated = self.calendar.reschedule(appt.id, new_start)
        notify(
            self.cfg,
            kind="reschedule",
            payload={"appointment_id": appt.id, "new_start_time": new_start.isoformat()},
        )
        return f"Rescheduled to {updated.start_time.strftime('%A %I:%M %p')}."

    @function_tool
    async def cancel_appointment(self, caller_phone: str) -> str:
        """Cancel the caller's existing appointment."""
        if self.calendar is None:
            return "This business doesn't take phone bookings."
        existing = self.calendar.find_by_phone(caller_phone)
        if not existing:
            return "I couldn't find an existing appointment under that number."
        appt = existing[0]
        self.calendar.cancel(appt.id)
        notify(self.cfg, kind="cancel", payload={"appointment_id": appt.id})
        return "Cancelled."

    # ---- Messaging / escalation --------------------------------------------

    @function_tool
    async def take_message(self, caller_name: str, caller_phone: str, message: str) -> str:
        """Record a callback message when the AI can't complete the request."""
        notify(
            self.cfg,
            kind="message",
            payload={"caller_name": caller_name, "caller_phone": caller_phone, "message": message},
        )
        return "Message recorded. Someone will call back."

    @function_tool
    async def transfer_call(self, target: str) -> str:
        """Warm-transfer the caller to a named department (e.g. 'front_desk')."""
        self._pending_transfer_target = target
        # TODO: actual LiveKit SIP transfer call goes here (server.py handles
        # the room-level mechanics once this tool signals intent).
        return f"Transferring you to {target} now."

    @function_tool
    async def end_call(self, reason: str = "completed") -> str:
        """End the call gracefully."""
        return f"Ending call ({reason})."

    # ---- Structured intake --------------------------------------------------

    @function_tool
    async def start_intake(self, case_type_name: str) -> str:
        """Begin a structured intake flow for a given case type (e.g. 'new_patient')."""
        self._intake_session = start_intake_session(
            self.call_id, self.cfg.intake_case_types, case_type_name
        )
        return self._intake_session.next_prompt() or "No questions configured for this case type."

    @function_tool
    async def record_intake_answer(self, question_id: str, answer: str) -> str:
        """Record the caller's answer to the current intake question."""
        if self._intake_session is None:
            return "No intake session in progress — call start_intake first."
        self._intake_session.record_answer(question_id, answer)
        next_prompt = self._intake_session.next_prompt()
        return next_prompt or "That's everything I need — ready to finalize."

    @function_tool
    async def finalize_intake(self) -> str:
        """Submit the completed intake and notify the business."""
        if self._intake_session is None:
            return "No intake session in progress."
        submission = self._intake_session.finalize()
        notify(self.cfg, kind="intake", payload=submission)
        self._intake_session = None
        return "Thanks — that's been submitted."

    # ---- Keypad / FAQ / hours --------------------------------------------

    @function_tool
    async def await_keypad_entry(self, prompt: str) -> str:
        """Ask the caller to enter digits on their keypad (DTMF), e.g. for a callback number."""
        # Actual DTMF capture happens at the LiveKit/SIP layer (server.py);
        # this tool just signals intent and returns the prompt to speak.
        return prompt

    @function_tool
    async def get_business_hours(self) -> str:
        """Return this business's hours as a spoken-friendly string."""
        hours = self.cfg.business_hours.model_dump()
        open_days = {day: hrs for day, hrs in hours.items() if hrs}
        if not open_days:
            return "Hours aren't configured for this business."
        return "; ".join(f"{day.title()} {hrs}" for day, hrs in open_days.items())

    @function_tool
    async def lookup_faq(self, question: str) -> str:
        """Look up a configured FAQ answer matching the caller's question."""
        # Naive substring match for the prototype; swap for embedding-based
        # matching once you have enough FAQs per business for it to matter.
        question_lower = question.lower()
        for q, a in self.cfg.faqs.items():
            if q.lower() in question_lower or question_lower in q.lower():
                return a
        return "I don't have that on file — I can take a message so someone can follow up."

    @function_tool
    async def send_info_packet(self, caller_phone: str, packet_name: str) -> str:
        """Send an SMS/email info packet to the caller (e.g. new-patient forms)."""
        notify(
            self.cfg,
            kind="info_packet",
            payload={"caller_phone": caller_phone, "packet_name": packet_name},
        )
        return f"Sent — you should get {packet_name} shortly."
