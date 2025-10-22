#!/bin/bash
##############################################################################
# Pandora Threat Intelligence Platform
# MASTER DEPLOYMENT SCRIPT - Deploy ALL Services
# 
# Server: 172.235.245.60
# User: pandora
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/pandora/projects/pandora-threat-project"
SYSTEMD_DIR="/etc/systemd/system"
CURRENT_USER=$(whoami)

echo ""
echo "========================================================================"
echo "   ____                 _                  "
echo "  |  _ \ __ _ _ __   __| | ___  _ __ __ _ "
echo "  | |_) / _\` | '_ \ / _\` |/ _ \| '__/ _\` |"
echo "  |  __/ (_| | | | | (_| | (_) | | | (_| |"
echo "  |_|   \__,_|_| |_|\__,_|\___/|_|  \__,_|"
echo ""
echo "  Threat Intelligence Platform - Full Deployment"
echo "========================================================================"
echo ""
echo -e "${CYAN}Server:${NC} 172.235.245.60"
echo -e "${CYAN}Date:${NC} $(date)"
echo -e "${CYAN}User:${NC} $CURRENT_USER"
echo ""
echo "========================================================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR]${NC} This script must be run as root"
   echo "Usage: sudo bash deploy-all.sh"
   exit 1
fi

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Project directory not found: $PROJECT_DIR"
    echo "Please clone the repository first:"
    echo "  cd ~/projects"
    echo "  git clone https://github.com/VyLHoang/pandora-threat-project.git"
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  PHASE 1: System Preparation${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${GREEN}[1/5]${NC} Updating system packages..."
apt update -qq

echo -e "${GREEN}[2/5]${NC} Installing system dependencies..."
apt install -y python3 python3-pip python3-venv curl wget git htop net-tools >/dev/null 2>&1

echo -e "${GREEN}[3/5]${NC} Installing Python packages..."
pip3 install --break-system-packages -q --upgrade pip
pip3 install --break-system-packages -q fastapi uvicorn sqlalchemy psycopg2-binary redis elasticsearch \
    python-jose passlib bcrypt python-multipart aiofiles pydantic-settings \
    scapy geoip2 requests flask || {
    echo -e "${RED}[ERROR]${NC} Failed to install Python dependencies"
    exit 1
}

echo -e "${GREEN}[4/5]${NC} Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker pandora
    echo -e "${GREEN}[OK]${NC} Docker installed"
else
    echo -e "${GREEN}[OK]${NC} Docker already installed"
fi

echo -e "${GREEN}[5/5]${NC} Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} Docker Compose not found. Installing..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}[OK]${NC} Docker Compose installed"
else
    echo -e "${GREEN}[OK]${NC} Docker Compose already installed"
fi

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  PHASE 2: Database Services${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${GREEN}[1/4]${NC} Starting shared databases (PostgreSQL, Redis, Elasticsearch, Kibana)..."
cd "$PROJECT_DIR/database"
docker-compose down 2>/dev/null || true
docker-compose up -d

echo -e "${GREEN}[2/4]${NC} Starting admin databases..."
cd "$PROJECT_DIR/backend-admin"
docker-compose down 2>/dev/null || true
docker-compose up -d

echo -e "${GREEN}[3/4]${NC} Starting user databases..."
cd "$PROJECT_DIR/backend-user"
docker-compose down 2>/dev/null || true
docker-compose up -d

echo -e "${GREEN}[4/4]${NC} Waiting for databases to be ready..."
sleep 30
echo -e "${GREEN}[OK]${NC} Database services started"

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  PHASE 3: SSL Certificates${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${GREEN}[1/1]${NC} Checking SSL certificates for HTTPS..."
cd "$PROJECT_DIR/custom-webserver"
if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
    echo -e "${YELLOW}[WARN]${NC} Generating self-signed certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout server.key -out server.crt -days 365 \
        -subj "/C=US/ST=State/L=City/O=Pandora/OU=Security/CN=172.235.245.60" 2>/dev/null
    echo -e "${GREEN}[OK]${NC} SSL certificate generated"
else
    echo -e "${GREEN}[OK]${NC} SSL certificates exist"
fi

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  PHASE 4: Systemd Services${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${GREEN}[1/7]${NC} Installing systemd service files..."
cp "$PROJECT_DIR/deploy/systemd"/*.service "$SYSTEMD_DIR/"
chmod 644 "$SYSTEMD_DIR"/pandora-*.service

echo -e "${GREEN}[2/7]${NC} Reloading systemd daemon..."
systemctl daemon-reload

echo -e "${GREEN}[3/7]${NC} Enabling all services (auto-start on boot)..."
systemctl enable pandora-backend-admin.service
systemctl enable pandora-backend-user.service
systemctl enable pandora-central-monitor.service
systemctl enable pandora-ids.service
systemctl enable pandora-http-80.service
systemctl enable pandora-https-443.service

echo -e "${GREEN}[4/7]${NC} Stopping old services..."
systemctl stop pandora-backend-admin.service 2>/dev/null || true
systemctl stop pandora-backend-user.service 2>/dev/null || true
systemctl stop pandora-central-monitor.service 2>/dev/null || true
systemctl stop pandora-ids.service 2>/dev/null || true
systemctl stop pandora-http-80.service 2>/dev/null || true
systemctl stop pandora-https-443.service 2>/dev/null || true

echo -e "${GREEN}[5/7]${NC} Starting Backend services..."
systemctl start pandora-backend-admin.service
systemctl start pandora-backend-user.service

echo -e "${GREEN}[6/7]${NC} Starting Web services..."
systemctl start pandora-http-80.service
systemctl start pandora-https-443.service
systemctl start pandora-central-monitor.service

echo -e "${GREEN}[7/7]${NC} Starting IDS Engine..."
systemctl start pandora-ids.service

echo ""
echo -e "${CYAN}Waiting for services to initialize...${NC}"
sleep 10

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  PHASE 5: Firewall Configuration${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${GREEN}[1/4]${NC} Installing UFW firewall..."
apt install -y ufw >/dev/null 2>&1

echo -e "${GREEN}[2/4]${NC} Configuring firewall rules..."
# Allow SSH (custom port 2222)
ufw allow 2222/tcp comment 'SSH'

# Allow web services
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow monitoring (optional - for debugging)
ufw allow 22002/tcp comment 'Central Monitor'
ufw allow 9000/tcp comment 'Backend Admin'
ufw allow 8000/tcp comment 'Backend User'
ufw allow 5601/tcp comment 'Kibana'

echo -e "${GREEN}[3/4]${NC} Enabling firewall..."
echo "y" | ufw enable 2>/dev/null || true

echo -e "${GREEN}[4/4]${NC} Firewall status:"
ufw status numbered

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  PHASE 6: Verification${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

# Function to check service status
check_service() {
    local service=$1
    local name=$2
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✓${NC} $name - RUNNING"
        return 0
    else
        echo -e "${RED}✗${NC} $name - FAILED"
        return 1
    fi
}

echo "Service Status:"
echo "----------------------------------------"
check_service "pandora-backend-admin.service" "Backend Admin (Port 9000)"
check_service "pandora-backend-user.service" "Backend User (Port 8000)"
check_service "pandora-central-monitor.service" "Central Monitor (Port 22002)"
check_service "pandora-http-80.service" "HTTP Server (Port 80)"
check_service "pandora-https-443.service" "HTTPS Server (Port 443)"
check_service "pandora-ids.service" "IDS Engine"

echo ""
echo "Docker Services:"
echo "----------------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "postgres|redis|elasticsearch|kibana" || echo "No docker containers found"

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  DEPLOYMENT COMPLETE!${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${CYAN}Access Points:${NC}"
echo "  • Main Website:      ${GREEN}https://172.235.245.60${NC}"
echo "  • Central Monitor:   ${GREEN}http://172.235.245.60:22002${NC}"
echo "  • Backend Admin:     ${GREEN}http://172.235.245.60:9000/docs${NC}"
echo "  • Backend User:      ${GREEN}http://172.235.245.60:8000/docs${NC}"
echo "  • Kibana Dashboard:  ${GREEN}http://172.235.245.60:5601${NC}"
echo ""

echo -e "${CYAN}Credentials:${NC}"
echo "  • Central Monitor:   ${YELLOW}admin / admin123${NC}"
echo "  • Kibana:            ${YELLOW}elastic / pandora123${NC}"
echo ""

echo -e "${CYAN}Quick Commands:${NC}"
echo "  • View all services:   ${YELLOW}sudo systemctl status pandora-*${NC}"
echo "  • Stop all services:   ${YELLOW}sudo systemctl stop pandora-*${NC}"
echo "  • Restart all:         ${YELLOW}sudo systemctl restart pandora-*${NC}"
echo "  • View logs:           ${YELLOW}sudo journalctl -u pandora-backend-admin -f${NC}"
echo "  • Check firewall:      ${YELLOW}sudo ufw status${NC}"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Import Kibana dashboards:"
echo "     ${YELLOW}cd /home/pandora/projects/pandora-threat-project/elasticsearch${NC}"
echo "     ${YELLOW}python3 import_dashboards.py${NC}"
echo ""
echo "  2. Test the system:"
echo "     ${YELLOW}curl http://172.235.245.60${NC}"
echo "     ${YELLOW}curl -k https://172.235.245.60${NC}"
echo ""
echo "  3. Monitor honeypot logs:"
echo "     ${YELLOW}sudo journalctl -u pandora-ids -f${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ALL SERVICES DEPLOYED & RUNNING!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

