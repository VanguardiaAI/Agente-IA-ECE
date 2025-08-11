# Automatic Updates Documentation

## Overview

Eva includes an automatic update system that keeps products and knowledge base synchronized with your WooCommerce store. Updates run twice daily to ensure customers always have access to the latest information.

## Features

- **Product Synchronization**: Incremental sync with WooCommerce (only changed products)
- **Knowledge Base Updates**: Automatic embedding generation for new/modified documents
- **Docker Integration**: Runs as a separate container in production
- **Timezone Support**: Configurable timezone for update schedules
- **Comprehensive Logging**: Detailed logs with 7-day retention
- **Status Monitoring**: JSON and text status files for easy monitoring

## Production Setup (Docker)

### 1. Configure Environment

Add timezone to your `.env.production`:
```env
# Timezone for cron jobs (default: UTC)
TZ=Europe/Madrid  # Adjust to your timezone
```

### 2. Deploy the Cron Service

```bash
# Run the setup script
./scripts/docker-update-setup.sh

# Or manually with docker-compose
docker-compose -f docker-compose.production.yml up -d cron-updater
```

### 3. Verify Installation

```bash
# Check service status
./scripts/check_docker_updates.sh

# View container logs
docker logs eva-cron-prod -f

# Check crontab
docker exec eva-cron-prod crontab -l
```

## Update Schedule

Updates run at:
- **6:00 AM** - Morning update
- **6:00 PM** - Evening update
- **Midnight** - Log rotation (keeps 7 days)

Times are in the configured timezone (TZ environment variable).

## Manual Operations

### Run Update Immediately
```bash
docker exec eva-cron-prod python /app/scripts/auto_update_docker.py
```

### Check Last Update Status
```bash
# Quick status
docker exec eva-cron-prod cat /app/logs/update_status.txt

# Detailed JSON status
docker exec eva-cron-prod cat /app/logs/update_status.json
```

### View Update Logs
```bash
# Today's logs
docker exec eva-cron-prod tail -f /app/logs/auto_update_$(date +%Y%m%d).log

# All recent logs
docker exec eva-cron-prod ls -la /app/logs/
```

## Monitoring

### Status Files

1. **Text Status** (`/app/logs/update_status.txt`):
   ```
   2025-01-11 06:00:15|SUCCESS|{'products': {'added': 5, 'updated': 12, ...}}
   ```

2. **JSON Status** (`/app/logs/update_status.json`):
   ```json
   {
     "timestamp": "2025-01-11 06:00:15",
     "success": true,
     "products": {
       "added": 5,
       "updated": 12,
       "deleted": 0,
       "errors": 0
     },
     "knowledge": true
   }
   ```

### Health Checks

The cron service writes health checks every 5 minutes:
```bash
docker exec eva-cron-prod tail /app/logs/cron_health.log
```

## Troubleshooting

### Updates Not Running

1. **Check container status**:
   ```bash
   docker ps | grep eva-cron-prod
   ```

2. **Verify environment variables**:
   ```bash
   docker exec eva-cron-prod env | grep -E "(POSTGRES|WOOCOMMERCE|TZ)"
   ```

3. **Test database connection**:
   ```bash
   docker exec eva-cron-prod python -c "
   import asyncio
   from services.database_service import DatabaseService
   from config.settings import settings
   async def test():
       db = DatabaseService(settings.DATABASE_URL)
       await db.initialize()
       print('Database connected!')
       await db.close()
   asyncio.run(test())
   "
   ```

### Common Issues

1. **Wrong timezone**: Updates run at unexpected times
   - Solution: Set correct TZ in `.env.production`

2. **Database connection errors**: PostgreSQL not accessible
   - Solution: Ensure postgres container is healthy
   - Check DATABASE_URL and network configuration

3. **WooCommerce API errors**: Failed to fetch products
   - Solution: Verify API credentials in `.env.production`
   - Check WooCommerce store accessibility

4. **Permission errors**: Can't write logs
   - Solution: `chmod -R 755 logs/`

## Integration with Monitoring

### Prometheus Metrics

Add to your monitoring setup:
```yaml
- job_name: 'eva-updates'
  static_configs:
    - targets: ['eva-cron-prod:9090']
  metrics_path: '/metrics'
```

### Alerts

Example alert for failed updates:
```yaml
- alert: EvaUpdateFailed
  expr: eva_update_success == 0
  for: 5m
  annotations:
    summary: "Eva automatic update failed"
```

## Best Practices

1. **Monitor regularly**: Check update status daily
2. **Review logs**: Look for patterns in errors
3. **Test after deployment**: Run manual update to verify setup
4. **Backup before updates**: Ensure database backups are current
5. **Set correct timezone**: Avoid confusion with update times

## Related Documentation

- [Incremental Sync](./INCREMENTAL_SYNC.md)
- [Knowledge Base](./KNOWLEDGE_BASE.md)
- [Docker Production](./docker-production.md)