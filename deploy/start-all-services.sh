#!/bin/bash
# ========================================================================
# Pandora Platform - Start All Services (đúng thứ tự)
# ========================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Starting Pandora Platform Services"
echo "========================================"

# Check root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root${NC}"
   exit 1
fi

# Start services theo thứ tự dependency
echo -e "${GREEN}[1/6] Starting User Backend API...${NC}"
systemctl start pandora-backend-user
sleep 2

echo -e "${GREEN}[2/6] Starting Admin Backend API...${NC}"
systemctl start pandora-backend-admin
sleep 2

echo -e "${GREEN}[3/6] Starting FastAPI Webserver...${NC}"
systemctl start pandora-webserver
sleep 2

echo -e "${GREEN}[4/6] Starting Nginx...${NC}"
systemctl start pandora-nginx
sleep 2

echo -e "${GREEN}[5/6] Starting IDS Engine...${NC}"
systemctl start pandora-ids
sleep 2

echo -e "${GREEN}[6/6] Starting Central Monitor...${NC}"
systemctl start pandora-central-monitor
sleep 2

echo ""
echo "========================================"
echo -e "${GREEN}All services started!${NC}"
echo "========================================"
echo ""

# Check status
echo "Service Status:"
systemctl status pandora-backend-user --no-pager -l | grep "Active:"
systemctl status pandora-backend-admin --no-pager -l | grep "Active:"
systemctl status pandora-webserver --no-pager -l | grep "Active:"
systemctl status pandora-nginx --no-pager -l | grep "Active:"
systemctl status pandora-ids --no-pager -l | grep "Active:"
systemctl status pandora-central-monitor --no-pager -l | grep "Active:"

echo ""
echo "To check logs:"
echo "  sudo journalctl -u pandora-nginx -f"
echo "  sudo journalctl -u pandora-webserver -f"
echo ""
echo "Access points:"
echo "  • Main App:  https://localhost"
echo "  • Monitor:   http://localhost:3000 (localhost only)"
echo ""

