"""init_db.py — Initialize PostgreSQL database with schema and seed data.

Idempotent: safe to re-run. Ignores unique-violation errors on seed data
so Docker restarts don't crash. Retries connection until PostgreSQL is ready.
"""
import os
import time
import psycopg2

SCRIPTS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(SCRIPTS_DIR, "..")
SQL_DIR = os.path.join(PROJECT_ROOT, "data")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://labops:labops@localhost:5432/labops")
MAX_RETRIES = 10
RETRY_DELAY = 3  # seconds


def _connect():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            print(f"Connected to {DATABASE_URL.split('@')[1]}")
            return conn
        except psycopg2.OperationalError as exc:
            print(f"Connection attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY)


def _run_file(cursor, filepath: str, ignore_duplicates: bool = False):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split file on semicolons to execute statements individually.
    # This lets us skip unique-violation errors during seeding.
    statements = [s.strip() for s in raw.split(";") if s.strip()]

    for stmt in statements:
        try:
            cursor.execute(stmt)
        except psycopg2.errors.UniqueViolation:
            if ignore_duplicates:
                cursor.connection.rollback()
            else:
                raise
        except psycopg2.Error:
            # Any other SQL error → rollback this statement and re-raise
            cursor.connection.rollback()
            raise


def main():
    conn = _connect()
    cursor = conn.cursor()

    print("Running create_tables.sql ...")
    _run_file(cursor, os.path.join(SQL_DIR, "create_tables.sql"), ignore_duplicates=False)
    conn.commit()

    print("Running seed_data.sql (idempotent) ...")
    _run_file(cursor, os.path.join(SQL_DIR, "seed_data.sql"), ignore_duplicates=True)
    conn.commit()

    cursor.close()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
