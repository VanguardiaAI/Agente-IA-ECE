#!/bin/bash

echo "🔐 Setting up Let's Encrypt SSL certificates..."

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Stop nginx temporarily to get certificates
echo "⏹️  Stopping nginx..."
docker-compose -f docker-compose.production.yml stop nginx

# Get certificates
echo "🔐 Obtaining SSL certificates..."
certbot certonly --standalone \
    -d ia.elcorteelectrico.com \
    --non-interactive \
    --agree-tos \
    --email admin@elcorteelectrico.com \
    --no-eff-email

# Check if certificates were created
if [ -d "/etc/letsencrypt/live/ia.elcorteelectrico.com" ]; then
    echo "✅ Certificates obtained successfully!"
    
    # Start nginx again
    echo "🚀 Starting nginx..."
    docker-compose -f docker-compose.production.yml up -d nginx
    
    # Test HTTPS
    sleep 5
    echo -e "\n🌐 Testing HTTPS..."
    curl -I https://ia.elcorteelectrico.com
else
    echo "❌ Failed to obtain certificates"
    echo "You may need to:"
    echo "1. Ensure port 80 is open"
    echo "2. Ensure domain points to this server"
    echo "3. Try manual setup: certbot certonly --manual -d ia.elcorteelectrico.com"
fi

# Set up auto-renewal
echo -e "\n🔄 Setting up auto-renewal..."
echo "0 0,12 * * * root certbot renew --quiet --post-hook 'docker restart eva-nginx-prod'" > /etc/cron.d/certbot-renew

echo -e "\n✅ SSL setup complete!"