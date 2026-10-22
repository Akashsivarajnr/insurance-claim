@echo off
setlocal enableextensions
title ClaimFlow launcher
cd /d "%~dp0"

echo ============================================
echo   ClaimFlow - Insurance Claim Processing
echo ============================================
echo.

rem ---- 1. Check prerequisites ----
set "PY="
python --version >nul 2>nul && set "PY=python"
if not defined PY (
    py -3 --version >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    echo [X] Python 3.10 or newer was not found.
    echo     Install it from https://www.python.org/downloads/
    echo     IMPORTANT: tick "Add python.exe to PATH" in the installer, then run this file again.
    pause
    exit /b 1
)
node --version >nul 2>nul
if errorlevel 1 (
    echo [X] Node.js was not found.
    echo     Install the LTS version from https://nodejs.org/ and run this file again.
    pause
    exit /b 1
)
call npm --version >nul 2>nul
if errorlevel 1 (
    echo [X] npm was not found. Re-install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Python and Node.js found.

rem ---- 2. Backend setup (nothing is overwritten or deleted) ----
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" (
    echo Creating Python virtual environment, please wait...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [X] Could not create the virtual environment.
        pause
        exit /b 1
    )
)
"venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, jose, bcrypt, multipart, pydantic_settings, email_validator" >nul 2>nul
if errorlevel 1 (
    echo Installing backend packages, this can take a few minutes the first time...
    "venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>nul
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [X] Backend package installation failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
)
if not exist ".env" (
    echo Creating backend\.env with a new random secret key...
    "venv\Scripts\python.exe" -c "import secrets,pathlib; s=pathlib.Path('.env.example').read_text(); pathlib.Path('.env').write_text(s.replace('replace-with-a-long-random-string', secrets.token_urlsafe(48)))"
) else (
    echo [OK] backend\.env already exists - leaving it unchanged.
)
echo [OK] Backend ready.

rem ---- 3. Frontend setup ----
cd /d "%~dp0frontend"
if not exist "node_modules\vite" (
    echo Installing frontend packages, this can take a few minutes the first time...
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo [X] Frontend package installation failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
)
echo [OK] Frontend ready.

rem ---- 4. Start both servers in their own windows ----
cd /d "%~dp0"
echo.
echo Starting backend  at http://localhost:8000  (API docs: http://localhost:8000/docs)
start "ClaimFlow Backend" /d "%~dp0backend" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
echo Starting frontend at http://localhost:5173
start "ClaimFlow Frontend" /d "%~dp0frontend" cmd /k "npm run dev"

echo.
echo ------------------------------------------------------------
echo  Two windows were opened (Backend and Frontend). Keep them open.
echo  Open your browser at:  http://localhost:5173
echo.
echo  First time? Create an administrator account. Open a NEW
echo  Command Prompt in the backend folder and run:
echo      venv\Scripts\activate
echo      python create_admin.py
echo  Optional demo data:  python seed_demo.py
echo ------------------------------------------------------------
timeout /t 8 >nul
start "" "http://localhost:5173"
endlocal
