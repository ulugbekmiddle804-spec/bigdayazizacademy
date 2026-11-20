# Celery is only needed on the server (Docker). Local runs (requirements-local.txt) work without it.
try:
    from .celery import app as celery_app
except ImportError:  # pragma: no cover
    celery_app = None

__all__ = ("celery_app",)
