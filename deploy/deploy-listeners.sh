#!/bin/bash
##############################################################################
# Pandora Threat Intelligence Platform
# Deploy HTTP/HTTPS Listeners (Port 80 & 443)
# 
# This script deploys honeypot web servers on port 80 and 443
##############################################################################

set -e  # Exit on error

echo "=========================================================================="
echo "   PANDORA - Deploy HTTP/HTTPS Honeypot Listeners"
echo "=========================================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="/home/pandora/projects/pandora-threat-project"
SYSTEMD_DIR="/etc/systemd/system"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR]${NC} This script must be run as root (needed for port 80/443)"
   echo "Run: sudo bash deploy-listeners.sh"
   exit 1
fi

echo -e "${GREEN}[1/8]${NC} Checking Python dependencies..."
pip3 install -q requests psycopg2-binary redis elasticsearch || {
    echo -e "${RED}[ERROR]${NC} Failed to install Python dependencies"
    exit 1
}

echo -e "${GREEN}[2/8]${NC} Checking SSL certificates..."
if [ ! -f "$PROJECT_DIR/custom-webserver/server.crt" ] || [ ! -f "$PROJECT_DIR/custom-webserver/server.key" ]; then
    echo -e "${YELLOW}[WARNING]${NC} SSL certificates not found. Generating self-signed certificate..."
    cd "$PROJECT_DIR/custom-webserver"
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout server.key -out server.crt -days 365 \
        -subj "/C=US/ST=State/L=City/O=Pandora/OU=Security/CN=172.235.245.60"
    echo -e "${GREEN}[OK]${NC} Self-signed certificate generated"
else
    echo -e "${GREEN}[OK]${NC} SSL certificates found"
fi

echo -e "${GREEN}[3/8]${NC} Copying systemd service files..."
cp "$PROJECT_DIR/deploy/systemd/pandora-http-80.service" "$SYSTEMD_DIR/"
cp "$PROJECT_DIR/deploy/systemd/pandora-https-443.service" "$SYSTEMD_DIR/"
chmod 644 "$SYSTEMD_DIR/pandora-http-80.service"
chmod 644 "$SYSTEMD_DIR/pandora-https-443.service"

echo -e "${GREEN}[4/8]${NC} Reloading systemd daemon..."
systemctl daemon-reload

echo -e "${GREEN}[5/8]${NC} Enabling services (auto-start on boot)..."
systemctl enable pandora-http-80.service
systemctl enable pandora-https-443.service

echo -e "${GREEN}[6/8]${NC} Stopping old services (if running)..."
systemctl stop pandora-http-80.service 2>/dev/null || true
systemctl stop pandora-https-443.service 2>/dev/null || true

echo -e "${GREEN}[7/8]${NC} Starting HTTP/HTTPS listeners..."
systemctl start pandora-http-80.service
systemctl start pandora-https-443.service

echo -e "${GREEN}[8/8]${NC} Verifying services status..."
sleep 2

echo ""
echo "=========================================================================="
echo "   SERVICE STATUS"
echo "=========================================================================="

# Check HTTP (Port 80)
if systemctl is-active --quiet pandora-http-80.service; then
    echo -e "${GREEN}✓ HTTP Server (Port 80)${NC} - RUNNING"
else
    echo -e "${RED}✗ HTTP Server (Port 80)${NC} - FAILED"
    echo "  Check logs: sudo journalctl -u pandora-http-80.service -n 50"
fi

# Check HTTPS (Port 443)
if systemctl is-active --quiet pandora-https-443.service; then
    echo -e "${GREEN}✓ HTTPS Server (Port 443)${NC} - RUNNING"
else
    echo -e "${RED}✗ HTTPS Server (Port 443)${NC} - FAILED"
    echo "  Check logs: sudo journalctl -u pandora-https-443.service -n 50"
fi

echo ""
echo "=========================================================================="
echo "   HONEYPOT LISTENERS DEPLOYED"
echo "=========================================================================="
echo ""
echo "Access from outside:"
echo "  • HTTP:  http://172.235.245.60"
echo "  • HTTPS: https://172.235.245.60"
echo ""
echo "Local test:"
echo "  • curl http://localhost"
echo "  • curl -k https://localhost"
echo ""
echo "View logs:"
echo "  • HTTP:  sudo journalctl -u pandora-http-80.service -f"
echo "  • HTTPS: sudo journalctl -u pandora-https-443.service -f"
echo ""
echo "Control services:"
echo "  • Start:   sudo systemctl start pandora-http-80.service"
echo "  • Stop:    sudo systemctl stop pandora-http-80.service"
echo "  • Restart: sudo systemctl restart pandora-http-80.service"
echo "  • Status:  sudo systemctl status pandora-http-80.service"
echo ""
echo "=========================================================================="
echo -e "${GREEN}✓ DEPLOYMENT COMPLETE!${NC}"
echo "=========================================================================="

