"""
Pydantic models for per-business config.

Design goal (per TRD): fail fast at startup on bad config (missing files,
invalid cross-references) rather than failing mid-call. Every field a
vertical might need lives here; a new vertical is onboarded by writing YAML
that fits this shape, never by writing new Python.
"""
from __future__ import annotations

import os
import re
from enum import Enum
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _interpolate_env(raw: str) -> str:
    """Replace ${VAR_NAME} with the value of the matching environment variable."""

    def _replace(match: "re.Match[str]") -> str:
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(
                f"Config references ${{{var_name}}} but that environment "
                f"variable is not set."
            )
        return value

    return _VAR_PATTERN.sub(_replace, raw)


class CalendarProvider(str, Enum):
    GOOGLE = "google"
    FAKE = "fake"  # in-memory calendar for prototyping, no real credentials needed
    NONE = "none"  # this vertical doesn't book appointments (e.g. grocery)


class MessageChannel(str, Enum):
    FILE = "file"
    EMAIL = "email"
    WEBHOOK = "webhook"


class BusinessHours(BaseModel):
    # Simple v1 shape: one open/close pair per weekday, "closed" if absent.
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None


class CalendarConfig(BaseModel):
    provider: CalendarProvider = CalendarProvider.FAKE
    calendar_id: Optional[str] = None
    credentials_path: Optional[str] = None
    appointment_duration_minutes: int = 30

    @model_validator(mode="after")
    def _google_needs_credentials(self) -> "CalendarConfig":
        if self.provider == CalendarProvider.GOOGLE and not self.credentials_path:
            raise ValueError(
                "calendar.provider is 'google' but no credentials_path was given."
            )
        return self


class IntakeQuestion(BaseModel):
    id: str
    prompt: str
    required: bool = False
    critical: bool = False  # must be read back to caller for confirmation
    allow_dtmf: bool = False


class IntakeCaseType(BaseModel):
    name: str
    description: str
    questions: list[IntakeQuestion]


class DTMFRoute(BaseModel):
    digit: str
    label: str
    action: str  # e.g. "transfer:front_desk" or "intake:new_patient"


class NotificationConfig(BaseModel):
    channels: list[MessageChannel] = Field(default_factory=lambda: [MessageChannel.FILE])
    email_to: Optional[str] = None
    smtp_password: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_token: Optional[str] = None


class RecordingConfig(BaseModel):
    enabled: bool = False
    storage: str = "local"  # "local" or "s3"
    consent_preamble: Optional[str] = None
    retention_days_recordings: int = 30
    retention_days_transcripts: int = 90
    retention_days_messages: int = 90


class BusinessConfig(BaseModel):
    slug: str
    display_name: str
    vertical: str  # "clinic" | "salon" | "grocery" | "general_office" | custom
    timezone: str = "America/New_York"
    assistant_name: str = "Stella"
    greeting: str
    persona_notes: str = ""
    business_hours: BusinessHours
    faqs: dict[str, str] = Field(default_factory=dict)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    intake_case_types: list[IntakeCaseType] = Field(default_factory=list)
    dtmf_routes: list[DTMFRoute] = Field(default_factory=list)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    max_call_duration_minutes: int = 15
    silence_timeout_seconds: int = 8

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9_-]+", v):
            raise ValueError("slug must be lowercase letters, numbers, - or _")
        return v


def load_business_config(path: str) -> BusinessConfig:
    """Load, env-interpolate, and validate a business YAML file. Fails fast."""
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    interpolated = _interpolate_env(raw_text)
    data = yaml.safe_load(interpolated)

    try:
        return BusinessConfig.model_validate(data)
    except Exception as exc:  # re-raise with the file path for a useful error
        raise ValueError(f"Invalid config at {path}: {exc}") from exc
