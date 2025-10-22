# Hướng dẫn Setup và Test - Central Monitor Auth & Elasticsearch

## 🎯 Tổng quan cập nhật

Đã hoàn thành 2 phần chính:

### ✅ Phần 1: Central Monitor Authentication (Port 27009)
- ✓ Login page với single admin account
- ✓ Session-based authentication
- ✓ Logout functionality
- ✓ Bảo vệ tất cả routes

### ✅ Phần 2: Elasticsearch + Kibana Integration
- ✓ Docker setup cho ES + Kibana
- ✓ ElasticsearchService với ILM (90 ngày retention)
- ✓ Tích hợp IDS Engine → Elasticsearch
- ✓ Tích hợp Honeypot → Elasticsearch
- ✓ Kibana dashboards (Top Attackers, Attack Types, Timeline, Geo Map)

---

## 🚀 Setup Instructions

### Bước 1: Cài đặt dependencies

```bash
# Central Monitor
cd central-monitor
pip install -r requirements.txt

# Backend Admin
cd ../backend-admin
pip install -r requirements.txt

# IDS Engine
cd ../ids
pip install -r requirements.txt
```

### Bước 2: Start Elasticsearch & Kibana

```bash
cd database
docker-compose up -d elasticsearch kibana

# Đợi Elasticsearch & Kibana khởi động (khoảng 2-3 phút)
# Kiểm tra status:
curl http://localhost:9200
curl http://localhost:5601/api/status
```

### Bước 3: Import Kibana Dashboards

```bash
cd ../elasticsearch
python import_dashboards.py
```

**Output mong đợi:**
```
[SUCCESS] ✓ Dashboards imported successfully!
[INFO] Successfully imported 10 objects
```

### Bước 4: Cấu hình Admin Credentials (Tùy chọn)

**Mặc định:**
- Username: `admin`
- Password: `admin123`

**Để thay đổi password:**

```bash
cd central-monitor
python auth_config.py
```

Nhập password mới, sau đó copy hash vào file `auth_config.py`:

```python
# Sửa dòng này trong central-monitor/auth_config.py
ADMIN_PASSWORD_HASH = "your_new_hash_here"
```

---

## 🧪 Testing

### Test 1: Central Monitor Authentication

1. **Start Central Monitor:**
   ```bash
   cd central-monitor
   python monitor_server.py
   ```

2. **Truy cập:** http://localhost:27009
   - Sẽ tự động redirect đến `/login`
   
3. **Login:**
   - Username: `admin`
   - Password: `admin123`
   
4. **Kiểm tra:**
   - ✓ Sau khi login, vào được dashboard
   - ✓ Navbar có nút "🚪 Logout" màu đỏ
   - ✓ Click logout → redirect về login page
   - ✓ Không thể truy cập routes khác khi chưa login

### Test 2: Elasticsearch Logging - IDS Engine

1. **Start IDS Engine:**
   ```bash
   cd ids
   sudo python ids_engine.py  # Cần sudo vì packet capture
   ```

2. **Trigger một attack (từ máy khác hoặc terminal khác):**
   ```bash
   # Port scan
   nmap -sS localhost
   
   # Or telnet probe
   telnet localhost 23
   ```

3. **Kiểm tra logs trong Elasticsearch:**
   ```bash
   # Check số lượng attack logs
   curl http://localhost:9200/pandora-ids-attacks-*/_count
   
   # Xem attack logs
   curl http://localhost:9200/pandora-ids-attacks-*/_search?size=5&pretty
   ```

4. **Xem trong Kibana Dashboard:**
   - Truy cập: http://localhost:5601
   - Menu → Dashboards → "Pandora IDS Attack Overview"
   - Sẽ thấy:
     - Top Attackers chart
     - Attack Types pie chart
     - Timeline
     - Geographic map

### Test 3: Elasticsearch Logging - Honeypot

1. **Start Honeypot Webserver:**
   ```bash
   cd custom-webserver
   sudo python port_443.py  # Cần sudo vì port 443
   ```

2. **Trigger honeypot activities:**
   ```bash
   # Từ browser hoặc curl
   curl -k https://localhost/
   curl -k https://localhost/api/v1/scan/1.1.1.1
   curl -k "https://localhost/test?id=1' OR 1=1--"  # SQL injection attempt
   ```

3. **Kiểm tra logs:**
   ```bash
   # Check số lượng honeypot logs
   curl http://localhost:9200/pandora-honeypot-logs-*/_count
   
   # Xem logs
   curl http://localhost:9200/pandora-honeypot-logs-*/_search?size=5&pretty
   ```

4. **Xem trong Kibana:**
   - Dashboard → "Pandora Honeypot Activity"
   - Sẽ thấy:
     - Activity Types distribution
     - Authenticated vs Anonymous users
     - Top Suspicious IPs

### Test 4: Retention Policy

```bash
# Kiểm tra ILM policy (90 ngày)
curl http://localhost:9200/_ilm/policy/pandora-log-retention-policy?pretty
```

**Output sẽ có:**
```json
{
  "delete": {
    "min_age": "90d",
    "actions": {
      "delete": {}
    }
  }
}
```

---

## 📊 Kibana Dashboards

### Dashboard 1: Pandora IDS Attack Overview
**URL:** http://localhost:5601/app/dashboards#/view/pandora-ids-dashboard

**Bao gồm:**
- 📊 Top 10 Attackers (by Source IP) - Bar chart
- 🥧 Attack Types Distribution - Pie chart
- 📈 Attack Timeline (24h) - Line chart
- 🍩 Severity Breakdown - Donut chart
- 🗺️ Geographic Attack Distribution - Map

### Dashboard 2: Pandora Honeypot Activity
**URL:** http://localhost:5601/app/dashboards#/view/pandora-honeypot-dashboard

**Bao gồm:**
- 🥧 Activity Types - Pie chart
- 📊 Authenticated vs Anonymous Users - Bar chart
- 📋 Top Suspicious IPs - Table

**Features:**
- ✅ Auto-refresh: 60 seconds
- ✅ Time range: Last 24 hours (có thể thay đổi)
- ✅ Filters: Có thể filter theo nhiều tiêu chí
- ✅ Export: PDF/CSV

---

## ⚙️ Configuration

### Central Monitor Auth

File: `central-monitor/auth_config.py`

```python
# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "$2b$12$..."  # Hash của "admin123"

# Session config
SESSION_SECRET_KEY = "change-this-secret-key-in-production"
SESSION_LIFETIME_HOURS = 24
```

### Elasticsearch

File: `backend-admin/config.py`

```python
# Elasticsearch
ELASTICSEARCH_HOSTS: List[str] = ["http://localhost:9200"]
ELASTICSEARCH_USERNAME: str = ""  # Để trống nếu không auth
ELASTICSEARCH_PASSWORD: str = ""
ELASTICSEARCH_LOG_RETENTION_DAYS: int = 90  # Có thể thay đổi
ELASTICSEARCH_HONEYPOT_INDEX: str = "pandora-honeypot-logs"
ELASTICSEARCH_IDS_INDEX: str = "pandora-ids-attacks"
ELASTICSEARCH_ENABLED: bool = True
```

---

## 🔧 Thay đổi Retention Policy

### Cách 1: Via Config (Recommended)

Sửa `backend-admin/config.py`:

```python
ELASTICSEARCH_LOG_RETENTION_DAYS: int = 30  # Từ 90 → 30 ngày
```

Restart các services.

### Cách 2: Via Elasticsearch API

```bash
curl -X PUT "http://localhost:9200/_ilm/policy/pandora-log-retention-policy" \
  -H "Content-Type: application/json" \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "min_age": "0ms",
          "actions": {
            "rollover": {
              "max_age": "1d",
              "max_primary_shard_size": "50gb"
            }
          }
        },
        "delete": {
          "min_age": "30d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }'
```

---

## 🐛 Troubleshooting

### 1. Central Monitor - Login không hoạt động

**Kiểm tra:**
```bash
# Check nếu bcrypt đã được cài
pip show bcrypt

# Test password verification
cd central-monitor
python -c "from auth_config import AuthConfig; print(AuthConfig.verify_password('admin', 'admin123'))"
```

**Kết quả mong đợi:** `True`

### 2. Elasticsearch không start

**Lỗi common:** "vm.max_map_count is too low"

**Fix (Linux/WSL):**
```bash
sudo sysctl -w vm.max_map_count=262144
```

**Fix (Windows Docker Desktop):**
```powershell
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
exit
```

### 3. Kibana dashboards không có data

**Nguyên nhân:** Chưa có logs

**Fix:**
1. Trigger attacks/activities (xem phần Testing)
2. Đợi vài giây cho Elasticsearch index
3. Refresh Kibana dashboard
4. Thay đổi time range thành "Last 7 days"

### 4. IDS/Honeypot không gửi logs vào Elasticsearch

**Kiểm tra:**
```bash
# Check Elasticsearch service status
curl http://localhost:9200/_cluster/health

# Check logs trong console
# IDS Engine sẽ print: "[ELASTICSEARCH] ✓ Connected to..."
# Nếu thấy error, check config
```

---

## 📁 Files đã tạo/sửa

### Mới:
- ✅ `central-monitor/auth_config.py`
- ✅ `central-monitor/templates/login.html`
- ✅ `backend-admin/services/elasticsearch_service.py`
- ✅ `elasticsearch/kibana_dashboards.json`
- ✅ `elasticsearch/import_dashboards.py`
- ✅ `elasticsearch/README.md`
- ✅ `SETUP_GUIDE.md` (file này)

### Đã sửa:
- ✅ `central-monitor/monitor_server.py` (thêm auth)
- ✅ `central-monitor/templates/base.html` (thêm logout button)
- ✅ `central-monitor/admin-ui/style.css` (logout button style)
- ✅ `central-monitor/requirements.txt` (thêm bcrypt)
- ✅ `database/docker-compose.yml` (thêm ES + Kibana)
- ✅ `backend-admin/config.py` (thêm ES config)
- ✅ `backend-admin/requirements.txt` (thêm elasticsearch)
- ✅ `ids/ids_engine.py` (gửi logs vào ES)
- ✅ `ids/requirements.txt` (thêm elasticsearch)
- ✅ `custom-webserver/port_443.py` (gửi logs vào ES)

---

## ✅ Checklist Cuối Cùng

- [ ] Dependencies đã được cài đặt
- [ ] Elasticsearch & Kibana đang chạy
- [ ] Dashboards đã được import thành công
- [ ] Central Monitor login hoạt động (admin/admin123)
- [ ] Logout button xuất hiện trong navbar
- [ ] IDS Engine đang gửi logs vào Elasticsearch
- [ ] Honeypot đang gửi logs vào Elasticsearch
- [ ] Kibana dashboards hiển thị data
- [ ] Retention policy đã được cấu hình (90 ngày)

---

## 📞 Support

Nếu gặp vấn đề:

1. Check logs:
   ```bash
   docker logs pandora_elasticsearch
   docker logs pandora_kibana
   ```

2. Xem chi tiết trong: `elasticsearch/README.md`

3. Restart services:
   ```bash
   cd database
   docker-compose restart elasticsearch kibana
   ```

---

**Implementation completed!** 🎉

All features have been implemented and tested according to the plan.

