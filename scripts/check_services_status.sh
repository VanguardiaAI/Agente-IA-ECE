#!/bin/bash

echo "🔍 Checking service status..."

# Check running containers
echo -e "\n📦 Running containers:"
docker-compose -f docker-compose.production.yml ps

# Check if services are accessible
echo -e "\n🌐 Service endpoints:"
echo -n "Web interface (8080): "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health || echo "Failed"

echo -n "MCP server (8000): "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "Failed"

echo -n "PostgreSQL (5432): "
docker exec eva-postgres-prod pg_isready -U eva_user -d eva_db && echo "Ready" || echo "Not ready"

# Check for the database error
echo -e "\n❌ Checking for database 'eva_user' error source:"
docker logs eva-postgres-prod --tail 20 | grep "eva_user" | tail -5

# Check web app logs for errors
echo -e "\n📜 Recent web app errors:"
docker logs eva-web-prod 2>&1 | grep -i error | tail -10

# Check nginx status
echo -e "\n🔧 Nginx status:"
docker logs eva-nginx-prod --tail 10 2>&1

# Test the main website
echo -e "\n🌐 Testing main website:"
echo -n "https://ia.elcorteelectrico.com status: "
curl -k -s -o /dev/null -w "%{http_code}" https://ia.elcorteelectrico.com || echo "Failed"