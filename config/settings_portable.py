import os
from pathlib import Path

from .settings import *  # noqa: F403


DATA_DIR = Path(os.environ["ACCRUAL_DATA_DIR"])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "accrual.sqlite3",
        "OPTIONS": {"timeout": 30},
    }
}

SECRET_KEY = os.environ["ACCRUAL_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
STATIC_ROOT = DATA_DIR / "staticfiles"
MEDIA_ROOT = DATA_DIR / "media"
