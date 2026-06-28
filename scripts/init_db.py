"""init_db.py — Initialize PostgreSQL database with schema and seed data."""
import os
import sys
import psycopg2

SCRIPTS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(SCRIPTS_DIR, "..")
SQL_DIR = os.path.join(PROJECT_ROOT, "data")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://labops:labops@localhost:5432/labops")


def run_sql_file(cursor, filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    cursor.execute(sql)


def main():
    print(f"Connecting to {DATABASE_URL.split('@')[1]} ...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("Running create_tables.sql ...")
    run_sql_file(cursor, os.path.join(SQL_DIR, "create_tables.sql"))

    print("Running seed_data.sql ...")
    run_sql_file(cursor, os.path.join(SQL_DIR, "seed_data.sql"))

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
