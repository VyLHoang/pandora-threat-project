# 🌐 Pandora Custom Web Servers

## 📁 Cấu trúc

```
custom-webserver/
├── port_80.py          # HTTP server (redirects to HTTPS)
├── port_443.py         # HTTPS server (serves Vue.js frontend)
├── server.crt          # SSL certificate (auto-generated)
├── server.key          # SSL private key (auto-generated)
└── requirements.txt    # Python dependencies
```

---

## 🎯 Chức năng

### **Port 80 (HTTP):**
- Redirect TẤT CẢ traffic sang HTTPS
- Log mọi request
- Honeypot: Thu thập thông tin attackers
- **Security best practice:** Always use HTTPS

### **Port 443 (HTTPS):**
- Serve Vue.js frontend (from `/frontend/dist`)
- Encrypt all traffic with TLS
- Log authenticated/anonymous activities
- Honeypot: Bait for attackers
- Proxy API requests to Backend-User

---

## 🚀 Cách chạy

### **Trên Windows (Local Test):**

#### **Option 1: Batch Script (Recommended)**
```bash
# From project root
cd E:\port\threat_project
.\deploy\TEST-LOCAL-WINDOWS.bat
```

#### **Option 2: Manual**
```bash
# Terminal 1: HTTP Server
cd E:\port\threat_project\custom-webserver
python port_80.py

# Terminal 2: HTTPS Server
cd E:\port\threat_project\custom-webserver
python port_443.py
```

**⚠️ Lưu ý:** Port 80 và 443 cần **Admin Rights** trên Windows!
- Right-click Command Prompt → Run as Administrator

---

### **Trên Linux/VPS (Production):**

#### **Option 1: Systemd Services (Recommended)**
```bash
# Deploy with automation
sudo bash deploy/deploy-listeners.sh

# Manual control
sudo systemctl start pandora-http-80
sudo systemctl start pandora-https-443
sudo systemctl status pandora-http-80
sudo systemctl status pandora-https-443
```

#### **Option 2: Manual**
```bash
# HTTP
sudo python3 port_80.py

# HTTPS
sudo python3 port_443.py
```

---

## 🔒 SSL Certificates

### **Self-Signed (Development/Honeypot):**

**Auto-generate:**
```bash
cd custom-webserver

# Linux/Mac
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout server.key -out server.crt -days 365 \
    -subj "/CN=localhost"

# Windows (PowerShell)
openssl req -x509 -newkey rsa:4096 -nodes `
    -keyout server.key -out server.crt -days 365 `
    -subj "/CN=localhost"
```

**Files generated:**
- `server.crt` - Public certificate
- `server.key` - Private key

**⚠️ Browser Warning:**
- Self-signed certificates will show a security warning
- For honeypot purposes: This is NORMAL and EXPECTED
- Click "Advanced" → "Proceed to site" (or equivalent)

---

### **Let's Encrypt (Production):**

**For a real domain:**
```bash
# Install Certbot
sudo apt install -y certbot

# Get certificate (replace yourdomain.com)
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem

# Update port_443.py to use new paths
```

---

## 🧪 Testing

### **From Browser:**
```
http://localhost          → Should redirect to https://localhost
https://localhost         → Should show Vue.js frontend
https://localhost/api/status → Should return JSON
```

### **From curl:**
```bash
# HTTP (will redirect)
curl -v http://localhost

# HTTPS (self-signed cert)
curl -k https://localhost

# API endpoint
curl -k https://localhost/api/status
curl -k https://localhost/api/server-info
```

### **From PowerShell:**
```powershell
# HTTP
Invoke-WebRequest http://localhost

# HTTPS
Invoke-WebRequest https://localhost -SkipCertificateCheck

# JSON response
(Invoke-WebRequest https://localhost/api/status -SkipCertificateCheck).Content | ConvertFrom-Json
```

---

## 📊 Honeypot Features

### **What gets logged:**

**HTTP (Port 80):**
- All incoming requests (before redirect)
- Source IPs
- User agents
- Request paths
- Headers
- Attack attempts (SQL injection, path traversal, etc.)

**HTTPS (Port 443):**
- All web application activity
- Login attempts (successful/failed)
- Scan submissions
- API calls
- Suspicious behavior
- Bot/scraper detection

### **Where logs go:**
1. **Console output:** Real-time display
2. **PostgreSQL:** `honeypot_logs` table
3. **Elasticsearch:** `pandora-honeypot-logs-*` index
4. **Central Monitor:** Web UI at http://localhost:22002/honeypot

---

## 🔧 Configuration

### **port_80.py:**
```python
# Server settings
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 80

# HTTPS redirect target
HTTPS_PORT = 443
```

### **port_443.py:**
```python
# Server settings
HOST = '0.0.0.0'
PORT = 443

# SSL certificate paths
CERT_FILE = 'server.crt'
KEY_FILE = 'server.key'

# Backend API
BACKEND_URL = 'http://localhost:8000'

# Frontend directory
FRONTEND_DIR = '../frontend/dist'
```

---

## 🌐 Architecture

```
Internet/User
    ↓
Port 80 (HTTP) ────[301 Redirect]────→ Port 443 (HTTPS)
    ↓                                        ↓
[Log Request]                          [Serve Frontend]
    ↓                                        ↓
PostgreSQL                            Vue.js App (Static)
Elasticsearch                              ↓
                                     [API Requests]
                                           ↓
                                    Backend-User (8000)
                                           ↓
                                    PostgreSQL (User DB)
                                    Elasticsearch
```

---

## 🐛 Troubleshooting

### **Error: Permission denied (Port 80/443)**

**Windows:**
```
Run Command Prompt as Administrator
```

**Linux:**
```bash
# Run with sudo
sudo python3 port_80.py

# OR use systemd service (recommended)
sudo systemctl start pandora-http-80
```

---

### **Error: Port already in use**

**Windows:**
```powershell
# Find process using port
netstat -ano | findstr :80
netstat -ano | findstr :443

# Kill process (replace PID)
taskkill /F /PID <PID>
```

**Linux:**
```bash
# Find process
sudo lsof -i :80
sudo lsof -i :443

# Kill process
sudo kill -9 <PID>
```

---

### **Error: SSL certificate not found**

```bash
cd custom-webserver

# Generate new certificate
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout server.key -out server.crt -days 365 \
    -subj "/CN=localhost"
```

---

### **Browser won't connect to HTTPS**

1. **Accept self-signed certificate:**
   - Chrome: Type `thisisunsafe` on the warning page
   - Firefox: Click "Advanced" → "Accept Risk and Continue"
   - Edge: Click "Advanced" → "Continue to localhost"

2. **Check if server is running:**
   ```bash
   # Test with curl
   curl -k https://localhost
   ```

3. **Check firewall:**
   ```bash
   # Windows: Allow in Windows Firewall
   # Linux: sudo ufw allow 443/tcp
   ```

---

## 📈 Performance

### **Expected Load:**
- **HTTP (Port 80):** Minimal (just redirects)
- **HTTPS (Port 443):** Moderate (serves frontend + API proxy)

### **Resource Usage:**
- **CPU:** ~2-5% per server (idle)
- **Memory:** ~50-100 MB per server
- **Disk I/O:** Minimal

### **Scaling:**
- For high traffic: Use Nginx/Apache as reverse proxy
- For load balancing: Deploy multiple instances
- For CDN: Serve static assets from CloudFlare

---

## 🔐 Security

### **Best Practices:**

1. **Always use HTTPS in production**
2. **Keep SSL certificates updated**
3. **Monitor logs for attacks**
4. **Use strong ciphers (TLS 1.2+)**
5. **Enable rate limiting**
6. **Filter suspicious IPs**
7. **Regular security audits**

### **Honeypot Mode:**
- Self-signed certificates are INTENTIONAL
- Designed to attract attackers
- All activities logged and analyzed
- Fake data served to waste attacker time

---

## 📞 Support

**View logs:**
```bash
# Systemd
sudo journalctl -u pandora-http-80 -f
sudo journalctl -u pandora-https-443 -f

# Manual run
# See console output
```

**Common Issues:**
- Port conflicts → Change port or kill conflicting process
- Permission errors → Run as admin/sudo
- Certificate errors → Regenerate or accept in browser
- Can't connect → Check firewall settings

---

**Version:** 1.0.0  
**Status:** Production Ready 🚀  
**Purpose:** Honeypot Web Servers for Threat Intelligence

