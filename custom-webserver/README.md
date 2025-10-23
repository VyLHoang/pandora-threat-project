# Pandora Custom Webserver (FastAPI)

## Mô tả

Custom webserver production-ready cho Pandora Threat Project, thay thế `http.server` cơ bản bằng FastAPI framework.

## Kiến trúc

```
Internet --> Nginx (Port 443, SSL) --> FastAPI Webserver (Port 8443, HTTP)
                                    └-> Backend APIs (8000, 9000)
```

### Luồng hoạt động:

1. **Nginx** (Port 443): Xử lý SSL/TLS termination
2. **FastAPI Webserver** (Port 8443): 
   - Serve Vue.js static files (SPA)
   - Log honeypot activities
   - Detect suspicious requests
3. **Backend APIs**:
   - User API (Port 8000)
   - Admin API (Port 9000)

## Tính năng

✓ **Production-ready**: FastAPI + Uvicorn thay vì `http.server`  
✓ **Không xử lý SSL**: Nginx xử lý hoàn toàn SSL/TLS  
✓ **Honeypot Logging**: Ghi lại mọi request vào database  
✓ **Threat Detection**: Phát hiện SQL injection, XSS, path traversal  
✓ **Real IP Tracking**: Lấy IP thật từ `X-Forwarded-For` header  
✓ **Async & Non-blocking**: Logging không làm chậm response  

## Cài đặt

```bash
cd custom-webserver
pip install -r requirements.txt
```

## Chạy Server

### Development:
```bash
python webserver_fastapi.py
```

### Production (với Uvicorn):
```bash
uvicorn webserver_fastapi:app --host 127.0.0.1 --port 8443 --workers 4
```

### Production (với Gunicorn + Uvicorn workers):
```bash
gunicorn webserver_fastapi:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8443 \
    --access-logfile /var/log/pandora/webserver.log
```

### Systemd Service:
```bash
sudo systemctl start pandora-webserver
sudo systemctl enable pandora-webserver
```

## Configuration

Chỉnh sửa `webserver_fastapi.py`:

```python
class Config:
    HOST = "127.0.0.1"  # Localhost only
    PORT = 8443
    
    USER_BACKEND_URL = "http://127.0.0.1:8000"
    ADMIN_BACKEND_URL = "http://127.0.0.1:9000"
```

## API Endpoints

### Local Endpoints (debug):
- `GET /api/status` - Server status
- `GET /api/health` - Health check
- `GET /api/server-info` - Server information

### Frontend:
- `GET /*` - Serve Vue.js SPA

## Logging

### Honeypot Logs:
Mọi request được log vào:
1. **PostgreSQL** (via Admin Backend API `/api/v1/honeypot/log`)
2. **Elasticsearch** (nếu có)

### Console Logs:
```
[14:23:45] 192.168.1.100 | GET /api/v1/scan -> 200 (0.123s)
[HONEYPOT] 🚨 Suspicious activity detected!
  IP: 203.0.113.45
  Method: GET /admin/config.php
  Score: 85
  Reasons: Exploit path scan: /admin
```

## Security Features

### 1. Suspicious Score Calculation
Mỗi request được chấm điểm nghi ngờ (0-100):
- SQL Injection patterns: +20
- Path Traversal: +30
- XSS patterns: +25
- Suspicious User Agent: +30
- Exploit path scan: +15

### 2. Real IP Detection
Lấy IP thật từ Nginx headers:
```python
X-Real-IP: 203.0.113.45
X-Forwarded-For: 203.0.113.45, 10.0.0.1
```

### 3. User Tracking
Theo dõi user đã authenticated qua JWT token.

## Khác biệt với `port_443.py` cũ

| Feature | port_443.py (Old) | webserver_fastapi.py (New) |
|---------|-------------------|----------------------------|
| Framework | `http.server` | FastAPI |
| SSL Handling | Python `ssl` module | Không (Nginx xử lý) |
| Performance | Đơn luồng, chậm | Async, multi-worker |
| Port | 443 (privileged) | 8443 (unprivileged) |
| Production Ready | ❌ | ✅ |

## Troubleshooting

### Lỗi: "Address already in use"
```bash
# Kiểm tra port đang sử dụng
sudo lsof -i :8443

# Kill process cũ
sudo kill -9 <PID>
```

### Lỗi: "Frontend not built"
```bash
cd ../frontend
npm install
npm run build
```

### Lỗi: "Elasticsearch not available"
Không sao cả! Webserver vẫn hoạt động bình thường, chỉ không log vào Elasticsearch.

## Performance

Benchmark (Apache Bench):
```bash
ab -n 10000 -c 100 https://localhost/

# FastAPI: ~5000 req/s
# http.server: ~500 req/s (10x chậm hơn)
```

## License

Part of Pandora Threat Intelligence Platform
