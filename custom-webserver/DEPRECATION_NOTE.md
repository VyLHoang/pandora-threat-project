# Deprecation Notice: port_80.py và port_443.py

## Tóm tắt

Các file `port_80.py` và `port_443.py` **KHÔNG CÒN CẦN THIẾT** trong kiến trúc mới và nên được **loại bỏ** hoặc **lưu trữ** (archive) để tránh nhầm lẫn.

## Lý do

### 1. port_443.py (❌ Deprecated)
**Vấn đề:**
- Tự xử lý SSL bằng Python `ssl` module
- Hiệu năng kém với `http.server`
- Chạy trên port 443 (privileged, cần root)
- Không production-ready

**Thay thế bằng:**
- `webserver_fastapi.py` - FastAPI framework
- Chạy trên port 8443 (unprivileged)
- Không xử lý SSL (Nginx xử lý)
- Production-ready với Uvicorn/Gunicorn

### 2. port_80.py (❌ Deprecated)
**Vấn đề:**
- Tự redirect HTTP → HTTPS
- Không cần thiết vì Nginx đã xử lý
- Chạy trên port 80 (privileged, cần root)
- Lãng phí tài nguyên

**Thay thế bằng:**
- Nginx config (dòng 16-22 trong `nginx.conf`):
```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

## Kiến trúc Cũ vs Mới

### ❌ Kiến trúc CŨ (Không khuyến khích):
```
Internet
    ↓
port_80.py (Port 80, Python)  → Redirect
    ↓
port_443.py (Port 443, Python + SSL)
    ↓
Backend APIs
```

**Vấn đề:**
- Python xử lý SSL → chậm, không tối ưu
- Chạy port < 1024 → cần root privileges
- `http.server` không production-ready
- SSL certificate phải cấu hình trong Python code

### ✅ Kiến trúc MỚI (Khuyến khích):
```
Internet
    ↓
Nginx (Port 80) → Redirect 301
    ↓
Nginx (Port 443, SSL Termination)
    ↓
webserver_fastapi.py (Port 8443, HTTP)
    ↓
Backend APIs (8000, 9000)
```

**Ưu điểm:**
- Nginx xử lý SSL → nhanh, tối ưu, battle-tested
- FastAPI chạy port > 1024 → không cần root
- Production-ready với Uvicorn/Gunicorn
- SSL certificate quản lý tập trung tại Nginx
- Dễ scale (load balancing, caching, rate limiting)

## Hành động cần làm

### Option 1: Loại bỏ hoàn toàn (Khuyến khích)
```bash
cd custom-webserver
rm port_80.py port_443.py
rm server.crt server.key  # SSL certs không còn dùng
```

### Option 2: Archive (Lưu trữ)
```bash
cd custom-webserver
mkdir -p archive
mv port_80.py port_443.py archive/
echo "Deprecated files. Use webserver_fastapi.py instead." > archive/README.txt
```

### Option 3: Giữ lại (Không khuyến khích)
Chỉ nên giữ nếu:
- Đang test/dev mà chưa có Nginx
- Cần chạy standalone (không có Nginx)
- Backup plan

**Lưu ý:** Nếu giữ lại, PHẢI thêm warning rõ ràng trong code.

## Migration Guide

### 1. Stop old services
```bash
# Stop port_80.py
sudo systemctl stop pandora-http-80  # nếu chạy systemd
# hoặc
pkill -f port_80.py

# Stop port_443.py
sudo systemctl stop pandora-https-443
# hoặc
pkill -f port_443.py
```

### 2. Start new services
```bash
# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Start FastAPI Webserver
sudo systemctl start pandora-webserver
sudo systemctl enable pandora-webserver
```

### 3. Verify
```bash
# Test HTTP redirect
curl -I http://localhost
# Expected: 301 Moved Permanently, Location: https://localhost

# Test HTTPS
curl -k https://localhost/api/status
# Expected: {"status":"online", "server":"Pandora FastAPI Webserver", ...}
```

## Câu hỏi thường gặp (FAQ)

### Q: Tôi vẫn cần chạy trên port 443/80 thì sao?
**A:** Nginx sẽ chạy trên port 443/80. FastAPI chạy trên port nội bộ 8443.

### Q: Tôi không muốn dùng Nginx?
**A:** Bạn có thể dùng các reverse proxy khác như:
- Caddy (auto SSL)
- Traefik
- HAProxy
Nhưng Nginx là lựa chọn tốt nhất cho production.

### Q: Tôi chỉ cần test local, không cần SSL?
**A:** Chạy trực tiếp FastAPI:
```bash
python webserver_fastapi.py
# Access: http://localhost:8443
```

### Q: File cũ có thể chạy song song với file mới không?
**A:** KHÔNG. Chúng conflict về port và logic. Chọn 1 trong 2.

## Kết luận

**Khuyến nghị:** Loại bỏ `port_80.py` và `port_443.py`, sử dụng kiến trúc mới với Nginx + FastAPI.

**Ngày deprecate:** 2025-10-23  
**Ngày kế hoạch xóa:** 2025-11-23 (sau 1 tháng)

