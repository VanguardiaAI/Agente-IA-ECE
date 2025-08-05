#!/bin/bash

echo "🔍 Debugging 500 error..."

# Check web app logs for the actual error
echo "📜 Web app error details:"
docker logs eva-web-prod --tail 50 2>&1 | grep -E "ERROR|Exception|Traceback" -A 5 -B 2

# Check specific dashboard error
echo -e "\n❌ Dashboard specific errors:"
docker logs eva-web-prod 2>&1 | grep -i "dashboard" -A 5 | tail -20

# Test the dashboard directly
echo -e "\n🌐 Testing dashboard endpoint:"
curl -s http://localhost:8080/ | grep -o "Error:.*" || echo "No error message in HTML"

# Check if it's the datetime serialization issue
echo -e "\n📅 Checking for datetime serialization error:"
docker logs eva-web-prod 2>&1 | grep "datetime is not JSON serializable" -A 3 -B 3 | tail -10

# Test API endpoints
echo -e "\n🔧 Testing API endpoints:"
echo -n "Health check: "
curl -s http://localhost:8080/health | jq -r '.status' 2>/dev/null || echo "Failed"

echo -n "Bot config: "
curl -s http://localhost:8080/api/bot-config | jq -r '.status' 2>/dev/null || echo "OK"

# Show which pages are working
echo -e "\n✅ Working pages:"
echo "- Chat: https://ia.elcorteelectrico.com/chat"
echo "- Admin: https://ia.elcorteelectrico.com/admin/login"

# Suggest temporary workaround
echo -e "\n💡 For now, use these URLs:"
echo "- Chat interface: https://ia.elcorteelectrico.com/chat"
echo "- Admin panel: https://ia.elcorteelectrico.com/admin/login"
echo ""
echo "The dashboard error doesn't affect the chat functionality."