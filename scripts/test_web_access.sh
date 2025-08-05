#!/bin/bash

echo "🌐 Testing web access..."

# Test local access
echo "📍 Local access tests:"
echo -n "  - Web app directly (port 8080): "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 && echo " ✅" || echo " ❌"

echo -n "  - Through nginx (port 80): "
curl -s -o /dev/null -w "%{http_code}" http://localhost && echo " ✅" || echo " ❌"

echo -n "  - Dashboard page: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ && echo " ✅" || echo " ❌"

# Test external domain
echo -e "\n🌍 External domain tests:"
echo -n "  - HTTP redirect: "
curl -s -o /dev/null -w "%{http_code}" http://ia.elcorteelectrico.com && echo " (should be 301)" || echo " ❌"

echo -n "  - HTTPS main page: "
response=$(curl -k -s -o /dev/null -w "%{http_code}" https://ia.elcorteelectrico.com 2>&1)
if [[ "$response" == "200" ]]; then
    echo "200 ✅"
elif [[ "$response" == "502" ]]; then
    echo "502 - Bad Gateway (nginx can't reach backend)"
else
    echo "$response"
fi

# Show a sample of the page content
echo -e "\n📄 Page content test:"
curl -k -s https://ia.elcorteelectrico.com | head -20 | grep -E "<title>|<h1>|Eva" || echo "Could not fetch page content"

# Test specific endpoints
echo -e "\n🔧 API endpoint tests:"
echo -n "  - Health check: "
curl -s http://localhost:8080/health | jq -r '.status' 2>/dev/null || echo "Failed"

echo -n "  - Admin login page: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/admin/login && echo " ✅" || echo " ❌"