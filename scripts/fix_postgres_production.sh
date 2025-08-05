#!/bin/bash

# Script to fix PostgreSQL production setup
set -e

echo "🔧 Fixing PostgreSQL production setup..."

# Stop all containers
echo "⏹️  Stopping all containers..."
docker-compose -f docker-compose.production.yml down

# Remove old containers and volumes
echo "🗑️  Removing old containers and orphans..."
docker-compose -f docker-compose.production.yml down --remove-orphans

# Remove the postgres data volume to start fresh
echo "🗑️  Removing old postgres data..."
docker volume rm agente-ia-ece_postgres_data 2>/dev/null || true

# Start PostgreSQL with the correct environment
echo "🚀 Starting fresh PostgreSQL container..."
docker-compose -f docker-compose.production.yml up -d postgres

# Wait for PostgreSQL to initialize
echo "⏳ Waiting for PostgreSQL to initialize (30 seconds)..."
sleep 30

# Now create the database and user using the postgres user from the container
echo "📦 Creating database and user..."
docker exec eva-postgres-prod psql -U postgres -c "CREATE DATABASE eva_db;" || echo "Database might already exist"
docker exec eva-postgres-prod psql -U postgres -c "CREATE USER eva_user WITH PASSWORD 'eva_secure_password_2025!';" || echo "User might already exist"
docker exec eva-postgres-prod psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE eva_db TO eva_user;"
docker exec eva-postgres-prod psql -U postgres -d eva_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec eva-postgres-prod psql -U postgres -d eva_db -c "GRANT ALL ON SCHEMA public TO eva_user;"

# Create tables
echo "📊 Creating tables..."
docker exec eva-postgres-prod psql -U eva_user -d eva_db -f /app/scripts/create_admin_tables.sql || echo "Admin tables might already exist"
docker exec eva-postgres-prod psql -U eva_user -d eva_db -f /app/scripts/create_metrics_tables.sql || echo "Metrics tables might already exist"

# Start all services
echo "🚀 Starting all services..."
docker-compose -f docker-compose.production.yml up -d

echo "✅ PostgreSQL fix complete!"
echo ""
echo "🔍 Checking service status..."
docker-compose -f docker-compose.production.yml ps