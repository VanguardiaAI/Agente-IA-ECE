#!/bin/bash
# Setup automatic updates for Eva (products and knowledge base)
# Runs twice daily at 6:00 AM and 6:00 PM

echo "🔧 Setting up automatic updates for Eva..."

# Create logs directory
sudo mkdir -p /opt/eva/logs
sudo chown $USER:$USER /opt/eva/logs

# Make scripts executable
chmod +x /opt/eva/MCP-WC/scripts/auto_update.py
chmod +x /opt/eva/MCP-WC/scripts/check_update_status.py

# Setup cron jobs
CRON_FILE="/tmp/eva_cron"

# Get current crontab (if exists)
crontab -l > "$CRON_FILE" 2>/dev/null || true

# Remove existing Eva update entries
grep -v "eva.*auto_update" "$CRON_FILE" > "$CRON_FILE.tmp" || true
mv "$CRON_FILE.tmp" "$CRON_FILE"

# Add new cron jobs
# 6:00 AM daily
echo "0 6 * * * cd /opt/eva/MCP-WC && /opt/eva/MCP-WC/venv/bin/python /opt/eva/MCP-WC/scripts/auto_update.py >> /opt/eva/logs/cron.log 2>&1" >> "$CRON_FILE"

# 6:00 PM daily
echo "0 18 * * * cd /opt/eva/MCP-WC && /opt/eva/MCP-WC/venv/bin/python /opt/eva/MCP-WC/scripts/auto_update.py >> /opt/eva/logs/cron.log 2>&1" >> "$CRON_FILE"

# Daily log rotation at midnight
echo "0 0 * * * find /opt/eva/logs -name '*.log' -mtime +7 -delete" >> "$CRON_FILE"

# Install new crontab
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "📅 Update Schedule:"
echo "  - Morning update: 6:00 AM"
echo "  - Evening update: 6:00 PM"
echo "  - Log rotation: Midnight (keeps 7 days)"
echo ""
echo "📂 Log files location: /opt/eva/logs/"
echo ""
echo "🔍 To check cron jobs: crontab -l"
echo "📊 To check update status: python scripts/check_update_status.py"
echo ""
echo "🚀 First update will run at the next scheduled time."