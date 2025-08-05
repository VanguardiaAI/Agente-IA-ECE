#!/bin/bash

echo "🔍 Verifying datetime fix was applied..."

# Check if the fix is in the code
echo "📄 Checking if DateTimeEncoder exists in app.py:"
docker exec eva-web-prod grep -n "DateTimeEncoder" /app/app.py | head -5 || echo "DateTimeEncoder not found!"

# Check if serialize_dates exists
echo -e "\n📄 Checking if serialize_dates function exists:"
docker exec eva-web-prod grep -n "serialize_dates" /app/app.py | head -5 || echo "serialize_dates not found!"

# Rebuild the web-app to ensure latest code
echo -e "\n🔨 Rebuilding web-app with latest code..."
docker-compose -f docker-compose.production.yml build web-app

# Restart with the new build
echo -e "\n🔄 Starting with new build..."
docker-compose -f docker-compose.production.yml up -d web-app

# Wait for startup
echo -e "\n⏳ Waiting for web-app to start..."
for i in {1..30}; do
    if docker exec eva-web-prod curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ Web app is ready!"
        break
    fi
    echo -n "."
    sleep 2
done

# Test dashboard
echo -e "\n\n🧪 Testing dashboard:"
curl -s http://localhost:8080/ 2>&1 | grep -E "<title>|Error:" | head -5

# Check the actual error in logs
echo -e "\n📜 Recent errors in web-app logs:"
docker logs eva-web-prod --tail 20 2>&1 | grep -i "error" | tail -5

echo -e "\n💡 If the fix isn't applied, we'll need to manually patch it."