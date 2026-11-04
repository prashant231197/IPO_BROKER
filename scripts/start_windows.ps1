# ==============================================================================
# IPO Radar Intelligence — Windows Startup Script (PowerShell)
# Launches FastAPI Backend (8000) and Streamlit Research Terminal (8501)
# ==============================================================================

$env:HOST = "127.0.0.1"
$env:API_PORT = "8000"
$env:STREAMLIT_PORT = "8501"
$env:DATABASE_URL = "sqlite:///backend/rhp.db"
$env:DEPLOYMENT_MODE = "lightweight"
$env:API_BASE_URL = "http://127.0.0.1:8000/api"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🎯 Starting IPO Radar Research Intelligence on Windows" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Start FastAPI backend in background process
Write-Host "-> Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "py" -ArgumentList "-3.13 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000" -PassThru

Start-Sleep -Seconds 2

try {
    Write-Host "-> Launching Streamlit Research Terminal on http://127.0.0.1:8501..." -ForegroundColor Green
    Write-Host "-> Open browser at: http://127.0.0.1:8501" -ForegroundColor Green
    py -3.13 -m streamlit run frontend/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
}
finally {
    Write-Host "Shutting down backend process..." -ForegroundColor Yellow
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
}

