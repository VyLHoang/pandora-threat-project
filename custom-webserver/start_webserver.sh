#!/bin/bash
# ========================================================================
# Pandora Webserver Startup Script (Linux)
# ========================================================================

cd "$(dirname "$0")"

echo "========================================"
echo "Pandora Custom Webserver Startup"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt

# Check if frontend is built
FRONTEND_DIST="../frontend/dist"
if [ ! -d "$FRONTEND_DIST" ]; then
    echo "[WARNING] Frontend not built!"
    echo "[INFO] Building frontend..."
    cd ../frontend
    npm install
    npm run build
    cd ../custom-webserver
fi

# Start webserver
echo "[INFO] Starting FastAPI webserver on port 8443..."
python webserver_fastapi.py

