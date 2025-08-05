#!/bin/bash

# Nuclear reset - completely remove everything and start fresh
set -e

echo "☢️  NUCLEAR RESET - This will delete ALL PostgreSQL data!"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Stop everything
echo "⏹️  Stopping ALL containers..."
docker-compose -f docker-compose.production.yml down -v --remove-orphans
docker stop $(docker ps -q) 2>/dev/null || true

# Remove the specific container
echo "🗑️  Removing PostgreSQL container..."
docker stop eva-postgres-prod 2>/dev/null || true
docker rm -f eva-postgres-prod 2>/dev/null || true

# Remove ALL volumes related to this project
echo "🗑️  Removing ALL volumes..."
docker volume ls | grep -E "(eva|postgres|agente)" | awk '{print $2}' | xargs -r docker volume rm 2>/dev/null || true

# Remove any local data directories
echo "🗑️  Removing local data directories..."
rm -rf ./docker/postgres/data 2>/dev/null || true
rm -rf ./postgres_data 2>/dev/null || true
rm -rf ./backups/*.sql 2>/dev/null || true

# Create fresh directories
echo "📁 Creating fresh directories..."
mkdir -p ./docker/postgres/data
mkdir -p ./backups

# Ensure we have the correct .env file
echo "📝 Setting up environment..."
if [ -f ".env.production" ]; then
    cp .env.production .env
    echo "✅ Using .env.production"
else
    echo "❌ .env.production not found!"
    exit 1
fi

# Export the correct variables from .env file
source .env
export POSTGRES_DB="${POSTGRES_DB:-eva_db}"
export POSTGRES_USER="${POSTGRES_USER:-eva_user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-chatbot_secure_2025!}"

echo "Using database: $POSTGRES_DB"
echo "Using user: $POSTGRES_USER"
echo "Using password: [hidden]"

# Start ONLY PostgreSQL with a clean state
echo "🚀 Starting PostgreSQL with clean state..."
docker-compose -f docker-compose.production.yml up -d postgres

# Wait longer for initialization
echo "⏳ Waiting for PostgreSQL to fully initialize (60 seconds)..."
for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""

# Check if it's ready
echo "🔍 Checking PostgreSQL status..."
docker exec eva-postgres-prod pg_isready -U eva_user -d eva_db && {
    echo "✅ PostgreSQL is ready!"
    
    # Create vector extension
    echo "📦 Creating vector extension..."
    docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
    
    # Create tables
    echo "📊 Creating admin tables..."
    docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_admin_tables.sql
    
    echo "📊 Creating metrics tables..."
    docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/create_metrics_tables.sql
    
    # Verify setup
    echo "🔍 Verifying setup..."
    docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "\dt"
    
    # Start all other services
    echo "🚀 Starting all services..."
    docker-compose -f docker-compose.production.yml up -d
    
    echo "✅ NUCLEAR RESET COMPLETE!"
    echo ""
    echo "📊 Service status:"
    docker-compose -f docker-compose.production.yml ps
} || {
    echo "❌ PostgreSQL initialization failed!"
    echo "📜 Container logs:"
    docker logs eva-postgres-prod --tail 50
    exit 1
}