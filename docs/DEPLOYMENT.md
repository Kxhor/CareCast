# CareCast Deployment Guide (Decision OD-04)

This document provides comprehensive operational deployment instructions for CareCast per User Decision **OD-04 (Option B: Local Virtualenv Deployment with Documented Run Command)**, with optional containerization guidance.

---

## 1. Option B: Local Virtualenv Deployment (Approved Target)

CareCast is designed as a lightweight, zero-external-service web application powered by Python, FastAPI, and an embedded read-only SQLite database.

### 1.1 Prerequisites
- Python $\ge$ 3.11 (Python 3.12 or 3.14 recommended)
- SQLite 3 (bundled with Python standard library)
- Web browser (Chromium, Edge, Firefox, or Safari)

### 1.2 Step-by-Step Installation & Run Instructions

```bash
# 1. Clone repository
git clone https://github.com/organization/carecast.git
cd carecast

# 2. Create isolated virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 4. Install production dependencies (zero dev dependencies)
pip install -r requirements.txt

# 5. Build pipeline & database (idempotent migration, ingestion, model training)
python -m carecast.pipeline rebuild

# 6. Verify installation and dependencies
python scripts/verify.py

# 7. Start production web server
CARECAST_ENV=prod python -m uvicorn carecast.api.main:app --host 127.0.0.1 --port 8000
```

### 1.3 Windows / PowerShell Launch Command
On Windows systems, environment variables can be set per command or exported:
```powershell
$env:CARECAST_ENV="prod"
$env:CARECAST_ENABLE_DOCS="0"
.venv\Scripts\python -m uvicorn carecast.api.main:app --host 127.0.0.1 --port 8000
```
Then navigate to: **`http://127.0.0.1:8000`**

### 1.4 HTTPS & Transport Security Note
> [!NOTE]
> For local loopback deployment (`127.0.0.1`), HTTPS controls and HSTS headers are **NOT APPLICABLE** because browsers ignore HSTS over local insecure origins. When deploying behind a production TLS reverse proxy (such as Nginx, Caddy, or AWS ALB), set `CARECAST_HSTS=1` to activate `Strict-Transport-Security: max-age=31536000; includeSubDomains`.

### 1.5 Systemd Service Unit Example (Linux Production)
`/etc/systemd/system/carecast.service`:
```ini
[Unit]
Description=CareCast Respiratory Forecasting Service
After=network.target

[Service]
Type=simple
User=carecast
Group=carecast
WorkingDirectory=/opt/carecast
Environment="CARECAST_ENV=prod"
Environment="CARECAST_ENABLE_DOCS=0"
Environment="CARECAST_DB_PATH=/opt/carecast/data/carecast.db"
ExecStart=/opt/carecast/.venv/bin/uvicorn carecast.api.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

---

## 2. Optional: Containerized Deployment (Docker)

For environments requiring containerization, a hardened multi-stage `Dockerfile` is provided in the repository root.

### Features
- **Minimal attack surface:** Python 3.12-slim base image.
- **Non-root user execution:** Runs under dedicated system UID `10001:10001`.
- **Zero build artifacts:** Build toolchains and wheels isolated in builder stage.
- **Automated Healthcheck:** Queries `/api/v1/health` every 30 seconds.

### Build and Run Commands
```bash
# Build production image
docker build -t carecast:latest .

# Run containerized service
docker run -d \
  --name carecast-app \
  -p 8000:8000 \
  --read-only \
  --tmpfs /tmp \
  carecast:latest

# Check health status
docker inspect --format='{{json .State.Health.Status}}' carecast-app
```

---

## 3. Operational Verification

To confirm the service is healthy:
```bash
# Query healthcheck endpoint
curl -s http://127.0.0.1:8000/api/v1/health
# Expected JSON response:
# {"status":"ok","db_ok":true,"data_as_of":"2026-10-03","version":"0.1.0"}
```
