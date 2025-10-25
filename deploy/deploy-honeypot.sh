#!/bin/bash
# ========================================================================
# Pandora Honeypot Server - Deployment Script
# ========================================================================
# Deploy this on the PUBLIC server (exposed to Internet)
# ========================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Pandora Honeypot Server - Deployment"
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
echo -e "${GREEN}[1/8] Installing system dependencies...${NC}"
apt update
apt install -y nginx python3.10 python3.10-venv python3-pip nodejs npm

# ========================================================================
# 2. Create Pandora User
# ========================================================================
echo -e "${GREEN}[2/8] Creating pandora user...${NC}"
if ! id -u pandora > /dev/null 2>&1; then
    useradd -r -s /bin/bash -d /opt/pandora -m pandora
    echo "[OK] User 'pandora' created"
else
    echo "[SKIP] User 'pandora' already exists"
fi

# ========================================================================
# 3. Setup SSL Certificate
# ========================================================================
echo -e "${GREEN}[3/8] Setting up SSL certificate...${NC}"
mkdir -p $NGINX_CONF_DIR/ssl
if [ ! -f "$NGINX_CONF_DIR/ssl/cert.pem" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $NGINX_CONF_DIR/ssl/key.pem \
        -out $NGINX_CONF_DIR/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=honeypot.local"
    echo "[OK] Self-signed certificate created"
else
    echo "[SKIP] Certificate already exists"
fi

# ========================================================================
# 4. Install Honeypot Webserver (Pure Honeypot Only)
# ========================================================================
echo -e "${GREEN}[4/6] Installing Honeypot Webserver...${NC}"
cd $INSTALL_DIR/custom-webserver
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
deactivate
chown -R pandora:pandora venv

# ========================================================================
# 5. Configure Nginx
# ========================================================================
echo -e "${GREEN}[5/6] Configuring Nginx...${NC}"
cp $INSTALL_DIR/honeypot-server/nginx.conf $NGINX_CONF_DIR/nginx.conf
nginx -t
systemctl restart nginx
systemctl enable nginx

# ========================================================================
# 6. Install Systemd Services
# ========================================================================
echo -e "${GREEN}[6/6] Installing systemd services...${NC}"

# Honeypot Webserver Service (Pure Honeypot)
cat > $SYSTEMD_DIR/pandora-honeypot.service << 'EOF'
[Unit]
Description=Pandora Pure Honeypot Webserver
After=network.target

[Service]
Type=simple
User=pandora
Group=pandora
WorkingDirectory=/opt/pandora/custom-webserver
Environment="PYTHONPATH=/opt/pandora"
Environment="CENTRAL_MONITOR_URL=https://your-central-server.com"
Environment="CENTRAL_MONITOR_API_KEY=your-secret-api-key"

ExecStart=/opt/pandora/custom-webserver/venv/bin/gunicorn honeypot_server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8443 \
    --access-logfile /var/log/pandora/honeypot.log \
    --error-logfile /var/log/pandora/honeypot-error.log

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
systemctl enable pandora-honeypot

echo ""
echo "========================================"
echo -e "${GREEN}Honeypot Server Deployment Complete!${NC}"
echo "========================================"
echo ""
echo "Services installed:"
echo "  • pandora-honeypot    - Pure honeypot webserver (Port 8443)"
echo "  • nginx                - Reverse proxy (Port 80/443)"
echo ""
echo -e "${YELLOW}IMPORTANT: Edit environment variables${NC}"
echo "  sudo nano /etc/systemd/system/pandora-honeypot.service"
echo "  - Set CENTRAL_MONITOR_URL to your Central Server IP"
echo "  - Set CENTRAL_MONITOR_API_KEY to match Central Server"
echo ""
echo "Then start services:"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl start pandora-honeypot"
echo ""
echo "Check status:"
echo "  sudo systemctl status pandora-honeypot"
echo ""
echo -e "${GREEN}Honeypot Server is now ready to lure attackers!${NC}"
echo "All traffic on ports 80/443 will be logged to Central Monitor."
echo ""

