<!-- 0bf39ae6-81af-474b-a525-86d4ad8814c4 9154355d-9a41-426d-bca5-29bd458b2dd1 -->
# Plan: Tách Honeypot và Central Monitor thành 2 Servers

## Kiến trúc mới

### HONEYPOT SERVER (Public - IP: X.X.X.X)

```
Internet → Nginx (80/443, SSL) → Custom Webserver (8443)
                                      ↓
                    ┌─────────────────┴──────────────┐
                    ↓                                ↓
              Fake Paths                        Real Paths
              /admin                            /app/*
              /phpmyadmin                       /dashboard
              /wp-admin                         /scan
              /.env                             /api/user/*
              /config.php                              ↓
              → Fake HTML                    Backend-user (8001)
                                                      ↓
                                            Send logs to Central Monitor
```

### CENTRAL MONITOR SERVER (Internal - IP: Y.Y.Y.Y)

```
Admin Only → Nginx (443, SSL) → Central Monitor (5000)
                               → Backend-admin (8002)
                                      ↓
                        ┌─────────────┴──────────────┐
                        ↓                            ↓
                  PostgreSQL                    IDS Engine
                  (All databases)               (Sniff Honeypot traffic)
                  - user_db
                  - admin_db
                  - honeypot_logs
                  - attack_logs
```

## Tasks

### 1. Honeypot Server - Custom Webserver (Fake + Real)

**File: `custom-webserver/honeypot_server.py`** (Tạo mới)

Routing logic:

- Fake paths (đứng trước, nhiều): `/admin`, `/phpmyadmin`, `/wp-admin`, `/config`, `/.env`, `/api/admin`, `/administrator`, `/cpanel`, `/backup`, etc
        - Return fake HTML responses
        - Log to Central Monitor (high priority)
- Real paths (ẩn sau): `/app/*`, `/dashboard`, `/scan`, `/login`, `/register`
        - Serve Vue.js SPA
        - Log to Central Monitor (normal priority)
- API paths: `/api/user/*`
        - Proxy to Backend-user (localhost:8001)

Fake responses:

```python
# Fake admin login page
@app.get("/admin")
async def fake_admin():
    return HTMLResponse("""
    <html><head><title>Admin Panel</title></head>
    <body><h1>Admin Login</h1>
    <form><input name="user"><input name="pass" type="password">
    <button>Login</button></form></body></html>
    """)

# Fake phpMyAdmin
@app.get("/phpmyadmin")
async def fake_phpmyadmin():
    return HTMLResponse("<html>phpMyAdmin 4.9.5...</html>")
```

Log mọi request về Central Monitor:

```python
async def log_to_central_monitor(request_data):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{CENTRAL_MONITOR_URL}/api/admin/honeypot/log",
            json=request_data,
            timeout=5
        )
```

### 2. Honeypot Server - Backend-user

**File: `backend-user/api/main.py`** (Sửa)

Thay đổi:

- Không kết nối database local
- Gửi tất cả logs về Central Monitor qua API
- Authentication: Gọi API của Central Monitor để verify user
- Scan history: Gọi API của Central Monitor để lưu/lấy
```python
# Thay vì:
db = SessionLocal()
scan = Scan(...)
db.add(scan)

# Thành:
async with httpx.AsyncClient() as client:
    await client.post(
        f"{CENTRAL_MONITOR_URL}/api/admin/scans/create",
        json=scan_data
    )
```


### 3. Honeypot Server - Nginx Config

**File: `honeypot-server/nginx.conf`** (Tạo mới)

Đơn giản hơn, chỉ proxy:

```nginx
server {
    listen 443 ssl http2;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Tất cả traffic → Custom Webserver (8443)
    location / {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 4. Central Monitor Server - Backend-admin

**File: `backend-admin/api/main.py`** (Sửa)

Thêm endpoints nhận logs từ Honeypot:

```python
@app.post("/api/admin/honeypot/log")
async def receive_honeypot_log(log_data: dict):
    # Lưu vào PostgreSQL local
    db = SessionLocal()
    log = HoneypotLog(**log_data)
    db.add(log)
    db.commit()
    return {"status": "logged"}

@app.post("/api/admin/scans/create")
async def receive_scan_result(scan_data: dict):
    # Lưu scan history
    db = SessionLocal()
    scan = Scan(**scan_data)
    db.add(scan)
    db.commit()
    return {"status": "saved"}
```

### 5. Central Monitor Server - IDS Engine

**File: `ids/ids_engine.py`** (Sửa)

Cấu hình sniff traffic từ Honeypot Server (remote):

```python
# Option 1: Sniff trên chính Central Monitor (nếu ở cùng network)
engine = IDSEngine(interface='eth0')

# Option 2: Nhận logs từ remote IDS agent trên Honeypot
# (Honeypot chạy lightweight IDS, gửi về Central)
```

### 6. Central Monitor Server - Nginx Config

**File: `central-monitor-server/nginx.conf`** (Tạo mới)

Bảo mật cao, chỉ cho admin:

```nginx
server {
    listen 443 ssl http2;
    
    # Chỉ cho phép IP admin
    allow <admin-ip>;
    deny all;
    
    location /dashboard/ {
        proxy_pass http://127.0.0.1:5000/;
    }
    
    location /api/admin/ {
        proxy_pass http://127.0.0.1:8002/;
    }
}
```

### 7. Frontend - Vue.js

**File: `frontend/src/services/api.js`** (Sửa)

Change base URL:

```javascript
// Honeypot Server sẽ serve Vue.js ở /app/*
const API_BASE = '/api/user'  // Giữ nguyên
```

**File: `frontend/src/router/index.js`** (Sửa)

Thêm base path:

```javascript
const router = createRouter({
  history: createWebHistory('/app/'),  // Real app ẩn ở /app/*
  routes: [...]
})
```

### 8. Database Configuration

**Honeypot Server:**

- Xóa tất cả database connections
- Environment variables:
  ```
  CENTRAL_MONITOR_URL=https://Y.Y.Y.Y
  CENTRAL_MONITOR_API_KEY=<secret-key>
  ```


**Central Monitor Server:**

- PostgreSQL với tất cả databases:
        - `pandora_user` (users, scans)
        - `pandora_admin` (honeypot_logs, attack_logs)

### 9. Deployment Scripts

**Honeypot Server: `deploy-honeypot.sh`**

```bash
# Install services
systemctl enable pandora-nginx-honeypot
systemctl enable pandora-honeypot-webserver
systemctl enable pandora-backend-user

# No database, no IDS
```

**Central Monitor Server: `deploy-central.sh`**

```bash
# Install services
systemctl enable pandora-nginx-central
systemctl enable pandora-central-monitor
systemctl enable pandora-backend-admin
systemctl enable pandora-ids
systemctl enable postgresql
systemctl enable elasticsearch
```

## Security Enhancements

### Honeypot Server (Public):

- NO sensitive data stored locally
- All logs sent to Central Monitor immediately
- Rate limiting on Nginx
- Fake responses for common exploit paths
- Real app hidden behind non-obvious paths

### Central Monitor Server (Admin only):

- Firewall: Only allow admin IPs
- VPN recommended
- Strong authentication
- All databases here
- Monitor Honeypot health

## Testing

1. Test fake paths on Honeypot:
   ```bash
   curl https://X.X.X.X/admin
   curl https://X.X.X.X/phpmyadmin
   # Expected: Fake HTML responses
   ```

2. Test real app on Honeypot:
   ```bash
   curl https://X.X.X.X/app/
   # Expected: Vue.js HTML
   ```

3. Test Central Monitor receives logs:
   ```bash
   # On Central Monitor
   psql -U pandora pandora_admin -c "SELECT COUNT(*) FROM honeypot_logs;"
   ```

4. Test IDS on Central Monitor:
   ```bash
   # Scan Honeypot from external
   nmap -sS X.X.X.X
   # Check Central Monitor logs
   ```


## Configuration Files Summary

New files to create:

- `honeypot-server/nginx.conf`
- `honeypot-server/systemd/*.service`
- `central-monitor-server/nginx.conf`
- `central-monitor-server/systemd/*.service`
- `custom-webserver/honeypot_server.py` (new, replace webserver_fastapi.py)
- `deploy/deploy-honeypot.sh`
- `deploy/deploy-central.sh`

Files to modify:

- `backend-user/api/main.py` (remove DB, add API calls to Central)
- `backend-user/config.py` (add CENTRAL_MONITOR_URL)
- `backend-admin/api/main.py` (add endpoints to receive logs)
- `frontend/src/router/index.js` (base path /app/)
- `ids/ids_engine.py` (optional: remote monitoring)

Files to keep:

- `frontend/src/services/api.js` (already correct)
- `central-monitor/monitor_server.py` (no change)

### To-dos

- [ ] Create honeypot_server.py with fake paths + real paths routing
- [ ] Create Honeypot Server nginx config (simple, all to port 8443)
- [ ] Modify backend-user to send logs to Central Monitor via API
- [ ] Add endpoints in backend-admin to receive logs from Honeypot
- [ ] Update Vue.js router with /app/ base path
- [ ] Create Central Monitor nginx config (secure, IP restricted)
- [ ] Create deploy-honeypot.sh and deploy-central.sh
- [ ] Create systemd services for both servers
- [ ] Update deployment docs for 2-server architecture
- [ ] Make sure this architecture is ready-production, build it for deploy right away. Not testing local