#!/bin/bash
# Script para inicializar todas las tablas de la base de datos

echo "🔧 Inicializando tablas de la base de datos Eva..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar si el contenedor PostgreSQL está ejecutándose
if ! docker ps | grep -q eva-postgres-prod; then
    echo -e "${RED}❌ El contenedor PostgreSQL no está ejecutándose${NC}"
    echo "Ejecuta: docker-compose -f docker-compose.production.yml up -d postgres"
    exit 1
fi

# Ejecutar el script SQL
echo -e "${YELLOW}Creando tablas...${NC}"
docker exec -i eva-postgres-prod psql -U eva_user -d eva_db < scripts/init_database_tables.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tablas creadas exitosamente${NC}"
    
    # Verificar las tablas creadas
    echo -e "\n${YELLOW}Verificando tablas creadas:${NC}"
    docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "\dt"
    
    # Reiniciar servicios
    echo -e "\n${YELLOW}Reiniciando servicios...${NC}"
    docker-compose -f docker-compose.production.yml restart mcp-server web-app
    
    echo -e "\n${GREEN}✅ Inicialización completada${NC}"
    echo -e "\n${YELLOW}Verifica los logs con:${NC}"
    echo "  docker logs eva-mcp-prod -f"
    echo "  docker logs eva-web-prod -f"
else
    echo -e "${RED}❌ Error al crear las tablas${NC}"
    exit 1
fi