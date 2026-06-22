from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    session_timeout_minutes: int = 60
    default_dashboard: str = "/management"
    theme: str = "system"


class SettingsUpdate(BaseModel):
    session_timeout_minutes: int | None = None
    default_dashboard: str | None = None
    theme: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
