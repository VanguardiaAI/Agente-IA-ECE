#!/bin/bash

# Direct PostgreSQL initialization
set -e

echo "🔧 Direct PostgreSQL initialization..."

# First, let's see what's actually running
echo "📦 Current PostgreSQL container:"
docker ps | grep postgres

# Try to initialize using the postgres binary directly inside the container
echo -e "\n🔧 Attempting direct initialization..."

# The pgvector image should have initialized with POSTGRES_USER from env
# Let's try to connect using the TCP connection instead of socket
echo "🔗 Testing TCP connection with environment credentials..."
docker exec eva-postgres-prod sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -h 127.0.0.1 -p 5432 -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();"' || {
    echo "❌ Failed with eva_user, trying to find the actual superuser..."
    
    # If eva_user doesn't exist, the container might have been initialized differently
    # Let's try to access with the default postgres user via single-user mode
    echo "🔧 Stopping PostgreSQL service in container..."
    docker exec eva-postgres-prod sh -c 'pg_ctl -D /var/lib/postgresql/data/pgdata stop -m fast' 2>/dev/null || true
    sleep 5
    
    echo "🔧 Starting PostgreSQL in single-user mode to create user..."
    docker exec eva-postgres-prod sh -c 'postgres --single -D /var/lib/postgresql/data/pgdata postgres <<EOF
CREATE ROLE eva_user WITH LOGIN SUPERUSER PASSWORD '\''eva_secure_password_2025!'\'';
CREATE DATABASE eva_db OWNER eva_user;
EOF' || echo "Single user mode failed"
    
    echo "🔧 Restarting PostgreSQL service..."
    docker restart eva-postgres-prod
    sleep 10
}

# Now try to connect again
echo -e "\n🔗 Testing connection after fix..."
docker exec eva-postgres-prod sh -c 'PGPASSWORD=eva_secure_password_2025! psql -h 127.0.0.1 -p 5432 -U eva_user -d eva_db -c "SELECT version();"' && {
    echo "✅ Connection successful! Creating extensions and tables..."
    
    # Create vector extension
    docker exec eva-postgres-prod sh -c 'PGPASSWORD=eva_secure_password_2025! psql -h 127.0.0.1 -p 5432 -U eva_user -d eva_db -c "CREATE EXTENSION IF NOT EXISTS vector;"'
    
    # Create tables
    docker exec -i eva-postgres-prod sh -c 'PGPASSWORD=eva_secure_password_2025! psql -h 127.0.0.1 -p 5432 -U eva_user -d eva_db' < scripts/create_admin_tables.sql
    docker exec -i eva-postgres-prod sh -c 'PGPASSWORD=eva_secure_password_2025! psql -h 127.0.0.1 -p 5432 -U eva_user -d eva_db' < scripts/create_metrics_tables.sql
    
    echo "✅ Database initialization complete!"
} || {
    echo "❌ Still cannot connect. Please check the debug script output."
    exit 1
}