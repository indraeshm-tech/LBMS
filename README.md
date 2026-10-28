# Library Management System (LBMS)
### Full-Fledged Interactive RDBMS Web Application
**Developed by Fathima Afroz, iPEC Solutions, Bangalore**  
**Theme:** Electric Kiwi (`#CCFF00`, `#FFFF00`, `#DEFF00`, `#000000`)

---

## 🌟 Project Overview

The **Library Management System (LBMS)** is an interactive, enterprise-grade Relational Database Management System (RDBMS) built with a **Python Flask** frontend and an **SQLite3** database backend. It comes pre-configured with a rich GUI featuring an Electric Kiwi aesthetic, dark glassmorphism surfaces, and live transactional workflows.

---

## 📑 Core Features

1. **Authentication Portal (Page 1)**:
   - **New User Sign-Up**: Stores User ID, hashed password, role (`Student` or `Staff`), registration number, department, semester, email, and phone directly into the SQLite database.
   - **Secure Login**: Verifies credentials against the `Users` database table to initiate a session and unlock the Main Dashboard.
   - Quick one-click test credentials for instant evaluation.

2. **Main Dashboard (3-Section Layout)**:
   - **Header Branding**: Centered title with top-left attribution *"Developed by Fathima Afroz, iPEC Solutions, Bangalore"*.
   - **Section 1 (Left Column - Circulation Desk)**:
     - **Dynamic Available Books Dropdown**: Instantly loads active inventory and displays a live book preview card (Title, Author, ISBN, Price, Stock).
     - **Issue Book Form**: Auto-populates book details upon dropdown selection, captures student details, calculates due dates, and deducts available stock.
     - **Return Book Form**: Allows selecting an active book loan, sets return dates, supports a *"Book Lost by Student"* toggle, and calculates fine/penalty previews live.
     - **Live Fine & Penalty Calculator Widget**: Interactive simulator to test overdue days and penalties with a transparent breakdown.
   - **Section 2 (Center Column - Catalog & Active Logs)**:
     - **KPI Overview Cards**: Total Titles, Available Copies, Active Loans, and Fines Collected.
     - **BookDetails Catalog**: Searchable inventory table with a modal form to add new books (`Bid, ISBN, Bname, Author, Title, Edition, Publisher, Volume, Price`).
     - **Active Issues Log (`IssueDate` Table)**: Displays real-time loan statuses with highlighted overdue badges.
     - **Audit Trail (`ReturnData` Table)**: Historical record of returned books, overdue days, and collected fees.
   - **Section 3 (Right Column - Identity & Clearance Engine)**:
     - **Smart Library Card Generator**: Generates an institutional ID card for the logged-in student with barcode, photo frame, loan limits, and a printable view (`/library_card`).
     - **Strict No-Due Certificate (NDC) Engine**: Checks SQLite database in real-time. If all books are returned and pending dues are ₹0, generates an official **No-Due Certificate** with official seals and serial numbers (`/no_due_certificate`). If dues exist, presents a clear blocker listing unreturned books and unpaid amounts.
     - **FineCalculation Panel**: Shows fine records with one-click payment clearance.

3. **Built-in Project ZIP Downloader**:
   - Includes a **"Download Project"** button in the top navigation bar (`/download_project`) that packages the entire codebase, database, templates, and static assets into `LBMS_Project_Fathima_Afroz.zip` for immediate download.

---

## 📐 RDBMS Schema Reference

The database `library_management_system.db` contains 5 relational tables:

| Table Name | Attributes / Columns | Description |
| :--- | :--- | :--- |
| **`Users`** | `UserId` (PK), `Password`, `Role`, `FullName`, `Regno`, `Branch`, `Sem`, `Email`, `Phone`, `CreatedAt` | Authentication & student profiles |
| **`BookDetails`** | `Bid` (PK AUTO), `ISBN` (UNIQUE), `Bname`, `Author`, `Title`, `Edition`, `Publisher`, `Volume`, `Price`, `AvailableCopies` | Master catalog of library books |
| **`IssueDate`** | `IssueId` (PK AUTO), `ISBN` (FK), `Title`, `Author`, `IssueDate`, `Regno`, `StudentName`, `Sem`, `Course_Branch`, `Duedate`, `IssuingStaffId`, `Status` | Active and historical book issues |
| **`ReturnData`** | `ReturnId` (PK AUTO), `ISBN`, `Title`, `Author`, `ReturnDate`, `Regno`, `StudentName`, `Sem`, `Course_Branch`, `Duedate`, `ReturningStaffId`, `DaysOverdue`, `FineAmount`, `PenaltyAmount` | Completed return transactions |
| **`FineCalculation`**| `FineId` (PK AUTO), `ISBN`, `Regno`, `StudentName`, `ReturnDate`, `IssueDate`, `Duration`, `Fine`, `Penality`, `Status` | Overdue fines & lost book penalties |

---

## 💰 Fine & Penalty Business Logic

1. **Overdue Fine**:
   - Returned on or before Due Date: **₹0**
   - **1 to 7 Days Overdue (Within a week)**: ₹10 per day.
   - **Exceeding 7 Days (Up to 1 month and beyond)**: ₹10/day for the first 7 days + ₹20/day for each day thereafter.
   - *Example: 10 days overdue = (7 × ₹10) + (3 × ₹20) = ₹70 + ₹60 = ₹130.*
2. **Lost Book Penalty**:
   - `Penalty = Original Book Price + Overdue Fine (if reported/returned past due date)`.

---

## 🚀 How to Run the Project

### Prerequisites
- Python 3.10 or higher installed on your system.

### Option A: One-Click Startup on Windows
Double-click `run.bat` located inside the project folder. It will:
1. Verify Python.
2. Initialize and seed `library_management_system.db`.
3. Launch Flask on `http://127.0.0.1:5000`.

### Option B: Terminal / Command Prompt
```bash
# 1. Navigate to the project directory
cd lbms_project

# 2. Install dependencies (Flask & Werkzeug)
pip install -r requirements.txt

# 3. Initialize and seed the SQLite database
python database.py

# 4. Start the Flask application
python app.py
```
Open your web browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Test Credentials Pre-Seeded in Database

| Role | User ID | Password | Name | Reg No / USN |
| :--- | :--- | :--- | :--- | :--- |
| **Student** | `fathima` | `fathima123` | Fathima Afroz | `1IPEC2024CS01` |
| **Staff** | `staff101` | `admin123` | Dr. Rajeshwari K. | `STAFF-LIB-01` |
| **Student** | `rahul` | `rahul123` | Rahul Sharma | `1IPEC2024IS02` |
| **Student** | `ananya` | `ananya123` | Ananya Hegde | `1IPEC2024AI03` |

*You can also click **"New User Sign Up"** at any time to create your own account.*

---

## 🗄️ Inspecting with "DB Browser for SQLite"

The database file `library_management_system.db` is a standard SQLite3 database fully compatible with **DB Browser for SQLite** (SQLite Database Browser):

1. **Download & Install**: Download DB Browser for SQLite from [https://sqlitebrowser.org/](https://sqlitebrowser.org/).
2. **Open Database**:
   - Launch DB Browser for SQLite.
   - Click **"Open Database"** (or press `Ctrl+O`).
   - Navigate to the `lbms_project` folder and select `library_management_system.db`.
3. **Database Structure**:
   - Under the **"Database Structure"** tab, you will see all 5 tables (`Users`, `BookDetails`, `IssueDate`, `ReturnData`, `FineCalculation`) along with their column definitions and primary keys.
4. **Browse Data**:
   - Click the **"Browse Data"** tab.
   - Select any table from the Table dropdown to inspect live records in real time.
5. **Execute SQL Queries**:
   - Switch to the **"Execute SQL"** tab to run custom queries, for example:
   ```sql
   -- View all books with prices and available stock
   SELECT ISBN, Title, Author, Price, AvailableCopies FROM BookDetails;

   -- Check active issues and overdue items
   SELECT IssueId, Title, StudentName, Duedate, Status FROM IssueDate WHERE Status = 'ISSUED';

   -- View all fines and settlement status
   SELECT * FROM FineCalculation;
   ```
