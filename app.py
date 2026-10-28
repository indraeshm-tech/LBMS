"""
app.py - Main Flask Application for Library Management System (LBMS)
Developed by Fathima Afroz, iPEC Solutions, Bangalore
"""

import os
import io
import zipfile
from datetime import datetime, date, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import (
    get_db_connection, init_db, calculate_fine, calculate_penalty, DB_PATH
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'local-development-only-change-me'
if os.environ.get('VERCEL') and not os.environ.get('SECRET_KEY'):
    raise RuntimeError('Set SECRET_KEY in Vercel Project Settings > Environment Variables before deploying.')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=bool(os.environ.get('VERCEL'))
)

# Ensure database is initialized
init_db()

def get_current_user():
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM Users WHERE UserId = ?", (session['user_id'],)).fetchone()
        conn.close()
        return user
    return None

# ----------------- AUTH ROUTES ----------------- #

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'LBMS'})

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()

        if not user_id or not password:
            flash("Please enter both User ID and Password.", "danger")
            return redirect(url_for('login'))

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM Users WHERE UserId = ?", (user_id,)).fetchone()
        conn.close()

        if user and check_password_hash(user['Password'], password):
            session['user_id'] = user['UserId']
            session['role'] = user['Role']
            session['fullname'] = user['FullName']
            session['regno'] = user['Regno']
            session['branch'] = user['Branch']
            session['sem'] = user['Sem']
            flash(f"Welcome back, {user['FullName']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid User ID or Password. Please try again or Sign Up.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    user_id = request.form.get('user_id', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'Student').strip()
    regno = request.form.get('regno', '').strip()
    branch = request.form.get('branch', '').strip()
    sem = request.form.get('sem', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()

    if not user_id or not password or not full_name:
        flash("User ID, Password, and Full Name are mandatory.", "danger")
        return redirect(url_for('login', tab='signup'))

    conn = get_db_connection()
    existing = conn.execute("SELECT UserId FROM Users WHERE UserId = ?", (user_id,)).fetchone()
    if existing:
        conn.close()
        flash("User ID already exists! Please choose another ID or Log In.", "warning")
        return redirect(url_for('login', tab='signup'))

    hashed_pw = generate_password_hash(password)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO Users (UserId, Password, Role, FullName, Regno, Branch, Sem, Email, Phone, CreatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, hashed_pw, role, full_name, regno, branch, sem, email, phone, now_str))
    conn.commit()
    conn.close()

    flash("Registration successful! You can now log in with your credentials.", "success")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('login'))

# ----------------- MAIN DASHBOARD ----------------- #

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in to access the Library Management System.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Fetch books for dropdown and inventory table
    books = conn.execute("SELECT * FROM BookDetails ORDER BY Title ASC").fetchall()

    # Available books for dropdown
    available_books = [b for b in books if b['AvailableCopies'] > 0]

    # Fetch active issues
    active_issues = conn.execute("""
        SELECT * FROM IssueDate 
        WHERE Status = 'ISSUED' 
        ORDER BY IssueId DESC
    """).fetchall()

    # Fetch return history
    return_history = conn.execute("""
        SELECT * FROM ReturnData 
        ORDER BY ReturnId DESC 
        LIMIT 20
    """).fetchall()

    # Fetch fine records
    fines = conn.execute("""
        SELECT * FROM FineCalculation 
        ORDER BY FineId DESC 
        LIMIT 20
    """).fetchall()

    # KPI Statistics
    total_titles = conn.execute("SELECT COUNT(*) FROM BookDetails").fetchone()[0]
    total_copies = conn.execute("SELECT SUM(AvailableCopies) FROM BookDetails").fetchone()[0] or 0
    currently_issued = len(active_issues)
    total_fines_collected = conn.execute("SELECT SUM(FineAmount + PenaltyAmount) FROM ReturnData").fetchone()[0] or 0.0
    pending_fines = conn.execute("SELECT SUM(Fine + Penality) FROM FineCalculation WHERE Status = 'PENDING'").fetchone()[0] or 0.0

    # User's specific active issues and fines
    user_regno = session.get('regno', '')
    user_active_issues = []
    user_pending_fines = []
    if user_regno:
        user_active_issues = conn.execute(
            "SELECT * FROM IssueDate WHERE Regno = ? AND Status = 'ISSUED'", (user_regno,)
        ).fetchall()
        user_pending_fines = conn.execute(
            "SELECT * FROM FineCalculation WHERE Regno = ? AND Status = 'PENDING'", (user_regno,)
        ).fetchall()

    today_str = date.today().strftime("%Y-%m-%d")
    default_due_str = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")

    conn.close()

    return render_template(
        'index.html',
        books=books,
        available_books=available_books,
        active_issues=active_issues,
        return_history=return_history,
        fines=fines,
        total_titles=total_titles,
        total_copies=total_copies,
        currently_issued=currently_issued,
        total_fines_collected=total_fines_collected,
        pending_fines=pending_fines,
        user_active_issues=user_active_issues,
        user_pending_fines=user_pending_fines,
        today_str=today_str,
        default_due_str=default_due_str
    )

# ----------------- BOOK ACTIONS ----------------- #

@app.route('/add_book', methods=['POST'])
def add_book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    isbn = request.form.get('isbn', '').strip()
    bname = request.form.get('bname', '').strip()
    author = request.form.get('author', '').strip()
    title = request.form.get('title', '').strip() or bname
    edition = request.form.get('edition', '').strip()
    publisher = request.form.get('publisher', '').strip()
    volume = request.form.get('volume', '').strip()
    price = float(request.form.get('price', 0.0))
    copies = int(request.form.get('copies', 1))

    if not isbn or not bname or not author:
        flash("ISBN, Book Name, and Author are required.", "danger")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO BookDetails (ISBN, Bname, Author, Title, Edition, Publisher, Volume, Price, AvailableCopies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (isbn, bname, author, title, edition, publisher, volume, price, copies))
        conn.commit()
        flash(f"Book '{title}' successfully added to catalog!", "success")
    except Exception as e:
        flash(f"Error adding book: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('dashboard'))

@app.route('/issue_book', methods=['POST'])
def issue_book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    isbn = request.form.get('isbn', '').strip()
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    regno = request.form.get('regno', '').strip()
    student_name = request.form.get('student_name', '').strip()
    sem = request.form.get('sem', '').strip()
    course_branch = request.form.get('course_branch', '').strip()
    issue_date = request.form.get('issue_date', '').strip() or date.today().strftime("%Y-%m-%d")
    due_date = request.form.get('due_date', '').strip()
    issuing_staff_id = request.form.get('issuing_staff_id', session.get('user_id', 'STAFF-LIB-01')).strip()

    if not isbn or not regno or not due_date:
        flash("ISBN, Student Reg No, and Due Date are required to issue a book.", "danger")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    book = conn.execute("SELECT * FROM BookDetails WHERE ISBN = ?", (isbn,)).fetchone()
    if not book:
        conn.close()
        flash("Selected book not found in database.", "danger")
        return redirect(url_for('dashboard'))

    if book['AvailableCopies'] < 1:
        conn.close()
        flash(f"No copies available for '{book['Title']}' right now.", "warning")
        return redirect(url_for('dashboard'))

    # Insert into IssueDate table
    conn.execute("""
        INSERT INTO IssueDate (ISBN, Title, Author, IssueDate, Regno, StudentName, Sem, Course_Branch, Duedate, IssuingStaffId, Status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ISSUED')
    """, (isbn, title or book['Title'], author or book['Author'], issue_date, regno, student_name, sem, course_branch, due_date, issuing_staff_id))

    # Decrement available copies
    conn.execute("UPDATE BookDetails SET AvailableCopies = AvailableCopies - 1 WHERE ISBN = ?", (isbn,))
    conn.commit()
    conn.close()

    flash(f"Book '{title or book['Title']}' successfully issued to {student_name} ({regno}).", "success")
    return redirect(url_for('dashboard'))

@app.route('/return_book', methods=['POST'])
def return_book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    issue_id = request.form.get('issue_id')
    return_date = request.form.get('return_date', '').strip() or date.today().strftime("%Y-%m-%d")
    returning_staff_id = request.form.get('returning_staff_id', session.get('user_id', 'STAFF-LIB-01')).strip()
    is_lost = bool(request.form.get('is_lost'))

    if not issue_id:
        flash("Please select an active issue record to process return.", "danger")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    issue = conn.execute("SELECT * FROM IssueDate WHERE IssueId = ?", (issue_id,)).fetchone()
    if not issue:
        conn.close()
        flash("Issue record not found.", "danger")
        return redirect(url_for('dashboard'))

    book = conn.execute("SELECT * FROM BookDetails WHERE ISBN = ?", (issue['ISBN'],)).fetchone()
    book_price = book['Price'] if book else 500.0

    days_overdue, fine = calculate_fine(issue['Duedate'], return_date)
    penalty = calculate_penalty(book_price, issue['Duedate'], return_date, is_lost=is_lost)

    # Calculate duration
    try:
        i_date = datetime.strptime(issue['IssueDate'], "%Y-%m-%d").date()
        r_date = datetime.strptime(return_date, "%Y-%m-%d").date()
        duration = (r_date - i_date).days
    except Exception:
        duration = 0

    new_status = 'LOST' if is_lost else 'RETURNED'

    # Update IssueDate record
    conn.execute("UPDATE IssueDate SET Status = ? WHERE IssueId = ?", (new_status, issue_id))

    # Insert into ReturnData table
    conn.execute("""
        INSERT INTO ReturnData (ISBN, Title, Author, ReturnDate, Regno, StudentName, Sem, Course_Branch, Duedate, ReturningStaffId, DaysOverdue, FineAmount, PenaltyAmount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (issue['ISBN'], issue['Title'], issue['Author'], return_date, issue['Regno'], issue['StudentName'], issue['Sem'], issue['Course_Branch'], issue['Duedate'], returning_staff_id, days_overdue, fine, penalty))

    # If there is a fine or penalty, record in FineCalculation table
    if fine > 0 or penalty > 0:
        conn.execute("""
            INSERT INTO FineCalculation (ISBN, Regno, StudentName, ReturnDate, IssueDate, Duration, Fine, Penality, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (issue['ISBN'], issue['Regno'], issue['StudentName'], return_date, issue['IssueDate'], duration, fine, penalty))

    # If returned safely, restore available copy
    if not is_lost:
        conn.execute("UPDATE BookDetails SET AvailableCopies = AvailableCopies + 1 WHERE ISBN = ?", (issue['ISBN'],))

    conn.commit()
    conn.close()

    if is_lost:
        flash(f"Book '{issue['Title']}' marked as LOST. Penalty of ₹{penalty:.2f} (Book Price: ₹{book_price:.2f} + Overdue Fine: ₹{fine:.2f}) recorded.", "warning")
    elif fine > 0:
        flash(f"Book '{issue['Title']}' returned. Overdue by {days_overdue} days. Fine of ₹{fine:.2f} recorded.", "warning")
    else:
        flash(f"Book '{issue['Title']}' returned safely with zero dues! Thank you.", "success")

    return redirect(url_for('dashboard'))

@app.route('/pay_fine/<int:fine_id>', methods=['POST'])
def pay_fine(fine_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    fine = conn.execute("SELECT * FROM FineCalculation WHERE FineId = ?", (fine_id,)).fetchone()
    if fine:
        conn.execute("UPDATE FineCalculation SET Status = 'PAID' WHERE FineId = ?", (fine_id,))
        conn.commit()
        flash(f"Fine #FINE-{fine_id} for student {fine['StudentName']} marked as PAID & CLEARED!", "success")
    conn.close()
    return redirect(url_for('dashboard'))

# ----------------- REST APIS FOR GUI COMPONENTS ----------------- #

@app.route('/api/book/<isbn>')
def api_get_book(isbn):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM BookDetails WHERE ISBN = ?", (isbn,)).fetchone()
    conn.close()
    if book:
        return jsonify({
            'success': True,
            'book': {
                'Bid': book['Bid'],
                'ISBN': book['ISBN'],
                'Bname': book['Bname'],
                'Author': book['Author'],
                'Title': book['Title'],
                'Edition': book['Edition'],
                'Publisher': book['Publisher'],
                'Volume': book['Volume'],
                'Price': book['Price'],
                'AvailableCopies': book['AvailableCopies']
            }
        })
    return jsonify({'success': False, 'message': 'Book not found'}), 404

@app.route('/api/calculate_fine', methods=['POST'])
def api_calculate_fine():
    data = request.get_json() or {}
    due_date = data.get('due_date', '')
    return_date = data.get('return_date', date.today().strftime("%Y-%m-%d"))
    price = float(data.get('price', 0.0))
    is_lost = bool(data.get('is_lost', False))

    days_overdue, fine = calculate_fine(due_date, return_date)
    penalty = calculate_penalty(price, due_date, return_date, is_lost=is_lost)

    breakdown = []
    if days_overdue <= 0:
        breakdown.append("No overdue (Returned on or before due date). Fine: ₹0.")
    elif days_overdue <= 7:
        breakdown.append(f"{days_overdue} days overdue within 1 week @ ₹10/day = ₹{fine:.2f}.")
    else:
        week1 = 7 * 10
        rem_days = days_overdue - 7
        rem_amount = rem_days * 20
        breakdown.append(f"First 7 days @ ₹10/day = ₹{week1:.2f}")
        breakdown.append(f"Remaining {rem_days} days @ ₹20/day = ₹{rem_amount:.2f}")
        breakdown.append(f"Total Overdue Fine = ₹{fine:.2f}")

    if is_lost:
        breakdown.append(f"Lost Book Penalty = Book Price (₹{price:.2f}) + Overdue Fine (₹{fine:.2f}) = ₹{penalty:.2f}")

    return jsonify({
        'days_overdue': days_overdue,
        'fine': fine,
        'penalty': penalty,
        'total_payable': fine if not is_lost else penalty,
        'breakdown': breakdown
    })

# ----------------- DOCUMENTS & CERTIFICATES ----------------- #

@app.route('/library_card')
def library_card():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_current_user()
    if not user:
        flash("User record not found.", "danger")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    active_loans = conn.execute(
        "SELECT COUNT(*) FROM IssueDate WHERE Regno = ? AND Status = 'ISSUED'", (user['Regno'],)
    ).fetchone()[0]
    conn.close()

    card_data = {
        'card_no': f"LIB-CARD-{user['UserId'].upper()}-2024",
        'name': user['FullName'],
        'regno': user['Regno'] or 'N/A',
        'branch': user['Branch'] or 'General Studies',
        'sem': user['Sem'] or 'N/A',
        'role': user['Role'],
        'email': user['Email'] or 'N/A',
        'phone': user['Phone'] or 'N/A',
        'issue_limit': 4 if user['Role'] == 'Student' else 10,
        'active_loans': active_loans,
        'issued_date': date.today().strftime("%d %b %Y"),
        'valid_till': (date.today() + timedelta(days=365)).strftime("%d %b %Y")
    }

    return render_template('library_card.html', card=card_data)

@app.route('/no_due_certificate')
def no_due_certificate():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_current_user()
    if not user:
        flash("User record not found.", "danger")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()

    # Query 1: Active unreturned books
    active_issues = conn.execute(
        "SELECT * FROM IssueDate WHERE Regno = ? AND Status = 'ISSUED'", (user['Regno'],)
    ).fetchall()

    # Query 2: Pending fines / penalties
    pending_fines = conn.execute(
        "SELECT * FROM FineCalculation WHERE Regno = ? AND Status = 'PENDING'", (user['Regno'],)
    ).fetchall()

    conn.close()

    total_pending_amount = sum(f['Fine'] + f['Penality'] for f in pending_fines)

    # Check eligibility
    is_eligible = (len(active_issues) == 0) and (total_pending_amount == 0)

    cert_data = {
        'cert_no': f"NDC-IPEC-{datetime.now().strftime('%Y%m')}-{user['UserId'].upper()}",
        'name': user['FullName'],
        'regno': user['Regno'] or 'N/A',
        'branch': user['Branch'] or 'Engineering',
        'sem': user['Sem'] or 'Final',
        'email': user['Email'] or 'N/A',
        'issue_date': datetime.now().strftime("%d %B %Y"),
        'authority': "Chief Librarian & Verification Officer",
        'institution': "iPEC Solutions Resource & Research Center, Bangalore"
    }

    return render_template(
        'no_due_certificate.html',
        is_eligible=is_eligible,
        user=user,
        cert=cert_data,
        active_issues=active_issues,
        pending_fines=pending_fines,
        total_pending_amount=total_pending_amount
    )

# ----------------- DOWNLOAD PROJECT ZIP ----------------- #

@app.route('/download_project')
def download_project():
    """Packages the entire project into a clean downloadable ZIP archive."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(project_dir):
            # Exclude cache or virtualenv directories if any
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.vscode', 'venv', 'env')]
            for file in files:
                if file.endswith('.pyc') or file.endswith('.tmp'):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                zip_file.write(file_path, arcname=os.path.join("LBMS_Project_Fathima_Afroz", rel_path))

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='LBMS_Project_Fathima_Afroz.zip'
    )

if __name__ == '__main__':
    print("=" * 70)
    print("   LIBRARY MANAGEMENT SYSTEM - LBMS (FLASK + SQLITE RDBMS)")
    print("   Developed by Fathima Afroz, iPEC Solutions, Bangalore")
    print("=" * 70)
    print("   App running at: http://127.0.0.1:5000")
    print("   Database File: library_management_system.db")
    print("   Electric Kiwi Palette: #CCFF00, #FFFF00, #DEFF00, #000000")
    print("=" * 70)
    app.run(debug=True, port=5000)
