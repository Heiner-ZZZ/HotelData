"""Shared Jinja2Templates instance for all web routes.

All route modules should import `templates` from here instead of creating
their own Jinja2Templates instance. This ensures a single instance is
used across the entire application.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = str(Path(__file__).resolve().parent / "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
