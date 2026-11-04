#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# IPO Radar Intelligence — Automated Android Termux Setup Script
# ==============================================================================

set -e

echo "=== 1. Checking Environment ==="
if [ -z "$TERMUX_VERSION" ] && [ ! -d "/data/data/com.termux" ]; then
    echo "Warning: Not running inside standard Android Termux. Proceeding with local setup..."
fi

echo "=== 2. Updating Termux Packages ==="
pkg update -y || apt-get update -y
pkg install -y python clang libjpeg-turbo libpng build-essential git || true

echo "=== 3. Creating Virtual Environment ==="
python -m venv .venv_termux || python -m venv .venv
source .venv_termux/bin/activate 2>/dev/null || source .venv/bin/activate

echo "=== 4. Installing Lightweight Dependencies ==="
pip install --upgrade pip setuptools wheel
pip install -r requirements-termux.txt

echo "=== 5. Initializing Local SQLite Database ==="
export DATABASE_URL="sqlite:///backend/rhp.db"
export DEPLOYMENT_MODE="lightweight"
python -c "import sys; sys.path.insert(0, 'backend'); from app.db import init_db; init_db(); print('SQLite Database initialized successfully!')"

echo "=== 6. Setup Complete! ==="
echo "To start the application, run:"
echo "  bash scripts/start_termux.sh"
echo "=============================================================================="

