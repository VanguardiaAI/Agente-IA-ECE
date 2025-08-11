#!/bin/bash
# Setup automatic updates in Docker production environment

echo "🚀 Setting up Eva automatic updates for Docker production..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on production server
if [ ! -f ".env.production" ]; then
    echo -e "${RED}❌ .env.production not found!${NC}"
    echo "Please ensure you're running this on the production server with proper environment files."
    exit 1
fi

# Ensure proper permissions
echo -e "${YELLOW}Setting up permissions...${NC}"
chmod +x scripts/auto_update_docker.py
chmod +x scripts/check_docker_updates.sh
chmod +x docker/cron/entrypoint.sh

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p logs
mkdir -p knowledge

# Build and start the cron service
echo -e "${YELLOW}Building and starting cron service...${NC}"
docker-compose -f docker-compose.production.yml build cron-updater
docker-compose -f docker-compose.production.yml up -d cron-updater

# Wait for container to start
sleep 5

# Check if container is running
if docker ps | grep -q eva-cron-prod; then
    echo -e "${GREEN}✅ Cron service started successfully!${NC}"
    
    # Show initial status
    echo -e "\n${YELLOW}Checking service status...${NC}"
    docker logs eva-cron-prod --tail 10
    
    # Show crontab
    echo -e "\n${YELLOW}Configured update schedule:${NC}"
    docker exec eva-cron-prod crontab -l
    
else
    echo -e "${RED}❌ Failed to start cron service!${NC}"
    echo "Check logs with: docker logs eva-cron-prod"
    exit 1
fi

echo -e "\n${GREEN}✅ Automatic updates configured successfully!${NC}"
echo -e "\n📅 Update Schedule (adjust TZ in .env.production for your timezone):"
echo "  - Morning update: 6:00 AM"
echo "  - Evening update: 6:00 PM"
echo "  - Log rotation: Daily at midnight"

echo -e "\n🔧 Useful commands:"
echo "  - Check status: ./scripts/check_docker_updates.sh"
echo "  - View logs: docker logs eva-cron-prod -f"
echo "  - Run update now: docker exec eva-cron-prod python /app/scripts/auto_update_docker.py"
echo "  - Enter container: docker exec -it eva-cron-prod bash"

echo -e "\n💡 Important notes:"
echo "  1. Set your timezone in .env.production (TZ=Europe/Madrid)"
echo "  2. Updates run inside the Docker network"
echo "  3. Logs are stored in ./logs/ directory"
echo "  4. Status file: ./logs/update_status.json"