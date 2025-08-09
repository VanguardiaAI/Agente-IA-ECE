#!/bin/bash

# Script para configurar la base de datos de producción usando Docker
# Usa el contenedor de PostgreSQL que ya está funcionando

set -e

echo "🚀 Configurando base de datos de producción (Docker)..."
echo "===================================================="

# Verificar que Docker está disponible
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker no está disponible"
    exit 1
fi

# Verificar que estamos en el directorio correcto
if [ ! -f "scripts/create_metrics_tables.sql" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto"
    exit 1
fi

# Función para cargar variables de .env
load_env() {
    if [ -f ".env" ]; then
        echo "⚠️  Cargando variables de entorno desde .env..."
        set -a
        source .env
        set +a
        echo "   ✅ Variables cargadas"
    else
        echo "❌ Error: Archivo .env no encontrado"
        exit 1
    fi
}

# Cargar variables
load_env

echo "📊 Configuración de base de datos:"
echo "   Host: $POSTGRES_HOST"
echo "   Database: $POSTGRES_DB"
echo "   User: $POSTGRES_USER"

# Buscar el contenedor de PostgreSQL
echo "🔍 Buscando contenedor de PostgreSQL..."

# Buscar específicamente el contenedor de PostgreSQL
POSTGRES_CONTAINER=""
for container in $(docker ps --format "{{.Names}}"); do
    if [[ "$container" == *"postgres"* ]]; then
        POSTGRES_CONTAINER=$container
        echo "   ✅ Encontrado contenedor de PostgreSQL: $container"
        break
    fi
done

# Si no encontramos contenedor específico de postgres, buscar uno que tenga psql
if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "   🔍 Buscando contenedor con cliente psql..."
    for container in $(docker ps --format "{{.Names}}"); do
        if docker exec $container psql --version &>/dev/null; then
            CLIENT_CONTAINER=$container
            echo "   ✅ Encontrado contenedor con psql: $container"
            break
        fi
    done
    
    if [ -z "$CLIENT_CONTAINER" ]; then
        echo "❌ No se encontró contenedor con PostgreSQL o psql"
        echo "   Contenedores disponibles:"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
        exit 1
    fi
else
    CLIENT_CONTAINER=$POSTGRES_CONTAINER
fi

# Función para ejecutar SQL usando Docker
execute_sql() {
    local file=$1
    local description=$2
    
    echo "🔧 Ejecutando $description..."
    
    if [ -f "$file" ]; then
        # Copiar archivo SQL al contenedor y ejecutarlo
        docker cp "$file" "$CLIENT_CONTAINER:/tmp/migration.sql"
        docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CLIENT_CONTAINER" psql -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/migration.sql
        docker exec "$CLIENT_CONTAINER" rm /tmp/migration.sql
        echo "   ✅ $description completado"
    else
        echo "   ⚠️  Archivo no encontrado: $file"
    fi
}

# Verificar conexión
echo "🔗 Verificando conexión a base de datos..."
echo "   Usando contenedor cliente: $CLIENT_CONTAINER"
echo "   Conectando a host: $POSTGRES_HOST"

if docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CLIENT_CONTAINER" psql -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version();" > /dev/null; then
    echo "   ✅ Conexión exitosa"
else
    echo "   ❌ Error de conexión"
    exit 1
fi

# Crear backup
echo "💾 Creando backup de seguridad..."
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="backup_production_${timestamp}.sql"

docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CLIENT_CONTAINER" pg_dump -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only > "$backup_file"
echo "   📁 Backup guardado como: $backup_file"

# Verificar tablas existentes
echo "📋 Verificando tablas existentes..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CLIENT_CONTAINER" psql -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT 
    table_name,
    CASE 
        WHEN table_name IN ('conversations', 'conversation_messages', 'metrics_hourly', 'metrics_daily') 
        THEN '🎯 CRÍTICA'
        ELSE '📊 adicional'
    END as importance
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('conversations', 'conversation_messages', 'metrics_hourly', 'metrics_daily', 'knowledge_base', 'admin_users')
ORDER BY importance DESC, table_name;
"

# Ejecutar migraciones
echo "📥 Aplicando migraciones..."

# 1. Tablas de métricas y conversaciones (CRÍTICO)
execute_sql "scripts/create_metrics_tables.sql" "tablas de conversaciones y métricas"

# 2. Tablas de administración (si existe)
if [ -f "scripts/create_admin_tables.sql" ]; then
    execute_sql "scripts/create_admin_tables.sql" "tablas de administración"
elif [ -f "scripts/create_admin_tables_simple.sql" ]; then
    execute_sql "scripts/create_admin_tables_simple.sql" "tablas de administración (simple)"
fi

# Verificar migración final
echo "✅ Verificando migración final..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CLIENT_CONTAINER" psql -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT 
    CASE 
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversations') 
        THEN '✅ conversations - LISTO'
        ELSE '❌ conversations - FALTA'
    END as conversations_status,
    CASE 
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversation_messages') 
        THEN '✅ conversation_messages - LISTO'
        ELSE '❌ conversation_messages - FALTA'
    END as messages_status,
    CASE 
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'knowledge_base') 
        THEN '✅ knowledge_base - LISTO'
        ELSE '⚠️  knowledge_base - Ya debería existir'
    END as knowledge_status;
"

# Verificar que las funciones críticas existen
echo "🔧 Verificando funciones de base de datos..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CLIENT_CONTAINER" psql -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT 
    routine_name,
    '✅ Disponible' as status
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN ('cleanup_old_metrics_data', 'aggregate_hourly_metrics', 'aggregate_daily_metrics')
ORDER BY routine_name;
"

echo ""
echo "🎉 ¡MIGRACIÓN COMPLETADA!"
echo "========================"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "1. Reiniciar servicios para aplicar cambios de código:"
echo "   ./scripts/docker-production.sh restart"
echo ""
echo "2. Verificar que el dashboard funciona:"
echo "   curl http://localhost:8080/api/admin/metrics/summary"
echo ""
echo "3. El sistema ahora registrará conversaciones correctamente"
echo ""
echo "📁 Backup guardado en: $backup_file"
echo "🎯 ¡Base de datos actualizada para el nuevo sistema de conversaciones!"
echo ""