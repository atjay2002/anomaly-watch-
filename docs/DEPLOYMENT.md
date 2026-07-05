## AnomalyWatch Deployment Guide

## Prerequisites

- Ubuntu 24.04 LTS (tested) or compatible Linux
- Python 3.10 or higher
- 4GB RAM minimum, 8GB recommended
- 1GB free disk space
- Sudo/root access for system installation

## Quick Installation

```bash
cd /path/to/anamoly_detection
chmod +x deploy/install.sh
./deploy/install.sh
sudo systemctl start anomalywatch
```

Access dashboard at `http://localhost:5000`

## Manual Installation

### 1. System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
```

### 2. Create Installation Directory

```bash
sudo mkdir -p /opt/anomalywatch
sudo cp -r . /opt/anomalywatch/
sudo chown -R $USER:$USER /opt/anomalywatch
```

### 3. Python Virtual Environment

```bash
cd /opt/anomalywatch
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r deploy/requirements.txt
```

### 4. Create Required Directories

```bash
mkdir -p models logs
```

### 5. Create System User

```bash
sudo useradd -r -s /bin/false anomalywatch
sudo chown -R anomalywatch:anomalywatch /opt/anomalywatch
```

### 6. Install Systemd Service

```bash
sudo cp deploy/anomalywatch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable anomalywatch
sudo systemctl start anomalywatch
```

### 7. Verify Installation

```bash
sudo systemctl status anomalywatch
journalctl -u anomalywatch -f
curl http://localhost:5000/health
```

## Configuration

### Environment Variables

Create `/opt/anomalywatch/.env`:
```bash
# Monitoring
ANOMALY_MONITOR_INTERVAL=5
ANOMALY_BASELINE_MINUTES=15

# Detection Thresholds
ANOMALY_WARNING_THRESHOLD=30
ANOMALY_CRITICAL_THRESHOLD=70

# Alerts
ANOMALY_ENABLE_DESKTOP=true
ANOMALY_ALERT_COOLDOWN=60

# Database
ANOMALY_DB_RETENTION_DAYS=7

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_SECRET_KEY=your-secret-key-here

# Logging
LOG_LEVEL=INFO
```

Load in service file by editing `/etc/systemd/system/anomalywatch.service`:
```ini
[Service]
EnvironmentFile=/opt/anomalywatch/.env
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart anomalywatch
```

## Raspberry Pi Deployment

### Additional Steps for GPIO

1. Install GPIO library:
```bash
source /opt/anomalywatch/venv/bin/activate
pip install RPi.GPIO
```

2. Enable GPIO alerts:
```bash
echo "ANOMALY_ENABLE_GPIO=true" | sudo tee -a /opt/anomalywatch/.env
```

3. Grant GPIO permissions:
```bash
sudo usermod -a -G gpio anomalywatch
```

4. Restart service:
```bash
sudo systemctl restart anomalywatch
```

## Network Access

### Allow External Access

By default, Flask binds to `0.0.0.0`. To restrict:
```bash
FLASK_HOST=127.0.0.1  # localhost only
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name anomalywatch.local;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # Important for SSE
        proxy_read_timeout 300s;
    }
}
```

### Firewall

```bash
sudo ufw allow 5000/tcp
```

## Monitoring & Maintenance

### Check Status

```bash
sudo systemctl status anomalywatch
```

### View Logs

```bash
# Real-time logs
journalctl -u anomalywatch -f

# Last 100 lines
journalctl -u anomalywatch -n 100

# Logs since yesterday
journalctl -u anomalywatch --since yesterday

# Application logs
tail -f /opt/anomalywatch/logs/anomalywatch.log
```

### Database Maintenance

```bash
# Check database size
du -h /opt/anomalywatch/anomalywatch.db

# Vacuum (compact) database
sqlite3 /opt/anomalywatch/anomalywatch.db "VACUUM;"

# Manually clean old data (>7 days)
sqlite3 /opt/anomalywatch/anomalywatch.db "DELETE FROM metrics WHERE timestamp < $(date -d '7 days ago' +%s);"
```

### Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/var/backups/anomalywatch"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /opt/anomalywatch/anomalywatch.db $BACKUP_DIR/db_$DATE.db
cp /opt/anomalywatch/models/* $BACKUP_DIR/

# Keep only last 7 backups
ls -t $BACKUP_DIR/db_*.db | tail -n +8 | xargs rm -f
```

### Update Deployment

```bash
# Stop service
sudo systemctl stop anomalywatch

# Backup
cp /opt/anomalywatch/anomalywatch.db /tmp/backup.db

# Update code
cd /opt/anomalywatch
git pull  # or copy new files

# Update dependencies
source venv/bin/activate
pip install -r deploy/requirements.txt

# Restart
sudo systemctl start anomalywatch
```

## Troubleshooting

### Service Won't Start

```bash
# Check service logs
journalctl -u anomalywatch -xe

# Check Python errors
sudo -u anomalywatch /opt/anomalywatch/venv/bin/python /opt/anomalywatch/app.py

# Verify permissions
ls -la /opt/anomalywatch
```

### High Memory Usage

- Reduce retention: `ANOMALY_DB_RETENTION_DAYS=3`
- Increase interval: `ANOMALY_MONITOR_INTERVAL=10`
- Vacuum database regularly

### Port Already in Use

```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill process
sudo kill -9 <PID>

# Or change port
FLASK_PORT=5001
```

### SSE Connection Issues

- Check firewall rules
- Verify `proxy_buffering off` if using Nginx
- Increase `proxy_read_timeout`
- Check browser console for errors

## Security Hardening

### Add Authentication (Nginx)

```nginx
location / {
    auth_basic "AnomalyWatch";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:5000;
}
```

Create password file:
```bash
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

### SSL/TLS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d anomalywatch.yourdomain.com
```

### Restrict Access by IP

```nginx
location / {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://127.0.0.1:5000;
}
```

## Performance Tuning

### Optimize Database

```bash
# Enable WAL mode for better concurrency
sqlite3 /opt/anomalywatch/anomalywatch.db "PRAGMA journal_mode=WAL;"

# Increase cache size
sqlite3 /opt/anomalywatch/anomalywatch.db "PRAGMA cache_size=10000;"
```

### Adjust Monitoring Frequency

For lower resource usage:
```bash
ANOMALY_MONITOR_INTERVAL=10  # instead of 5
```

For higher precision (more resources):
```bash
ANOMALY_MONITOR_INTERVAL=2
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop anomalywatch
sudo systemctl disable anomalywatch
sudo rm /etc/systemd/system/anomalywatch.service
sudo systemctl daemon-reload

# Remove files
sudo rm -rf /opt/anomalywatch

# Remove user
sudo userdel anomalywatch

# Remove logs
sudo rm -rf /var/log/anomalywatch
```
