import os

from .settings import *  # noqa: F403


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_DATABASE", ":memory:"),
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
SECURE_SSL_REDIRECT = False
