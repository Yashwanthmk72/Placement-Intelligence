$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Write-Host "Starting Placement Intelligence at http://127.0.0.1:8000" -ForegroundColor Green
Start-Process 'http://127.0.0.1:8000'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
