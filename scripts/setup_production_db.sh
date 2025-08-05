#!/bin/bash

# Script to set up production database
# This should be run on the server after docker-compose is up

set -e

echo "🔧 Setting up production database..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Initialize database
echo "📦 Creating database and user..."
docker exec -i eva-postgres-prod psql -U postgres < scripts/init_database.sql

# Create tables
echo "📊 Creating tables..."
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_admin_tables.sql
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_metrics_tables.sql

echo "✅ Database setup complete!"

# Restart services
echo "🔄 Restarting services..."
docker-compose -f docker-compose.production.yml restart web-app mcp-server

echo "🚀 Production setup complete!"