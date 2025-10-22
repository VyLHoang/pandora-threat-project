# 🚀 Deploy Pandora lên VPS: 172.235.245.60

## ✅ TÓM TẮT NHANH

### **1. Push code lên GitHub (từ Windows):**
```bash
cd E:\port\threat_project
git add .
git commit -m "Ready for deployment"
git push origin main
```

### **2. SSH vào VPS:**
```bash
ssh pandora@172.235.245.60 -p 2222
```

### **3. Clone project:**
```bash
cd ~/projects
git clone https://github.com/VyLHoang/pandora-threat-project.git
cd pandora-threat-project
```

### **4. Deploy HTTP/HTTPS listeners:**
```bash
sudo bash deploy/deploy-listeners.sh
```

### **5. Kiểm tra:**
```bash
# Từ VPS
curl http://localhost
curl -k https://localhost

# Từ browser (Windows)
# Mở: https://172.235.245.60
```

---

## 📋 CHI TIẾT TỪNG BƯỚC

### **BƯỚC 1: Chuẩn bị trên Windows**

```bash
# 1.1. Đảm bảo đã commit all changes
cd E:\port\threat_project
git status

# 1.2. Add deployment files
git add deploy/
git add custom-webserver/

# 1.3. Commit
git commit -m "Add deployment scripts for HTTP/HTTPS listeners"

# 1.4. Push to GitHub
git push origin main
```

---

### **BƯỚC 2: Kết nối VPS**

```bash
# Từ PowerShell hoặc Command Prompt
ssh pandora@172.235.245.60 -p 2222

# Nếu chưa có user pandora, tạo:
# ssh root@172.235.245.60
# adduser pandora
# usermod -aG sudo pandora
# su - pandora
```

---

### **BƯỚC 3: Setup môi trường VPS**

```bash
# 3.1. Update system
sudo apt update && sudo apt upgrade -y

# 3.2. Cài Python và dependencies
sudo apt install -y python3 python3-pip python3-venv
sudo apt install -y git curl wget

# 3.3. Cài Docker (nếu chưa có)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pandora
# Logout và login lại

# 3.4. Cài Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

### **BƯỚC 4: Clone và Deploy**

```bash
# 4.1. Tạo thư mục
mkdir -p ~/projects
cd ~/projects

# 4.2. Clone project
git clone https://github.com/VyLHoang/pandora-threat-project.git
cd pandora-threat-project

# 4.3. Make deploy script executable
chmod +x deploy/deploy-listeners.sh

# 4.4. Run deployment
sudo bash deploy/deploy-listeners.sh
```

**Script sẽ tự động:**
- ✅ Cài Python dependencies
- ✅ Tạo SSL certificates (self-signed)
- ✅ Tạo systemd services
- ✅ Start HTTP server (port 80)
- ✅ Start HTTPS server (port 443)
- ✅ Enable auto-start on boot

---

### **BƯỚC 5: Cấu hình Firewall**

```bash
# 5.1. Cài UFW
sudo apt install -y ufw

# 5.2. Allow ports
sudo ufw allow 2222/tcp  # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# 5.3. Enable firewall
sudo ufw enable

# 5.4. Check status
sudo ufw status
```

---

### **BƯỚC 6: Kiểm tra**

#### **Từ VPS:**
```bash
# Check services
sudo systemctl status pandora-http-80
sudo systemctl status pandora-https-443

# Test locally
curl http://localhost
curl -k https://localhost

# View logs
sudo journalctl -u pandora-http-80 -f
sudo journalctl -u pandora-https-443 -f
```

#### **Từ Windows:**
```bash
# Test với curl
curl http://172.235.245.60
curl -k https://172.235.245.60

# Test với browser
# Mở: https://172.235.245.60
# Accept self-signed certificate warning
```

---

## 🎯 EXPECTED RESULTS

### **Port 80 (HTTP):**
```
➜ curl http://172.235.245.60

HTTP/1.1 301 Moved Permanently
Location: https://172.235.245.60:443/

<!DOCTYPE html>
<html>
<head>
    <title>Redirecting to HTTPS</title>
    ...
```

**✅ Đúng:** Redirect sang HTTPS

---

### **Port 443 (HTTPS):**
```
➜ curl -k https://172.235.245.60

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pandora</title>
    ...
```

**✅ Đúng:** Serve Vue.js frontend

---

## 🔍 MONITORING

### **View real-time logs:**
```bash
# HTTP logs
sudo journalctl -u pandora-http-80 -f

# HTTPS logs
sudo journalctl -u pandora-https-443 -f

# System logs
sudo tail -f /var/log/syslog
```

### **Check network traffic:**
```bash
# Watch HTTP
sudo tcpdump -i any port 80 -n -A

# Watch HTTPS
sudo tcpdump -i any port 443 -n
```

### **System resources:**
```bash
# Install htop
sudo apt install -y htop

# Monitor
htop
```

---

## 🛠️ TROUBLESHOOTING

### **Lỗi: Port already in use**
```bash
# Check what's using the port
sudo lsof -i :80
sudo lsof -i :443

# Kill process
sudo kill -9 <PID>

# Restart service
sudo systemctl restart pandora-http-80
```

### **Lỗi: Permission denied**
```bash
# Run with sudo
sudo systemctl start pandora-http-80
sudo systemctl start pandora-https-443
```

### **Lỗi: SSL certificate not found**
```bash
# Generate manually
cd ~/projects/pandora-threat-project/custom-webserver
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout server.key -out server.crt -days 365 \
    -subj "/CN=172.235.245.60"
```

### **Service won't start**
```bash
# Check logs
sudo journalctl -u pandora-https-443 -xe

# Check systemd file
sudo systemctl cat pandora-https-443

# Test manually
cd ~/projects/pandora-threat-project/custom-webserver
sudo python3 port_443.py
```

---

## 🎨 OPTIONAL: Deploy Full Stack

Nếu muốn deploy toàn bộ (backends, databases, monitor):

```bash
# 1. Start databases
cd ~/projects/pandora-threat-project/database
docker-compose up -d

# 2. Wait for Elasticsearch
sleep 180

# 3. Import Kibana dashboards
cd ~/projects/pandora-threat-project/elasticsearch
python3 import_dashboards.py

# 4. Start backends (tạo systemd services)
# ... (xem SETUP_GUIDE.md)
```

---

## ✅ CHECKLIST

- [ ] Code pushed to GitHub
- [ ] SSH vào VPS thành công
- [ ] Project cloned
- [ ] Deploy script chạy thành công
- [ ] HTTP (80) listener running
- [ ] HTTPS (443) listener running
- [ ] Firewall configured
- [ ] Test từ browser OK
- [ ] Logs đang ghi nhận traffic

---

## 📞 NEXT STEPS

Sau khi deploy HTTP/HTTPS listeners:

1. **Deploy databases:**
   ```bash
   cd ~/projects/pandora-threat-project/database
   docker-compose up -d
   ```

2. **Deploy backends:**
   - Backend-User (port 8000)
   - Backend-Admin (port 9000)
   - Central Monitor (port 22002)
   - IDS Engine

3. **Monitor honeypot:**
   - View logs trong Elasticsearch
   - Xem dashboards trong Kibana
   - Check Central Monitor

---

**Server:** 172.235.245.60  
**Status:** Ready for deployment! 🚀

