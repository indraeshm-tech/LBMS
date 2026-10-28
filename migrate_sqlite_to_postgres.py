"""Copy local SQLite LBMS records to the PostgreSQL database in DATABASE_URL.

Usage:
  set DATABASE_URL=postgresql://...   (Windows CMD)
  python migrate_sqlite_to_postgres.py

By default, conflicting records are kept as they are in PostgreSQL.
Use --replace to clear the five LBMS tables first and replace their contents
with the local SQLite database. Back up PostgreSQL before using --replace.
"""
import argparse
import os
import sqlite3
import sys

from database import DB_PATH, get_db_connection, init_db

TABLES = ["Users", "BookDetails", "IssueDate", "ReturnData", "FineCalculation"]
ID_COLUMNS = {
    "BookDetails": "Bid",
    "IssueDate": "IssueId",
    "ReturnData": "ReturnId",
    "FineCalculation": "FineId",
}


def main():
    parser = argparse.ArgumentParser(description="Migrate local LBMS SQLite data to PostgreSQL")
    parser.add_argument("--replace", action="store_true", help="Clear PostgreSQL LBMS tables before importing")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL", "").strip():
        sys.exit("ERROR: Set DATABASE_URL to your hosted PostgreSQL connection string first.")
    if not os.path.exists(DB_PATH):
        sys.exit(f"ERROR: Local SQLite database not found: {DB_PATH}")

    if args.replace:
        print("WARNING: --replace will delete all existing records from the five LBMS tables in PostgreSQL.")
        answer = input("Type REPLACE to continue: ").strip()
        if answer != "REPLACE":
            sys.exit("Cancelled; no data was changed.")

    init_db()  # Creates the PostgreSQL schema if needed.
    source = sqlite3.connect(DB_PATH)
    source.row_factory = sqlite3.Row
    target = get_db_connection()
    try:
        if args.replace:
            target.execute("TRUNCATE TABLE FineCalculation, ReturnData, IssueDate, BookDetails, Users RESTART IDENTITY CASCADE")
            target.commit()

        for table in TABLES:
            rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
            if not rows:
                print(f"{table}: no rows to import")
                continue
            columns = [item[1] for item in source.execute(f'PRAGMA table_info("{table}")').fetchall()]
            col_sql = ", ".join('"' + col + '"' for col in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            sql = f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            imported = 0
            for row in rows:
                cursor = target.execute(sql, tuple(row[col] for col in columns))
                if cursor.rowcount > 0:
                    imported += 1
            target.commit()
            print(f"{table}: imported {imported} of {len(rows)} local rows (conflicts skipped)")

        for table, column in ID_COLUMNS.items():
            target.execute(
                "SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE(MAX(" + column + "), 1), MAX(" + column + ") IS NOT NULL) FROM " + table,
                (table.lower(), column.lower()),
            )
        target.commit()
        print("Migration finished. Verify the live application and database records.")
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    main()
