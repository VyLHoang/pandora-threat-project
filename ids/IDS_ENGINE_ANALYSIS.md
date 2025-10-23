# Phân tích và Đề xuất: IDS Engine

## Tổng quan

IDS Engine (`ids/ids_engine.py`) hoạt động **độc lập** và **song song** với Honeypot Webserver, không có xung đột về mặt kỹ thuật.

## Kiến trúc Capture Data (Song song)

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
            ┌──────────────────────┐
            │  Network Interface   │
            │     (eth0/ens33)     │
            └──────────┬───────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ↓ (Packet Level)              ↓ (Application Level)
┌───────────────────┐       ┌─────────────────────┐
│   IDS Engine      │       │     Nginx:443       │
│  (Scapy Sniffer)  │       │  (SSL Termination)  │
│                   │       └──────────┬──────────┘
│ - Sniff packets   │                  │
│ - Detect attacks  │                  ↓
│ - Log to DB       │       ┌─────────────────────┐
│                   │       │  FastAPI Webserver  │
└───────────────────┘       │     (Port 8443)     │
                            │                     │
                            │ - Serve Vue.js      │
                            │ - Log honeypot      │
                            │ - Proxy API         │
                            └─────────────────────┘
```

## Cơ chế Capture Data

### 1. Tầng Mạng (Network Layer) - IDS Engine
**Công cụ:** Scapy  
**Layer:** OSI Layer 3-4 (IP, TCP, UDP)  
**Phát hiện:**
- Port Scan (nmap, masscan)
- SYN Flood
- Packet anomalies
- Connection patterns

**Ưu điểm:**
- Phát hiện tấn công TRƯỚC KHI đến application
- Có thể detect các tấn công không qua HTTP (raw TCP/UDP)
- Không bị bypass bởi encryption (vì sniff trước SSL)

**Nhược điểm:**
- Không hiểu nội dung HTTP request
- Cần root/admin privileges
- Có thể tạo false positive

### 2. Tầng Ứng dụng (Application Layer) - Honeypot Webserver
**Công cụ:** FastAPI + Middleware  
**Layer:** OSI Layer 7 (HTTP/HTTPS)  
**Phát hiện:**
- SQL Injection
- XSS attempts
- Path Traversal
- Suspicious payloads
- User behavior

**Ưu điểm:**
- Hiểu rõ HTTP request content
- Track user sessions và authentication
- Detect application-level attacks
- Không cần root privileges

**Nhược điểm:**
- Chỉ phát hiện SAU KHI request đến webserver
- Không detect được non-HTTP attacks

## Bảng so sánh

| Tính năng | IDS Engine | Honeypot Webserver |
|-----------|------------|-------------------|
| **Layer** | Network (L3-L4) | Application (L7) |
| **Tool** | Scapy | FastAPI |
| **Detect** | Port scan, SYN flood | SQL injection, XSS |
| **Privileges** | Root/Admin required | User-level OK |
| **Performance Impact** | Medium | Low |
| **Database Table** | `attack_logs` | `honeypot_logs` |
| **False Positives** | High | Low |
| **Bypass Risk** | Low | Medium |

## Xung đột và Giải pháp

### ❌ Không có xung đột về mặt kỹ thuật

IDS Engine và Webserver **KHÔNG xung đột** vì:
1. **Khác layer:** IDS ở tầng packet, Webserver ở tầng HTTP
2. **Khác port:** IDS sniff tất cả, Webserver listen port 8443
3. **Khác database:** IDS → `attack_logs`, Webserver → `honeypot_logs`

### ⚠️ Cần cấu hình đúng

#### 1. Network Interface cho IDS
IDS cần biết interface nào để sniff:

```python
# Tự động detect (khuyến khích)
engine = IDSEngine(interface=None)

# Hoặc chỉ định cụ thể
engine = IDSEngine(interface='eth0')  # Linux
engine = IDSEngine(interface='ens33')  # Ubuntu/CentOS
```

**Kiểm tra interface:**
```bash
ip addr show  # Linux
ifconfig      # macOS
ipconfig      # Windows
```

#### 2. Firewall Rules
Đảm bảo firewall KHÔNG block traffic trước khi IDS kịp sniff:

```bash
# ✅ ĐÚNG: IDS sniff trước khi iptables filter
# iptables filter chain: PREROUTING → INPUT → FORWARD → OUTPUT → POSTROUTING
# Scapy sniff tại PREROUTING (raw socket)

# ❌ SAI: Đừng drop packets quá sớm
iptables -I INPUT -j DROP  # Bad: IDS không kịp thấy
```

#### 3. Permissions
IDS cần chạy với quyền cao:

```bash
# Linux
sudo python ids_engine.py

# Hoặc dùng capabilities (không cần root)
sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)
```

## Đề xuất Cải tiến

### 1. Tích hợp IDS và Honeypot (Correlation)

**Vấn đề hiện tại:** Hai hệ thống chạy độc lập, không liên kết.

**Giải pháp:** Tạo "Correlation Engine" để liên kết:

```python
# Ví dụ: Nếu IDS phát hiện port scan từ IP X
# → Honeypot tăng suspicious score cho tất cả request từ IP X

class CorrelationEngine:
    def __init__(self):
        self.threat_ips = set()
    
    def mark_threat(self, ip: str):
        """Được gọi từ IDS khi detect attack"""
        self.threat_ips.add(ip)
        # Cache vào Redis với TTL 1 giờ
        redis_client.setex(f"threat:{ip}", 3600, "1")
    
    def is_threat(self, ip: str) -> bool:
        """Được gọi từ Honeypot để check"""
        return ip in self.threat_ips or redis_client.exists(f"threat:{ip}")
```

**Cập nhật Honeypot:**
```python
# Trong webserver_fastapi.py
suspicious_score, reasons = calculate_suspicious_score(...)

# Nếu IP đã bị IDS đánh dấu → tăng score
if correlation_engine.is_threat(client_ip):
    suspicious_score += 40
    reasons.append("IP flagged by IDS")
```

### 2. Cấu hình IDS cho môi trường Nginx

**File mới:** `ids/ids_config.yaml`
```yaml
ids:
  # Network interface to monitor
  interface: auto  # auto-detect hoặc 'eth0', 'ens33'
  
  # Ports to monitor (skip internal traffic)
  critical_ports:
    - 80
    - 443
    - 22
    - 3306
    - 5432
  
  # Whitelist IPs (không alert)
  whitelist_ips:
    - 127.0.0.1
    - ::1
  
  # Thresholds
  thresholds:
    port_scan: 3        # số port trong time_window
    syn_flood: 20       # số SYN trong time_window
    time_window: 60     # seconds
  
  # Logging
  log_to_db: true
  log_to_elasticsearch: true
  log_to_file: /var/log/pandora/ids.log
```

### 3. IDS Dashboard (Real-time)

**Tích hợp với Central Monitor:**
```python
# Thêm WebSocket endpoint để stream IDS alerts
@app.websocket("/ws/ids")
async def ids_stream(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Stream real-time attacks từ IDS
        attack = await get_latest_attack()
        await websocket.send_json(attack)
```

**Frontend (Vue.js):**
```javascript
// Real-time IDS alerts
const ws = new WebSocket('wss://localhost/ws/ids')
ws.onmessage = (event) => {
  const attack = JSON.parse(event.data)
  showNotification(`Attack detected: ${attack.type} from ${attack.source_ip}`)
}
```

### 4. Giảm False Positives

**Vấn đề:** IDS phát hiện cả traffic hợp lệ (ví dụ: browser pre-connect).

**Giải pháp:**

```python
# Whitelist established connections
def is_legitimate_traffic(packet):
    """Skip alert cho traffic hợp lệ"""
    src_ip = packet[IP].src
    dst_port = packet[TCP].dport
    
    # 1. Whitelist known IPs
    if src_ip in WHITELIST_IPS:
        return True
    
    # 2. Whitelist established connections (có ACK flag)
    if 'A' in str(packet[TCP].flags):
        return True
    
    # 3. Whitelist return traffic (src_port = server port)
    if packet[TCP].sport in [80, 443]:
        return True
    
    return False
```

### 5. Performance Optimization

**Vấn đề:** Sniffing mọi packet → CPU cao.

**Giải pháp:**

```python
# BPF Filter (Berkeley Packet Filter) - hardware level
filter_str = "tcp and (dst port 80 or dst port 443 or dst port 22)"

sniff(
    iface=interface,
    filter=filter_str,  # Filter ngay tại kernel level
    prn=packet_handler,
    store=False
)
```

## Cấu hình Systemd cho IDS

**File:** `deploy/systemd/pandora-ids.service`

```ini
[Unit]
Description=Pandora IDS Engine (Network Intrusion Detection)
After=network.target postgresql.service

[Service]
Type=simple
User=root  # Required for packet capture
WorkingDirectory=/opt/pandora/ids
ExecStart=/opt/pandora/ids/venv/bin/python ids_engine.py
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Kiểm tra hoạt động

### Test IDS Detection

```bash
# 1. Port Scan Test
nmap -sS -p 1-1000 <your-server-ip>

# Kết quả mong đợi:
# IDS log: "Port scan detected from <scanner-ip>"
# Database: attack_logs table có record mới
```

### Test Honeypot Logging

```bash
# 2. SQL Injection Test
curl "https://localhost/api/test?id=1' OR '1'='1"

# Kết quả mong đợi:
# Honeypot log: "Suspicious activity, score: 85"
# Database: honeypot_logs table có record mới
```

### Test Correlation

```bash
# 3. Combined Test
# Bước 1: Trigger IDS (port scan)
nmap -sS -p 80,443 <your-server-ip>

# Bước 2: Send HTTP request từ cùng IP
curl https://localhost/

# Kết quả mong đợi:
# Honeypot tăng suspicious score vì IP đã bị IDS flag
```

## Tóm tắt Đề xuất

### ✅ Cần làm ngay:
1. **Cấu hình interface:** Đảm bảo IDS sniff đúng interface
2. **Chạy với quyền root:** IDS cần privileges
3. **Whitelist localhost:** Không alert cho traffic nội bộ

### 🚀 Cải tiến tương lai:
1. **Correlation Engine:** Liên kết IDS và Honeypot
2. **BPF Filter:** Giảm CPU usage
3. **Real-time Dashboard:** WebSocket stream
4. **Machine Learning:** Giảm false positive

### ⚠️ Lưu ý:
- IDS và Honeypot **KHÔNG xung đột**
- Chúng **bổ sung** cho nhau (defense in depth)
- IDS = Tầng mạng, Honeypot = Tầng ứng dụng
- Không tắt một trong hai, chạy song song để đạt hiệu quả cao nhất

## Kết luận

IDS Engine hoạt động tốt với kiến trúc Nginx mới. Không cần thay đổi gì về mặt code, chỉ cần:
1. Chạy IDS với quyền root/admin
2. Cấu hình đúng network interface
3. Đảm bảo database connection

**Recommendation:** Giữ nguyên IDS Engine, thêm Correlation Engine để tích hợp tốt hơn với Honeypot.

