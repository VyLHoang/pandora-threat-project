# 🛡️ Pandora Threat Intelligence Platform

## Overview

Pandora là nền tảng Threat Intelligence tích hợp **Honeypot** và **IDS** (Intrusion Detection System) để phát hiện, phân tích và monitor các mối đe dọa mạng.

## 🏗️ Architecture (v3.0 - Split Architecture)

Hệ thống được tách thành **2 servers riêng biệt**:

### 1. Honeypot Server (Public - Exposed to Internet)

```
┌─────────────────────────────────┐
│   HONEYPOT SERVER               │
├─────────────────────────────────┤
│ Nginx (80/443 - SSL)            │
│ ↓                               │
│ Custom Webserver (8443)         │
│  ├─ Fake Paths:                 │
│  │   /admin, /phpmyadmin        │
│  │   /wp-admin, /.env           │
│  │   → Fake HTML responses      │
│  │                              │
│  └─ Real Paths (Hidden):        │
│      /app/* → Vue.js SPA        │
│      /api/user/* → Backend      │
│                                 │
│ Backend-user (8001)             │
│  - Authentication               │
│  - VirusTotal Scan              │
│  - Scan History                 │
│                                 │
│ NO Database (stateless)         │
│ All logs → Central Monitor      │
└─────────────────────────────────┘
```

### 2. Central Monitor Server (Internal - Admin Only)

```
┌─────────────────────────────────┐
│   CENTRAL MONITOR SERVER        │
├─────────────────────────────────┤
│ Nginx (443 - SSL, IP whitelist) │
│ ↓                               │
│ Central Monitor Dashboard       │
│  - Real-time attack monitoring  │
│  - Honeypot activity            │
│  - User behavior analytics      │
│  - Interactive maps             │
│                                 │
│ Backend-admin (8002)            │
│  - Receive logs from Honeypot   │
│  - Attack logs management       │
│  - User monitoring              │
│                                 │
│ PostgreSQL (All Databases)      │
│  - pandora_user                 │
│  - pandora_admin                │
│  - honeypot_logs                │
│  - attack_logs                  │
│                                 │
│ IDS Engine (Scapy)              │
│  - Packet sniffing              │
│  - Port scan detection          │
│  - SYN flood detection          │
│                                 │
│ Elasticsearch (Optional)        │
│  - Log indexing                 │
│  - Analytics                    │
└─────────────────────────────────┘
```

## 🎯 Key Features

### Honeypot Server (Public)
✅ **Fake Website** - Dụ hacker với nhiều fake paths  
✅ **Real App Hidden** - Vue.js app ẩn ở `/app/*`  
✅ **Stateless** - Không lưu data, chỉ forward logs  
✅ **High Performance** - FastAPI + Gunicorn  
✅ **SSL/TLS** - Nginx xử lý encryption  

### Central Monitor Server (Internal)
✅ **All-in-One Monitoring** - Dashboard, APIs, Databases  
✅ **IDS Engine** - Network-level attack detection  
✅ **Real-time Analytics** - Live attack visualization  
✅ **Secure** - Firewall, IP whitelist, VPN  
✅ **Scalable** - Support multiple Honeypot servers  

## 📦 Quick Start

### 1. Deploy Honeypot Server (Public)

```bash
# On public server
cd /opt
sudo git clone <repo-url> pandora
cd pandora/deploy
sudo chmod +x deploy-honeypot.sh
sudo ./deploy-honeypot.sh

# Configure
sudo nano /etc/systemd/system/pandora-honeypot.service
# Set: CENTRAL_MONITOR_URL, CENTRAL_MONITOR_API_KEY

# Start
sudo systemctl daemon-reload
sudo systemctl start pandora-honeypot
sudo systemctl start pandora-backend-user
```

### 2. Deploy Central Monitor Server (Internal)

```bash
# On internal server
cd /opt
sudo git clone <repo-url> pandora
cd pandora/deploy
sudo chmod +x deploy-central.sh
sudo ./deploy-central.sh

# Configure
sudo nano /etc/nginx/nginx.conf
# Set: allow <admin-ip>; deny all;

sudo nano /etc/systemd/system/pandora-backend-admin.service
# Set: DATABASE_URL with correct password

# Start
sudo systemctl daemon-reload
sudo systemctl start pandora-backend-admin
sudo systemctl start pandora-central-monitor
sudo systemctl start pandora-ids
```

## 📚 Documentation

- **[SPLIT-ARCHITECTURE-GUIDE.md](SPLIT-ARCHITECTURE-GUIDE.md)** - Full deployment guide
- **[split-honeypot-architecture.plan.md](split-honeypot-architecture.plan.md)** - Architecture plan
- **[deploy/README.md](deploy/README.md)** - Deployment scripts

## 🔒 Security

### Honeypot Server
- Exposed to Internet (ports 80, 443)
- NO sensitive data stored
- All logs sent immediately to Central
- Fake responses for exploit attempts

### Central Monitor Server
- Internal network only
- Firewall: Admin IPs whitelisted
- VPN recommended
- All databases encrypted
- Strong authentication

## 🧪 Testing

### Test Fake Paths (Honeypot)
```bash
curl -k https://honeypot-ip/admin
curl -k https://honeypot-ip/phpmyadmin
curl -k https://honeypot-ip/.env
# Expected: Fake HTML responses
```

### Test Real App (Honeypot)
```bash
curl -k https://honeypot-ip/app/
# Expected: Vue.js HTML
```

### Test Logs (Central Monitor)
```bash
sudo -u postgres psql pandora_admin -c "SELECT COUNT(*) FROM honeypot_logs;"
# Expected: Log count increasing
```

## 🛠️ Tech Stack

### Honeypot Server
- **Nginx** - Reverse proxy, SSL termination
- **FastAPI** - Python async web framework
- **Gunicorn** - WSGI server (multi-worker)
- **Vue.js** - Frontend SPA
- **Python 3.10+** - Backend language

### Central Monitor Server
- **Flask** - Dashboard (central-monitor)
- **FastAPI** - Admin API (backend-admin)
- **PostgreSQL** - Relational database
- **Redis** - Cache and sessions
- **Scapy** - IDS packet sniffing
- **Elasticsearch** - Log indexing (optional)
- **GeoIP** - IP geolocation
- **WHOIS** - Domain lookup

## 📊 Monitoring

```bash
# Honeypot Server
sudo systemctl status pandora-honeypot
sudo journalctl -u pandora-honeypot -f

# Central Monitor Server
sudo systemctl status pandora-*
sudo journalctl -u pandora-ids -f

# Database stats
sudo -u postgres psql pandora_admin -c "
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_logs,
    SUM(CASE WHEN is_fake_path THEN 1 ELSE 0 END) as fake_probes
FROM honeypot_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp);
"
```

## 🚀 Scaling

Deploy multiple Honeypot servers (different regions), all sending logs to one Central Monitor:

```
Internet → Honeypot US     ──┐
           Honeypot EU     ──┼─→ Central Monitor (Admin)
           Honeypot Asia   ──┘
```

## 📝 License

Copyright © 2025 Pandora Team

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📞 Support

- **Issues:** GitHub Issues
- **Documentation:** `/docs/` folder
- **Logs:** `/var/log/pandora/`

---

**Version:** 3.0.0 (Split Architecture)  
**Status:** ✅ Production Ready  
**Last Updated:** 2025-10-23
