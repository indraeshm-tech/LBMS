"""
database.py - SQLite Database Initializer and Connection Helper
Library Management System (LBMS)
Developed by Fathima Afroz, iPEC Solutions, Bangalore
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library_management_system.db')
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRES = bool(DATABASE_URL)

class DatabaseConnection:
    """Small compatibility wrapper so the existing app can use SQLite or PostgreSQL."""
    def __init__(self, connection, postgres=False):
        self._connection = connection
        self._postgres = postgres

    def _sql(self, sql):
        if self._postgres:
            return sql.replace('?', '%s')
        return sql

    def execute(self, sql, params=()):
        if self._postgres:
            cursor = CompatibleCursor(self)
            cursor.execute(sql, params)
            return cursor
        return self._connection.execute(sql, params)

    def cursor(self):
        return self._connection.cursor()

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()


def get_db_connection():
    """Return a connection to hosted PostgreSQL or local SQLite for development."""
    database_url = os.environ.get('DATABASE_URL', '').strip()
    if database_url:
        try:
            import psycopg2
            from psycopg2.extras import DictCursor
        except ImportError as exc:
            raise RuntimeError('PostgreSQL driver missing. Install psycopg2-binary.') from exc
        # Some providers supply postgres://; psycopg2 accepts postgresql:// reliably.
        if database_url.startswith('postgres://'):
            database_url = 'postgresql://' + database_url[len('postgres://'):]
        raw = psycopg2.connect(database_url, cursor_factory=DictCursor, connect_timeout=10)
        return DatabaseConnection(raw, postgres=True)

    if os.environ.get('VERCEL'):
        raise RuntimeError('DATABASE_URL is required on Vercel. Configure a hosted PostgreSQL database in Project Settings > Environment Variables.')

    import sqlite3
    raw = sqlite3.connect(DB_PATH)
    raw.row_factory = sqlite3.Row
    raw.execute('PRAGMA foreign_keys = ON')
    return DatabaseConnection(raw, postgres=False)

def calculate_fine(due_date_str, return_date_str):
    """
    Calculates overdue fine based on rules:
    - Within a week (1-7 days overdue): Rs 10 per day.
    - Exceeding 1 week / 1 month (> 7 days overdue):
      First 7 days @ Rs 10/day + remaining days @ Rs 20/day.
    """
    try:
        due_d = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        return_d = datetime.strptime(return_date_str, "%Y-%m-%d").date()
    except Exception:
        return 0, 0.0

    if return_d <= due_d:
        return 0, 0.0  # No overdue

    days_overdue = (return_d - due_d).days

    if days_overdue <= 7:
        fine = days_overdue * 10.0
    else:
        fine = (7 * 10.0) + ((days_overdue - 7) * 20.0)

    return days_overdue, float(fine)

def calculate_penalty(book_price, due_date_str, return_date_str, is_lost=False):
    """
    Calculates penalty for lost book:
    Original Price + (if due date has occurred, calculate fine accordingly)
    """
    if not is_lost:
        return 0.0

    days_overdue, fine = calculate_fine(due_date_str, return_date_str)
    penalty = float(book_price) + fine
    return penalty

class RowProxy:
    """Make PostgreSQL's lowercase unquoted column names compatible with app keys."""
    def __init__(self, row):
        self.row = row

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.row[key]
        try:
            return self.row[key]
        except (KeyError, IndexError):
            wanted = str(key).lower()
            for name in self.row.keys():
                if str(name).lower() == wanted:
                    return self.row[name]
            raise KeyError(key)

    def keys(self):
        return self.row.keys()

    def __iter__(self):
        return iter(self.row)


class CompatibleCursor:
    """Cursor facade applying placeholder conversion for PostgreSQL."""
    def __init__(self, connection):
        self.connection = connection
        self.raw = connection.cursor()

    def execute(self, sql, params=()):
        if self.connection._postgres:
            sql = sql.replace('?', '%s')
        self.raw.execute(sql, params)
        return self

    def executemany(self, sql, seq):
        if self.connection._postgres:
            sql = sql.replace('?', '%s')
        self.raw.executemany(sql, seq)
        return self

    @property
    def rowcount(self):
        return self.raw.rowcount

    def fetchone(self):
        row = self.raw.fetchone()
        if row is None or not self.connection._postgres:
            return row
        return RowProxy(row)

    def fetchall(self):
        rows = self.raw.fetchall()
        if not self.connection._postgres:
            return rows
        return [RowProxy(row) for row in rows]


def init_db():
    """Create the schema for the active database and seed demo data if empty."""
    conn = get_db_connection()
    cursor = CompatibleCursor(conn)
    postgres = bool(os.environ.get('DATABASE_URL', '').strip())

    if postgres:
        statements = [
            """CREATE TABLE IF NOT EXISTS Users (
                UserId TEXT PRIMARY KEY, Password TEXT NOT NULL,
                Role TEXT NOT NULL CHECK(Role IN ('Staff', 'Student')),
                FullName TEXT NOT NULL, Regno TEXT, Branch TEXT, Sem TEXT,
                Email TEXT, Phone TEXT, CreatedAt TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS BookDetails (
                Bid SERIAL PRIMARY KEY, ISBN TEXT UNIQUE NOT NULL, Bname TEXT NOT NULL,
                Author TEXT NOT NULL, Title TEXT NOT NULL, Edition TEXT, Publisher TEXT,
                Volume TEXT, Price DOUBLE PRECISION NOT NULL,
                AvailableCopies INTEGER NOT NULL DEFAULT 1)""",
            """CREATE TABLE IF NOT EXISTS IssueDate (
                IssueId SERIAL PRIMARY KEY, ISBN TEXT NOT NULL, Title TEXT NOT NULL,
                Author TEXT NOT NULL, IssueDate TEXT NOT NULL, Regno TEXT NOT NULL,
                StudentName TEXT NOT NULL, Sem TEXT NOT NULL, Course_Branch TEXT NOT NULL,
                Duedate TEXT NOT NULL, IssuingStaffId TEXT NOT NULL,
                Status TEXT NOT NULL DEFAULT 'ISSUED',
                FOREIGN KEY (ISBN) REFERENCES BookDetails (ISBN))""",
            """CREATE TABLE IF NOT EXISTS ReturnData (
                ReturnId SERIAL PRIMARY KEY, ISBN TEXT NOT NULL, Title TEXT NOT NULL,
                Author TEXT NOT NULL, ReturnDate TEXT NOT NULL, Regno TEXT NOT NULL,
                StudentName TEXT NOT NULL, Sem TEXT NOT NULL, Course_Branch TEXT NOT NULL,
                Duedate TEXT NOT NULL, ReturningStaffId TEXT NOT NULL,
                DaysOverdue INTEGER DEFAULT 0, FineAmount DOUBLE PRECISION DEFAULT 0.0,
                PenaltyAmount DOUBLE PRECISION DEFAULT 0.0)""",
            """CREATE TABLE IF NOT EXISTS FineCalculation (
                FineId SERIAL PRIMARY KEY, ISBN TEXT NOT NULL, Regno TEXT NOT NULL,
                StudentName TEXT NOT NULL, ReturnDate TEXT NOT NULL, IssueDate TEXT NOT NULL,
                Duration INTEGER NOT NULL, Fine DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                Penality DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                Status TEXT NOT NULL DEFAULT 'PENDING')""",
        ]
        for statement in statements:
            cursor.execute(statement)
    else:
        statements = [
            """CREATE TABLE IF NOT EXISTS Users (
                UserId TEXT PRIMARY KEY, Password TEXT NOT NULL,
                Role TEXT NOT NULL CHECK(Role IN ('Staff', 'Student')),
                FullName TEXT NOT NULL, Regno TEXT, Branch TEXT, Sem TEXT,
                Email TEXT, Phone TEXT, CreatedAt TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS BookDetails (
                Bid INTEGER PRIMARY KEY AUTOINCREMENT, ISBN TEXT UNIQUE NOT NULL,
                Bname TEXT NOT NULL, Author TEXT NOT NULL, Title TEXT NOT NULL,
                Edition TEXT, Publisher TEXT, Volume TEXT, Price REAL NOT NULL,
                AvailableCopies INTEGER NOT NULL DEFAULT 1)""",
            """CREATE TABLE IF NOT EXISTS IssueDate (
                IssueId INTEGER PRIMARY KEY AUTOINCREMENT, ISBN TEXT NOT NULL,
                Title TEXT NOT NULL, Author TEXT NOT NULL, IssueDate TEXT NOT NULL,
                Regno TEXT NOT NULL, StudentName TEXT NOT NULL, Sem TEXT NOT NULL,
                Course_Branch TEXT NOT NULL, Duedate TEXT NOT NULL, IssuingStaffId TEXT NOT NULL,
                Status TEXT NOT NULL DEFAULT 'ISSUED',
                FOREIGN KEY (ISBN) REFERENCES BookDetails (ISBN))""",
            """CREATE TABLE IF NOT EXISTS ReturnData (
                ReturnId INTEGER PRIMARY KEY AUTOINCREMENT, ISBN TEXT NOT NULL,
                Title TEXT NOT NULL, Author TEXT NOT NULL, ReturnDate TEXT NOT NULL,
                Regno TEXT NOT NULL, StudentName TEXT NOT NULL, Sem TEXT NOT NULL,
                Course_Branch TEXT NOT NULL, Duedate TEXT NOT NULL,
                ReturningStaffId TEXT NOT NULL, DaysOverdue INTEGER DEFAULT 0,
                FineAmount REAL DEFAULT 0.0, PenaltyAmount REAL DEFAULT 0.0)""",
            """CREATE TABLE IF NOT EXISTS FineCalculation (
                FineId INTEGER PRIMARY KEY AUTOINCREMENT, ISBN TEXT NOT NULL,
                Regno TEXT NOT NULL, StudentName TEXT NOT NULL, ReturnDate TEXT NOT NULL,
                IssueDate TEXT NOT NULL, Duration INTEGER NOT NULL, Fine REAL NOT NULL DEFAULT 0.0,
                Penality REAL NOT NULL DEFAULT 0.0, Status TEXT NOT NULL DEFAULT 'PENDING')""",
        ]
        for statement in statements:
            conn.execute(statement)

    conn.commit()
    cursor = CompatibleCursor(conn)

    # Seed initial data if Users table is empty
    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Seed Users (Staff & Students)
        sample_users = [
            ('fathima', generate_password_hash('fathima123'), 'Student', 'Fathima Afroz', '1IPEC2024CS01', 'Computer Science & Engineering', '6th', 'fathima.afroz@ipecsolutions.in', '+91 98860 12345', now_str),
            ('staff101', generate_password_hash('admin123'), 'Staff', 'Dr. Rajeshwari K.', 'STAFF-LIB-01', 'Information Resource Center', 'Staff', 'librarian@ipecsolutions.in', '+91 98450 67890', now_str),
            ('rahul', generate_password_hash('rahul123'), 'Student', 'Rahul Sharma', '1IPEC2024IS02', 'Information Science & Engineering', '4th', 'rahul.s@ipecsolutions.in', '+91 99000 54321', now_str),
            ('ananya', generate_password_hash('ananya123'), 'Student', 'Ananya Hegde', '1IPEC2024AI03', 'Artificial Intelligence & Data Science', '6th', 'ananya.h@ipecsolutions.in', '+91 97410 98765', now_str),
        ]
        cursor.executemany("""
            INSERT INTO Users (UserId, Password, Role, FullName, Regno, Branch, Sem, Email, Phone, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_users)

        # Seed Book Details
        sample_books = [
            ('978-0078022159', 'Database System Concepts', 'Abraham Silberschatz, Henry F. Korth', 'Database System Concepts', '7th Edition', 'McGraw-Hill Education', 'Vol 1', 850.00, 4),
            ('978-0131103627', 'The C Programming Language', 'Brian W. Kernighan, Dennis M. Ritchie', 'The C Programming Language', '2nd Edition', 'Prentice Hall', 'Vol 1', 450.00, 3),
            ('978-0262033848', 'Introduction to Algorithms', 'Thomas H. Cormen, Charles E. Leiserson', 'Introduction to Algorithms (CLRS)', '3rd Edition', 'MIT Press', 'Vol 1', 1250.00, 2),
            ('978-0132126953', 'Computer Networks', 'Andrew S. Tanenbaum, David J. Wetherall', 'Computer Networks: A Systems Approach', '5th Edition', 'Pearson Education', 'Vol 1', 720.00, 5),
            ('978-1119456339', 'Operating System Concepts', 'Abraham Silberschatz, Peter B. Galvin', 'Operating System Concepts', '10th Edition', 'Wiley Publishing', 'Vol 1', 890.00, 3),
            ('978-0134610993', 'Artificial Intelligence: A Modern Approach', 'Stuart Russell, Peter Norvig', 'Artificial Intelligence: A Modern Approach', '4th Edition', 'Pearson Education', 'Vol 1', 1100.00, 2),
            ('978-9351072973', 'Fundamentals of Software Engineering', 'Rajib Mall', 'Fundamentals of Software Engineering', '5th Edition', 'Prentice Hall India', 'Vol 1', 595.00, 4),
            ('978-0199455324', 'Web Technologies', 'Uttam K. Roy', 'Web Technologies: HTML, JavaScript & PHP', '2nd Edition', 'Oxford University Press', 'Vol 1', 650.00, 3),
        ]
        cursor.executemany("""
            INSERT INTO BookDetails (ISBN, Bname, Author, Title, Edition, Publisher, Volume, Price, AvailableCopies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_books)

        # Seed Sample Issue Records (one active on-time, one active overdue for demonstration)
        today = date.today()
        # Active Issue 1: Fathima (Due in 5 days -> no overdue)
        issue_date_1 = (today - timedelta(days=9)).strftime("%Y-%m-%d")
        due_date_1 = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO IssueDate (ISBN, Title, Author, IssueDate, Regno, StudentName, Sem, Course_Branch, Duedate, IssuingStaffId, Status)
            VALUES ('978-0078022159', 'Database System Concepts', 'Abraham Silberschatz, Henry F. Korth', ?, '1IPEC2024CS01', 'Fathima Afroz', '6th', 'Computer Science & Engineering', ?, 'STAFF-LIB-01', 'ISSUED')
        """, (issue_date_1, due_date_1))

        # Active Issue 2: Rahul Sharma (Issued 20 days ago, due 6 days ago -> Overdue by 6 days: fine = 6 * 10 = Rs 60)
        issue_date_2 = (today - timedelta(days=20)).strftime("%Y-%m-%d")
        due_date_2 = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO IssueDate (ISBN, Title, Author, IssueDate, Regno, StudentName, Sem, Course_Branch, Duedate, IssuingStaffId, Status)
            VALUES ('978-0132126953', 'Computer Networks: A Systems Approach', 'Andrew S. Tanenbaum, David J. Wetherall', ?, '1IPEC2024IS02', 'Rahul Sharma', '4th', 'Information Science & Engineering', ?, 'STAFF-LIB-01', 'ISSUED')
        """, (issue_date_2, due_date_2))

        # Sample Past Return record for Ananya Hegde (Returned on time)
        past_issue = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        past_due = (today - timedelta(days=16)).strftime("%Y-%m-%d")
        past_return = (today - timedelta(days=18)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO ReturnData (ISBN, Title, Author, ReturnDate, Regno, StudentName, Sem, Course_Branch, Duedate, ReturningStaffId, DaysOverdue, FineAmount, PenaltyAmount)
            VALUES ('978-0262033848', 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen, Charles E. Leiserson', ?, '1IPEC2024AI03', 'Ananya Hegde', '6th', 'Artificial Intelligence & Data Science', ?, 'STAFF-LIB-01', 0, 0.0, 0.0)
        """, (past_return, past_due))

        conn.commit()

    conn.close()

if __name__ == '__main__':
    init_db()
    print(f"Database initialized successfully at: {DB_PATH}")
