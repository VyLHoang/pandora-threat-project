# Hướng dẫn Routing - Pandora Threat Project

## 📌 Tổng quan

Nginx là **cổng vào duy nhất** của hệ thống. Tất cả traffic từ Internet phải đi qua Nginx trên port 443 (HTTPS).

---

## 🌐 URL Routing (External Access)

### 1. Vue.js Frontend + Honeypot (Public)
```
URL: https://your-domain.com/
Backend: FastAPI Honeypot (Port 8443)
Access: Public
```

**Chức năng:**
- Serve Vue.js Single Page Application
- Log mọi request vào `honeypot_logs` table
- Detect suspicious patterns (SQL injection, XSS, etc.)

**Ví dụ:**
```bash
curl -k https://localhost/
curl -k https://localhost/login
curl -k https://localhost/dashboard
```

---

### 2. User API (Public với Rate Limiting)
```
URL: https://your-domain.com/api/user/*
Backend: FastAPI User Backend (Port 8001)
Access: Public
```

**Endpoints:**

#### 2.1 Authentication
```bash
# Login
curl -k -X POST https://localhost/api/user/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Register
curl -k -X POST https://localhost/api/user/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","username":"testuser"}'

# Health check
curl -k https://localhost/api/user/auth/health
```

#### 2.2 VirusTotal Scanning
```bash
# Scan IP
curl -k -X POST https://localhost/api/user/scan/ip \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"ip_address":"8.8.8.8"}'

# Scan Hash
curl -k -X POST https://localhost/api/user/scan/hash \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"file_hash":"<hash>"}'
```

#### 2.3 Scan History
```bash
curl -k https://localhost/api/user/history/ \
  -H "Authorization: Bearer <your-token>"
```

#### 2.4 User Profile
```bash
curl -k https://localhost/api/user/profile/ \
  -H "Authorization: Bearer <your-token>"
```

**Rate Limits:**
- Authentication: 5 req/s
- Scan: 30 req/s
- Other: 30 req/s

---

### 3. Admin API (Localhost Only)
```
URL: https://your-domain.com/api/admin/*
Backend: FastAPI Admin Backend (Port 8002)
Access: Localhost only
```

**⚠️ Security:** Nginx chặn tất cả requests từ external IPs

**Endpoints:**

#### 3.1 Honeypot Logs
```bash
# Get honeypot activities (chỉ từ localhost)
curl http://127.0.0.1:8002/honeypot/activities

# Via Nginx (chỉ từ localhost)
curl -k https://localhost/api/admin/honeypot/activities
```

#### 3.2 Attack Logs
```bash
# Get attack logs
curl http://127.0.0.1:8002/attacks/

# Via Nginx
curl -k https://localhost/api/admin/attacks/
```

#### 3.3 User Monitoring
```bash
# Get user activities
curl http://127.0.0.1:8002/users/activities
```

**Nếu cần access từ remote:**
```bash
# SSH Tunnel
ssh -L 8002:localhost:8002 user@your-server
# Sau đó: curl http://localhost:8002/...
```

---

### 4. Admin Dashboard (Localhost Only)
```
URL: https://your-domain.com/admin-dashboard/
Backend: Flask Central Monitor (Port 5000)
Access: Localhost only
```

**⚠️ Security:** Nginx chặn tất cả requests từ external IPs

**Chức năng:**
- Real-time attack monitoring
- Honeypot activity dashboard
- User behavior analytics
- Interactive threat maps

**Access từ localhost:**
```bash
# Direct
curl http://127.0.0.1:5000/

# Via Nginx
curl -k https://localhost/admin-dashboard/
```

**Access từ remote (SSH Tunnel):**
```bash
# Tạo SSH tunnel
ssh -L 5000:localhost:5000 user@your-server

# Mở browser trên máy local
firefox http://localhost:5000
```

---

## 🔒 Security Matrix

| Service | External Access | Localhost Access | Authentication | Rate Limit |
|---------|----------------|------------------|----------------|------------|
| **Vue.js Frontend** | ✅ Public | ✅ | Optional | 10 req/s |
| **User API** | ✅ Public | ✅ | Required (JWT) | 5-30 req/s |
| **Admin API** | ❌ Blocked | ✅ | - | - |
| **Admin Dashboard** | ❌ Blocked | ✅ | - | - |

---

## 🧪 Testing Routing

### Test 1: Frontend (Public)
```bash
curl -k https://localhost/
# Expected: HTML của Vue.js
```

### Test 2: User API (Public)
```bash
curl -k https://localhost/api/user/auth/health
# Expected: {"status":"healthy"}
```

### Test 3: Admin API (Blocked từ external)
```bash
# Từ máy external
curl -k https://your-server-ip/api/admin/honeypot/activities
# Expected: 403 Forbidden

# Từ localhost
curl -k https://localhost/api/admin/honeypot/activities
# Expected: {"activities": [...]}
```

### Test 4: Admin Dashboard (Blocked từ external)
```bash
# Từ máy external
curl -k https://your-server-ip/admin-dashboard/
# Expected: 403 Forbidden

# Từ localhost
curl -k https://localhost/admin-dashboard/
# Expected: HTML của Flask dashboard
```

---

## 🔧 Nginx Configuration (Reference)

```nginx
# Admin Dashboard (localhost only)
location /admin-dashboard/ {
    allow 127.0.0.1;
    deny all;
    proxy_pass http://127.0.0.1:5000/;
}

# Admin API (localhost only)
location /api/admin/ {
    allow 127.0.0.1;
    deny all;
    proxy_pass http://127.0.0.1:8002/;
}

# User API (public với rate limiting)
location /api/user/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://127.0.0.1:8001/api/v1/;
}

# Frontend + Honeypot (default, public)
location / {
    limit_req zone=general burst=20 nodelay;
    proxy_pass http://127.0.0.1:8443;
}
```

---

## 📊 Traffic Flow

### Scenario 1: User login
```
Browser
  → https://your-domain.com/login
  → Nginx (Port 443, SSL)
  → Honeypot (Port 8443) - Log request
  → Serve Vue.js login page
  → User submits form
  → POST https://your-domain.com/api/user/auth/login
  → Nginx
  → User Backend (Port 8001)
  → PostgreSQL
  → Return JWT token
```

### Scenario 2: Admin monitoring
```
Admin Browser (từ server)
  → https://localhost/admin-dashboard/
  → Nginx (Port 443, SSL)
  → Check IP (127.0.0.1) - PASS
  → Central Monitor (Port 5000)
  → Render Flask template
  → Query Admin Backend (Port 8002)
  → PostgreSQL (honeypot_logs, attack_logs)
  → Display dashboard
```

### Scenario 3: Attack attempt
```
Attacker
  → https://your-domain.com/admin/config.php?id=1' OR '1'='1
  → Nginx (Port 443, SSL)
  → Honeypot (Port 8443)
  → Calculate suspicious_score (85/100)
  → Log to honeypot_logs
  → Return 404 (or fake response)
  
Parallel:
  → IDS Engine (Scapy)
  → Sniff packet at network level
  → Detect port scan
  → Log to attack_logs
```

---

## 🚨 Troubleshooting

### Lỗi: 403 Forbidden khi access Admin Dashboard từ browser
**Nguyên nhân:** Admin Dashboard chỉ cho phép localhost

**Giải pháp:**
1. Access từ server: `curl http://localhost:5000`
2. SSH Tunnel:
   ```bash
   ssh -L 5000:localhost:5000 user@server
   firefox http://localhost:5000
   ```
3. Tạm thời mở access (KHÔNG khuyến khích):
   ```nginx
   location /admin-dashboard/ {
       allow <your-ip>;  # Thêm IP của bạn
       allow 127.0.0.1;
       deny all;
   }
   ```

### Lỗi: 502 Bad Gateway
**Nguyên nhân:** Backend service chưa chạy

**Giải pháp:**
```bash
# Check services
sudo systemctl status pandora-backend-user
sudo systemctl status pandora-backend-admin
sudo systemctl status pandora-central-monitor
sudo systemctl status pandora-webserver

# Restart
sudo systemctl restart pandora-backend-user
```

### Lỗi: 429 Too Many Requests
**Nguyên nhân:** Vượt quá rate limit

**Giải pháp:**
- Chờ 1 phút
- Hoặc tăng rate limit trong `nginx.conf`:
  ```nginx
  limit_req_zone $binary_remote_addr zone=api:10m rate=50r/s;  # Tăng từ 30 lên 50
  ```

---

## 🎯 Best Practices

1. **Luôn dùng HTTPS**: Tất cả traffic phải qua port 443
2. **Không expose ports nội bộ**: Firewall phải block 5000, 8001, 8002, 8443
3. **Dùng JWT cho authentication**: User API yêu cầu Bearer token
4. **SSH Tunnel cho admin access**: Không mở Admin Dashboard ra Internet
5. **Monitor logs**: `sudo journalctl -u pandora-nginx -f`
6. **Rate limiting**: Đừng spam API, sẽ bị block

---

## 📚 Related Docs

- **Architecture**: `ARCHITECTURE.md`
- **Deployment**: `deploy/DEPLOYMENT-GUIDE-NEW-ARCHITECTURE.md`
- **Security**: `SECURITY.md`

---

**Last Updated**: 2025-10-23  
**Version**: 2.0.0

