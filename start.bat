@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating the virtual environment...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 goto error
)
call ".venv\Scripts\activate.bat"
echo Installing or checking dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Starting Placement Intelligence at http://127.0.0.1:8000
start "Placement Intelligence" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto error
goto end
:error
echo.
echo Startup failed. Check the error above. You can also run: python -m pip install -r requirements.txt
pause
:end
endlocal
