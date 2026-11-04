#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# IPO Radar Intelligence — Termux Startup Script
# Starts FastAPI backend (port 8000) and Streamlit Research Terminal (port 8501)
# ==============================================================================

set -e

# Activate virtual environment if present
if [ -d ".venv_termux" ]; then
    source .venv_termux/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export HOST="127.0.0.1"
export API_PORT="8000"
export STREAMLIT_PORT="8501"
export DATABASE_URL="sqlite:///backend/rhp.db"
export DEPLOYMENT_MODE="lightweight"
export API_BASE_URL="http://127.0.0.1:8000/api"

echo "=========================================================="
echo "🎯 Starting IPO Radar Research Intelligence on Android Termux"
echo "=========================================================="

# Start FastAPI backend in background
echo "-> Launching FastAPI Backend on http://${HOST}:${API_PORT}..."
python -m uvicorn backend.app.main:app --host ${HOST} --port ${API_PORT} &
BACKEND_PID=$!

sleep 2

# Trap signals to kill background backend on exit
trap "echo 'Stopping servers...'; kill $BACKEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM EXIT

# Start Streamlit Research Dashboard
echo "-> Launching Streamlit Research Terminal on http://${HOST}:${STREAMLIT_PORT}..."
echo "-> Open your mobile browser and navigate to: http://${HOST}:${STREAMLIT_PORT}"
echo "=========================================================="

python -m streamlit run frontend/streamlit_app.py --server.address ${HOST} --server.port ${STREAMLIT_PORT} --server.headless true

