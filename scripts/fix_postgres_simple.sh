#!/bin/bash

# Simple fix for PostgreSQL - use the configured user directly
set -e

echo "🔧 Simple PostgreSQL fix..."

# Get the configured user from the environment
POSTGRES_USER="${POSTGRES_USER:-eva_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-eva_secure_password_2025!}"
POSTGRES_DB="${POSTGRES_DB:-eva_db}"

echo "📊 Creating tables using configured user: $POSTGRES_USER"

# The database and user already exist from the container initialization
# Just create the extension and tables

# Create vector extension (as superuser which is eva_user in this setup)
docker exec eva-postgres-prod psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "Extension might already exist"

# Create tables
echo "📊 Creating admin tables..."
docker exec -i eva-postgres-prod psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < scripts/create_admin_tables.sql || echo "Admin tables might already exist"

echo "📊 Creating metrics tables..."
docker exec -i eva-postgres-prod psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < scripts/create_metrics_tables.sql || echo "Metrics tables might already exist"

# Restart services
echo "🔄 Restarting web services..."
docker-compose -f docker-compose.production.yml restart web-app mcp-server

echo "✅ Setup complete!"