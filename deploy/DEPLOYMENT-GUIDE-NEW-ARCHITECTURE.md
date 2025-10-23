# Hướng dẫn Deployment - Kiến trúc Mới (Nginx + FastAPI)

## Tổng quan

Tài liệu này hướng dẫn deployment hệ thống Pandora Threat Project với **kiến trúc mới**, thay thế các custom Python HTTP server bằng Nginx + FastAPI production-ready stack.

## Kiến trúc Mới vs Cũ

### ❌ Kiến trúc CŨ (Deprecated)
```
Internet → port_80.py (Port 80) → port_443.py (Port 443, SSL) → Backends
```
**Vấn đề:** Python xử lý SSL, không production-ready, hiệu năng kém

### ✅ Kiến trúc MỚI (Production-Ready)
```
Internet → Nginx (Port 80/443, SSL) → FastAPI (Port 8443) → Backends
                                    ↓
                              IDS Engine (Packet Sniffing)
```
**Ưu điểm:** Nginx xử lý SSL, FastAPI hiệu năng cao, dễ scale

---

## Yêu cầu Hệ thống

### Phần cứng
- **CPU:** 4 cores (khuyến nghị)
- **RAM:** 4GB minimum, 8GB khuyến nghị
- **Disk:** 20GB SSD
- **Network:** 100Mbps+

### Phần mềm
- **OS:** Ubuntu 22.04 LTS / CentOS 8 / Debian 11
- **Python:** 3.10+
- **Nginx:** 1.18+
- **PostgreSQL:** 14+
- **Redis:** 6+
- **Node.js:** 18+ (để build frontend)

---

## Cài đặt từ đầu

### 1. Cài đặt Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install Nginx
sudo apt install nginx -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Redis
sudo apt install redis-server -y

# Install Node.js (để build Vue.js)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install build tools
sudo apt install git build-essential libpcap-dev -y
```

### 2. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/yourusername/threat_project.git pandora
cd pandora
sudo chown -R $USER:$USER /opt/pandora
```

### 3. Setup Database

```bash
# Tạo PostgreSQL databases
sudo -u postgres psql << EOF
CREATE DATABASE pandora_user;
CREATE DATABASE pandora_admin;
CREATE USER pandora WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE pandora_user TO pandora;
GRANT ALL PRIVILEGES ON DATABASE pandora_admin TO pandora;
EOF

# Chạy migrations (nếu có)
cd /opt/pandora/backend-user
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Run migrations here
deactivate

cd /opt/pandora/backend-admin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Run migrations here
deactivate
```

### 4. Setup Backend Services

#### Backend User (Port 8000)
```bash
cd /opt/pandora/backend-user
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Test
source venv/bin/activate
python api/main.py
# Nếu chạy OK → Ctrl+C
deactivate
```

#### Backend Admin (Port 9000)
```bash
cd /opt/pandora/backend-admin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Test
source venv/bin/activate
python api/main.py
# Nếu chạy OK → Ctrl+C
deactivate
```

### 5. Setup Custom Webserver (FastAPI)

```bash
cd /opt/pandora/custom-webserver
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Gunicorn cho production
pip install gunicorn

deactivate

# Test
source venv/bin/activate
python webserver_fastapi.py
# Nếu chạy OK → Ctrl+C
deactivate
```

### 6. Build Frontend (Vue.js)

```bash
cd /opt/pandora/frontend
npm install
npm run build

# Kiểm tra
ls -la dist/
# Phải có: index.html, assets/, pandora-logo.png
```

### 7. Setup SSL Certificate

```bash
cd /opt/pandora/nginx

# Option 1: Self-signed certificate (Development)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=VN/ST=HCM/L=HCM/O=Pandora/CN=localhost"

# Option 2: Let's Encrypt (Production)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com

# Nếu dùng Let's Encrypt, cập nhật nginx.conf:
# ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

### 8. Setup Nginx

```bash
# Copy nginx config
sudo cp /opt/pandora/nginx/nginx.conf /etc/nginx/nginx.conf

# Tạo thư mục SSL (nếu chưa có)
sudo mkdir -p /etc/nginx/ssl

# Copy SSL certificates
sudo cp /opt/pandora/nginx/ssl/cert.pem /etc/nginx/ssl/
sudo cp /opt/pandora/nginx/ssl/key.pem /etc/nginx/ssl/

# Test config
sudo nginx -t

# Nếu OK, reload
sudo systemctl restart nginx
```

### 9. Setup IDS Engine

```bash
cd /opt/pandora/ids
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Test (cần sudo)
sudo /opt/pandora/ids/venv/bin/python ids_engine.py
# Nếu chạy OK → Ctrl+C
```

### 10. Setup Central Monitor

```bash
cd /opt/pandora/central-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Test
source venv/bin/activate
python monitor_server.py
# Nếu chạy OK → Ctrl+C
deactivate
```

---

## Cài đặt Systemd Services

### 1. Install Service Files

```bash
cd /opt/pandora/deploy
sudo ./install-services.sh
```

Script sẽ:
- Tạo user `pandora` và `www-data`
- Copy service files vào `/etc/systemd/system/`
- Enable services (chưa start)
- Tạo thư mục log `/var/log/pandora/`

### 2. Start Services

```bash
# Start tất cả services
sudo /opt/pandora/deploy/start-all-services.sh

# Hoặc start từng service
sudo systemctl start pandora-backend-user
sudo systemctl start pandora-backend-admin
sudo systemctl start pandora-webserver
sudo systemctl start pandora-nginx
sudo systemctl start pandora-ids
sudo systemctl start pandora-central-monitor
```

### 3. Check Status

```bash
# Check tất cả services
sudo systemctl status pandora-*

# Check từng service
sudo systemctl status pandora-nginx
sudo systemctl status pandora-webserver

# Xem logs real-time
sudo journalctl -u pandora-nginx -f
sudo journalctl -u pandora-webserver -f
```

---

## Kiểm tra Deployment

### 1. Test HTTP → HTTPS Redirect

```bash
curl -I http://localhost
# Expected: HTTP/1.1 301 Moved Permanently
# Location: https://localhost/
```

### 2. Test HTTPS (Vue.js Frontend)

```bash
curl -k https://localhost/
# Expected: HTML content của Vue.js

# Hoặc dùng browser
firefox https://localhost
```

### 3. Test Backend APIs

```bash
# User API
curl -k https://localhost/api/v1/auth/health
# Expected: {"status": "healthy", ...}

# WebServer API
curl -k https://localhost/api/status
# Expected: {"status": "online", "server": "Pandora FastAPI Webserver", ...}
```

### 4. Test Honeypot Logging

```bash
# Send suspicious request
curl -k "https://localhost/admin/config.php?id=1' OR '1'='1"

# Check honeypot logs
sudo -u postgres psql pandora_admin -c "SELECT * FROM honeypot_logs ORDER BY id DESC LIMIT 1;"

# Nên thấy suspicious_score cao (> 50)
```

### 5. Test IDS Detection

```bash
# Trigger port scan (từ máy khác)
nmap -sS -p 1-1000 <your-server-ip>

# Check attack logs
sudo -u postgres psql pandora_admin -c "SELECT * FROM attack_logs ORDER BY detected_at DESC LIMIT 1;"

# Nên thấy attack_type = 'port_scan'
```

---

## Cấu trúc Ports

| Service | Port | Protocol | Access |
|---------|------|----------|--------|
| Nginx HTTP | 80 | HTTP | Public (redirect) |
| Nginx HTTPS | 443 | HTTPS | Public |
| FastAPI Webserver | 8443 | HTTP | Localhost only |
| User Backend | 8000 | HTTP | Localhost only |
| Admin Backend | 9000 | HTTP | Localhost only |
| Central Monitor | 3000 | HTTP | Localhost only |
| PostgreSQL | 5432 | TCP | Localhost only |
| Redis | 6379 | TCP | Localhost only |

**Lưu ý:** Chỉ mở port 80 và 443 ra Internet. Các port nội bộ khác phải chặn từ firewall.

---

## Cấu hình Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH (cẩn thận!)
sudo ufw enable

# Hoặc iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -j DROP
sudo iptables-save > /etc/iptables/rules.v4
```

---

## Troubleshooting

### Lỗi: "Address already in use"

```bash
# Kiểm tra port đang sử dụng
sudo lsof -i :443
sudo lsof -i :8443

# Kill process cũ
sudo kill -9 <PID>

# Hoặc stop service cũ
sudo systemctl stop pandora-https-443  # service cũ
sudo systemctl stop pandora-webserver  # service mới
```

### Lỗi: "Nginx: 502 Bad Gateway"

**Nguyên nhân:** Backend chưa chạy hoặc port sai

```bash
# Check backend services
sudo systemctl status pandora-webserver
sudo systemctl status pandora-backend-user

# Check port listening
sudo netstat -tulnp | grep 8443
sudo netstat -tulnp | grep 8000

# Check logs
sudo journalctl -u pandora-webserver -n 50
```

### Lỗi: "Permission denied (port 443)"

**Nguyên nhân:** Nginx chưa chạy với quyền root

```bash
# Nginx phải chạy với root để bind port < 1024
sudo systemctl restart nginx

# Kiểm tra
ps aux | grep nginx
# Phải thấy: root ... nginx: master process
```

### Lỗi: "Frontend not built"

```bash
cd /opt/pandora/frontend
npm install
npm run build

# Restart webserver
sudo systemctl restart pandora-webserver
```

### Lỗi: "IDS: Permission denied"

**Nguyên nhân:** IDS cần root để capture packets

```bash
# IDS phải chạy với root
sudo systemctl status pandora-ids

# Nếu chạy manual:
sudo /opt/pandora/ids/venv/bin/python ids_engine.py
```

---

## Monitoring và Logs

### 1. System Logs

```bash
# Tất cả services
sudo journalctl -u pandora-* -f

# Nginx
sudo journalctl -u pandora-nginx -f
tail -f /var/log/nginx/pandora_access.log

# Webserver
sudo journalctl -u pandora-webserver -f
tail -f /var/log/pandora/webserver-access.log

# IDS
sudo journalctl -u pandora-ids -f
```

### 2. Application Logs

```bash
# Honeypot logs (database)
sudo -u postgres psql pandora_admin -c "
SELECT 
    id, 
    client_ip, 
    request_path, 
    suspicious_score, 
    created_at 
FROM honeypot_logs 
ORDER BY created_at DESC 
LIMIT 10;
"

# Attack logs (database)
sudo -u postgres psql pandora_admin -c "
SELECT 
    id, 
    source_ip, 
    attack_type, 
    severity, 
    detected_at 
FROM attack_logs 
ORDER BY detected_at DESC 
LIMIT 10;
"
```

### 3. Central Monitor Dashboard

```bash
# Access từ localhost
firefox http://localhost:3000

# Hoặc SSH tunnel từ máy remote
ssh -L 3000:localhost:3000 user@your-server
# Sau đó mở: http://localhost:3000 trên máy local
```

---

## Backup và Restore

### Backup Database

```bash
# Backup PostgreSQL
sudo -u postgres pg_dump pandora_user > /backup/pandora_user_$(date +%Y%m%d).sql
sudo -u postgres pg_dump pandora_admin > /backup/pandora_admin_$(date +%Y%m%d).sql

# Backup Redis (nếu có data persistent)
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis_$(date +%Y%m%d).rdb
```

### Restore Database

```bash
# Restore PostgreSQL
sudo -u postgres psql pandora_user < /backup/pandora_user_20251023.sql
sudo -u postgres psql pandora_admin < /backup/pandora_admin_20251023.sql
```

---

## Scale và Optimization

### 1. Tăng Workers cho FastAPI

Chỉnh sửa `/etc/systemd/system/pandora-webserver.service`:

```ini
ExecStart=/opt/pandora/custom-webserver/venv/bin/gunicorn webserver_fastapi:app \
    --workers 8 \        # Tăng từ 4 lên 8
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8443
```

Sau đó reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart pandora-webserver
```

### 2. Nginx Caching (Static Assets)

Thêm vào `nginx.conf`:

```nginx
# Cache static files
location /assets/ {
    proxy_pass http://127.0.0.1:8443;
    proxy_cache_valid 200 7d;
    add_header X-Cache-Status $upstream_cache_status;
}
```

### 3. Rate Limiting (DDoS Protection)

Đã có sẵn trong `nginx.conf`:
```nginx
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
```

Có thể giảm rate nếu bị tấn công:
```nginx
limit_req_zone $binary_remote_addr zone=general:10m rate=5r/s;  # Giảm từ 10 xuống 5
```

---

## Tóm tắt Commands

```bash
# Start all
sudo /opt/pandora/deploy/start-all-services.sh

# Stop all
sudo /opt/pandora/deploy/stop-all-services.sh

# Restart service cụ thể
sudo systemctl restart pandora-webserver

# Check logs
sudo journalctl -u pandora-webserver -f

# Test
curl -k https://localhost/api/status
```

---

## Liên hệ và Hỗ trợ

- **GitHub Issues:** [Link]
- **Documentation:** [Link]
- **Email:** support@pandora.com

---

**Ngày cập nhật:** 2025-10-23  
**Phiên bản:** 2.0.0 (New Architecture)

