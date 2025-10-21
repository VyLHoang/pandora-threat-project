#!/bin/bash

echo "========================================"
echo "  PANDORA IDS - NETWORK MONITOR"
echo "========================================"
echo ""
echo "[WARNING] This requires root privileges"
echo "          to capture network packets"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Please run as root (sudo)"
    exit 1
fi

echo "[OK] Running with root privileges"
echo ""
echo "[STARTING] IDS Engine..."

cd "$(dirname "$0")"
python3 ids_engine.py

