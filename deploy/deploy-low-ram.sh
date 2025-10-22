#!/bin/bash

#################################################
# PANDORA THREAT INTELLIGENCE PLATFORM
# DEPLOYMENT SCRIPT - LOW RAM VERSION
# Optimized for VPS with < 2GB RAM
#################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/pandora/projects/pandora-threat-project"
SYSTEMD_DIR="/etc/systemd/system"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  PANDORA THREAT INTELLIGENCE PLATFORM - LOW RAM DEPLOYMENT      ║${NC}"
echo -e "${BLUE}║  Optimized for VPS with limited RAM (< 2GB)                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
   echo -e "${RED}[ERROR]${NC} Please run as root (sudo bash deploy-low-ram.sh)"
   exit 1
fi

# Check project directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Project directory not found: $PROJECT_DIR"
    echo "Please clone the repository first:"
    echo "  mkdir -p /home/pandora/projects"
    echo "  cd /home/pandora/projects"
    echo "  git clone <your-repo-url> pandora-threat-project"
    exit 1
fi

cd "$PROJECT_DIR"

#################################################
# STEP 1: SYSTEM DEPENDENCIES
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[1/8] INSTALLING SYSTEM DEPENDENCIES${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

echo -e "${GREEN}[1/5]${NC} Updating package list..."
apt update -qq

echo -e "${GREEN}[2/5]${NC} Installing system packages..."
apt install -y python3 python3-pip curl wget git htop net-tools >/dev/null 2>&1

echo -e "${GREEN}[3/5]${NC} Installing Python packages..."
pip3 install --break-system-packages --ignore-installed -q \
    fastapi uvicorn sqlalchemy psycopg2-binary redis \
    python-jose passlib bcrypt python-multipart aiofiles pydantic-settings \
    scapy geoip2 requests flask || {
    echo -e "${RED}[ERROR]${NC} Failed to install Python dependencies"
    exit 1
}

echo -e "${GREEN}[4/5]${NC} Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh >/dev/null 2>&1
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

echo -e "${GREEN}[5/5]${NC} Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
         -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo -e "${GREEN}✓${NC} System dependencies installed"

#################################################
# STEP 2: DATABASE LAYER (PostgreSQL + Redis ONLY)
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[2/8] SETTING UP DATABASES${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

cd "$PROJECT_DIR/database"

echo -e "${GREEN}[INFO]${NC} Creating optimized docker-compose for low RAM..."
cat > docker-compose-low-ram.yml <<'EOF'
version: '3.8'

services:
  # PostgreSQL - Main Database
  postgres:
    image: postgres:15-alpine
    container_name: pandora-postgres
    restart: always
    environment:
      POSTGRES_DB: pandora_threat_db
      POSTGRES_USER: pandora_admin
      POSTGRES_PASSWORD: SecurePassword123!
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    shm_size: 128mb
    command: >
      postgres
      -c shared_buffers=128MB
      -c max_connections=50
      -c work_mem=4MB

  # Redis - Cache & Session Store
  redis:
    image: redis:7-alpine
    container_name: pandora-redis
    restart: always
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
EOF

echo -e "${GREEN}[INFO]${NC} Stopping old containers..."
docker-compose down 2>/dev/null || true

echo -e "${GREEN}[INFO]${NC} Starting optimized databases (PostgreSQL + Redis)..."
docker-compose -f docker-compose-low-ram.yml up -d

echo -e "${GREEN}[INFO]${NC} Waiting for databases to be ready..."
sleep 10

# Check database health
if ! docker exec pandora-postgres pg_isready -U pandora_admin >/dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} PostgreSQL failed to start"
    exit 1
fi

if ! docker exec pandora-redis redis-cli ping >/dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} Redis failed to start"
    exit 1
fi

echo -e "${GREEN}✓${NC} Databases running (RAM usage: ~300MB)"

#################################################
# STEP 3: ENVIRONMENT FILES
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[3/8] CONFIGURING ENVIRONMENT${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# Get server IP
SERVER_IP=$(curl -s ifconfig.me || echo "YOUR_SERVER_IP")

# Backend-Admin .env
cat > "$PROJECT_DIR/backend-admin/.env" <<EOF
# Database
DATABASE_URL=postgresql://pandora_admin:SecurePassword123!@localhost:5432/pandora_admin_db
USER_DATABASE_URL=postgresql://pandora_user:UserPassword123!@localhost:5432/pandora_user_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Elasticsearch - DISABLED for low RAM
ELASTICSEARCH_ENABLED=false

# GeoIP
GEOIP_DB_PATH=./GeoLite2-City.mmdb

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
EOF

# Backend-User .env
cat > "$PROJECT_DIR/backend-user/.env" <<EOF
# Database
DATABASE_URL=postgresql://pandora_user:UserPassword123!@localhost:5432/pandora_user_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Elasticsearch - DISABLED for low RAM
ELASTICSEARCH_ENABLED=false

# GeoIP
GEOIP_DB_PATH=./GeoLite2-City.mmdb

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8002
EOF

# Central Monitor .env
cat > "$PROJECT_DIR/central-monitor/.env" <<EOF
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pandora_admin_db
POSTGRES_USER=pandora_admin
POSTGRES_PASSWORD=SecurePassword123!

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Elasticsearch - DISABLED
ELASTICSEARCH_ENABLED=false

# Flask
SECRET_KEY=$(openssl rand -hex 32)
SERVER_HOST=0.0.0.0
SERVER_PORT=27009
EOF

# IDS .env
cat > "$PROJECT_DIR/ids/.env" <<EOF
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pandora_admin_db
POSTGRES_USER=pandora_admin
POSTGRES_PASSWORD=SecurePassword123!

# Elasticsearch - DISABLED
ELASTICSEARCH_ENABLED=false

# Network Interface (auto-detect)
NETWORK_INTERFACE=auto
EOF

echo -e "${GREEN}✓${NC} Environment files created"

#################################################
# STEP 4: SYSTEMD SERVICES
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[4/8] INSTALLING SYSTEMD SERVICES${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# Copy all service files
cp "$PROJECT_DIR/deploy/systemd/"*.service "$SYSTEMD_DIR/"

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}✓${NC} Systemd services installed"

#################################################
# STEP 5: GENERATE SSL CERTIFICATES
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[5/8] GENERATING SSL CERTIFICATES${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

cd "$PROJECT_DIR/custom-webserver"

if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
    echo -e "${GREEN}[INFO]${NC} Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout server.key \
        -out server.crt \
        -subj "/C=US/ST=State/L=City/O=Pandora/CN=$SERVER_IP" \
        >/dev/null 2>&1
    echo -e "${GREEN}✓${NC} SSL certificate generated"
else
    echo -e "${GREEN}✓${NC} SSL certificate already exists"
fi

#################################################
# STEP 6: START SERVICES
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[6/8] STARTING ALL SERVICES${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# Start and enable all services
SERVICES=(
    "pandora-backend-admin"
    "pandora-backend-user"
    "pandora-central-monitor"
    "pandora-ids"
    "pandora-http-listener"
    "pandora-https-listener"
)

for service in "${SERVICES[@]}"; do
    echo -e "${GREEN}[INFO]${NC} Starting $service..."
    systemctl enable "$service" >/dev/null 2>&1
    systemctl start "$service"
    
    # Check if started successfully
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓${NC} $service is running"
    else
        echo -e "${YELLOW}[WARN]${NC} $service may have issues (check: systemctl status $service)"
    fi
done

#################################################
# STEP 7: CONFIGURE FIREWALL
#################################################
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}[7/8] CONFIGURING FIREWALL${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

if command -v ufw &> /dev/null; then
    echo -e "${GREEN}[INFO]${NC} Setting up UFW firewall..."
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 27009/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP Honeypot'
    ufw allow 443/tcp comment 'HTTPS Honeypot'
    ufw allow 27009/tcp comment 'Central Monitor'
    ufw reload
    echo -e "${GREEN}✓${NC} Firewall configured"
else
    echo -e "${YELLOW}[WARN]${NC} UFW not found. Please configure firewall manually"
fi

#################################################
# STEP 8: DEPLOYMENT SUMMARY
#################################################
echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               DEPLOYMENT COMPLETED SUCCESSFULLY                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Databases:${NC}"
echo "  - PostgreSQL: localhost:5432 (RAM: ~200MB)"
echo "  - Redis: localhost:6379 (RAM: ~50MB)"
echo ""
echo -e "${GREEN}✓ Backend Services:${NC}"
echo "  - Backend Admin API: http://localhost:8001 (RAM: ~150MB)"
echo "  - Backend User API: http://localhost:8002 (RAM: ~150MB)"
echo ""
echo -e "${GREEN}✓ Monitoring:${NC}"
echo "  - Central Monitor: http://$SERVER_IP:27009"
echo "    Username: admin"
echo "    Password: admin123"
echo ""
echo -e "${GREEN}✓ Honeypot Listeners:${NC}"
echo "  - HTTP: http://$SERVER_IP:80 (redirects to HTTPS)"
echo "  - HTTPS: https://$SERVER_IP:443"
echo ""
echo -e "${GREEN}✓ IDS Engine:${NC}"
echo "  - Status: systemctl status pandora-ids"
echo "  - Logs: journalctl -u pandora-ids -f"
echo ""
echo -e "${YELLOW}⚠ NOTE - LOW RAM OPTIMIZATIONS:${NC}"
echo "  - Elasticsearch & Kibana: DISABLED (saves ~2GB RAM)"
echo "  - PostgreSQL: Limited to 128MB shared buffers"
echo "  - Redis: Limited to 128MB max memory"
echo "  - Total RAM usage: ~900MB (safe for 1GB+ VPS)"
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Estimated Total RAM Usage: ~900MB${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Check all services:${NC} systemctl status pandora-*"
echo -e "${GREEN}View logs:${NC} journalctl -u pandora-backend-admin -f"
echo ""
echo -e "${GREEN}Deployment complete! 🚀${NC}"

