#!/bin/bash

# Fix Issues Script for Pandora Option C Architecture
# Run this on Central Monitor Server

echo "========================================"
echo "🔧 FIXING PANDORA ISSUES"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service status
check_service() {
    local service_name=$1
    if systemctl is-active --quiet $service_name; then
        echo -e "${GREEN}✓${NC} $service_name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name is not running"
        return 1
    fi
}

# Function to restart service
restart_service() {
    local service_name=$1
    echo -e "${YELLOW}Restarting $service_name...${NC}"
    sudo systemctl restart $service_name
    sleep 2
    if check_service $service_name; then
        echo -e "${GREEN}✓${NC} $service_name restarted successfully"
    else
        echo -e "${RED}✗${NC} Failed to restart $service_name"
    fi
}

echo ""
echo "1. Checking service status..."
echo "================================"

# Check all services
services=("pandora-backend-user" "pandora-backend-admin" "pandora-central-monitor" "pandora-ids" "nginx" "postgresql" "redis")

for service in "${services[@]}"; do
    check_service $service
done

echo ""
echo "2. Fixing database connections..."
echo "================================"

# Update backend-admin config
echo "Updating backend-admin config..."
sudo sed -i 's/localhost:5434/localhost/g' /opt/pandora/backend-admin/config.py
sudo sed -i 's/localhost:5433/localhost/g' /opt/pandora/backend-admin/config.py
sudo sed -i 's/localhost:6381/localhost:6379/g' /opt/pandora/backend-admin/config.py

# Update backend-user config
echo "Updating backend-user config..."
sudo sed -i 's/localhost:27009\/api\/logs/https:\/\/172.232.246.68\/api\/admin\/honeypot\/log/g' /opt/pandora/backend-user/config.py

echo ""
echo "3. Setting environment variables..."
echo "================================"

# Set API keys in systemd services
API_KEY="pandora-secret-key-2024"

# Backend-user service
sudo sed -i "s/change-this-api-key-in-production/$API_KEY/g" /etc/systemd/system/pandora-backend-user.service
sudo sed -i "s/https:\/\/localhost\/api\/admin\/honeypot\/log/https:\/\/172.232.246.68\/api\/admin\/honeypot\/log/g" /etc/systemd/system/pandora-backend-user.service

# Backend-admin service
sudo sed -i "s/change-this-api-key-in-production/$API_KEY/g" /etc/systemd/system/pandora-backend-admin.service

# Honeypot service (if exists)
if [ -f "/etc/systemd/system/pandora-honeypot.service" ]; then
    sudo sed -i "s/your-secret-api-key/$API_KEY/g" /etc/systemd/system/pandora-honeypot.service
    sudo sed -i "s/https:\/\/your-central-server.com/https:\/\/172.232.246.68/g" /etc/systemd/system/pandora-honeypot.service
fi

echo ""
echo "4. Reloading systemd and restarting services..."
echo "================================"

sudo systemctl daemon-reload

# Restart services in order
restart_service "postgresql"
restart_service "redis"
restart_service "pandora-backend-user"
restart_service "pandora-backend-admin"
restart_service "pandora-central-monitor"
restart_service "pandora-ids"
restart_service "nginx"

echo ""
echo "5. Testing connections..."
echo "================================"

# Test database connections
echo "Testing database connections..."
sudo -u postgres psql -c "SELECT 1;" pandora_user > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} User database connection OK"
else
    echo -e "${RED}✗${NC} User database connection failed"
fi

sudo -u postgres psql -c "SELECT 1;" pandora_admin > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Admin database connection OK"
else
    echo -e "${RED}✗${NC} Admin database connection failed"
fi

# Test API endpoints
echo "Testing API endpoints..."
curl -s http://localhost:8001/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Backend-user API (8001) OK"
else
    echo -e "${RED}✗${NC} Backend-user API (8001) failed"
fi

curl -s http://localhost:8002/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Backend-admin API (8002) OK"
else
    echo -e "${RED}✗${NC} Backend-admin API (8002) failed"
fi

curl -s http://localhost:5000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Central Monitor (5000) OK"
else
    echo -e "${RED}✗${NC} Central Monitor (5000) failed"
fi

echo ""
echo "6. Checking logs for errors..."
echo "================================"

# Check recent errors
echo "Recent errors in services:"
for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "--- $service ---"
        sudo journalctl -u $service --since "5 minutes ago" | grep -i error | tail -3
    fi
done

echo ""
echo "========================================"
echo -e "${GREEN}✅ FIX COMPLETE${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Test Central Monitor: https://172.232.246.68/"
echo "2. Test Admin Dashboard: https://172.232.246.68/admin-dashboard/"
echo "3. Test Honeypot: https://172.235.245.60/"
echo "4. Check logs: sudo journalctl -u pandora-* -f"
echo ""
echo "If issues persist, check:"
echo "- Database passwords in systemd services"
echo "- Firewall rules (ports 80, 443, 8001, 8002, 5000)"
echo "- SSL certificates in /etc/nginx/ssl/"
echo ""
