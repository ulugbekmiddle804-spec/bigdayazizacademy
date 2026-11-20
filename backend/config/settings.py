"""Django settings for the Online Test Platform.

All environment-specific values come from environment variables (see .env.example).
"""
import os
from urllib.parse import unquote, urlparse
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_local_env(path):
    """Local runs (no Docker): read backend/.env.local if it exists. Real env variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env(BASE_DIR / ".env.local")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG or env_bool("DJANGO_TESTING", False):
        SECRET_KEY = "dev-insecure-secret-key-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1")
# Railway: its own domain, plus the public site (e.g. the Cloudflare Pages domain) given in FRONTEND_URL.
for _url in [f"https://{env('RAILWAY_PUBLIC_DOMAIN')}" if env("RAILWAY_PUBLIC_DOMAIN") else "", *env_list("FRONTEND_URL", "")]:
    if _url:
        _host = urlparse(_url).hostname
        if _host and _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)
        if _url.rstrip("/") not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_url.rstrip("/"))
if env("RAILWAY_PRIVATE_DOMAIN") and env("RAILWAY_PRIVATE_DOMAIN") not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(env("RAILWAY_PRIVATE_DOMAIN"))
if env("RAILWAY_ENVIRONMENT") and "healthcheck.railway.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("healthcheck.railway.app")  # Railway's health check uses this Host header
# Shared secret of the Cloudflare Pages proxy: requests carrying it may report the visitor's real IP.
PROXY_SECRET = env("PROXY_SECRET", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.catalog",
    "apps.exams",
    "apps.adminapi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# --- Database -----------------------------------------------------------------
if env("DB_ENGINE", "postgres") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # Several requests may write at once (autosave); wait instead of failing with "database is locked".
            "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE", "init_command": "PRAGMA journal_mode=WAL;"},
        }
    }
else:
    _db_options = {"connect_timeout": 5}
    _use_pool = env_bool("DB_POOL", True)
    if _use_pool:
        # psycopg3 connection pool (Django >= 5.1). One pool per process.
        _db_options["pool"] = {
            "min_size": env_int("DB_POOL_MIN", 2),
            "max_size": env_int("DB_POOL_MAX", 10),
            "timeout": env_int("DB_POOL_TIMEOUT", 10),
        }
    # Railway (and most PaaS) give one DATABASE_URL; docker compose uses the POSTGRES_* variables.
    _db_url = urlparse(env("DATABASE_URL", "")) if env("DATABASE_URL") else None
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(_db_url.path.lstrip("/")) if _db_url else env("POSTGRES_DB", "testplatform"),
            "USER": unquote(_db_url.username or "") if _db_url else env("POSTGRES_USER", "testplatform"),
            "PASSWORD": unquote(_db_url.password or "") if _db_url else env("POSTGRES_PASSWORD", "testplatform"),
            "HOST": _db_url.hostname if _db_url else env("POSTGRES_HOST", "localhost"),
            "PORT": str(_db_url.port or 5432) if _db_url else env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 0 if _use_pool else env_int("DB_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": not _use_pool,
            "OPTIONS": _db_options,
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cache / Redis --------------------------------------------------------------
REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "otp",
            "TIMEOUT": 300,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": env_int("REDIS_MAX_CONNECTIONS", 50)},
                "SOCKET_CONNECT_TIMEOUT": 3,
                "SOCKET_TIMEOUT": 3,
                # The site keeps working (slower) if Redis goes down.
                "IGNORE_EXCEPTIONS": True,
            },
        }
    }
    DJANGO_REDIS_IGNORE_EXCEPTIONS = True
    DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# --- Auth -----------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Passwords are stored with PBKDF2-SHA256 (Django default, salted, 1M+ iterations).

# --- I18N -------------------------------------------------------------------------
LANGUAGE_CODE = "uz"
TIME_ZONE = env("TIME_ZONE", "Asia/Tashkent")
USE_I18N = True
USE_TZ = True

# --- Static files -------------------------------------------------------------------
STATIC_URL = env("STATIC_URL", "/static/")  # point to a CDN in production if desired
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL", "django-admin/")
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Security -------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = env_int("ADMIN_SESSION_AGE", 60 * 60 * 8)
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # the SPA reads it to send X-CSRFToken
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if env_bool("HTTPS", False):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# --- REST framework ---------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_RATES": {
        # Exam rooms often share one public IP, so per-IP limits are generous.
        "attempt_start": env("THROTTLE_ATTEMPT_START", "1000/min"),
        "public_meta": env("THROTTLE_PUBLIC_META", "1200/min"),
        "attempt_token": env("THROTTLE_ATTEMPT_TOKEN", "240/min"),
        "admin_login": env("THROTTLE_ADMIN_LOGIN", "10/min"),
        "admin": env("THROTTLE_ADMIN", "600/min"),
    },
    "NUM_PROXIES": env_int("NUM_PROXIES", 1),
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# --- Exam rules ------------------------------------------------------------------------------
EXAM = {
    # Answers/finish requests arriving shortly after the deadline are still accepted
    # (network latency, slow devices).
    "GRACE_SECONDS": env_int("EXAM_GRACE_SECONDS", 20),
    # Maximum pause between stage 1 and stage 2 before the attempt is closed.
    "STAGE_BREAK_MAX_MINUTES": env_int("EXAM_STAGE_BREAK_MAX_MINUTES", 15),
    "QUESTION_POOL_CACHE_SECONDS": env_int("QUESTION_POOL_CACHE_SECONDS", 600),
}

# --- Celery ------------------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL or "memory://")
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_BEAT_SCHEDULE = {
    "finalize-expired-attempts": {
        "task": "apps.exams.tasks.finalize_expired_attempts",
        "schedule": timedelta(seconds=env_int("EXPIRED_SWEEP_SECONDS", 60)),
    },
}

# --- Logging -------------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}
