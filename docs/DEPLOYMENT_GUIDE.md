# Deployment Guide - Eva MCP-WC

## Quick Start

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- PostgreSQL with pgvector extension
- WooCommerce store with API access

### 1. Clone and Setup
```bash
git clone <repository>
cd MCP-WC
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp env.example .env
cp env.agent.example env.agent
# Edit .env and env.agent with your credentials
```

### 3. Start Services

#### Option A: Automated Start
```bash
python start_services.py
```

#### Option B: Docker Production
```bash
./scripts/docker-production.sh start
```

#### Option C: Manual Start
```bash
# Terminal 1: Start PostgreSQL
docker-compose up -d postgres

# Terminal 2: Start MCP Server
python main.py

# Terminal 3: Start Web Interface
python app.py
```

## Production Deployment

### 1. Server Requirements
- CPU: 2+ cores
- RAM: 4GB minimum
- Storage: 20GB+ for database
- OS: Ubuntu 20.04+ or similar

### 2. Security Setup
```bash
# Create non-root user
adduser eva
usermod -aG docker eva

# Setup firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 3. SSL/TLS Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /mcp {
        proxy_pass http://localhost:8000;
    }
}
```

### 4. Systemd Services
```ini
# /etc/systemd/system/eva-mcp.service
[Unit]
Description=Eva MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=eva
WorkingDirectory=/opt/eva/MCP-WC
Environment="PATH=/opt/eva/MCP-WC/venv/bin"
ExecStart=/opt/eva/MCP-WC/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5. Monitoring Setup
```bash
# Install monitoring tools
apt install htop postgresql-client

# Setup log rotation
cat > /etc/logrotate.d/eva << EOF
/opt/eva/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### 6. Backup Configuration
```bash
# Automated daily backups
0 2 * * * /opt/eva/MCP-WC/scripts/docker-production.sh backup
```

## Scaling Considerations

### Horizontal Scaling
- Load balancer for multiple web instances
- Read replicas for PostgreSQL
- Redis for session management

### Performance Tuning
```bash
# PostgreSQL optimization
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 1GB

# pgvector optimization
ivfflat.probes = 10
max_parallel_workers = 4
```

## Troubleshooting

### Check Service Status
```bash
systemctl status eva-mcp
systemctl status eva-web
docker-compose ps
```

### View Logs
```bash
journalctl -u eva-mcp -f
docker-compose logs -f postgres
tail -f logs/app.log
```

### Database Issues
```bash
# Check connections
docker exec postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d postgres
python scripts/setup_phase2.py
```

### Performance Issues
```bash
# Check resource usage
htop
docker stats

# Analyze slow queries
docker exec postgres psql -U postgres -d eva -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## Maintenance

### Regular Tasks
1. **Daily**: Check logs for errors
2. **Weekly**: Update dependencies, run tests
3. **Monthly**: Review performance metrics
4. **Quarterly**: Security audit

### Update Procedure
```bash
git pull origin main
pip install -r requirements.txt --upgrade
./scripts/docker-production.sh update
python tests/run_tests.py
```

### Rollback Procedure
```bash
# Restore from backup
./scripts/docker-production.sh restore backup_20240115_020000.sql

# Or revert code
git checkout <previous-version>
./scripts/docker-production.sh restart
```