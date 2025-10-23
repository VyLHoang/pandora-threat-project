#!/bin/bash
# ========================================================================
# Pandora Platform - Install Systemd Services
# ========================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Pandora Platform - Service Installation"
echo "========================================"

# Check root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root${NC}"
   exit 1
fi

# Variables
INSTALL_DIR="/opt/pandora"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log/pandora"

# Create log directory
echo -e "${GREEN}[1/5] Creating log directory...${NC}"
mkdir -p "$LOG_DIR"
chown -R www-data:www-data "$LOG_DIR"
chmod 755 "$LOG_DIR"

# Create pandora user (if not exists)
echo -e "${GREEN}[2/5] Creating pandora user...${NC}"
if ! id -u pandora > /dev/null 2>&1; then
    useradd -r -s /bin/bash -d /opt/pandora -m pandora
    echo "[OK] User 'pandora' created"
else
    echo "[SKIP] User 'pandora' already exists"
fi

# Copy systemd service files
echo -e "${GREEN}[3/5] Installing systemd service files...${NC}"
cp systemd/pandora-webserver.service "$SYSTEMD_DIR/"
cp systemd/pandora-nginx.service "$SYSTEMD_DIR/"
cp systemd/pandora-backend-user.service "$SYSTEMD_DIR/"
cp systemd/pandora-backend-admin.service "$SYSTEMD_DIR/"
cp systemd/pandora-ids.service "$SYSTEMD_DIR/"
cp systemd/pandora-central-monitor.service "$SYSTEMD_DIR/"

# Set permissions
chmod 644 "$SYSTEMD_DIR"/pandora-*.service

echo "[OK] Service files installed"

# Reload systemd
echo -e "${GREEN}[4/5] Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo "[OK] Systemd reloaded"

# Enable services (không start, user tự start sau)
echo -e "${GREEN}[5/5] Enabling services...${NC}"
systemctl enable pandora-nginx.service
systemctl enable pandora-webserver.service
systemctl enable pandora-backend-user.service
systemctl enable pandora-backend-admin.service
systemctl enable pandora-ids.service
systemctl enable pandora-central-monitor.service

echo ""
echo "========================================"
echo -e "${GREEN}Installation completed!${NC}"
echo "========================================"
echo ""
echo "Services installed:"
echo "  • pandora-nginx           - Nginx reverse proxy (Port 80/443)"
echo "  • pandora-webserver       - FastAPI webserver (Port 8443)"
echo "  • pandora-backend-user    - User API (Port 8000)"
echo "  • pandora-backend-admin   - Admin API (Port 9000)"
echo "  • pandora-ids             - IDS Engine"
echo "  • pandora-central-monitor - Monitoring Dashboard (Port 3000)"
echo ""
echo "To start all services:"
echo "  sudo ./start-all-services.sh"
echo ""
echo "To start individually:"
echo "  sudo systemctl start pandora-nginx"
echo "  sudo systemctl start pandora-webserver"
echo "  sudo systemctl start pandora-backend-user"
echo "  sudo systemctl start pandora-backend-admin"
echo "  sudo systemctl start pandora-ids"
echo "  sudo systemctl start pandora-central-monitor"
echo ""
echo "To check status:"
echo "  sudo systemctl status pandora-*"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u pandora-nginx -f"
echo "  sudo journalctl -u pandora-webserver -f"
echo ""

