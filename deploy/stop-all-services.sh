#!/bin/bash
# ========================================================================
# Pandora Platform - Stop All Services
# ========================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "========================================"
echo "Stopping Pandora Platform Services"
echo "========================================"

# Check root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root${NC}"
   exit 1
fi

# Stop services (ngược thứ tự start)
echo -e "${GREEN}[1/6] Stopping Central Monitor...${NC}"
systemctl stop pandora-central-monitor || true

echo -e "${GREEN}[2/6] Stopping IDS Engine...${NC}"
systemctl stop pandora-ids || true

echo -e "${GREEN}[3/6] Stopping Nginx...${NC}"
systemctl stop pandora-nginx || true

echo -e "${GREEN}[4/6] Stopping FastAPI Webserver...${NC}"
systemctl stop pandora-webserver || true

echo -e "${GREEN}[5/6] Stopping Admin Backend API...${NC}"
systemctl stop pandora-backend-admin || true

echo -e "${GREEN}[6/6] Stopping User Backend API...${NC}"
systemctl stop pandora-backend-user || true

echo ""
echo "========================================"
echo -e "${GREEN}All services stopped!${NC}"
echo "========================================"

