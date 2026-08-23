"""Auth routes package — split into focused submodules.

Keeps backward compatibility by re-exporting the three routers
that `main.py` imports.

Router naming convention:
  router       → module-level admin/status endpoints    (prefix /modules/auth)
  web_router   → web form endpoints                     (prefix /auth)
  api_router   → JSON API endpoints                     (prefix /api/auth)

Re-exported from login.py (main session management):
  router, web_router (login_form, login_submit, logout)
  api_router (login_api, sessions, terminate)

Re-exported from register.py:
  register_api_router (send-code, register, confirm-code)  → merged into api_router

Re-exported from profile.py:
  profile_api_router (me, heartbeat, refresh)  → merged into api_router
  profile_web_router (me)                       → merged into web_router

Re-exported from password.py:
  password_api_router (recover, reset)  → merged into api_router
"""

from __future__ import annotations

from fastapi import APIRouter

from .login import router, web_router, api_router as _login_api_router
from .register import api_router as _register_api_router
from .register_property import api_router as _register_property_api_router
from .registration_status import api_router as _registration_status_api_router
from .profile import api_router as _profile_api_router, web_router as _profile_web_router
from .password import api_router as _password_api_router
from .guest_prefs import api_router as _guest_prefs_api_router

# Merge all api_router routes into _login_api_router (the main one)
for sub_router in (
    _register_api_router,
    _register_property_api_router,
    _registration_status_api_router,
    _profile_api_router,
    _password_api_router,
    _guest_prefs_api_router,
):
    for route in sub_router.routes:
        _login_api_router.routes.append(route)

# Merge profile_web_router into web_router
for route in _profile_web_router.routes:
    web_router.routes.append(route)

api_router = _login_api_router

__all__ = ["router", "web_router", "api_router"]
