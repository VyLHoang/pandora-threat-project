# Pandora Split Architecture - Deployment Guide

## Overview

Hệ thống Pandora được tách thành **2 servers riêng biệt**:

1. **Honeypot Server** (Public) - Pure honeypot, chỉ fake paths, không có real user app
2. **Central Monitor Server** (Internal) - Real user app + Admin dashboard + databases + IDS

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INTERNET                             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────┐
        │   HONEYPOT SERVER (Public)   │
        │   IP: X.X.X.X                │
        │   Domain: honeypot.example.com│
        ├──────────────────────────────┤
        │ • Nginx (80/443)             │
        │ • Pure Honeypot (8443)       │
        │   - Fake paths (/admin, etc) │
        │   - Fake APIs (/api/v1/*)    │
        │   - NO real user app         │
        │                              │
        │ NO Database                  │
        │ NO Real User Data            │
        │ All logs → Central Monitor   │
        └──────────────┬───────────────┘
                       │
                       │ (Logs via API)
                       ↓
        ┌──────────────────────────────┐
        │  CENTRAL MONITOR (Internal)  │
        │  IP: Y.Y.Y.Y                 │
        │  Domain: app.example.com     │
        ├──────────────────────────────┤
        │ • Nginx (443)                │
        │ • Vue.js Frontend (/)        │
        │ • Backend-user (8001)        │
        │ • Backend-admin (8002)       │
        │ • Central Monitor (5000)     │
        │ • PostgreSQL (all DBs)       │
        │ • IDS Engine                 │
        │ • Elasticsearch (optional)   │
        │                              │
        │ Real User App + Admin        │
        └──────────────────────────────┘
```

## Server Requirements

### Honeypot Server (Public)

**Minimum:**
- CPU: 2 cores
- RAM: 2GB
- Disk: 10GB
- Network: Public IP, ports 80/443 open

**Software:**
- Ubuntu 22.04 LTS
- Python 3.10+
- Nginx 1.18+
- Node.js 18+ (for building frontend)

**NO database, NO IDS on this server!**

### Central Monitor Server (Internal)

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB SSD
- Network: Internal IP, firewall restricted

**Software:**
- Ubuntu 22.04 LTS
- Python 3.10+
- Nginx 1.18+
- PostgreSQL 14+
- Redis 6+
- Elasticsearch 8+ (optional)

**All databases and monitoring here!**

---

## Deployment Steps

### Step 1: Deploy Honeypot Server

**On the PUBLIC server:**

```bash
# 1. Clone repository
cd /opt
sudo git clone <your-repo-url> pandora
cd pandora

# 2. Run deployment script
cd deploy
sudo chmod +x deploy-honeypot.sh
sudo ./deploy-honeypot.sh

# 3. Configure environment
sudo nano /etc/systemd/system/pandora-honeypot.service
# Edit:
# - CENTRAL_MONITOR_URL=https://your-central-server.com
# - CENTRAL_MONITOR_API_KEY=your-secret-key

sudo nano /etc/systemd/system/pandora-backend-user.service
# Edit same variables

# 4. Start services
sudo systemctl daemon-reload
sudo systemctl start pandora-honeypot
sudo systemctl start pandora-backend-user

# 5. Check status
sudo systemctl status pandora-honeypot
sudo systemctl status pandora-backend-user
sudo journalctl -u pandora-honeypot -f
```

### Step 2: Deploy Central Monitor Server

**On the INTERNAL server:**

```bash
# 1. Clone repository
cd /opt
sudo git clone <your-repo-url> pandora
cd pandora

# 2. Run deployment script
cd deploy
sudo chmod +x deploy-central.sh
sudo ./deploy-central.sh

# 3. Configure database password
sudo nano /etc/systemd/system/pandora-backend-admin.service
# Edit DATABASE_URL with correct password

# 4. Configure Nginx IP whitelist
sudo nano /etc/nginx/nginx.conf
# Uncomment and set:
# allow 192.168.1.100;  # Your admin IP
# deny all;

# 5. Test Nginx config
sudo nginx -t

# 6. Start services
sudo systemctl daemon-reload
sudo systemctl start pandora-backend-admin
sudo systemctl start pandora-central-monitor
sudo systemctl start pandora-ids

# 7. Check status
sudo systemctl status pandora-backend-admin
sudo systemctl status pandora-central-monitor
sudo systemctl status pandora-ids
```

---

## Configuration

### Honeypot Server Environment Variables

File: `/etc/systemd/system/pandora-honeypot.service`

```ini
Environment="CENTRAL_MONITOR_URL=https://central.yourcompany.com"
Environment="CENTRAL_MONITOR_API_KEY=generate-strong-random-key-here"
```

### Central Monitor API Key

File: `/opt/pandora/backend-admin/config.py` or `.env`

```bash
CENTRAL_MONITOR_API_KEY=same-key-as-honeypot
```

### Generate Strong API Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Testing

### Test Honeypot Server

```bash
# 1. Test fake paths (should return fake HTML)
curl -k https://honeypot-ip/admin
curl -k https://honeypot-ip/phpmyadmin
curl -k https://honeypot-ip/.env

# 2. Test real app (should serve Vue.js)
curl -k https://honeypot-ip/app/

# 3. Test API proxy
curl -k https://honeypot-ip/api/user/auth/health
```

### Test Central Monitor Server

```bash
# 1. Test admin dashboard (from whitelisted IP)
curl -k https://central-ip/

# 2. Test admin API
curl -k https://central-ip/api/admin/honeypot/logs

# 3. Check database for honeypot logs
sudo -u postgres psql pandora_admin -c "SELECT COUNT(*) FROM honeypot_logs;"

# 4. Check IDS is running
sudo systemctl status pandora-ids
sudo journalctl -u pandora-ids | tail -20
```

### Test End-to-End Logging

```bash
# 1. Send suspicious request to Honeypot
curl -k "https://honeypot-ip/admin?user=admin&pass=' OR '1'='1"

# 2. Wait 5 seconds, then check Central Monitor database
sudo -u postgres psql pandora_admin -c "
SELECT client_ip, request_path, suspicious_score 
FROM honeypot_logs 
ORDER BY id DESC 
LIMIT 5;
"

# Expected: New log entry with is_fake_path=true, suspicious_score > 80
```

---

## Firewall Configuration

### Honeypot Server (Public)

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp   # SSH

# Block all other ports
sudo ufw deny 8443/tcp  # Internal webserver
sudo ufw deny 8001/tcp  # Internal backend

sudo ufw enable
```

### Central Monitor Server (Internal)

```bash
# Only allow from specific IPs
sudo ufw allow from <admin-ip> to any port 443 proto tcp
sudo ufw allow from <honeypot-server-ip> to any port 443 proto tcp
sudo ufw allow 22/tcp   # SSH

# Block everything else
sudo ufw enable
```

---

## Monitoring

### Honeypot Server

```bash
# Check services
sudo systemctl status pandora-honeypot
sudo systemctl status pandora-backend-user

# View logs
sudo journalctl -u pandora-honeypot -f
sudo tail -f /var/log/pandora/honeypot.log

# Check Nginx access
sudo tail -f /var/log/nginx/honeypot_access.log
```

### Central Monitor Server

```bash
# Check all services
sudo systemctl status pandora-*

# View logs
sudo journalctl -u pandora-backend-admin -f
sudo journalctl -u pandora-ids -f

# Check database size
sudo -u postgres psql -c "
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database
WHERE datname IN ('pandora_user', 'pandora_admin');
"

# Check honeypot log count
sudo -u postgres psql pandora_admin -c "
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as log_count,
    SUM(CASE WHEN is_fake_path THEN 1 ELSE 0 END) as fake_probes,
    SUM(CASE WHEN suspicious_score > 50 THEN 1 ELSE 0 END) as suspicious
FROM honeypot_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
"
```

---

## Troubleshooting

### Honeypot: Logs not reaching Central Monitor

```bash
# 1. Check honeypot service logs
sudo journalctl -u pandora-honeypot | grep "Central Monitor"

# 2. Test connectivity
curl -k https://central-server-url/health

# 3. Verify environment variables
sudo systemctl show pandora-honeypot | grep CENTRAL_MONITOR

# 4. Test API endpoint manually
curl -k -X POST https://central-server-url/api/admin/honeypot/log \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"client_ip":"1.2.3.4","request_method":"GET","request_path":"/test","request_headers":{},"activity_type":"page_view"}'
```

### Central Monitor: IDS not detecting

```bash
# 1. Check IDS is running
sudo systemctl status pandora-ids

# 2. Check network interface
ip addr show
# Make sure IDS is sniffing the correct interface

# 3. Test with port scan (from external machine)
nmap -sS -p 80,443 <honeypot-ip>

# 4. Check attack logs
sudo -u postgres psql pandora_admin -c "SELECT * FROM attack_logs ORDER BY detected_at DESC LIMIT 5;"
```

### Nginx: 502 Bad Gateway

```bash
# 1. Check backend services are running
sudo systemctl status pandora-honeypot
sudo systemctl status pandora-backend-admin

# 2. Check port binding
sudo netstat -tulnp | grep -E '8443|8001|8002|5000'

# 3. Check Nginx error log
sudo tail -f /var/log/nginx/*error.log
```

---

## Security Best Practices

### Honeypot Server
1. ✅ No sensitive data stored locally
2. ✅ Regular security updates
3. ✅ Monitor outbound connections
4. ✅ Rate limiting enabled
5. ✅ Logs sent immediately to Central

### Central Monitor Server
1. ✅ Firewall restricted to admin IPs only
2. ✅ VPN recommended
3. ✅ Strong database passwords
4. ✅ Regular backups
5. ✅ Monitor failed login attempts

---

## Backup

### Central Monitor (Important!)

```bash
# Backup databases
sudo -u postgres pg_dump pandora_user > /backup/pandora_user_$(date +%Y%m%d).sql
sudo -u postgres pg_dump pandora_admin > /backup/pandora_admin_$(date +%Y%m%d).sql

# Backup configuration
tar -czf /backup/pandora_config_$(date +%Y%m%d).tar.gz \
    /etc/nginx/nginx.conf \
    /etc/systemd/system/pandora-*.service \
    /opt/pandora/backend-admin/config.py
```

---

## Scaling

### Multiple Honeypot Servers

You can deploy multiple Honeypot servers, all sending logs to the same Central Monitor:

```
Internet → Honeypot 1 (US)  ──┐
           Honeypot 2 (EU)  ──┼─→ Central Monitor
           Honeypot 3 (Asia) ──┘
```

Each Honeypot:
- Same configuration
- Same CENTRAL_MONITOR_URL
- Same API key
- Different public IPs

---

## Support

- **Documentation:** `/opt/pandora/docs/`
- **Logs:** `/var/log/pandora/`
- **Issues:** Check systemd logs with `journalctl`

---

**Version:** 3.0.0 (Split Architecture)  
**Last Updated:** 2025-10-23

