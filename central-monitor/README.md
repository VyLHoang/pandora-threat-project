# 🔍 CENTRAL MONITOR - Pandora Platform

**Centralized real-time monitoring dashboard for all Pandora services**

---

## 📊 Overview

Central Monitor is the **eyes and ears** of the Pandora Platform, tracking all activity across every service and port.

### What it monitors:

```
┌─────────────────────────────────────────────┐
│  CENTRAL MONITOR (Port 3000)                │
│  ┌─────────────────────────────────────┐   │
│  │  Real-time Dashboard                │   │
│  │  - All HTTP requests                │   │
│  │  - API calls                        │   │
│  │  - Database queries                 │   │
│  │  - Cache hits/misses                │   │
│  │  - User authentication              │   │
│  │  - Scan activities                  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ▲
                    │ Receives logs from:
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼────┐  ┌───▼────┐  ┌───▼────┐
    │Port 80 │  │Port 443│  │Port 5173│
    │ HTTP   │  │ HTTPS  │  │ Vue Dev │
    └────────┘  └────────┘  └─────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼────┐  ┌───▼────┐  ┌───▼────┐
    │Port 9000│ │Port 5432│ │Port 6379│
    │Backend  │ │PostgreSQL│ │Redis    │
    └─────────┘ └──────────┘ └─────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd central-monitor
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Start Monitor Server

```bash
python monitor_server.py
```

### 3. Access Dashboard

Open: **http://localhost:3000**

---

## 📡 Features

### ✅ Real-time Dashboard
- Live feed of all platform activity
- Auto-refreshes every 3 seconds
- Clean terminal-style UI (Matrix theme!)

### ✅ Service Tracking
- Per-service request counts
- Response times
- Error rates

### ✅ Port Monitoring
- Track activity on all ports
- Identify bottlenecks
- Spot unusual patterns

### ✅ Smart Logging
- Last 200 events kept in memory
- Automatic log rotation
- Lightweight and fast

---

## 🔌 Integration

### Backend Integration

The backend automatically forwards logs when `ENABLE_MONITORING=True`:

```python
# In config.py
ENABLE_MONITORING: bool = True
CENTRAL_MONITOR_URL: str = "http://localhost:3000/api/logs"
```

### Manual Logging

```python
from services.monitoring_service import monitoring_service

# Log a custom event
monitoring_service.log_request({
    'service': 'my-service',
    'method': 'POST',
    'path': '/api/custom',
    'ip': '127.0.0.1',
    'status': 200
})
```

---

## 🎯 API Endpoints

### `GET /`
Main dashboard (HTML)

### `POST /api/logs`
Receive logs from services

**Request Body:**
```json
{
    "service": "backend-api",
    "method": "POST",
    "path": "/api/v1/auth/login",
    "ip": "127.0.0.1",
    "status": 200,
    "duration_ms": 45,
    "port": "9000"
}
```

### `GET /api/stats`
Get monitoring statistics

**Response:**
```json
{
    "total_events": 1234,
    "services": {
        "backend-api": 890,
        "frontend": 234,
        "database": 110
    },
    "ports": {
        "9000": 890,
        "5173": 234,
        "5432": 110
    },
    "recent_count": 200
}
```

### `GET /health`
Health check endpoint

---

## 🎨 Dashboard Preview

```
┌─────────────────────────────────────────────────────────────┐
│              [MONITOR] Pandora Platform                     │
│        Real-time Traffic Monitoring Across All Services     │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │  1,234  │  │    5    │  │   200   │  │    6    │      │
│  │  Total  │  │ Active  │  │ Recent  │  │  Ports  │      │
│  │ Events  │  │Services │  │  Logs   │  │Monitored│      │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │
│                                                             │
│  [SERVICES] Activity Breakdown                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐         │
│  │ backend-api │ │  frontend   │ │  database   │         │
│  │     890     │ │     234     │ │     110     │         │
│  └─────────────┘ └─────────────┘ └─────────────┘         │
│                                                             │
│  [LOGS] Live Traffic Feed                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 2024-10-10 20:45:32                                 │  │
│  │ [backend-api] POST /api/v1/scan/ip from 127.0.0.1  │  │
│  │ [User: 123]                                         │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │ 2024-10-10 20:45:30                                 │  │
│  │ [frontend] GET /scanner from 127.0.0.1             │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Configuration

Edit settings in `monitor_server.py`:

```python
# Port to run on
PORT = 3000

# Max logs to keep in memory
MAX_LOGS = 200

# Auto-refresh interval (in HTML)
REFRESH_INTERVAL = 3  # seconds
```

---

## 🎓 Use Cases

### 1. Development Debugging
See exactly what requests are hitting your API in real-time

### 2. Performance Monitoring
Track slow endpoints and database queries

### 3. Security Auditing
Monitor suspicious activity patterns

### 4. User Analytics
See what features users are actually using

### 5. Integration Testing
Verify that all services are communicating correctly

---

## 🔐 Security Notes

⚠️ **This is a development tool!**

For production:
- Add authentication
- Use HTTPS
- Implement proper log rotation
- Add rate limiting
- Consider using ELK stack for serious logging

---

## 🚨 Troubleshooting

### Monitor not receiving logs?

Check if `ENABLE_MONITORING=True` in backend config

### Dashboard not loading?

Ensure port 3000 is not in use:
```bash
netstat -ano | findstr :3000
```

### Services not forwarding logs?

Check that `CENTRAL_MONITOR_URL` points to correct host

---

## 📈 Future Enhancements

- [ ] WebSocket for real-time updates (no refresh needed)
- [ ] Export logs to file
- [ ] Search and filter logs
- [ ] Alert on error thresholds
- [ ] Integration with Elasticsearch
- [ ] Grafana dashboard
- [ ] Mobile-responsive UI

---

## 🤝 Integration with Existing Services

All services automatically forward logs when:

1. `ENABLE_MONITORING=True` in config
2. Central Monitor is running on port 3000
3. Service imports `monitoring_service`

No additional code changes needed!

---

**Built with ❤️ for the Pandora Platform**

