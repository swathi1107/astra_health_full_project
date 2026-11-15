@echo off
setlocal
cd /d "%~dp0"
title ASTRA HEALTH
echo ==========================================
echo          ASTRA HEALTH STARTUP
echo ==========================================
where python >nul 2>nul
if errorlevel 1 (echo Python 3.10+ is required. Install from python.org and enable Add to PATH.& pause& exit /b 1)
if not exist ".venv\Scripts\python.exe" (
 echo Creating virtual environment...
 python -m venv .venv
 if errorlevel 1 (echo Failed to create virtual environment.& pause& exit /b 1)
)
call ".venv\Scripts\activate.bat"
echo Installing or verifying dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed.& pause& exit /b 1)
if not exist ".env" (
 copy ".env.example" ".env" >nul
 echo Created .env using SQLite demo mode.
)
for /f "usebackq tokens=1,* delims==" %%A in (".env") do if "%%A"=="DATABASE_URL" set DATABASE_URL=%%B
echo Checking database and preparing demo accounts...
python scripts\seed_demo.py
if errorlevel 1 (echo Database setup failed. Check .env and MySQL service if configured.& pause& exit /b 1)
echo Starting FastAPI...
start "ASTRA HEALTH SERVER" /min cmd /c ""%CD%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo Waiting for server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='http://127.0.0.1:8000/health'; for($i=0;$i -lt 40;$i++){try{$r=Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2;if($r.StatusCode -eq 200){Start-Process 'http://127.0.0.1:8000';exit 0}}catch{};Start-Sleep -Seconds 1};exit 1"
if errorlevel 1 (echo Server did not become ready. Check port 8000 and database settings.& pause& exit /b 1)
echo ASTRA HEALTH is running at http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo Keep the server window open. Use STOP_ASTRA_HEALTH.bat to stop.
pause
