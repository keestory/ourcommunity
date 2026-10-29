"""Strict request schemas; ownership and timestamps are checked again on server."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginInput(InputModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=1, max_length=128)


class RegisterInput(LoginInput):
    display_name: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=10, max_length=128)


class DemoInput(InputModel):
    persona: Literal["mira", "jun", "sora", "outsider"]


class MessageInput(InputModel):
    client_id: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    body: str = Field(min_length=1, max_length=2000)


class BodyInput(InputModel):
    body: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(min_length=8, max_length=100)


class ReadInput(InputModel):
    seq: int = Field(ge=0)


class EventInput(InputModel):
    request_id: str = Field(min_length=8, max_length=100)
    title: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=1000)
    location: str = Field(min_length=2, max_length=120)
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=2, le=100)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("시간대가 포함된 날짜를 보내 주세요.")
        return value


class RsvpInput(InputModel):
    action: Literal["join", "cancel", "accept"]
    request_id: str = Field(min_length=8, max_length=100)


class VersionInput(InputModel):
    version: int = Field(ge=1)


class AttendanceInput(InputModel):
    user_id: str = Field(min_length=1, max_length=80)
    present: bool


class PreferenceInput(InputModel):
    activity_consent: bool | None = None
    muted: bool | None = None


class SettingsInput(InputModel):
    public_space: bool | None = None
    palette: Literal["dawn", "forest", "sunset"] | None = None
    version: int = Field(ge=1)


class ReportInput(InputModel):
    message_id: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=300)


class ResolveInput(InputModel):
    status: Literal["reviewed"]


class InviteInput(InputModel):
    max_uses: int = Field(default=20, ge=1, le=100)
