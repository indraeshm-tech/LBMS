@echo off
title Library Management System (LBMS) - Fathima Afroz
echo =====================================================================
echo    LIBRARY MANAGEMENT SYSTEM (LBMS) - FLASK ^& SQLITE RDBMS
echo    Developed by Fathima Afroz, iPEC Solutions, Bangalore
echo =====================================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from python.org and add to PATH.
    pause
    exit /b 1
)

echo [2/3] Initializing SQLite database...
python database.py

echo [3/3] Launching Flask Application on http://127.0.0.1:5000 ...
echo.
echo Press Ctrl+C in this window to stop the server.
echo =====================================================================
python app.py
pause
