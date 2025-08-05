#!/bin/bash

# Complete PostgreSQL reset for production
set -e

echo "🔧 Complete PostgreSQL reset for production..."

# Stop all containers
echo "⏹️  Stopping all containers..."
docker-compose -f docker-compose.production.yml down -v --remove-orphans

# Stop any remaining PostgreSQL containers
docker stop eva-postgres-prod 2>/dev/null || true
docker rm eva-postgres-prod 2>/dev/null || true

# Clean up any remaining volumes
echo "🗑️  Cleaning up volumes..."
docker volume rm agente-ia-ece_postgres_data 2>/dev/null || true
docker volume rm $(docker volume ls -q | grep eva) 2>/dev/null || true
docker volume rm $(docker volume ls -q | grep postgres) 2>/dev/null || true
docker volume rm $(docker volume ls -q | grep agente-ia-ece) 2>/dev/null || true

# Clean up the local directory bind mount if it exists
echo "🗑️  Cleaning local data directory..."
rm -rf ./docker/postgres/data/* 2>/dev/null || true

# Start only PostgreSQL with correct environment
echo "🚀 Starting PostgreSQL with correct settings..."
# Export the variables so docker-compose can use them
export POSTGRES_DB=eva_db
export POSTGRES_USER=eva_user
export POSTGRES_PASSWORD=eva_secure_password_2025!

docker-compose -f docker-compose.production.yml up -d postgres

# Wait for PostgreSQL to fully initialize
echo "⏳ Waiting for PostgreSQL to initialize (45 seconds)..."
sleep 45

# Verify the setup
echo "🔍 Verifying PostgreSQL setup..."
docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "SELECT version();" || {
    echo "❌ Failed to connect. Checking container logs..."
    docker logs eva-postgres-prod --tail 50
    exit 1
}

# Create vector extension
echo "📦 Creating vector extension..."
docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Create tables
echo "📊 Creating tables..."
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_admin_tables.sql
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_metrics_tables.sql

# Start all other services
echo "🚀 Starting all services..."
docker-compose -f docker-compose.production.yml up -d

echo "✅ PostgreSQL reset complete!"
echo ""
echo "🔍 Service status:"
docker-compose -f docker-compose.production.yml ps