# 🚨 HƯỚNG DẪN KHẮC PHỤC SERVER BỊ TREO

## ❌ NGUYÊN NHÂN:
- **Elasticsearch** ăn quá nhiều RAM (2-4GB)
- Server RAM thấp → bị treo/crash
- Không thể SSH vào server

---

## ✅ BƯỚC 1: RESTART SERVER

### Cách 1: Từ Control Panel
1. Đăng nhập vào **control panel của VPS provider**
2. Tìm server IP: `172.235.245.60`
3. Nhấn nút **"Restart"** hoặc **"Reboot"**
4. Đợi 2-3 phút

### Cách 2: Yêu cầu người mua VPS
- Liên hệ người mua VPS
- Yêu cầu họ restart server từ control panel
- Hoặc xin quyền truy cập control panel

---

## ✅ BƯỚC 2: KIỂM TRA SERVER SỐNG LẠI

```bash
# Windows PowerShell
ping 172.235.245.60

# Nếu thấy "Reply from..." → Server đã sống
# Nếu thấy "Request timed out" → Chưa sống, đợi thêm
```

---

## ✅ BƯỚC 3: SSH VÀO SERVER

```bash
# Thử port 22 (mặc định)
ssh pandora@172.235.245.60 -p 22

# Hoặc port 22002 (nếu đã cấu hình)
ssh pandora@172.235.245.60 -p 22002
```

---

## ✅ BƯỚC 4: DỌN DẸP VÀ DEPLOY LẠI

### A. Dọn dẹp Elasticsearch (nguyên nhân gây treo)

```bash
# Stop tất cả containers
cd ~/projects/pandora-threat-project/database
sudo docker-compose down

# Xóa containers và volumes
sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null
sudo docker volume prune -f

# Stop các systemd services cũ
sudo systemctl stop pandora-*
```

### B. Deploy phiên bản tối ưu RAM thấp

```bash
# Pull code mới nhất
cd ~/projects/pandora-threat-project
git pull origin main

# Chạy script deployment tối ưu RAM
sudo bash deploy/deploy-low-ram.sh
```

**Script này sẽ:**
- ✅ Chỉ cài PostgreSQL + Redis (không có Elasticsearch)
- ✅ Tối ưu RAM cho PostgreSQL (128MB thay vì 512MB)
- ✅ Giới hạn Redis chỉ dùng 128MB
- ✅ Deploy tất cả các service khác bình thường
- ✅ Tổng RAM sử dụng: **~900MB** (thay vì 3-4GB)

---

## ✅ BƯỚC 5: KIỂM TRA HỆ THỐNG

### Kiểm tra RAM usage:
```bash
free -h
```

**Kết quả mong đợi:**
```
              total        used        free      shared  buff/cache   available
Mem:          1.0Gi       900Mi       100Mi       10Mi       50Mi       100Mi
```

### Kiểm tra các services:
```bash
sudo systemctl status pandora-*
```

**Tất cả phải "active (running)" màu xanh**

### Kiểm tra databases:
```bash
sudo docker ps
```

**Kết quả mong đợi:**
```
CONTAINER ID   IMAGE                  STATUS
xxxxx          postgres:15-alpine     Up X minutes
xxxxx          redis:7-alpine         Up X minutes
```

---

## 📊 SO SÁNH RAM USAGE

### ❌ Deploy đầy đủ (có Elasticsearch):
- PostgreSQL: 200MB
- Redis: 50MB
- Elasticsearch: **2000MB** ← Nguyên nhân treo
- Kibana: **500MB**
- Backend APIs: 300MB
- Services khác: 200MB
- **TỔNG: ~3.2GB RAM**

### ✅ Deploy tối ưu (không có Elasticsearch):
- PostgreSQL: 200MB (optimized)
- Redis: 50MB (limited)
- Backend APIs: 300MB
- Central Monitor: 100MB
- IDS Engine: 150MB
- Honeypot listeners: 100MB
- **TỔNG: ~900MB RAM** ← An toàn cho server 1GB

---

## ⚠️ TÍNH NĂNG BỊ MẤT (khi tắt Elasticsearch):

### ❌ Không có:
- Kibana dashboard (visualize logs)
- Full-text search trong logs
- Advanced log analytics

### ✅ Vẫn có đầy đủ:
- ✅ Backend Admin API (quản lý system)
- ✅ Backend User API (người dùng quét IP)
- ✅ Central Monitor (xem attacks, traffic, users)
- ✅ IDS Engine (phát hiện tấn công)
- ✅ Honeypot HTTP/HTTPS (thu thập dữ liệu)
- ✅ PostgreSQL (lưu tất cả logs và data)
- ✅ Redis (cache và sessions)

**→ Hệ thống vẫn hoạt động đầy đủ 100%, chỉ mất phần visualize trên Kibana**

---

## 🎯 KHUYẾN NGHỊ THEO RAM:

### Server có < 1GB RAM:
- ❌ KHÔNG chạy được Elasticsearch
- ✅ Dùng `deploy-low-ram.sh`
- ✅ Logs lưu trong PostgreSQL, xem qua Central Monitor

### Server có 1-2GB RAM:
- ⚠️ CÓ THỂ chạy Elasticsearch nhưng sẽ rất chậm
- ✅ Khuyến nghị dùng `deploy-low-ram.sh` để ổn định

### Server có > 2GB RAM:
- ✅ Có thể chạy đầy đủ Elasticsearch + Kibana
- ✅ Dùng `deploy-all.sh` bình thường

---

## 📞 NẾU VẪN CÒN VẤN ĐỀ:

1. **Server vẫn không sống lại sau 10 phút:**
   - Liên hệ VPS provider support
   - Có thể cần force restart từ control panel

2. **RAM vẫn không đủ sau khi deploy:**
   - Kiểm tra: `free -h`
   - Stop một số services không cần thiết
   - Hoặc upgrade RAM

3. **Services không chạy:**
   - Xem logs: `journalctl -u pandora-backend-admin -n 50`
   - Kiểm tra `.env` files
   - Đảm bảo databases đã chạy

---

## 🚀 TÓM TẮT NHANH:

```bash
# 1. Restart server từ control panel

# 2. SSH vào
ssh pandora@172.235.245.60 -p 22

# 3. Dọn dẹp
cd ~/projects/pandora-threat-project/database
sudo docker-compose down
sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null

# 4. Deploy lại (tối ưu RAM)
cd ~/projects/pandora-threat-project
git pull origin main
sudo bash deploy/deploy-low-ram.sh

# 5. Kiểm tra
sudo systemctl status pandora-*
free -h
```

**→ XONG! Hệ thống sẽ chạy ổn định với ~900MB RAM** ✅

