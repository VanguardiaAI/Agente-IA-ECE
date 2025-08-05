#!/bin/bash

# Fix password mismatch between PostgreSQL and application
set -e

echo "🔧 Fixing password mismatch..."

# Get the actual password from the environment file
if [ -f ".env" ]; then
    ACTUAL_PASSWORD=$(grep "^POSTGRES_PASSWORD=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    echo "📋 Password from .env: $ACTUAL_PASSWORD"
elif [ -f ".env.production" ]; then
    ACTUAL_PASSWORD=$(grep "^POSTGRES_PASSWORD=" .env.production | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    echo "📋 Password from .env.production: $ACTUAL_PASSWORD"
else
    echo "❌ No .env file found! Using default password..."
    ACTUAL_PASSWORD="chatbot_secure_2025!"
fi

# Update the eva_user password in PostgreSQL
echo "🔐 Updating eva_user password in PostgreSQL..."
docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "ALTER USER eva_user WITH PASSWORD '$ACTUAL_PASSWORD';" || {
    # If we can't connect as eva_user, we need to use superuser mode
    echo "⚠️  Cannot connect as eva_user, trying alternative method..."
    
    # Try to create a temporary superuser
    docker exec eva-postgres-prod sh -c "
        psql -U \$POSTGRES_USER -d \$POSTGRES_DB <<EOF
ALTER USER eva_user WITH PASSWORD '$ACTUAL_PASSWORD';
EOF
    " || {
        echo "❌ Failed to update password. Trying single-user mode..."
        
        # Stop PostgreSQL service
        docker exec eva-postgres-prod sh -c 'pg_ctl -D /var/lib/postgresql/data/pgdata stop -m fast' 2>/dev/null || true
        sleep 5
        
        # Update password in single-user mode
        docker exec eva-postgres-prod sh -c "
            su - postgres -c \"postgres --single -D /var/lib/postgresql/data/pgdata eva_db <<EOF
ALTER USER eva_user WITH PASSWORD '$ACTUAL_PASSWORD';
EOF\"
        "
        
        # Restart container
        docker restart eva-postgres-prod
        sleep 10
    }
}

# Test the connection
echo -e "\n🔍 Testing connection with updated password..."
docker exec eva-postgres-prod sh -c "PGPASSWORD='$ACTUAL_PASSWORD' psql -U eva_user -d eva_db -c 'SELECT version();'" && {
    echo "✅ Password updated successfully!"
    
    # Restart the web services to use the new password
    echo "🔄 Restarting web services..."
    docker-compose -f docker-compose.production.yml restart web-app mcp-server
    
    echo "✅ Fix complete!"
} || {
    echo "❌ Still cannot connect. Please check the logs."
    exit 1
}