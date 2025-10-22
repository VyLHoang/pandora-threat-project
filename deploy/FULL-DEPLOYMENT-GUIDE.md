# 🚀 Pandora Full Deployment Guide

## ⚡ QUICK START (Recommended)

### **Deploy tất cả services với 1 lệnh:**

```bash
# 1. SSH vào VPS
ssh pandora@172.235.245.60 -p 2222

# 2. Clone project (nếu chưa có)
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/VyLHoang/pandora-threat-project.git
cd pandora-threat-project

# 3. Make deploy script executable
chmod +x deploy/deploy-all.sh

# 4. Deploy ALL services
sudo bash deploy/deploy-all.sh
```

**Script sẽ tự động:**
- ✅ Install system dependencies
- ✅ Install Python packages
- ✅ Start all Docker containers (PostgreSQL, Redis, Elasticsearch, Kibana)
- ✅ Generate SSL certificates
- ✅ Create systemd services
- ✅ Start all 6 services (backends, IDS, web servers, monitor)
- ✅ Configure firewall
- ✅ Enable auto-start on boot

**Thời gian:** ~10-15 phút

---

## 📋 MANUAL DEPLOYMENT (Step by Step)

### **1. System Preparation**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv curl wget git htop

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pandora

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for docker group to take effect
exit
ssh pandora@172.235.245.60 -p 2222
```

---

### **2. Clone Project**

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/VyLHoang/pandora-threat-project.git
cd pandora-threat-project
```

---

### **3. Install Python Dependencies**

```bash
pip3 install --upgrade pip

# All required packages
pip3 install fastapi uvicorn sqlalchemy psycopg2-binary redis elasticsearch \
    python-jose passlib bcrypt python-multipart aiofiles pydantic-settings \
    scapy geoip2 requests flask
```

---

### **4. Start Database Services**

```bash
# Shared databases (PostgreSQL, Redis, Elasticsearch, Kibana)
cd ~/projects/pandora-threat-project/database
docker-compose up -d

# Admin databases
cd ~/projects/pandora-threat-project/backend-admin
docker-compose up -d

# User databases
cd ~/projects/pandora-threat-project/backend-user
docker-compose up -d

# Wait for Elasticsearch to be ready (important!)
sleep 180
```

---

### **5. Generate SSL Certificates**

```bash
cd ~/projects/pandora-threat-project/custom-webserver

# Self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout server.key -out server.crt -days 365 \
    -subj "/CN=172.235.245.60"
```

---

### **6. Deploy Systemd Services**

```bash
cd ~/projects/pandora-threat-project

# Copy service files
sudo cp deploy/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (auto-start on boot)
sudo systemctl enable pandora-backend-admin
sudo systemctl enable pandora-backend-user
sudo systemctl enable pandora-central-monitor
sudo systemctl enable pandora-ids
sudo systemctl enable pandora-http-80
sudo systemctl enable pandora-https-443

# Start services
sudo systemctl start pandora-backend-admin
sudo systemctl start pandora-backend-user
sudo systemctl start pandora-central-monitor
sudo systemctl start pandora-ids
sudo systemctl start pandora-http-80
sudo systemctl start pandora-https-443
```

---

### **7. Configure Firewall**

```bash
# Install UFW
sudo apt install -y ufw

# Allow SSH (port 2222)
sudo ufw allow 2222/tcp

# Allow web services
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow monitoring (optional)
sudo ufw allow 22002/tcp  # Central Monitor
sudo ufw allow 9000/tcp   # Backend Admin API
sudo ufw allow 8000/tcp   # Backend User API
sudo ufw allow 5601/tcp   # Kibana

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

### **8. Import Kibana Dashboards**

```bash
cd ~/projects/pandora-threat-project/elasticsearch

# Wait for Kibana to be ready
sleep 60

# Import dashboards
python3 import_dashboards.py
```

---

## ✅ VERIFICATION

### **Check All Services**

```bash
# Service status
sudo systemctl status pandora-*

# Individual services
sudo systemctl status pandora-backend-admin
sudo systemctl status pandora-backend-user
sudo systemctl status pandora-central-monitor
sudo systemctl status pandora-ids
sudo systemctl status pandora-http-80
sudo systemctl status pandora-https-443

# Docker containers
docker ps

# Listening ports
sudo netstat -tuln | grep -E '80|443|8000|9000|22002|5432|6379|9200|5601'
```

---

### **Test Endpoints**

```bash
# From VPS (localhost)
curl http://localhost
curl -k https://localhost
curl http://localhost:9000/api/v1/health
curl http://localhost:8000/api/v1/health
curl http://localhost:22002

# From your Windows machine
curl http://172.235.245.60
curl -k https://172.235.245.60
```

---

### **Test in Browser**

From your Windows machine:

1. **Main Website:** https://172.235.245.60
   - Accept self-signed certificate
   - Should show Vue.js frontend

2. **Central Monitor:** http://172.235.245.60:22002
   - Login: `admin` / `admin123`
   - Should show admin dashboard

3. **Backend Admin API:** http://172.235.245.60:9000/docs
   - Should show Swagger UI

4. **Backend User API:** http://172.235.245.60:8000/docs
   - Should show Swagger UI

5. **Kibana:** http://172.235.245.60:5601
   - Login: `elastic` / `pandora123`
   - Should show dashboards

---

## 📊 ARCHITECTURE OVERVIEW

```
Internet
   ↓
Port 80 (HTTP) ──[Redirect]──> Port 443 (HTTPS)
   ↓                                ↓
   ↓                          Vue.js Frontend
   ↓                                ↓
   ↓                          Backend User API (8000)
   ↓                                ↓
   ↓                          PostgreSQL (User DB)
   ↓                          Elasticsearch
   ↓
   ↓
IDS Engine ───[Monitor Network]───> PostgreSQL (Admin DB)
   ↓                                 Elasticsearch
   ↓
   ↓
Central Monitor (22002) ──[Query]──> Backend Admin API (9000)
   ↓                                      ↓
Admin Dashboard                    PostgreSQL (Admin DB)
                                   Elasticsearch
                                   User DB Client (Read-only)
```

---

## 🔧 SERVICE MANAGEMENT

### **Start/Stop/Restart Services**

```bash
# All services
sudo systemctl start pandora-*
sudo systemctl stop pandora-*
sudo systemctl restart pandora-*

# Individual service
sudo systemctl start pandora-backend-admin
sudo systemctl stop pandora-backend-admin
sudo systemctl restart pandora-backend-admin
```

---

### **View Logs**

```bash
# Real-time logs
sudo journalctl -u pandora-backend-admin -f
sudo journalctl -u pandora-backend-user -f
sudo journalctl -u pandora-central-monitor -f
sudo journalctl -u pandora-ids -f
sudo journalctl -u pandora-http-80 -f
sudo journalctl -u pandora-https-443 -f

# Last 100 lines
sudo journalctl -u pandora-backend-admin -n 100

# All Pandora services
sudo journalctl -u pandora-* -f
```

---

### **Database Management**

```bash
# Stop all databases
cd ~/projects/pandora-threat-project/database
docker-compose down

cd ~/projects/pandora-threat-project/backend-admin
docker-compose down

cd ~/projects/pandora-threat-project/backend-user
docker-compose down

# Start all databases
cd ~/projects/pandora-threat-project/database
docker-compose up -d

cd ~/projects/pandora-threat-project/backend-admin
docker-compose up -d

cd ~/projects/pandora-threat-project/backend-user
docker-compose up -d

# Check database status
docker ps

# Connect to PostgreSQL
docker exec -it database-postgres-1 psql -U admin -d pandora_db

# Connect to Redis
docker exec -it database-redis-1 redis-cli

# Check Elasticsearch
curl http://localhost:9200
curl http://localhost:9200/_cluster/health
```

---

## 🐛 TROUBLESHOOTING

### **Service won't start**

```bash
# Check logs
sudo journalctl -u pandora-backend-admin -xe

# Check service file
sudo systemctl cat pandora-backend-admin

# Test manually
cd ~/projects/pandora-threat-project/backend-admin
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 9000
```

---

### **Port already in use**

```bash
# Find process using port
sudo lsof -i :9000

# Kill process
sudo kill -9 <PID>

# Or stop the service
sudo systemctl stop pandora-backend-admin
```

---

### **Database connection error**

```bash
# Check if databases are running
docker ps

# Restart databases
cd ~/projects/pandora-threat-project/database
docker-compose restart

# Check database logs
docker logs database-postgres-1
docker logs database-redis-1
docker logs database-elasticsearch-1
```

---

### **Elasticsearch not ready**

```bash
# Check status
curl http://localhost:9200/_cluster/health

# Wait for green/yellow status
while [[ "$(curl -s http://localhost:9200/_cluster/health | grep -o '\"status\":\"[^\"]*\"' | cut -d'"' -f4)" != "green" ]]; do
    echo "Waiting for Elasticsearch..."
    sleep 10
done
```

---

### **IDS Engine permission error**

```bash
# IDS needs root for packet capture
sudo systemctl status pandora-ids

# Check capabilities
sudo getcap /usr/bin/python3

# If needed, grant capabilities
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3
```

---

### **Firewall blocking connections**

```bash
# Check firewall status
sudo ufw status

# Allow port
sudo ufw allow 9000/tcp

# Disable firewall (temporary, for testing)
sudo ufw disable

# Re-enable
sudo ufw enable
```

---

## 📈 MONITORING

### **System Resources**

```bash
# CPU, Memory, Processes
htop

# Disk usage
df -h

# Network connections
sudo netstat -tuln

# Active connections
sudo ss -tunlp
```

---

### **Attack Detection**

```bash
# Watch IDS logs
sudo journalctl -u pandora-ids -f

# Check attack count in database
docker exec -it backend-admin-postgres-admin-1 psql -U admin -d pandora_admin -c "SELECT COUNT(*) FROM attack_logs;"

# Recent attacks
docker exec -it backend-admin-postgres-admin-1 psql -U admin -d pandora_admin -c "SELECT source_ip, attack_type, severity, detected_at FROM attack_logs ORDER BY detected_at DESC LIMIT 10;"
```

---

### **Honeypot Activity**

```bash
# Check honeypot logs
sudo journalctl -u pandora-https-443 -f

# Count honeypot logs
docker exec -it backend-user-postgres-user-1 psql -U user -d pandora_user -c "SELECT COUNT(*) FROM honeypot_logs;"
```

---

## 🔒 SECURITY

### **Change Default Passwords**

#### **1. Central Monitor Admin:**
```bash
cd ~/projects/pandora-threat-project/central-monitor

# Generate new password hash
python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('YOUR_NEW_PASSWORD'))"

# Update auth_config.py with new hash
nano auth_config.py

# Restart service
sudo systemctl restart pandora-central-monitor
```

#### **2. PostgreSQL:**
```bash
# Connect to database
docker exec -it database-postgres-1 psql -U admin -d pandora_db

# Change password
ALTER USER admin WITH PASSWORD 'new_password';

# Update .env files
nano backend-admin/.env
nano backend-user/.env

# Restart backends
sudo systemctl restart pandora-backend-admin
sudo systemctl restart pandora-backend-user
```

#### **3. Elasticsearch/Kibana:**
```bash
# Update docker-compose.yml
nano database/docker-compose.yml

# Change ELASTIC_PASSWORD

# Restart
cd database
docker-compose down
docker-compose up -d
```

---

### **Use Real SSL Certificate (Let's Encrypt)**

```bash
# Install Certbot
sudo apt install -y certbot

# Get certificate (requires domain)
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem

# Update port_443.py to use new certificates
nano custom-webserver/port_443.py

# Restart HTTPS service
sudo systemctl restart pandora-https-443
```

---

## 🎯 MAINTENANCE

### **Update Code**

```bash
cd ~/projects/pandora-threat-project

# Pull latest changes
git pull origin main

# Restart services
sudo systemctl restart pandora-*
```

---

### **Backup Database**

```bash
# PostgreSQL backup
docker exec database-postgres-1 pg_dump -U admin pandora_db > backup_shared_$(date +%Y%m%d).sql
docker exec backend-admin-postgres-admin-1 pg_dump -U admin pandora_admin > backup_admin_$(date +%Y%m%d).sql
docker exec backend-user-postgres-user-1 pg_dump -U user pandora_user > backup_user_$(date +%Y%m%d).sql

# Elasticsearch backup
curl -XPUT "http://localhost:9200/_snapshot/my_backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/usr/share/elasticsearch/backup"
  }
}'
```

---

### **Clean Old Logs**

```bash
# Clean journal logs (keep last 7 days)
sudo journalctl --vacuum-time=7d

# Clean Docker logs
docker system prune -a --volumes

# Clean Elasticsearch old indices
curl -XDELETE "http://localhost:9200/pandora-*-$(date -d '30 days ago' +%Y.%m.%d)"
```

---

## 📞 SUPPORT

### **Useful Commands**

```bash
# Service status summary
sudo systemctl list-units pandora-* --all

# Resource usage by service
sudo systemctl status pandora-backend-admin | grep -E 'Memory|CPU'

# Network traffic
sudo tcpdump -i any port 80 or port 443

# Open files by service
sudo lsof -u pandora
```

---

## ✅ POST-DEPLOYMENT CHECKLIST

- [ ] All 6 systemd services running
- [ ] All Docker containers running
- [ ] Firewall configured
- [ ] Can access HTTPS website from browser
- [ ] Can login to Central Monitor
- [ ] Kibana dashboards imported
- [ ] IDS Engine capturing packets
- [ ] Attack logs appearing in database
- [ ] Honeypot logs being recorded
- [ ] Changed default passwords
- [ ] Backups configured
- [ ] Monitoring setup

---

**Deployment Date:** 2025-10-22  
**Version:** 1.0.0  
**Status:** Production Ready 🚀

