# Pandora Elasticsearch & Kibana Setup

Hướng dẫn cài đặt và sử dụng Elasticsearch + Kibana cho Pandora Threat Intelligence Platform.

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Cài đặt](#cài-đặt)
- [Cấu hình](#cấu-hình)
- [Import Dashboards](#import-dashboards)
- [Truy cập Kibana](#truy-cập-kibana)
- [Quản lý Retention Policy](#quản-lý-retention-policy)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Tổng quan

Elasticsearch được sử dụng để lưu trữ và phân tích:
- **IDS Attack Logs**: Các cuộc tấn công được phát hiện bởi IDS Engine
- **Honeypot Activity Logs**: Tất cả hoạt động trên port 443 webserver

Kibana cung cấp dashboard trực quan để:
- Xem Top Attackers (IPs tấn công nhiều nhất)
- Phân tích Attack Types (loại tấn công)
- Timeline của các cuộc tấn công
- Geographic distribution (bản đồ địa lý)
- Honeypot activity patterns

---

## 🚀 Cài đặt

### Bước 1: Start Elasticsearch & Kibana

```bash
cd database
docker-compose up -d elasticsearch kibana
```

### Bước 2: Kiểm tra trạng thái

```bash
# Kiểm tra Elasticsearch
curl http://localhost:9200

# Kiểm tra Kibana
curl http://localhost:5601/api/status
```

**Output mong đợi:**
```json
{
  "name": "pandora-es-node",
  "cluster_name": "pandora-cluster",
  "version": {
    "number": "8.11.0"
  }
}
```

### Bước 3: Import Dashboards

```bash
cd elasticsearch
python import_dashboards.py
```

**Output:**
```
[SUCCESS] ✓ Dashboards imported successfully!
[INFO] Successfully imported 10 objects
```

---

## ⚙️ Cấu hình

### Config trong `backend-admin/config.py`:

```python
# Elasticsearch Configuration
ELASTICSEARCH_HOSTS: List[str] = ["http://localhost:9200"]
ELASTICSEARCH_USERNAME: str = ""  # Để trống nếu không dùng auth
ELASTICSEARCH_PASSWORD: str = ""
ELASTICSEARCH_LOG_RETENTION_DAYS: int = 90  # Mặc định 90 ngày
ELASTICSEARCH_HONEYPOT_INDEX: str = "pandora-honeypot-logs"
ELASTICSEARCH_IDS_INDEX: str = "pandora-ids-attacks"
ELASTICSEARCH_ENABLED: bool = True
```

### Ports:
- **Elasticsearch**: `http://localhost:9200`
- **Kibana**: `http://localhost:5601`

---

## 📊 Import Dashboards

Script `import_dashboards.py` tự động import:

### 1. Index Patterns
- `pandora-ids-attacks-*`
- `pandora-honeypot-logs-*`

### 2. Dashboards
- **Pandora IDS Attack Overview**: Tổng quan các cuộc tấn công
- **Pandora Honeypot Activity**: Hoạt động trên honeypot

### 3. Visualizations
- Top 10 Attackers (Bar chart)
- Attack Types Distribution (Pie chart)
- Attack Timeline (Line chart)
- Severity Breakdown (Donut chart)
- Geographic Attack Distribution (Map)
- Honeypot Activity Types (Pie chart)
- Authenticated vs Anonymous Users (Bar chart)
- Top Suspicious IPs (Table)

### Manual Import (nếu script fail):

1. Truy cập Kibana: http://localhost:5601
2. Menu → **Stack Management** → **Saved Objects**
3. Click **Import**
4. Chọn file `kibana_dashboards.json`
5. Click **Import**

---

## 🎨 Truy cập Kibana

### URL:
```
http://localhost:5601
```

### Xem Dashboards:

1. **IDS Attack Overview**:
   ```
   http://localhost:5601/app/dashboards#/view/pandora-ids-dashboard
   ```

2. **Honeypot Activity**:
   ```
   http://localhost:5601/app/dashboards#/view/pandora-honeypot-dashboard
   ```

### Tính năng:
- ✅ Auto-refresh mỗi 60 giây
- ✅ Time range: Last 24 hours (có thể thay đổi)
- ✅ Filters: Có thể filter theo severity, attack type, IP, etc.
- ✅ Export: Có thể export reports dạng PDF/CSV

---

## 🗄️ Quản lý Retention Policy

### Mặc định: 90 ngày

Logs sẽ tự động xóa sau 90 ngày nhờ Index Lifecycle Management (ILM).

### Thay đổi Retention Period:

#### Method 1: Via Config (Recommended)

Sửa file `backend-admin/config.py`:

```python
ELASTICSEARCH_LOG_RETENTION_DAYS: int = 30  # Thay đổi từ 90 → 30 ngày
```

Sau đó restart services để áp dụng:

```bash
# Restart IDS Engine
# Restart Honeypot Webserver
# Restart Backend Admin
```

#### Method 2: Via Kibana UI

1. Truy cập Kibana: http://localhost:5601
2. Menu → **Stack Management** → **Index Lifecycle Policies**
3. Tìm policy: `pandora-log-retention-policy`
4. Click **Edit**
5. Sửa `delete` phase → `min_age`: `30d` (thay vì 90d)
6. Save

#### Method 3: Via Elasticsearch API

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

### Kiểm tra ILM Policy:

```bash
curl http://localhost:9200/_ilm/policy/pandora-log-retention-policy
```

---

## 🔍 Query Examples

### Tìm tất cả attacks từ một IP:

```bash
curl -X GET "http://localhost:9200/pandora-ids-attacks-*/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "source_ip": "192.168.1.100"
      }
    }
  }'
```

### Tìm critical attacks trong 24h qua:

```bash
curl -X GET "http://localhost:9200/pandora-ids-attacks-*/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"match": {"severity": "critical"}},
          {"range": {"@timestamp": {"gte": "now-24h"}}}
        ]
      }
    }
  }'
```

### Đếm số lượng logs:

```bash
# IDS Attacks
curl http://localhost:9200/pandora-ids-attacks-*/_count

# Honeypot Logs
curl http://localhost:9200/pandora-honeypot-logs-*/_count
```

---

## 🐛 Troubleshooting

### 1. Elasticsearch không start

**Lỗi: "max virtual memory areas vm.max_map_count [65530] is too low"**

**Fix (Linux/WSL):**
```bash
sudo sysctl -w vm.max_map_count=262144
# Permanent fix:
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

**Fix (Windows Docker Desktop):**
```powershell
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
exit
```

### 2. Kibana không kết nối được Elasticsearch

```bash
# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# Check Kibana logs
docker logs pandora_kibana

# Restart Kibana
docker restart pandora_kibana
```

### 3. Dashboards không hiển thị data

**Nguyên nhân:** Chưa có logs hoặc time range không đúng

**Fix:**
1. Kiểm tra có logs không:
   ```bash
   curl http://localhost:9200/pandora-ids-attacks-*/_count
   curl http://localhost:9200/pandora-honeypot-logs-*/_count
   ```

2. Trigger một số attacks để tạo data:
   ```bash
   # Run nmap scan
   nmap -sS localhost
   ```

3. Trong Kibana, đổi time range thành "Last 7 days" hoặc "Last 30 days"

### 4. Import dashboards failed

```bash
# Retry import
cd elasticsearch
python import_dashboards.py

# Manual import via Kibana UI
# Vào http://localhost:5601 → Stack Management → Saved Objects → Import
```

### 5. Disk space đầy

```bash
# Xem dung lượng sử dụng
curl http://localhost:9200/_cat/indices?v

# Xóa old indices manually
curl -X DELETE http://localhost:9200/pandora-ids-attacks-2024.01.01

# Hoặc giảm retention period (xem phần trên)
```

---

## 📈 Performance Tips

### 1. Tăng memory cho Elasticsearch (nếu có nhiều logs)

Sửa `database/docker-compose.yml`:

```yaml
elasticsearch:
  environment:
    - "ES_JAVA_OPTS=-Xms1g -Xmx1g"  # Tăng từ 512m → 1g
```

### 2. Tăng số shards (cho cluster lớn)

Trong template config, sửa:
```json
"number_of_shards": 3  // Tăng từ 1 → 3
```

### 3. Enable replicas (cho high availability)

```json
"number_of_replicas": 1  // Tăng từ 0 → 1
```

---

## 📚 Tài liệu tham khảo

- [Elasticsearch Official Docs](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Official Docs](https://www.elastic.co/guide/en/kibana/current/index.html)
- [ILM Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-lifecycle-management.html)

---

## ✅ Checklist

- [ ] Elasticsearch đang chạy (port 9200)
- [ ] Kibana đang chạy (port 5601)
- [ ] Dashboards đã được import
- [ ] IDS Engine đang gửi logs
- [ ] Honeypot đang gửi logs
- [ ] Retention policy đã được cấu hình
- [ ] Dashboards hiển thị data

---

**Created by:** Pandora Team
**Last Updated:** 2024

