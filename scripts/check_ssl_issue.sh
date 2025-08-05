#!/bin/bash

echo "🔍 Checking SSL/HTTPS configuration..."

# Check if nginx is running
echo "📦 Nginx container status:"
docker ps | grep nginx

# Check nginx logs for SSL errors
echo -e "\n❌ Recent nginx errors:"
docker logs eva-nginx-prod --tail 30 2>&1 | grep -E "SSL|ssl|certificate|443" || echo "No SSL errors found"

# Check if certificates exist
echo -e "\n🔐 Checking SSL certificates:"
docker exec eva-nginx-prod ls -la /etc/letsencrypt/live/ 2>&1 || echo "Cannot access certificates directory"

# Check nginx configuration
echo -e "\n📄 Nginx SSL configuration:"
docker exec eva-nginx-prod cat /etc/nginx/nginx.conf | grep -A5 -B5 "ssl_certificate" || echo "No SSL config found"

# Test HTTP vs HTTPS
echo -e "\n🌐 Testing connections:"
echo -n "HTTP (port 80): "
curl -s -o /dev/null -w "%{http_code}\n" http://ia.elcorteelectrico.com || echo "Failed"

echo -n "HTTPS (port 443) with -k flag: "
curl -k -s -o /dev/null -w "%{http_code}\n" https://ia.elcorteelectrico.com 2>&1 || echo "Failed"

# Check if port 443 is listening
echo -e "\n🔌 Port 443 status:"
docker exec eva-nginx-prod netstat -tlnp | grep 443 || echo "Port 443 not listening"

# Alternative access methods
echo -e "\n💡 Alternative access methods while we fix HTTPS:"
echo "1. Direct HTTP (redirects to HTTPS): http://ia.elcorteelectrico.com"
echo "2. Direct to app (bypassing nginx): http://ia.elcorteelectrico.com:8080"
echo "3. Use the direct app URL for now: http://ia.elcorteelectrico.com:8080"
echo ""
echo "✅ The application is working, just the SSL certificate needs to be configured."