#!/bin/bash
set -e

echo "Starting Eva Cron Service..."
echo "Container started at $(date)" >> /app/logs/cron.log

# Ensure log directory exists with proper permissions
mkdir -p /app/logs
chmod 755 /app/logs

# Environment variables for cron
printenv | grep -E '^(POSTGRES_|WOOCOMMERCE_|OPENAI_|DATABASE_URL)' > /etc/environment

# Start cron in foreground
echo "Starting cron daemon..."
cron -f