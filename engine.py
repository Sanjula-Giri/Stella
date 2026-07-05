"""
Generic, config-defined intake engine. A vertical defines its own case types
and questions in YAML (see config/schema.py: IntakeCaseType) — no code
changes needed to add a new intake flow.

Supports partial-answer persistence so a dropped call doesn't lose captured
data (persisted to a per-call JSON file under ./data/intake_sessions/).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from config.schema import IntakeCaseType


@dataclass
class IntakeSession:
    call_id: str
    case_type: IntakeCaseType
    answers: dict[str, str] = field(default_factory=dict)

    @property
    def remaining_required_questions(self) -> list[str]:
        return [
            q.id
            for q in self.case_type.questions
            if q.required and q.id not in self.answers
        ]

    @property
    def is_complete(self) -> bool:
        return len(self.remaining_required_questions) == 0

    def next_prompt(self) -> str | None:
        for q in self.case_type.questions:
            if q.id not in self.answers:
                return q.prompt
        return None

    def record_answer(self, question_id: str, answer: str) -> None:
        self.answers[question_id] = answer
        self._persist()

    def _session_path(self) -> str:
        directory = os.path.join("data", "intake_sessions")
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, f"{self.call_id}.json")

    def _persist(self) -> None:
        with open(self._session_path(), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "call_id": self.call_id,
                    "case_type": self.case_type.name,
                    "answers": self.answers,
                },
                f,
                indent=2,
            )

    def finalize(self) -> dict:
        """Write final submission and return it. Caller (agent.py) is
        responsible for routing this into notification channels."""
        submission = {
            "call_id": self.call_id,
            "case_type": self.case_type.name,
            "answers": self.answers,
            "complete": self.is_complete,
        }
        directory = os.path.join("data", "intake_submissions")
        os.makedirs(directory, exist_ok=True)
        with open(
            os.path.join(directory, f"{self.call_id}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(submission, f, indent=2)
        return submission


def start_intake_session(call_id: str, case_types: list[IntakeCaseType], case_type_name: str) -> IntakeSession:
    match = next((c for c in case_types if c.name == case_type_name), None)
    if match is None:
        available = ", ".join(c.name for c in case_types) or "(none configured)"
        raise ValueError(
            f"Unknown intake case type '{case_type_name}'. Available: {available}"
        )
    return IntakeSession(call_id=call_id, case_type=match)
