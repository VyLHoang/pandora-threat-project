# 🚀 Pandora Deployment Guide for VPS

## 📍 Server Information
- **IP Address:** 172.235.245.60
- **OS:** Ubuntu 22.04 LTS (recommended)
- **User:** pandora
- **SSH Port:** 2222

---

## 🎯 Quick Deploy - HTTP/HTTPS Listeners

### **From your VPS (as root or sudo):**

```bash
# 1. Navigate to project directory
cd /home/pandora/projects/pandora-threat-project

# 2. Run deployment script
sudo bash deploy/deploy-listeners.sh
```

This will:
- ✅ Install Python dependencies
- ✅ Generate SSL certificates (if not exists)
- ✅ Create systemd services
- ✅ Start HTTP server on port 80
- ✅ Start HTTPS server on port 443
- ✅ Enable auto-start on boot

---

## 🔍 Verify Deployment

### **Check services status:**
```bash
sudo systemctl status pandora-http-80
sudo systemctl status pandora-https-443
```

### **Test from server:**
```bash
# HTTP (should redirect to HTTPS)
curl http://localhost

# HTTPS (self-signed cert)
curl -k https://localhost

# Check API
curl http://localhost/api/status
curl -k https://localhost/api/status
```

### **Test from outside:**
```bash
# From your Windows machine:
curl http://172.235.245.60
curl -k https://172.235.245.60
```

### **Browser test:**
- Open browser: `https://172.235.245.60`
- Accept self-signed certificate warning
- Should see Vue.js frontend

---

## 📋 Service Management

### **Start/Stop/Restart:**
```bash
# HTTP Server (Port 80)
sudo systemctl start pandora-http-80
sudo systemctl stop pandora-http-80
sudo systemctl restart pandora-http-80

# HTTPS Server (Port 443)
sudo systemctl start pandora-https-443
sudo systemctl stop pandora-https-443
sudo systemctl restart pandora-https-443
```

### **View logs:**
```bash
# Real-time logs
sudo journalctl -u pandora-http-80 -f
sudo journalctl -u pandora-https-443 -f

# Last 100 lines
sudo journalctl -u pandora-http-80 -n 100
sudo journalctl -u pandora-https-443 -n 100
```

### **Enable/Disable auto-start:**
```bash
# Enable (start on boot)
sudo systemctl enable pandora-http-80
sudo systemctl enable pandora-https-443

# Disable (don't start on boot)
sudo systemctl disable pandora-http-80
sudo systemctl disable pandora-https-443
```

---

## 🔥 Firewall Configuration

### **Allow HTTP and HTTPS:**
```bash
# Install UFW
sudo apt install -y ufw

# Allow ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 2222/tcp  # SSH

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## 🔒 SSL Certificate

### **Self-Signed Certificate (Already Generated):**
Located at:
- Certificate: `/home/pandora/projects/pandora-threat-project/custom-webserver/server.crt`
- Private Key: `/home/pandora/projects/pandora-threat-project/custom-webserver/server.key`

### **For Production - Use Let's Encrypt:**

```bash
# Install Certbot
sudo apt install -y certbot

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem

# Update port_443.py to use new certificates
```

---

## 🍯 Honeypot Features

### **What the listeners capture:**

**HTTP (Port 80):**
- All traffic redirected to HTTPS
- Logs all HTTP requests
- Tracks attack attempts

**HTTPS (Port 443):**
- Serves Vue.js frontend (bait)
- Logs all authenticated/anonymous activity
- Tracks:
  - Login attempts
  - Scan requests
  - SQL injection attempts
  - Path traversal attempts
  - Suspicious user agents

### **Where logs are stored:**
- PostgreSQL: `honeypot_logs` table
- Elasticsearch: `pandora-honeypot-logs-*` index
- View in Kibana: http://localhost:5601

---

## 🔍 Monitoring

### **Real-time monitoring:**
```bash
# Watch HTTP traffic
sudo tcpdump -i any port 80 -n

# Watch HTTPS traffic
sudo tcpdump -i any port 443 -n

# System resources
htop
```

### **Check honeypot logs:**
```bash
# Via Central Monitor
# SSH tunnel: ssh -L 22002:localhost:22002 pandora@172.235.245.60 -p 2222
# Open: http://localhost:22002/honeypot

# Via API
curl http://localhost:9000/api/v1/honeypot/logs?limit=10
```

---

## 🚨 Troubleshooting

### **Port already in use:**
```bash
# Check what's using port 80/443
sudo lsof -i :80
sudo lsof -i :443

# Kill process
sudo kill -9 <PID>
```

### **Permission denied:**
```bash
# Ports < 1024 require root
sudo systemctl restart pandora-http-80
sudo systemctl restart pandora-https-443
```

### **Service won't start:**
```bash
# Check detailed logs
sudo journalctl -u pandora-http-80 -xe
sudo journalctl -u pandora-https-443 -xe

# Check config
sudo systemctl cat pandora-http-80
```

### **SSL certificate issues:**
```bash
# Regenerate self-signed certificate
cd /home/pandora/projects/pandora-threat-project/custom-webserver
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout server.key -out server.crt -days 365 \
    -subj "/C=US/ST=State/L=City/O=Pandora/CN=172.235.245.60"

# Restart HTTPS service
sudo systemctl restart pandora-https-443
```

---

## 📊 Architecture

```
Internet → Port 80 (HTTP)  → Redirect to HTTPS
       ↓
Internet → Port 443 (HTTPS) → Frontend (Vue.js)
       ↓                    ↓
   Honeypot Logging    → Backend API
       ↓                    ↓
   PostgreSQL          Elasticsearch
       ↓                    ↓
   Central Monitor     Kibana Dashboard
```

---

## ✅ Deployment Checklist

- [ ] Server has public IP: 172.235.245.60
- [ ] SSH configured (port 2222)
- [ ] User 'pandora' created
- [ ] Docker containers running (databases)
- [ ] Python dependencies installed
- [ ] SSL certificates generated
- [ ] Systemd services created
- [ ] HTTP listener (port 80) running
- [ ] HTTPS listener (port 443) running
- [ ] Firewall configured
- [ ] Can access from browser
- [ ] Logs being captured

---

## 📞 Support

For issues:
1. Check service logs: `sudo journalctl -u pandora-https-443 -n 100`
2. Check system logs: `sudo tail -f /var/log/syslog`
3. Test connectivity: `telnet 172.235.245.60 443`
4. Check firewall: `sudo ufw status`

---

**Deployment Date:** 2025-10-22  
**Server IP:** 172.235.245.60  
**Status:** Production Ready 🚀

