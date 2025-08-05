#!/bin/bash

# Script to set up production database
# This should be run on the server after docker-compose is up

set -e

echo "🔧 Setting up production database..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Initialize database
echo "📦 Setting up database..."
# The pgvector image creates the user and database from environment variables
# We just need to create the extension
docker exec eva-postgres-prod psql -U "${POSTGRES_USER:-eva_user}" -d "${POSTGRES_DB:-eva_db}" -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "Extension might already exist"

# Create tables
echo "📊 Creating tables..."
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_admin_tables.sql
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_metrics_tables.sql

echo "✅ Database setup complete!"

# Restart services
echo "🔄 Restarting services..."
docker-compose -f docker-compose.production.yml restart web-app mcp-server

echo "🚀 Production setup complete!"