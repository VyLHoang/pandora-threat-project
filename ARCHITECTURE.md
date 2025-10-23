# Pandora Threat Project - Kiến trúc Hệ thống (v2.0)

## Tổng quan

Pandora là một nền tảng Threat Intelligence tích hợp Honeypot và IDS (Intrusion Detection System) để phát hiện, phân tích và monitor các mối đe dọa mạng.

---

## Kiến trúc Tổng thể

```
                           ┌──────────────────────────────────────┐
                           │          INTERNET                    │
                           └──────────────┬───────────────────────┘
                                          │
                                          ↓
                           ┌──────────────────────────────────────┐
                           │   NETWORK INTERFACE (eth0/ens33)     │
                           └──────────────┬───────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
                    ↓ (Packet Level)                            ↓ (HTTP Level)
          ┌──────────────────────┐                  ┌──────────────────────┐
          │    IDS Engine        │                  │   Nginx (Port 443)   │
          │   (Scapy Sniffer)    │                  │  SSL/TLS Termination │
          │                      │                  └──────────┬───────────┘
          │  - Port Scan         │                             │
          │  - SYN Flood         │                             ↓
          │  - Attack Detection  │              ┌──────────────────────────────┐
          │                      │              │  FastAPI Webserver (8443)    │
          │  → attack_logs DB    │              │  - Serve Vue.js SPA          │
          └──────────────────────┘              │  - Honeypot Logging          │
                                                │  - Suspicious Detection      │
                                                └──────────┬───────────────────┘
                                                           │
                                                           ↓
                                   ┌───────────────────────┴───────────────────┐
                                   │                                           │
                                   ↓                                           ↓
                    ┌──────────────────────────┐              ┌──────────────────────────┐
                    │  User Backend (8000)     │              │  Admin Backend (9000)    │
                    │  - Authentication        │              │  - Honeypot Management   │
                    │  - VirusTotal Scan       │              │  - Attack Logs           │
                    │  - Scan History          │              │  - User Monitoring       │
                    │                          │              │                          │
                    │  → user_db               │              │  → admin_db              │
                    └──────────────────────────┘              └──────────────────────────┘
                                   │                                           │
                                   └───────────────────┬───────────────────────┘
                                                       │
                                                       ↓
                                        ┌──────────────────────────┐
                                        │    PostgreSQL (5432)     │
                                        │  - pandora_user DB       │
                                        │  - pandora_admin DB      │
                                        │    • honeypot_logs       │
                                        │    • attack_logs         │
                                        │    • scan_history        │
                                        └──────────────────────────┘
```

---

## Luồng Dữ liệu

### 1. Luồng HTTP Request (Normal User)

```
User Browser 
    → HTTPS Request (Port 443)
    → Nginx (SSL Termination)
    → FastAPI Webserver (Port 8443)
    → Vue.js Frontend (HTML/JS/CSS)
    → User Backend API (Port 8000)
    → PostgreSQL
    → Response back to User
```

**Log points:**
- **Nginx:** Access log (IP, URL, status)
- **FastAPI:** Honeypot log (request details, suspicious score)
- **Backend:** Application log (API calls, errors)

### 2. Luồng Attack Detection (IDS)

```
Attacker (Port Scan)
    → Network Interface
    → IDS Engine (Scapy Sniff)
    → Detect Pattern (SYN scan, multiple ports)
    → Log to attack_logs table
    → Email Alert (optional)
    → Elasticsearch (optional)
```

**Detection types:**
- Port Scan (nmap, masscan)
- SYN Flood
- Critical Port Probes (SSH, RDP, DB)

### 3. Luồng Honeypot Logging (Application Layer)

```
Attacker sends malicious request
    → https://localhost/admin/config.php?id=1' OR '1'='1
    → Nginx (forward to FastAPI)
    → FastAPI Middleware (log request)
    → Calculate suspicious_score (85/100)
    → Log to honeypot_logs table
    → Elasticsearch (optional)
    → Response (404 or honeypot response)
```

**Detection patterns:**
- SQL Injection
- XSS attempts
- Path Traversal
- Suspicious User Agents (sqlmap, nmap, nikto)

---

## Components Chi tiết

### 1. Nginx Reverse Proxy

**File:** `nginx/nginx.conf`  
**Port:** 80 (HTTP), 443 (HTTPS)  
**Chức năng:**
- SSL/TLS Termination (giải mã HTTPS)
- HTTP → HTTPS Redirect (301)
- Reverse Proxy cho các services
- Rate Limiting (DDoS protection)
- Security Headers (HSTS, X-Frame-Options)

**Proxy Rules:**
- `/api/v1/auth/` → User Backend (8000)
- `/api/v1/scan/` → User Backend (8000)
- `/api/v1/honeypot/` → Admin Backend (9000) - **localhost only**
- `/api/v1/attacks/` → Admin Backend (9000) - **localhost only**
- `/` → FastAPI Webserver (8443)

### 2. FastAPI Webserver

**File:** `custom-webserver/webserver_fastapi.py`  
**Port:** 8443 (HTTP, localhost only)  
**Framework:** FastAPI + Uvicorn  
**Chức năng:**
- Serve Vue.js static files (SPA)
- Honeypot logging (middleware)
- Suspicious request detection
- Real IP tracking (X-Forwarded-For)

**Key Features:**
- Async/non-blocking logging
- JWT token parsing (user tracking)
- Suspicious score calculation (0-100)
- Elasticsearch integration

### 3. User Backend API

**Directory:** `backend-user/`  
**Port:** 8000 (HTTP, localhost only)  
**Framework:** FastAPI  
**Database:** `pandora_user`  
**Endpoints:**
- `/api/v1/auth/login` - Authentication
- `/api/v1/auth/register` - User registration
- `/api/v1/scan/ip` - VirusTotal IP scan
- `/api/v1/scan/hash` - VirusTotal hash scan
- `/api/v1/history/` - Scan history
- `/api/v1/user/profile` - User profile

**Tables:**
- `users` - User accounts
- `scan_history` - VirusTotal scan results

### 4. Admin Backend API

**Directory:** `backend-admin/`  
**Port:** 9000 (HTTP, localhost only)  
**Framework:** FastAPI  
**Database:** `pandora_admin`  
**Endpoints:**
- `/api/v1/honeypot/log` - Log honeypot activity
- `/api/v1/honeypot/activities` - Get honeypot logs
- `/api/v1/attacks/` - Get attack logs
- `/api/v1/users/` - Monitor user activities

**Tables:**
- `honeypot_logs` - Application-level attack logs
- `attack_logs` - Network-level attack logs (from IDS)

### 5. IDS Engine

**File:** `ids/ids_engine.py`  
**Framework:** Scapy  
**Privileges:** Root/Admin required  
**Chức năng:**
- Network packet sniffing (raw sockets)
- Attack pattern detection
- GeoIP lookup
- Email alerts

**Detection Rules:**
- Port Scan: ≥3 ports in 60 seconds
- SYN Flood: ≥20 SYNs in 10 seconds
- Critical Port Probe: Multiple attempts to SSH/RDP/DB ports

**Filtering:**
- Chỉ monitor INBOUND traffic (external → local)
- Skip OUTBOUND traffic (local → external)
- Skip established connections (ACK flag)
- Skip return traffic (src_port = 80/443)

### 6. Central Monitor Dashboard

**Directory:** `central-monitor/`  
**Port:** 3000 (HTTP, localhost only)  
**Framework:** Flask + Jinja2  
**Chức năng:**
- Real-time attack monitoring
- Honeypot activity dashboard
- User behavior analytics
- Interactive maps (GeoIP visualization)

**Access:** `http://localhost:3000` (SSH tunnel cho remote access)

---

## Database Schema

### honeypot_logs (Admin DB)

```sql
CREATE TABLE honeypot_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,                    -- Nếu user đã login
    is_authenticated BOOLEAN,
    session_id VARCHAR(255),
    client_ip VARCHAR(45),
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path TEXT,
    request_headers JSONB,
    request_body TEXT,
    response_status INTEGER,
    response_size INTEGER,
    activity_type VARCHAR(50),          -- page_view, scan, login_attempt
    suspicious_score INTEGER,           -- 0-100
    suspicious_reasons TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);
```

### attack_logs (Admin DB)

```sql
CREATE TABLE attack_logs (
    id SERIAL PRIMARY KEY,
    source_ip VARCHAR(45),
    source_port INTEGER,
    target_ip VARCHAR(45),
    target_port INTEGER,
    attack_type VARCHAR(100),           -- port_scan, syn_flood, ssh_probe
    severity VARCHAR(20),               -- low, medium, high, critical
    packet_count INTEGER,
    protocol VARCHAR(10),               -- TCP, UDP, ICMP
    flags VARCHAR(20),                  -- SYN, ACK, FIN, etc.
    payload_sample TEXT,
    country VARCHAR(100),
    city VARCHAR(100),
    latitude VARCHAR(20),
    longitude VARCHAR(20),
    detected_tool VARCHAR(100),         -- nmap, masscan, unknown
    confidence INTEGER,                 -- 0-100
    raw_packet_info JSONB,
    detected_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP
);
```

---

## Security Features

### 1. Network Level (IDS)
- ✅ Port scan detection
- ✅ SYN flood detection
- ✅ Packet anomaly detection
- ✅ GeoIP blocking (optional)

### 2. Application Level (Honeypot)
- ✅ SQL injection detection
- ✅ XSS detection
- ✅ Path traversal detection
- ✅ Suspicious user agent detection
- ✅ User behavior tracking

### 3. Transport Level (Nginx)
- ✅ SSL/TLS encryption (TLS 1.2+)
- ✅ Rate limiting (10 req/s general, 30 req/s API)
- ✅ DDoS protection
- ✅ Security headers (HSTS, CSP, X-Frame-Options)

### 4. Access Control
- ✅ Admin API: localhost only
- ✅ User API: authenticated users only
- ✅ Central Monitor: localhost only
- ✅ JWT-based authentication

---

## Monitoring và Logging

### Log Levels

1. **System Logs** (journalctl)
   - Service status (start/stop/restart)
   - Error logs
   - Performance metrics

2. **Access Logs** (Nginx)
   - HTTP requests (IP, URL, status, response time)
   - File: `/var/log/nginx/pandora_access.log`

3. **Application Logs** (FastAPI)
   - API calls
   - Request/response details
   - File: `/var/log/pandora/webserver-access.log`

4. **Honeypot Logs** (Database)
   - All HTTP requests with suspicious score
   - Table: `honeypot_logs`

5. **Attack Logs** (Database)
   - Network-level attacks
   - Table: `attack_logs`

6. **Elasticsearch Logs** (Optional)
   - Centralized logging
   - Real-time analytics
   - Kibana dashboards

### Monitoring Tools

- **systemctl:** Service status
- **journalctl:** System logs
- **htop:** Resource usage
- **netstat:** Network connections
- **Central Monitor:** Web dashboard

---

## Deployment Architecture

### Development Environment
```
Localhost:
  - All services chạy trên 1 máy
  - Self-signed SSL certificate
  - Debug mode enabled
```

### Production Environment
```
Server (VPS/Dedicated):
  - All services chạy trên 1 máy (hoặc containerized)
  - Let's Encrypt SSL certificate
  - Production mode (no debug)
  - Firewall: chỉ mở port 80, 443
```

### High Availability (Future)
```
Load Balancer (Nginx)
    ├─ Webserver Instance 1
    ├─ Webserver Instance 2
    └─ Webserver Instance 3

Backend APIs:
    ├─ Backend Instance 1
    └─ Backend Instance 2

Database:
    ├─ PostgreSQL Primary
    └─ PostgreSQL Replica (Read)

IDS:
    - Chạy trên từng server (không cluster)
```

---

## Performance

### Benchmarks

**HTTP Server Performance:**
- `http.server` (old): ~500 req/s
- FastAPI + Uvicorn (new): ~5,000 req/s
- FastAPI + Gunicorn (4 workers): ~15,000 req/s

**IDS Performance:**
- Packet capture: ~10,000 packets/s
- CPU usage: 10-30%
- RAM usage: 200-500MB

**Database Performance:**
- PostgreSQL: ~1,000 writes/s (honeypot logs)
- Redis: ~10,000 ops/s (cache)

---

## Scalability

### Horizontal Scaling
- Load balancer (Nginx/HAProxy)
- Multiple webserver instances
- Multiple backend instances
- Database replication

### Vertical Scaling
- Increase Gunicorn workers
- Increase Nginx worker_connections
- Increase database connection pool

### Caching
- Redis for session storage
- Nginx cache for static assets
- Database query caching

---

## Tóm tắt

**Ưu điểm kiến trúc mới:**
1. ✅ Production-ready (Nginx + FastAPI)
2. ✅ Hiệu năng cao (10x nhanh hơn)
3. ✅ Dễ scale (multi-worker, load balancing)
4. ✅ Bảo mật tốt (SSL termination, rate limiting)
5. ✅ Dễ maintain (systemd services, centralized logs)

**Defense in Depth:**
- **Layer 3-4:** IDS Engine (packet level)
- **Layer 7:** Honeypot (application level)
- **Layer 7:** Nginx (transport security)
- **Layer 7:** Backend (business logic)

---

**Ngày cập nhật:** 2025-10-23  
**Phiên bản:** 2.0.0

