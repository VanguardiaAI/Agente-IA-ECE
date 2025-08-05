#!/bin/bash

echo "⏳ Waiting for services to be fully ready..."

# Wait for services to be healthy
for i in {1..30}; do
    echo -n "."
    sleep 2
    
    # Check if web-app is healthy
    if docker inspect eva-web-prod --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        echo ""
        echo "✅ Web app is healthy!"
        break
    fi
done

echo ""

# Check service status
echo "📊 Service status:"
docker-compose -f docker-compose.production.yml ps

# Check if there are any errors in the logs
echo -e "\n❌ Recent errors (if any):"
docker logs eva-web-prod --tail 20 2>&1 | grep -i error || echo "No errors found"

# Test access again
echo -e "\n🌐 Testing access:"
echo -n "Local web app (8080): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/

echo -n "Through nginx (80): "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/

echo -n "HTTPS site: "
curl -k -s -o /dev/null -w "%{http_code}\n" https://ia.elcorteelectrico.com/

# Check specific pages
echo -e "\n📄 Page availability:"
echo -n "Dashboard: "
curl -k -s https://ia.elcorteelectrico.com/ | grep -o "<title>.*</title>" | head -1 || echo "Not accessible"

echo -n "Chat interface: "
curl -k -s https://ia.elcorteelectrico.com/chat | grep -o "<title>.*</title>" | head -1 || echo "Not accessible"

echo -n "Admin login: "
curl -k -s https://ia.elcorteelectrico.com/admin/login | grep -o "<title>.*</title>" | head -1 || echo "Not accessible"

# Check for the database error
echo -e "\n🔍 Checking for 'database eva_user' errors:"
docker logs eva-postgres-prod --tail 10 2>&1 | grep "eva_user" || echo "No recent database errors"