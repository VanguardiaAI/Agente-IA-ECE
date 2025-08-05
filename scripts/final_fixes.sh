#!/bin/bash

echo "🔧 Applying final fixes..."

# 1. Stop the backup service that's causing database errors
echo "📦 Stopping backup service (causing database eva_user errors)..."
docker-compose -f docker-compose.production.yml stop backup
docker-compose -f docker-compose.production.yml rm -f backup

# 2. Check what's trying to connect to database "eva_user"
echo -e "\n🔍 Finding source of 'database eva_user' error..."
# It might be in the backup script
if [ -f scripts/backup.sh ]; then
    echo "Checking backup.sh..."
    grep -n "eva_user\|chatbot_user" scripts/backup.sh || echo "Not found in backup.sh"
fi

# 3. Show the error in dashboard
echo -e "\n❌ Dashboard error details:"
docker logs eva-web-prod 2>&1 | grep -A5 "datetime is not JSON serializable" | tail -10

# 4. Test if the chat interface works
echo -e "\n💬 Testing chat interface:"
curl -s http://localhost:8080/chat | grep -o "<title>.*</title>" || echo "Chat page not accessible"

# 5. Final status
echo -e "\n✅ Final service status:"
docker-compose -f docker-compose.production.yml ps

echo -e "\n🌐 Website access test:"
echo "Main page (HTTPS): $(curl -k -s -o /dev/null -w "%{http_code}" https://ia.elcorteelectrico.com)"
echo "Chat page (HTTPS): $(curl -k -s -o /dev/null -w "%{http_code}" https://ia.elcorteelectrico.com/chat)"
echo "Admin page (HTTPS): $(curl -k -s -o /dev/null -w "%{http_code}" https://ia.elcorteelectrico.com/admin/login)"