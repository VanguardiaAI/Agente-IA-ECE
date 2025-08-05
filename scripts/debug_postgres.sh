#!/bin/bash

echo "🔍 Debugging PostgreSQL setup..."

# Check what user the PostgreSQL process is running as
echo -e "\n👤 PostgreSQL process info:"
docker exec eva-postgres-prod ps aux | grep postgres

# Check the data directory
echo -e "\n📁 Data directory contents:"
docker exec eva-postgres-prod ls -la /var/lib/postgresql/data/

# Check if there's a pgdata subdirectory
echo -e "\n📁 Checking pgdata subdirectory:"
docker exec eva-postgres-prod ls -la /var/lib/postgresql/data/pgdata/ 2>/dev/null || echo "No pgdata subdirectory"

# Try to find the actual superuser
echo -e "\n🔍 Looking for actual PostgreSQL users:"
docker exec eva-postgres-prod sh -c 'find /var/lib/postgresql/data -name "pg_authid" -exec cat {} \; 2>/dev/null | head -5' || echo "Could not read pg_authid"

# Check PostgreSQL logs
echo -e "\n📜 PostgreSQL container logs (last 30 lines):"
docker logs eva-postgres-prod --tail 30

# Check if we can connect using the container's network
echo -e "\n🔗 Trying to connect via container network:"
docker exec eva-postgres-prod sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"' 2>&1