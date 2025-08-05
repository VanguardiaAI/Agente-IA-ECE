#!/bin/bash

echo "🔧 Fixing nginx proxy configuration..."

# Check nginx error logs
echo "📜 Nginx error logs:"
docker logs eva-nginx-prod --tail 20 2>&1 | grep -E "error|Error|ERROR" || echo "No errors in logs"

# Check if nginx can reach the backend
echo -e "\n🔗 Testing backend connectivity from nginx:"
docker exec eva-nginx-prod wget -O- http://web-app:8080/health 2>&1 | grep -E "status|failed|error" || echo "Backend not reachable"

# Check nginx access logs for 500 errors
echo -e "\n📊 Recent 500 errors in nginx:"
docker logs eva-nginx-prod 2>&1 | grep " 500 " | tail -5

# Test the actual error
echo -e "\n🌐 Getting actual error from HTTPS:"
curl -k -s https://ia.elcorteelectrico.com 2>&1 | grep -E "Error|error|500" | head -20

# Check if it's the datetime error on dashboard
echo -e "\n📅 Checking if it's the dashboard datetime error:"
curl -s http://localhost:8080/ | grep -o "Error:.*" || echo "No error in direct access"

# Restart nginx to ensure fresh connection
echo -e "\n🔄 Restarting nginx..."
docker-compose -f docker-compose.production.yml restart nginx

# Wait and test again
echo -e "\n⏳ Waiting for nginx to restart..."
sleep 10

echo -e "\n🌐 Testing after restart:"
echo -n "HTTP: "
curl -s -o /dev/null -w "%{http_code}\n" http://ia.elcorteelectrico.com

echo -n "HTTPS: "
curl -k -s -o /dev/null -w "%{http_code}\n" https://ia.elcorteelectrico.com

echo -n "HTTPS Chat: "
curl -k -s -o /dev/null -w "%{http_code}\n" https://ia.elcorteelectrico.com/chat

echo -n "Direct app: "
curl -s -o /dev/null -w "%{http_code}\n" http://ia.elcorteelectrico.com:8080/

echo -e "\n✅ Summary:"
echo "- If HTTPS returns 502: nginx can't reach backend"
echo "- If HTTPS returns 500: backend error (likely dashboard datetime)"
echo "- If HTTPS returns 200: everything is working!"
echo ""
echo "🎯 Use these URLs:"
echo "- Dashboard: http://ia.elcorteelectrico.com:8080/"
echo "- Chat (HTTPS): https://ia.elcorteelectrico.com/chat"
echo "- Admin (HTTPS): https://ia.elcorteelectrico.com/admin/login"