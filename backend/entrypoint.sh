#!/bin/sh
set -e

# Wait for PostgreSQL (up to ~60 s).
if [ "${DB_ENGINE:-postgres}" = "postgres" ]; then
  i=0
  until python /app/scripts/wait_for_db.py; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
      echo "PostgreSQL is not reachable" >&2
      exit 1
    fi
    echo "Waiting for PostgreSQL... ($i)"
    sleep 2
  done
fi

# Only the web container prepares the database (Celery containers set RUN_SETUP=0).
if [ "${RUN_SETUP:-1}" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput -v 0
  if [ "${SEED_DEMO:-1}" = "1" ]; then
    python manage.py seed_demo
  fi
  python manage.py ensure_admin
fi

# Without Celery (e.g. Railway): finish timed-out attempts every minute from the web container.
if [ "${EXPIRED_SWEEP_IN_WEB:-0}" = "1" ]; then
  (
    while true; do
      sleep "${EXPIRED_SWEEP_SECONDS:-60}"
      python manage.py finalize_expired >/dev/null 2>&1 || true
    done
  ) &
fi

exec "$@"
