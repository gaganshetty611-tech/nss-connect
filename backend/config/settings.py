"""
NSS Connect – Django settings.

All secrets and deployment-specific values come from environment variables
(see ../.env.example). A local `.env` file is loaded if present.
"""
import json
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# --- .env loading (tiny built-in loader; python-dotenv is used if installed) --
def _load_env_file(path):
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(path, override=False)
        return
    except ImportError:
        pass
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


_load_env_file(BASE_DIR / ".env")
_load_env_file(PROJECT_ROOT / ".env")


def env(key, default=None):
    """Environment value; empty strings count as unset so a blank line in .env keeps the default."""
    val = os.environ.get(key)
    return default if val is None or val.strip() == "" else val.strip()


def env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None or val == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [item.strip() for item in os.environ.get(key, default).split(",") if item.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Development-only fallback. Never used when DEBUG=False.
        SECRET_KEY = "dev-insecure-key-change-me-" + "x" * 20
    else:
        raise RuntimeError("SECRET_KEY environment variable is required when DEBUG=False")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
if DEBUG:
    # Development only: accept LAN IPs (phone on the same Wi-Fi) and tunnel hostnames.
    ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # local
    "core",
    "accounts",
    "notifications",
    "ngos",
    "nss_units",
    "events",
    "attendance",
    "certificates",
    "ai_matching",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Serve Django-admin static files in production when WhiteNoise is installed (requirements.txt).
try:
    import whitenoise  # noqa: F401

    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
except ImportError:
    pass

ROOT_URLCONF = "config.urls"

FRONTEND_DIST = Path(env("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist")))

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database: PostgreSQL if DATABASE_URL is set, otherwise SQLite -------------
DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", str(BASE_DIR / "staticfiles")))

MEDIA_URL = env("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
# Serve uploaded media through Django even with DEBUG=False. Convenient for a
# single-machine demo behind a tunnel; use nginx/cloud storage for real traffic.
SERVE_MEDIA = env_bool("SERVE_MEDIA", True)

# Optional S3-compatible storage (requires `pip install django-storages boto3`).
if env("AWS_STORAGE_BUCKET_NAME"):
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
    AWS_QUERYSTRING_AUTH = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Upload limits (bytes)
MAX_IMAGE_UPLOAD_SIZE = int(env("MAX_IMAGE_UPLOAD_SIZE", 5 * 1024 * 1024))
MAX_DOCUMENT_UPLOAD_SIZE = int(env("MAX_DOCUMENT_UPLOAD_SIZE", 10 * 1024 * 1024))
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- REST framework / JWT ----------------------------------------------------
REST_FRAMEWORK = {
    # JWT only in production. Session auth (CSRF-enforced) is enabled in DEBUG for the browsable API.
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"]
    + (["rest_framework.authentication.SessionAuthentication"] if DEBUG else []),
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", "120/min"),
        "user": env("THROTTLE_USER", "600/min"),
        "auth": env("THROTTLE_AUTH", "20/min"),
        "checkin": env("THROTTLE_CHECKIN", "30/min"),
    },
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", 30))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY") or SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Refresh token is also set as an httpOnly cookie so the SPA never has to put it
# in localStorage. Same-origin setups (Vite proxy / Django serving the build /
# a single tunnel URL) work with SameSite=Lax. Cross-site deployments need
# JWT_COOKIE_SAMESITE=None and HTTPS.
JWT_REFRESH_COOKIE = "nss_refresh"
JWT_COOKIE_SECURE = env_bool("JWT_COOKIE_SECURE", not DEBUG)
JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", "Lax")

# --- CORS / CSRF ---------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else ""
)
CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://[\w-]+\.trycloudflare\.com$",
        r"^https://[\w-]+\.ngrok-free\.app$",
        r"^http://192\.168\.\d+\.\d+:\d+$",
    ]
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS))

# --- Security headers ------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", True)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)  # tunnels/proxies usually terminate TLS
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", 0))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)

# --- Email -------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend" if env("EMAIL_HOST") else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", 587))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "NSS Connect <no-reply@nssconnect.local>")

# Public URL of the React app. Used in emails, QR codes and certificate QR codes.
# If empty, the request's Origin header is used (works for same-origin & tunnels).
FRONTEND_URL = env("FRONTEND_URL", "").rstrip("/")

REQUIRE_EMAIL_VERIFICATION = env_bool("REQUIRE_EMAIL_VERIFICATION", True)

# --- Google OAuth (optional) ---------------------------------------------------------
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI", "")

# --- AI ------------------------------------------------------------------------------
AI_PROVIDER = env("AI_PROVIDER", "rule_based")
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = env("GEMINI_API_KEY", "")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-1.5-flash")
AI_MATCH_WEIGHTS = {
    "distance": 0.25,
    "skills": 0.20,
    "availability": 0.20,
    "attendance": 0.20,
    "interest": 0.15,
}
if env("AI_MATCH_WEIGHTS"):
    AI_MATCH_WEIGHTS.update(json.loads(env("AI_MATCH_WEIGHTS")))
AI_MAX_DISTANCE_KM = float(env("AI_MAX_DISTANCE_KM", 50))

# --- Attendance rules ---------------------------------------------------------------
ATTENDANCE_EARLY_CHECKIN_MINUTES = int(env("ATTENDANCE_EARLY_CHECKIN_MINUTES", 60))
ATTENDANCE_LATE_AFTER_MINUTES = int(env("ATTENDANCE_LATE_AFTER_MINUTES", 15))
ATTENDANCE_CHECKOUT_GRACE_MINUTES = int(env("ATTENDANCE_CHECKOUT_GRACE_MINUTES", 120))
# Guards against an accidental double scan checking a volunteer out immediately.
ATTENDANCE_MIN_MINUTES = int(env("ATTENDANCE_MIN_MINUTES", 15))

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
