#!/bin/bash

echo "🔍 Checking PostgreSQL setup..."

# Check if postgres container is running
echo "📦 Container status:"
docker ps | grep postgres

# Try to connect as postgres user (default superuser)
echo -e "\n👤 Trying to connect as postgres user:"
docker exec eva-postgres-prod psql -U postgres -c "\du" 2>&1

# Check what databases exist
echo -e "\n📊 Checking databases:"
docker exec eva-postgres-prod psql -U postgres -l 2>&1

# Check environment variables in the container
echo -e "\n🔧 Container environment variables:"
docker exec eva-postgres-prod env | grep POSTGRES

# Check if we can connect with the environment variables
echo -e "\n🔗 Checking connection with env vars:"
docker exec eva-postgres-prod sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();"' 2>&1