# 🚀 Pandora Deployment Scripts

Deployment scripts và hướng dẫn để deploy Pandora Threat Intelligence Platform lên production server.

---

## ⚡ QUICK DEPLOY (1 Command)

```bash
# SSH vào VPS
ssh pandora@172.232.246.68 -p 2222

# Clone project
cd ~/projects
git clone https://github.com/VyLHoang/pandora-threat-project.git
cd pandora-threat-project

# Deploy ALL services
sudo bash deploy/deploy-all.sh
```

**Thời gian:** ~10-15 phút  
**Kết quả:** Toàn bộ hệ thống chạy tự động!

---

## 📁 Cấu trúc Files

```
deploy/
├── systemd/                    # Systemd service files
│   ├── pandora-backend-admin.service
│   ├── pandora-backend-user.service
│   ├── pandora-central-monitor.service
│   ├── pandora-ids.service
│   ├── pandora-http-80.service
│   └── pandora-https-443.service
│
├── deploy-all.sh              # Master deployment script (ALL services)
├── deploy-listeners.sh        # Deploy HTTP/HTTPS only
├── test-deployment.sh         # Test all services after deploy
│
├── FULL-DEPLOYMENT-GUIDE.md   # Chi tiết deployment từng bước
├── DEPLOY-TO-VPS.md          # Hướng dẫn deploy listeners
├── README-DEPLOYMENT.md       # Technical deployment docs
└── README.md                  # File này
```

---

## 🎯 Deployment Options

### **Option 1: Full Stack (Recommended)**
Deploy toàn bộ hệ thống với 1 lệnh:

```bash
sudo bash deploy/deploy-all.sh
```

**Bao gồm:**
- ✅ Backend Admin API (port 9000)
- ✅ Backend User API (port 8000)
- ✅ Central Monitor (port 27009)
- ✅ IDS Engine
- ✅ HTTP Server (port 80)
- ✅ HTTPS Server (port 443)
- ✅ PostgreSQL databases (3 instances)
- ✅ Redis caches (3 instances)
- ✅ Elasticsearch + Kibana
- ✅ Firewall configuration
- ✅ SSL certificates

---

### **Option 2: Web Servers Only**
Chỉ deploy HTTP/HTTPS listeners:

```bash
sudo bash deploy/deploy-listeners.sh
```

**Bao gồm:**
- ✅ HTTP Server (port 80)
- ✅ HTTPS Server (port 443)
- ✅ SSL certificates
- ✅ Auto-redirect HTTP → HTTPS

---

### **Option 3: Manual Deployment**
Deploy từng service riêng lẻ (xem `FULL-DEPLOYMENT-GUIDE.md`)

---

## ✅ Verify Deployment

```bash
# Run test script
sudo bash deploy/test-deployment.sh

# Manual check
sudo systemctl status pandora-*
docker ps
sudo netstat -tuln | grep -E '80|443|8000|9000|27009'
```

---

## 📊 Deployed Services

| Service | Port | User | Description |
|---------|------|------|-------------|
| Backend Admin | 9000 | pandora | Admin API & Attack Management |
| Backend User | 8000 | pandora | User API & Scanning Services |
| Central Monitor | 27009 | pandora | Admin Dashboard (Flask) |
| IDS Engine | - | root | Network Intrusion Detection |
| HTTP Server | 80 | root | HTTP Listener (Honeypot) |
| HTTPS Server | 443 | root | HTTPS + Vue.js Frontend |
| PostgreSQL (Shared) | 5432 | postgres | Shared database |
| PostgreSQL (Admin) | 5434 | postgres | Admin database |
| PostgreSQL (User) | 5433 | postgres | User database (Honeypot) |
| Redis (Shared) | 6379 | redis | Shared cache |
| Redis (Admin) | 6381 | redis | Admin cache |
| Redis (User) | 6380 | redis | User cache |
| Elasticsearch | 9200 | elasticsearch | Log storage & search |
| Kibana | 5601 | kibana | Visualization & dashboards |

---

## 🔧 Service Management

### Start/Stop/Restart

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

### View Logs

```bash
# Real-time logs
sudo journalctl -u pandora-backend-admin -f

# Last 100 lines
sudo journalctl -u pandora-backend-admin -n 100

# All Pandora services
sudo journalctl -u pandora-* -f
```

### Check Status

```bash
# Service status
sudo systemctl status pandora-backend-admin

# All services
sudo systemctl status pandora-*

# Brief overview
sudo systemctl list-units pandora-* --all
```

---

## 🌐 Access Points

After deployment:

- **Main Website:** https://172.232.246.68
- **Central Monitor:** http://172.232.246.68:27009 (admin/admin123)
- **Backend Admin API:** http://172.232.246.68:9000/docs
- **Backend User API:** http://172.232.246.68:8000/docs
- **Kibana Dashboard:** http://172.232.246.68:5601 (elastic/pandora123)

---

## 🔒 Security Notes

### Default Credentials

**⚠️ CHANGE THESE IN PRODUCTION!**

| Service | Username | Password |
|---------|----------|----------|
| Central Monitor | admin | admin123 |
| Kibana | elastic | pandora123 |
| PostgreSQL (Shared) | admin | admin123 |
| PostgreSQL (Admin) | admin | admin123 |
| PostgreSQL (User) | user | user123 |

### Change Passwords

See `FULL-DEPLOYMENT-GUIDE.md` section "Security" for instructions.

---

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u pandora-backend-admin -xe

# Test manually
cd ~/projects/pandora-threat-project/backend-admin
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 9000
```

### Database connection error

```bash
# Check Docker containers
docker ps

# Restart databases
cd ~/projects/pandora-threat-project/database
docker-compose restart
```

### Port already in use

```bash
# Find process
sudo lsof -i :9000

# Kill it
sudo kill -9 <PID>
```

More troubleshooting in `FULL-DEPLOYMENT-GUIDE.md`

---

## 📈 Monitoring

```bash
# System resources
htop

# Network traffic
sudo tcpdump -i any port 80 or port 443

# Attack logs (IDS)
sudo journalctl -u pandora-ids -f

# Service resource usage
sudo systemctl status pandora-backend-admin | grep -E 'Memory|CPU'
```

---

## 🔄 Update Deployment

```bash
# Pull latest code
cd ~/projects/pandora-threat-project
git pull origin main

# Restart services
sudo systemctl restart pandora-*

# Or re-run deployment
sudo bash deploy/deploy-all.sh
```

---

## 📚 Documentation

- **FULL-DEPLOYMENT-GUIDE.md** - Step-by-step deployment guide
- **DEPLOY-TO-VPS.md** - Quick deploy listeners guide
- **README-DEPLOYMENT.md** - Technical deployment reference
- **TEST-LOCAL-WINDOWS.bat** - Test on Windows locally

---

## ✅ Deployment Checklist

Before deploying:
- [ ] Server có IP public: 172.232.246.68
- [ ] SSH configured (port 2222)
- [ ] User 'pandora' exists
- [ ] Git repository cloned
- [ ] Firewall rules planned

After deploying:
- [ ] All services running: `sudo systemctl status pandora-*`
- [ ] Docker containers running: `docker ps`
- [ ] Can access website: https://172.232.246.68
- [ ] Can login Central Monitor
- [ ] Kibana dashboards imported
- [ ] IDS capturing packets
- [ ] Firewall configured
- [ ] SSL certificates generated
- [ ] Changed default passwords

---

## 📞 Support Commands

```bash
# Quick health check
sudo bash deploy/test-deployment.sh

# View all Pandora services
sudo systemctl list-units pandora-*

# Check all listening ports
sudo netstat -tuln | grep -E '80|443|8000|9000|27009|5432|6379|9200|5601'

# Docker status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Service logs (all)
sudo journalctl -u pandora-* --since "10 minutes ago"
```

---

**Version:** 1.0.0  
**Last Updated:** 2025-10-22  
**Server:** 172.232.246.68  
**Status:** Production Ready 🚀

