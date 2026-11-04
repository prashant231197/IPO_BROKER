# ==============================================================================
# IPO Radar Intelligence — Windows Setup Script (PowerShell)
# ==============================================================================

Write-Host "=== 1. Checking Python Installation ===" -ForegroundColor Cyan
py -3.13 --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.13 not found via 'py -3.13'. Trying 'python'..." -ForegroundColor Yellow
    python --version
}

Write-Host "=== 2. Installing Dependencies ===" -ForegroundColor Cyan
py -3.13 -m pip install --upgrade pip
py -3.13 -m pip install -r requirements-termux.txt
py -3.13 -m pip install -r backend/requirements.txt

Write-Host "=== 3. Initializing Local Database ===" -ForegroundColor Cyan
py -3.13 -c "import sys; sys.path.insert(0, 'backend'); from app.db import init_db; init_db(); print('SQLite Database initialized successfully!')"

Write-Host "=== Setup Complete! ===" -ForegroundColor Green
Write-Host "Run '.\scripts\start_windows.ps1' to launch the platform." -ForegroundColor Green

