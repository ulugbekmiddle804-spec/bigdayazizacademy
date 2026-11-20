"""Gunicorn settings. Threads + a per-process DB pool handle many short requests well."""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", f"0.0.0.0:{os.environ.get('PORT', '8000')}")  # Railway sets PORT
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 8)))
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_class = "gthread"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
graceful_timeout = 20
keepalive = 75  # longer than nginx upstream keepalive_timeout, avoids races on reused connections
# Recycle workers rarely and staggered (big jitter) so they never all restart at once.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 20000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 5000))
accesslog = "-" if os.environ.get("GUNICORN_ACCESS_LOG", "0") == "1" else None
errorlog = "-"
forwarded_allow_ips = "*"
