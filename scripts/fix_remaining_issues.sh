#!/bin/bash

echo "🔧 Fixing remaining issues..."

# 1. Fix the backup service that's trying to connect to wrong database
echo "📦 Fixing backup service configuration..."
docker-compose -f docker-compose.production.yml stop backup
docker-compose -f docker-compose.production.yml rm -f backup

# 2. Check MCP server logs
echo -e "\n📜 MCP server logs:"
docker logs eva-mcp-prod --tail 20

# 3. Rebuild MCP server with health endpoint
echo -e "\n🔨 Rebuilding MCP server..."
docker-compose -f docker-compose.production.yml build mcp-server
docker-compose -f docker-compose.production.yml up -d mcp-server

# 4. Wait for MCP to start
echo -e "\n⏳ Waiting for MCP server to start..."
sleep 10

# 5. Test MCP health endpoint
echo -e "\n🔍 Testing MCP health endpoint:"
curl -v http://localhost:8000/health

# 6. Check nginx configuration
echo -e "\n🔧 Checking nginx upstream configuration:"
docker exec eva-nginx-prod cat /etc/nginx/nginx.conf | grep -A5 "upstream"

# 7. Test website through nginx
echo -e "\n🌐 Testing website through nginx:"
curl -s -I http://localhost/ | head -10

# 8. Final status check
echo -e "\n📊 Final container status:"
docker-compose -f docker-compose.production.yml ps