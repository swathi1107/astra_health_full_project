@echo off
echo Stopping ASTRA HEALTH server on port 8000...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /PID %%P /T /F >nul 2>nul
echo Stop command completed.
pause
