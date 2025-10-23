# 📋 Deployment Checklist - Pandora v2.0

## ✅ Pre-Deployment

- [ ] Đọc `README-REFACTORING.md`
- [ ] Đọc `FINAL-REFACTORING-SUMMARY.md`
- [ ] Backup database hiện tại
- [ ] Note lại ports cũ (để rollback nếu cần)

---

## 🚀 Deployment Steps

### 1. Stop Old Services
```bash
sudo systemctl stop pandora-http-80 2>/dev/null || true
sudo systemctl stop pandora-https-443 2>/dev/null || true
pkill -f port_80.py 2>/dev/null || true
pkill -f port_443.py 2>/dev/null || true
```
- [ ] Old services stopped

### 2. Pull New Code
```bash
cd /opt/pandora
git pull origin main
```
- [ ] Code updated

### 3. Setup SSL Certificate
```bash
cd /opt/pandora/nginx
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=VN/ST=HCM/L=HCM/O=Pandora/CN=localhost"
```
- [ ] SSL certificate created
- [ ] Files exist: `/etc/nginx/ssl/cert.pem` và `key.pem`

### 4. Update Nginx Config
```bash
sudo cp /opt/pandora/nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
```
- [ ] Nginx config test passed
```bash
sudo systemctl restart nginx
sudo systemctl status nginx
```
- [ ] Nginx restarted successfully

### 5. Update Dependencies (nếu cần)
```bash
# Backend User
cd /opt/pandora/backend-user
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Backend Admin
cd /opt/pandora/backend-admin
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Custom Webserver
cd /opt/pandora/custom-webserver
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
deactivate
```
- [ ] Dependencies updated

### 6. Build Frontend
```bash
cd /opt/pandora/frontend
npm install
npm run build
```
- [ ] Frontend built
- [ ] `dist/` folder exists

### 7. Install Systemd Services
```bash
cd /opt/pandora/deploy
sudo ./install-services.sh
```
- [ ] Services installed
- [ ] Check: `ls /etc/systemd/system/pandora-*`

### 8. Start All Services
```bash
sudo ./start-all-services.sh
```
- [ ] All services started

### 9. Check Services Status
```bash
sudo systemctl status pandora-backend-user
sudo systemctl status pandora-backend-admin
sudo systemctl status pandora-central-monitor
sudo systemctl status pandora-webserver
sudo systemctl status pandora-nginx
sudo systemctl status pandora-ids
```
- [ ] All services: `active (running)`

---

## 🧪 Verification

### Test 1: HTTP Redirect
```bash
curl -I http://localhost
```
**Expected:** `301 Moved Permanently`
- [ ] ✅ PASS

### Test 2: HTTPS Frontend
```bash
curl -k https://localhost/
```
**Expected:** Vue.js HTML
- [ ] ✅ PASS

### Test 3: User API Health
```bash
curl -k https://localhost/api/user/auth/health
```
**Expected:** `{"status":"healthy"}`
- [ ] ✅ PASS

### Test 4: Backend Direct (Internal)
```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:5000/
curl http://127.0.0.1:8443/api/status
```
**Expected:** All return success
- [ ] ✅ User Backend (8001) OK
- [ ] ✅ Admin Backend (8002) OK
- [ ] ✅ Central Monitor (5000) OK
- [ ] ✅ Honeypot (8443) OK

### Test 5: Admin Dashboard (Localhost Only)
```bash
# Từ external (should fail)
curl -k https://your-server-ip/admin-dashboard/

# Từ localhost (should work)
curl -k https://localhost/admin-dashboard/
```
- [ ] ✅ External access blocked (403)
- [ ] ✅ Localhost access OK

### Test 6: Honeypot Logging
```bash
# Send suspicious request
curl -k "https://localhost/admin/config.php?id=1' OR '1'='1"

# Check database
sudo -u postgres psql pandora_admin -c "SELECT * FROM honeypot_logs ORDER BY id DESC LIMIT 1;"
```
**Expected:** New row with `suspicious_score > 50`
- [ ] ✅ Honeypot logged

### Test 7: IDS Detection (từ máy khác)
```bash
# Trigger port scan
nmap -sS -p 1-100 your-server-ip

# Check logs
sudo journalctl -u pandora-ids | tail -20

# Check database
sudo -u postgres psql pandora_admin -c "SELECT * FROM attack_logs ORDER BY detected_at DESC LIMIT 1;"
```
**Expected:** New row with `attack_type = 'port_scan'`
- [ ] ✅ IDS detected

---

## 🔒 Security Verification

### Firewall Check
```bash
sudo ufw status
```
**Expected:** Only 80, 443, 22 open
- [ ] ✅ Port 80 open
- [ ] ✅ Port 443 open
- [ ] ✅ Port 22 open (SSH)
- [ ] ✅ Other ports blocked

### Port Binding Check
```bash
sudo netstat -tulnp | grep -E '80|443|5000|8001|8002|8443'
```
**Expected:**
- [ ] ✅ Nginx: 0.0.0.0:80, 0.0.0.0:443
- [ ] ✅ User Backend: 127.0.0.1:8001
- [ ] ✅ Admin Backend: 127.0.0.1:8002
- [ ] ✅ Central Monitor: 127.0.0.1:5000
- [ ] ✅ Honeypot: 127.0.0.1:8443

---

## 📊 Monitoring

### Check Logs
```bash
# Real-time logs
sudo journalctl -u pandora-nginx -f
sudo journalctl -u pandora-webserver -f
sudo journalctl -u pandora-backend-user -f

# Nginx access log
sudo tail -f /var/log/nginx/pandora_access.log
```
- [ ] ✅ Logs working

### Database Check
```bash
# Honeypot logs count
sudo -u postgres psql pandora_admin -c "SELECT COUNT(*) FROM honeypot_logs;"

# Attack logs count
sudo -u postgres psql pandora_admin -c "SELECT COUNT(*) FROM attack_logs;"
```
- [ ] ✅ Database accessible

---

## 🎯 Post-Deployment

### Performance Check
```bash
# CPU usage
htop

# Memory usage
free -h

# Network
netstat -an | grep ESTABLISHED | wc -l
```
- [ ] ✅ CPU < 50%
- [ ] ✅ Memory < 80%
- [ ] ✅ Network stable

### Access Points Documented
- [ ] ✅ Main app: `https://your-domain.com`
- [ ] ✅ Admin Dashboard: `https://your-domain.com/admin-dashboard/` (localhost only)
- [ ] ✅ User API: `https://your-domain.com/api/user/`
- [ ] ✅ Admin API: `https://your-domain.com/api/admin/` (localhost only)

### Documentation Updated
- [ ] ✅ Update team wiki với URLs mới
- [ ] ✅ Inform team về port changes
- [ ] ✅ Setup monitoring alerts

---

## 🚨 Rollback Plan (If Needed)

### If something goes wrong:
```bash
# Stop new services
sudo systemctl stop pandora-nginx
sudo systemctl stop pandora-webserver
sudo systemctl stop pandora-backend-user
sudo systemctl stop pandora-backend-admin
sudo systemctl stop pandora-central-monitor

# Start old services
sudo systemctl start pandora-http-80
sudo systemctl start pandora-https-443

# Restore old nginx config
sudo cp /etc/nginx/nginx.conf.backup /etc/nginx/nginx.conf
sudo systemctl restart nginx
```

---

## ✅ Sign-off

**Deployment completed by:** _________________

**Date:** _________________

**Verified by:** _________________

**Status:** 
- [ ] ✅ SUCCESS - All tests passed
- [ ] ⚠️ PARTIAL - Some issues (document below)
- [ ] ❌ FAILED - Rolled back

**Notes:**
_______________________________________________________
_______________________________________________________
_______________________________________________________

---

## 📞 Support

**Issues?** Check:
1. `README-REFACTORING.md`
2. `ROUTING-GUIDE.md`
3. `deploy/DEPLOYMENT-GUIDE-NEW-ARCHITECTURE.md`

**Logs:**
```bash
sudo journalctl -u pandora-* -f
```

---

**📅 Checklist Version:** 2.0.0  
**📝 Last Updated:** 2025-10-23

