# Quick Start Guide - Kiến trúc Mới (v2.0)

## 🚀 Chạy nhanh (5 phút)

### Điều kiện tiên quyết
- Ubuntu 22.04 / Debian 11 / CentOS 8
- Python 3.10+
- Nginx
- PostgreSQL 14+
- Root/sudo access

---

## 1️⃣ Clone và Setup

```bash
# Clone repository
cd /opt
sudo git clone <your-repo-url> pandora
cd pandora

# Cài đặt dependencies hệ thống
sudo apt update
sudo apt install nginx postgresql postgresql-contrib redis-server python3.10 python3.10-venv -y
```

---

## 2️⃣ Setup Database

```bash
sudo -u postgres psql << EOF
CREATE DATABASE pandora_user;
CREATE DATABASE pandora_admin;
CREATE USER pandora WITH PASSWORD 'changeme123';
GRANT ALL PRIVILEGES ON DATABASE pandora_user TO pandora;
GRANT ALL PRIVILEGES ON DATABASE pandora_admin TO pandora;
EOF
```

---

## 3️⃣ Install Services

```bash
# Backend User
cd /opt/pandora/backend-user
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Backend Admin
cd /opt/pandora/backend-admin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Custom Webserver
cd /opt/pandora/custom-webserver
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn  # Production server
deactivate

# IDS Engine
cd /opt/pandora/ids
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Central Monitor
cd /opt/pandora/central-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

---

## 4️⃣ Build Frontend

```bash
cd /opt/pandora/frontend
npm install
npm run build

# Verify
ls -la dist/  # Phải có index.html
```

---

## 5️⃣ Setup SSL Certificate

```bash
cd /opt/pandora/nginx

# Tạo thư mục SSL
sudo mkdir -p ssl

# Self-signed certificate (Development)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=VN/ST=HCM/L=HCM/O=Pandora/CN=localhost"

# Copy vào /etc/nginx/ssl/
sudo mkdir -p /etc/nginx/ssl
sudo cp ssl/cert.pem /etc/nginx/ssl/
sudo cp ssl/key.pem /etc/nginx/ssl/
```

---

## 6️⃣ Setup Nginx

```bash
# Backup nginx config cũ
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Copy config mới
sudo cp /opt/pandora/nginx/nginx.conf /etc/nginx/nginx.conf

# Test config
sudo nginx -t

# Nếu OK, restart
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 7️⃣ Install Systemd Services

```bash
cd /opt/pandora/deploy

# Make scripts executable
chmod +x install-services.sh
chmod +x start-all-services.sh
chmod +x stop-all-services.sh

# Install services
sudo ./install-services.sh
```

---

## 8️⃣ Start All Services

```bash
sudo /opt/pandora/deploy/start-all-services.sh
```

**Thứ tự start:**
1. Backend User (Port 8000)
2. Backend Admin (Port 9000)
3. FastAPI Webserver (Port 8443)
4. Nginx (Port 80/443)
5. IDS Engine
6. Central Monitor (Port 3000)

---

## 9️⃣ Verify

### Test HTTP → HTTPS Redirect
```bash
curl -I http://localhost
# Expected: 301 Moved Permanently
```

### Test HTTPS Frontend
```bash
curl -k https://localhost/
# Expected: HTML của Vue.js
```

### Test API
```bash
curl -k https://localhost/api/status
# Expected: {"status":"online", "server":"Pandora FastAPI Webserver", ...}
```

### Test Backend
```bash
curl http://127.0.0.1:8000/health
# Expected: {"status":"healthy", ...}
```

### Check Services
```bash
sudo systemctl status pandora-*
# Tất cả phải: active (running)
```

### Check Logs
```bash
# Nginx logs
sudo tail -f /var/log/nginx/pandora_access.log

# Webserver logs
sudo journalctl -u pandora-webserver -f

# IDS logs
sudo journalctl -u pandora-ids -f
```

---

## 🔟 Access Points

### Main Application (Public)
- **URL:** https://localhost (hoặc https://your-domain.com)
- **Port:** 443 (HTTPS)

### Admin Dashboard (Localhost only)
- **URL:** https://localhost/admin-dashboard/
- **Access:** Chỉ từ localhost qua Nginx

**Nếu cần access từ xa:**
```bash
# SSH Tunnel
ssh -L 5000:localhost:5000 user@your-server
# Sau đó mở: http://localhost:5000 trên máy local (bypass Nginx)
```

### API Endpoints
- **User API:** https://localhost/api/user/
- **Admin API:** https://localhost/api/admin/ (localhost only)

---

## 🔧 Troubleshooting

### Lỗi: "Address already in use"
```bash
# Check port
sudo lsof -i :443

# Kill process
sudo kill -9 <PID>
```

### Lỗi: "502 Bad Gateway"
```bash
# Check backend services
sudo systemctl status pandora-webserver
sudo systemctl status pandora-backend-user

# Restart
sudo systemctl restart pandora-webserver
```

### Lỗi: "Permission denied"
```bash
# Nginx cần quyền root cho port 443
sudo systemctl restart nginx

# IDS cần quyền root
sudo systemctl restart pandora-ids
```

### Lỗi: "Frontend not built"
```bash
cd /opt/pandora/frontend
npm run build
sudo systemctl restart pandora-webserver
```

---

## 📊 Monitoring

```bash
# Check all services
sudo systemctl status pandora-*

# Real-time logs
sudo journalctl -u pandora-nginx -f

# Check database
sudo -u postgres psql pandora_admin -c "SELECT COUNT(*) FROM honeypot_logs;"
sudo -u postgres psql pandora_admin -c "SELECT COUNT(*) FROM attack_logs;"
```

---

## 🛑 Stop All Services

```bash
sudo /opt/pandora/deploy/stop-all-services.sh
```

---

## 📚 Tài liệu đầy đủ

- **Architecture:** `ARCHITECTURE.md`
- **Deployment:** `deploy/DEPLOYMENT-GUIDE-NEW-ARCHITECTURE.md`
- **Refactoring:** `REFACTORING_SUMMARY.md`
- **IDS Analysis:** `ids/IDS_ENGINE_ANALYSIS.md`
- **Deprecation:** `custom-webserver/DEPRECATION_NOTE.md`

---

## 🎯 Default Credentials

**PostgreSQL:**
- User: `pandora`
- Password: `changeme123` (THAY ĐỔI NGAY!)

**Admin Monitor:**
- Xem `central-monitor/auth_config.py`

---

## ✅ Checklist

- [ ] Database created
- [ ] Backend services installed
- [ ] Frontend built
- [ ] SSL certificate generated
- [ ] Nginx configured
- [ ] Systemd services installed
- [ ] All services running
- [ ] HTTP redirect works
- [ ] HTTPS works
- [ ] API responds
- [ ] Firewall configured (chỉ mở 80, 443)

---

## 🚀 Next Steps

1. Thay đổi password database
2. Cấu hình Let's Encrypt (production)
3. Setup firewall (ufw/iptables)
4. Configure email alerts
5. Setup Elasticsearch (optional)
6. Monitor logs và performance

---

**Chúc mừng! Hệ thống đã sẵn sàng! 🎉**

