import os
import sys
from functools import wraps
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from flask import session, redirect, request

URL_PREFIX = os.environ.get("KEEPSAKE_URL_PREFIX", "/monitor").rstrip("/")
DASHBOARD_PASSWORD = os.environ.get("KEEPSAKE_DASHBOARD_PASSWORD", "")
SESSION_SECRET = os.environ.get("KEEPSAKE_SESSION_SECRET", "change-me-in-production")
AUTH_REQUIRED = bool(DASHBOARD_PASSWORD)


def check_startup():
    if not DASHBOARD_PASSWORD:
        print(
            "WARNING: KEEPSAKE_DASHBOARD_PASSWORD not set. "
            "Dashboard is unprotected — do not expose publicly.",
            file=sys.stderr,
        )


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_REQUIRED:
            return f(*args, **kwargs)
        if session.get("authenticated"):
            return f(*args, **kwargs)
        return redirect(f"{URL_PREFIX}/login")
    return decorated


def verify_password(password: str) -> bool:
    if not DASHBOARD_PASSWORD:
        return False
    return password == DASHBOARD_PASSWORD
