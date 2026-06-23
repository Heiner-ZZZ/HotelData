import re

from pydantic import BaseModel, field_validator


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
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v) > 128:
            raise ValueError("La contraseña no puede tener más de 128 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe contener al menos un dígito")
        return v
