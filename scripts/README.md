# Scripts Folder - Utility Scripts

Thư mục này chứa các utility scripts để debug, test và quản lý IDS system.

## 📝 Available Scripts

### 1. `check_attacks.py`
**Mục đích:** Kiểm tra attacks trong database

**Chức năng:**
- Hiển thị tổng số attacks
- Hiển thị attack mới nhất
- Hiển thị attack cũ nhất
- Đếm số attacks hôm nay
- Liệt kê 5 attacks gần nhất

**Sử dụng:**
```bash
cd e:\port\threat_project
python scripts\check_attacks.py
```

**Output ví dụ:**
```
[TOTAL] 1072 attacks in database

[LATEST ATTACK]
  Time: 2025-10-12 18:37:44
  Type: https_probe
  From: 18.211.186.168:443
  Tool: http_probe
  Severity: medium
  Location: Ashburn, United States

[TODAY] 15 attacks
```

---

### 2. `check_local_ips.py`
**Mục đích:** Kiểm tra local IPs được IDS detect

**Chức năng:**
- Auto-detect tất cả local IPs của server
- Hiển thị hostname
- Hiển thị primary IP
- Liệt kê tất cả network interfaces
- Giải thích IDS behavior với các IPs này

**Sử dụng:**
```bash
cd e:\port\threat_project
python scripts\check_local_ips.py
```

**Output ví dụ:**
```
[DETECTED LOCAL IPs]
  + 127.0.0.1
  + 192.168.1.33
  + 192.168.52.1
  + 172.25.240.1

Traffic FROM these IPs -> IGNORED (outbound)
Traffic TO these IPs -> DETECTED (inbound)
```

**Khi nào dùng:**
- Sau khi cài đặt IDS
- Khi thay đổi network configuration
- Khi debug IDS không detect đúng
- Để verify local IPs được filter

---

### 3. `clear_old_attacks.py`
**Mục đích:** Xóa old attacks từ database (for testing)

**Chức năng:**
- Hiển thị tổng số attacks hiện tại
- Prompt xác nhận trước khi xóa
- Xóa TẤT CẢ attacks trong database
- Hiển thị số lượng sau khi xóa

**Sử dụng:**
```bash
cd e:\port\threat_project
python scripts\clear_old_attacks.py
```

**⚠️ CẢNH BÁO:**
- Script này sẽ XÓA TẤT CẢ attacks!
- Chỉ dùng khi testing hoặc muốn reset database
- KHÔNG chạy trên production!

**Use cases:**
- Fresh testing của IDS
- Clear old test data
- Reset dashboard statistics
- Debugging IDS detection

---

## 🔧 Requirements

Tất cả scripts đều require:
- Python 3.x
- Backend dependencies (SQLAlchemy, psycopg)
- Database connection active

**Cài đặt dependencies:**
```bash
cd e:\port\threat_project\backend
pip install -r requirements.txt
```

---

## 📊 Workflow Example

### Scenario 1: Setup và Testing IDS mới
```bash
# 1. Check local IPs
python scripts\check_local_ips.py

# 2. Clear old test data
python scripts\clear_old_attacks.py

# 3. Start IDS
cd ids
.\start_ids_windows.bat

# 4. Test attack từ máy khác
# (nmap, telnet, etc)

# 5. Check results
python scripts\check_attacks.py
```

---

### Scenario 2: Debug IDS không detect
```bash
# 1. Verify local IPs
python scripts\check_local_ips.py
# → Check xem IP của bạn có trong list không

# 2. Check có attacks nào được log không
python scripts\check_attacks.py
# → Nếu empty, IDS có vấn đề

# 3. Clear và test lại
python scripts\clear_old_attacks.py
# Test attack từ external IP
python scripts\check_attacks.py
```

---

### Scenario 3: Monitor Daily Attacks
```bash
# Morning check
python scripts\check_attacks.py

# Check TODAY count
# Monitor patterns
# Investigate suspicious IPs
```

---

## 🛠️ Troubleshooting

### Error: "No module named 'database'"
**Fix:** Chạy từ project root, không phải từ scripts folder
```bash
cd e:\port\threat_project  # ← Đúng
python scripts\check_attacks.py
```

### Error: "Database connection failed"
**Fix:** Đảm bảo PostgreSQL đang chạy
```bash
# Check database
docker ps | grep postgres
# Hoặc check Windows service
```

### Error: "Permission denied"
**Fix:** Chạy với quyền admin nếu cần
```bash
# PowerShell as Administrator
python scripts\check_attacks.py
```

---

## 📝 Notes

- Scripts này **READ-ONLY** (trừ clear_old_attacks.py)
- Safe để chạy bất cứ lúc nào
- Không affect IDS operation
- Không modify configuration

---

## 🔗 Related Files

- `../ids/ids_engine.py` - Main IDS engine
- `../backend/models/attack.py` - Attack model
- `../backend/database/database.py` - Database connection
- `../IDS_v2.1_UPDATE.md` - IDS documentation

---

**Last Updated:** 2025-10-12  
**Version:** 1.0

