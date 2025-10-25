#!/bin/bash
# ========================================================================
# Pandora Central Monitor Server - Deployment Script
# ========================================================================
# Deploy this on the INTERNAL server (admin access only)
# ========================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Pandora Central Monitor - Deployment"
echo "========================================"

# Check root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root${NC}"
   exit 1
fi

# Variables
INSTALL_DIR="/opt/pandora"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_CONF_DIR="/etc/nginx"

# ========================================================================
# 1. Install System Dependencies
# ========================================================================
echo -e "${GREEN}[1/9] Installing system dependencies...${NC}"
apt update
apt install -y nginx python3.10 python3.10-venv python3-pip postgresql postgresql-contrib redis-server

# Optional: Elasticsearch
# apt install -y elasticsearch

# ========================================================================
# 2. Create Pandora User
# ========================================================================
echo -e "${GREEN}[2/9] Creating pandora user...${NC}"
if ! id -u pandora > /dev/null 2>&1; then
    useradd -r -s /bin/bash -d /opt/pandora -m pandora
    echo "[OK] User 'pandora' created"
else
    echo "[SKIP] User 'pandora' already exists"
fi

# ========================================================================
# 3. Setup PostgreSQL
# ========================================================================
echo -e "${GREEN}[3/9] Setting up PostgreSQL...${NC}"
sudo -u postgres psql << EOF
CREATE DATABASE pandora_user;
CREATE DATABASE pandora_admin;
CREATE USER pandora WITH PASSWORD 'change_this_password';
GRANT ALL PRIVILEGES ON DATABASE pandora_user TO pandora;
GRANT ALL PRIVILEGES ON DATABASE pandora_admin TO pandora;
EOF

# ========================================================================
# 4. Setup SSL Certificate
# ========================================================================
echo -e "${GREEN}[4/9] Setting up SSL certificate...${NC}"
mkdir -p $NGINX_CONF_DIR/ssl
if [ ! -f "$NGINX_CONF_DIR/ssl/cert.pem" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $NGINX_CONF_DIR/ssl/key.pem \
        -out $NGINX_CONF_DIR/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=central.local"
    echo "[OK] Self-signed certificate created"
else
    echo "[SKIP] Certificate already exists"
fi

# ========================================================================
# 5. Install Backend-user (Real User App)
# ========================================================================
echo -e "${GREEN}[5/10] Installing Backend-user...${NC}"
cd $INSTALL_DIR/backend-user
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
chown -R pandora:pandora venv

# ========================================================================
# 6. Install Backend-admin
# ========================================================================
echo -e "${GREEN}[6/10] Installing Backend-admin...${NC}"
cd $INSTALL_DIR/backend-admin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
chown -R pandora:pandora venv

# ========================================================================
# 7. Install Central Monitor
# ========================================================================
echo -e "${GREEN}[7/10] Installing Central Monitor...${NC}"
cd $INSTALL_DIR/central-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
chown -R pandora:pandora venv

# ========================================================================
# 8. Install IDS Engine
# ========================================================================
echo -e "${GREEN}[8/10] Installing IDS Engine...${NC}"
cd $INSTALL_DIR/ids
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
chown -R pandora:pandora venv

# ========================================================================
# 9. Build Frontend (Real User App)
# ========================================================================
echo -e "${GREEN}[9/10] Building Vue.js frontend...${NC}"
cd $INSTALL_DIR/frontend
npm install
npm run build
chown -R pandora:pandora dist

# ========================================================================
# 10. Configure Nginx
# ========================================================================
echo -e "${GREEN}[10/10] Configuring Nginx...${NC}"
cp $INSTALL_DIR/central-monitor-server/nginx.conf $NGINX_CONF_DIR/nginx.conf

echo -e "${YELLOW}[IMPORTANT] Edit nginx.conf to add your admin IP whitelist${NC}"
echo "  sudo nano $NGINX_CONF_DIR/nginx.conf"
echo "  Uncomment and set: allow <your-admin-ip>;"

nginx -t
systemctl restart nginx
systemctl enable nginx

# ========================================================================
# 11. Install Systemd Services
# ========================================================================
echo -e "${GREEN}[11/11] Installing systemd services...${NC}"

# Backend-user Service (Real User App)
cat > $SYSTEMD_DIR/pandora-backend-user.service << 'EOF'
[Unit]
Description=Pandora Backend User API (Real User App)
After=network.target postgresql.service

[Service]
Type=simple
User=pandora
Group=pandora
WorkingDirectory=/opt/pandora/backend-user
Environment="PYTHONPATH=/opt/pandora"
Environment="DATABASE_URL=postgresql+psycopg://pandora:change_this_password@localhost/pandora_user"
Environment="CENTRAL_MONITOR_URL=https://localhost/api/admin/honeypot/log"
Environment="CENTRAL_MONITOR_API_KEY=change-this-api-key-in-production"

ExecStart=/opt/pandora/backend-user/venv/bin/uvicorn api.main:app \
    --host 127.0.0.1 \
    --port 8001 \
    --workers 2

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Backend-admin Service
cat > $SYSTEMD_DIR/pandora-backend-admin.service << 'EOF'
[Unit]
Description=Pandora Backend Admin API
After=network.target postgresql.service

[Service]
Type=simple
User=pandora
Group=pandora
WorkingDirectory=/opt/pandora/backend-admin
Environment="PYTHONPATH=/opt/pandora"
Environment="DATABASE_URL=postgresql+psycopg://pandora:change_this_password@localhost/pandora_admin"
Environment="CENTRAL_MONITOR_API_KEY=change-this-api-key-in-production"

ExecStart=/opt/pandora/backend-admin/venv/bin/uvicorn api.main:app \
    --host 127.0.0.1 \
    --port 8002 \
    --workers 2

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Central Monitor Service
cat > $SYSTEMD_DIR/pandora-central-monitor.service << 'EOF'
[Unit]
Description=Pandora Central Monitoring Dashboard
After=network.target pandora-backend-admin.service

[Service]
Type=simple
User=pandora
Group=pandora
WorkingDirectory=/opt/pandora/central-monitor
Environment="PYTHONPATH=/opt/pandora"

ExecStart=/opt/pandora/central-monitor/venv/bin/python monitor_server.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# IDS Engine Service
cat > $SYSTEMD_DIR/pandora-ids.service << 'EOF'
[Unit]
Description=Pandora IDS Engine
After=network.target postgresql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/pandora/ids
Environment="PYTHONPATH=/opt/pandora"

ExecStart=/opt/pandora/ids/venv/bin/python ids_engine.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p /var/log/pandora
chown -R pandora:pandora /var/log/pandora

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable pandora-backend-user
systemctl enable pandora-backend-admin
systemctl enable pandora-central-monitor
systemctl enable pandora-ids

echo ""
echo "========================================"
echo -e "${GREEN}Central Monitor Deployment Complete!${NC}"
echo "========================================"
echo ""
echo "Services installed:"
echo "  • pandora-backend-user     - Real User API (Port 8001)"
echo "  • pandora-backend-admin    - Admin API (Port 8002)"
echo "  • pandora-central-monitor  - Dashboard (Port 5000)"
echo "  • pandora-ids              - IDS Engine"
echo "  • nginx                    - Reverse proxy (Port 443)"
echo "  • postgresql               - Database"
echo "  • redis                    - Cache"
echo "  • Vue.js Frontend          - Real User App"
echo ""
echo -e "${YELLOW}IMPORTANT: Configure database passwords${NC}"
echo "  sudo nano /etc/systemd/system/pandora-backend-user.service"
echo "  sudo nano /etc/systemd/system/pandora-backend-admin.service"
echo "  - Set correct DATABASE_URL with your password"
echo ""
echo -e "${YELLOW}IMPORTANT: Configure Nginx IP whitelist${NC}"
echo "  sudo nano /etc/nginx/nginx.conf"
echo "  - Uncomment and set admin IPs"
echo ""
echo "Then start services:"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl start pandora-backend-user"
echo "  sudo systemctl start pandora-backend-admin"
echo "  sudo systemctl start pandora-central-monitor"
echo "  sudo systemctl start pandora-ids"
echo ""
echo "Check status:"
echo "  sudo systemctl status pandora-*"
echo ""
echo -e "${GREEN}Central Monitor Server is ready!${NC}"
echo "Real users can access: https://central-server-ip/"
echo "Admin dashboard: https://central-server-ip/admin-dashboard/"
echo ""

