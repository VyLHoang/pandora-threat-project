# 🚀 Quick Deploy to VPS

## ⚡ Deploy trong 5 phút!

### **1. SSH vào VPS**

```bash
ssh pandora@172.232.246.68 -p 2222
```

Nếu chưa có user `pandora`, tạo user:
```bash
# SSH as root first
ssh root@172.232.246.68

# Create user
adduser pandora
usermod -aG sudo pandora

# Exit and login as pandora
exit
ssh pandora@172.232.246.68 -p 2222
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

### **3. Deploy ALL Services (1 Command)**

```bash
chmod +x deploy/deploy-all.sh
sudo bash deploy/deploy-all.sh
```

**Script sẽ tự động:**
- ✅ Install Python, Docker, dependencies
- ✅ Start 8 Docker containers (databases)
- ✅ Generate SSL certificates
- ✅ Create 6 systemd services
- ✅ Start all services
- ✅ Configure firewall (UFW)
- ✅ Enable auto-start on boot

**Thời gian:** ~10-15 phút

---

### **4. Import Kibana Dashboards** (Optional)

```bash
cd ~/projects/pandora-threat-project/elasticsearch
python3 import_dashboards.py
```

---

### **5. Test Deployment**

```bash
cd ~/projects/pandora-threat-project
sudo bash deploy/test-deployment.sh
```

---

## ✅ **Verification**

### **From VPS (localhost):**
```bash
# Check services
sudo systemctl status pandora-*

# Check Docker
docker ps

# Test endpoints
curl http://localhost
curl -k https://localhost
curl http://localhost:9000/api/v1/health
curl http://localhost:8000/api/v1/health
```

### **From your Windows machine:**

Open browser:
- **Website:** https://172.232.246.68
- **Central Monitor:** http://172.232.246.68:27009 (admin/admin123)
- **Admin API:** http://172.232.246.68:9000/docs
- **User API:** http://172.232.246.68:8000/docs
- **Kibana:** http://172.232.246.68:5601 (elastic/pandora123)

---

## 📊 **What's Running**

After deployment, you'll have:

| Service | Port | Status |
|---------|------|--------|
| HTTP Server | 80 | ✅ Running |
| HTTPS Server | 443 | ✅ Running |
| Backend User | 8000 | ✅ Running |
| Backend Admin | 9000 | ✅ Running |
| Central Monitor | 27009 | ✅ Running |
| IDS Engine | - | ✅ Running |
| PostgreSQL (3x) | 5432, 5433, 5434 | ✅ Running |
| Redis (3x) | 6379, 6380, 6381 | ✅ Running |
| Elasticsearch | 9200 | ✅ Running |
| Kibana | 5601 | ✅ Running |

**Total:** 6 systemd services + 8 Docker containers

---

## 🔧 **Useful Commands**

### Service Management
```bash
# Start all
sudo systemctl start pandora-*

# Stop all
sudo systemctl stop pandora-*

# Restart all
sudo systemctl restart pandora-*

# Status
sudo systemctl status pandora-*
```

### View Logs
```bash
# Backend Admin
sudo journalctl -u pandora-backend-admin -f

# IDS Engine
sudo journalctl -u pandora-ids -f

# All services
sudo journalctl -u pandora-* -f
```

### Database Management
```bash
# Stop databases
cd ~/projects/pandora-threat-project/database
docker-compose down

# Start databases
docker-compose up -d

# View PostgreSQL logs
docker logs database-postgres-1
```

---

## 🐛 **Troubleshooting**

### Service failed to start
```bash
# Check logs
sudo journalctl -u pandora-backend-admin -xe

# Test manually
cd ~/projects/pandora-threat-project/backend-admin
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 9000
```

### Port already in use
```bash
# Find process
sudo lsof -i :9000

# Kill it
sudo kill -9 <PID>
```

### Re-deploy
```bash
cd ~/projects/pandora-threat-project
git pull origin main
sudo bash deploy/deploy-all.sh
```

---

## 🔒 **Security**

**⚠️ IMPORTANT:** Change default passwords!

See `deploy/FULL-DEPLOYMENT-GUIDE.md` section "Security" for instructions.

---

## 📈 **Next Steps**

1. ✅ Deploy system (done by script)
2. Test all endpoints
3. Import Kibana dashboards
4. Change default passwords
5. Configure email alerts (optional)
6. Setup domain + real SSL (Let's Encrypt)
7. Monitor logs for attacks

---

## 📞 **Support**

Full documentation:
- `deploy/README.md` - Overview
- `deploy/FULL-DEPLOYMENT-GUIDE.md` - Detailed guide
- `deploy/DEPLOY-TO-VPS.md` - Listeners deployment
- `deploy/README-DEPLOYMENT.md` - Technical docs

Run test:
```bash
sudo bash deploy/test-deployment.sh
```

---

**Ready to deploy?** Just run:
```bash
sudo bash deploy/deploy-all.sh
```

🚀 **Good luck!**

