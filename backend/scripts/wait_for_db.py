"""Exit 0 when PostgreSQL accepts connections, 1 otherwise."""
import os
import sys

import psycopg

try:
    url = os.environ.get("DATABASE_URL")
    conn = psycopg.connect(url, connect_timeout=3) if url else psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        connect_timeout=3,
    )
    conn.close()
except Exception:
    sys.exit(1)
sys.exit(0)
