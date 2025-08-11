#!/bin/bash
# Check the status of automatic updates in Docker environment

echo "🔍 Eva Docker Auto Update Status"
echo "================================"

# Check if cron container is running
if docker ps | grep -q eva-cron-prod; then
    echo "✅ Cron container is running"
    
    # Show container logs (last 20 lines)
    echo -e "\n📋 Recent cron logs:"
    docker logs eva-cron-prod --tail 20 2>&1 | grep -E "(Starting|completed|ERROR|Product|Knowledge)"
    
    # Check cron health
    echo -e "\n🏥 Cron health check:"
    docker exec eva-cron-prod tail -5 /app/logs/cron_health.log 2>/dev/null || echo "No health log found yet"
    
    # Check update status
    echo -e "\n📊 Last update status:"
    docker exec eva-cron-prod cat /app/logs/update_status.txt 2>/dev/null || echo "No status file found yet"
    
    # Show update logs
    echo -e "\n📄 Recent update logs:"
    docker exec eva-cron-prod tail -20 /app/logs/auto_update_*.log 2>/dev/null | grep -E "(Product sync|Knowledge base|completed|ERROR)" || echo "No update logs found yet"
    
else
    echo "❌ Cron container is not running!"
    echo "   Run: docker-compose -f docker-compose.production.yml up -d cron-updater"
fi

echo -e "\n💡 Useful commands:"
echo "  - View full logs: docker logs eva-cron-prod -f"
echo "  - Enter container: docker exec -it eva-cron-prod bash"
echo "  - Check crontab: docker exec eva-cron-prod crontab -l"
echo "  - Run update manually: docker exec eva-cron-prod python /app/scripts/auto_update_docker.py"