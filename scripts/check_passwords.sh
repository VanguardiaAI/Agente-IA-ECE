#!/bin/bash

echo "🔍 Checking password configuration..."

echo -e "\n📋 PostgreSQL container environment:"
docker exec eva-postgres-prod env | grep POSTGRES_PASSWORD

echo -e "\n📋 Web app container environment:"
docker exec eva-web-prod env | grep -E "POSTGRES_PASSWORD|DATABASE_URL"

echo -e "\n📋 Environment file passwords:"
grep -E "POSTGRES_PASSWORD|DATABASE_URL" .env 2>/dev/null || echo ".env not found"
echo ""
grep -E "POSTGRES_PASSWORD|DATABASE_URL" .env.production 2>/dev/null || echo ".env.production not found"

echo -e "\n🔧 Testing connection with different passwords..."

# Test with the password from nuclear script
echo "Testing with eva_secure_password_2025!:"
docker exec eva-postgres-prod sh -c 'PGPASSWORD=eva_secure_password_2025! psql -U eva_user -d eva_db -c "SELECT 1;"' 2>&1 | head -1

# Test with the password from env files
echo -e "\nTesting with chatbot_secure_2025!:"
docker exec eva-postgres-prod sh -c 'PGPASSWORD=chatbot_secure_2025! psql -U eva_user -d eva_db -c "SELECT 1;"' 2>&1 | head -1

# Test with the container's environment password
echo -e "\nTesting with container's POSTGRES_PASSWORD:"
docker exec eva-postgres-prod sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -U eva_user -d eva_db -c "SELECT 1;"' 2>&1 | head -1