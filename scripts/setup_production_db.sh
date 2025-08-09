#!/bin/bash

# Script para configurar la base de datos de producción
# Este script aplica todas las migraciones necesarias para el sistema de conversaciones

set -e  # Salir si hay errores

echo "🚀 Configurando base de datos de producción..."
echo "================================================"

# Verificar que estamos en el directorio correcto
if [ ! -f "scripts/create_metrics_tables.sql" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar variables de entorno
if [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_DB" ] || [ -z "$POSTGRES_USER" ]; then
    echo "⚠️  Cargando variables de entorno desde .env..."
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo "❌ Error: Archivo .env no encontrado"
        exit 1
    fi
fi

echo "📊 Configuración de base de datos:"
echo "   Host: $POSTGRES_HOST"
echo "   Database: $POSTGRES_DB"
echo "   User: $POSTGRES_USER"

# Función para ejecutar SQL
execute_sql() {
    local file=$1
    local description=$2
    
    echo "🔧 Ejecutando $description..."
    
    if [ -f "$file" ]; then
        PGPASSWORD=$POSTGRES_PASSWORD psql \
            -h $POSTGRES_HOST \
            -p $POSTGRES_PORT \
            -U $POSTGRES_USER \
            -d $POSTGRES_DB \
            -f "$file"
        echo "   ✅ $description completado"
    else
        echo "   ⚠️  Archivo no encontrado: $file"
    fi
}

# Verificar conexión
echo "🔗 Verificando conexión a base de datos..."
PGPASSWORD=$POSTGRES_PASSWORD psql \
    -h $POSTGRES_HOST \
    -p $POSTGRES_PORT \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -c "SELECT version();" > /dev/null

if [ $? -eq 0 ]; then
    echo "   ✅ Conexión exitosa"
else
    echo "   ❌ Error de conexión"
    exit 1
fi

# Crear backup de datos importantes
echo "💾 Creando backup de seguridad..."
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="backup_production_${timestamp}.sql"

PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
    -h $POSTGRES_HOST \
    -p $POSTGRES_PORT \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    --schema-only \
    > "$backup_file" 2>/dev/null || echo "   ⚠️  No se pudo crear backup (base de datos nueva?)"

echo "   📁 Backup guardado como: $backup_file"

# Ejecutar scripts de migración
echo "📥 Aplicando migraciones..."

# 1. Configuración básica de base de datos
execute_sql "scripts/init_database.sql" "inicialización de base de datos"

# 2. Tablas de métricas y conversaciones (CRÍTICO)
execute_sql "scripts/create_metrics_tables.sql" "tablas de conversaciones y métricas"

# 3. Tablas de administración
if [ -f "scripts/create_admin_tables.sql" ]; then
    execute_sql "scripts/create_admin_tables.sql" "tablas de administración"
elif [ -f "scripts/create_admin_tables_simple.sql" ]; then
    execute_sql "scripts/create_admin_tables_simple.sql" "tablas de administración (simple)"
fi

# Verificar que las tablas críticas existen
echo "✅ Verificando migración..."

PGPASSWORD=$POSTGRES_PASSWORD psql \
    -h $POSTGRES_HOST \
    -p $POSTGRES_PORT \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -c "
    SELECT 
        CASE 
            WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversations') 
            THEN '✅ conversations'
            ELSE '❌ conversations FALTA'
        END as conversations_status,
        CASE 
            WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversation_messages') 
            THEN '✅ conversation_messages'
            ELSE '❌ conversation_messages FALTA'
        END as messages_status,
        CASE 
            WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'knowledge_base') 
            THEN '✅ knowledge_base'
            ELSE '❌ knowledge_base FALTA'
        END as knowledge_status;
    "

echo ""
echo "🎉 ¡Migración completada!"
echo "========================="
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "1. Reiniciar servicios de producción:"
echo "   ./scripts/docker-production.sh restart"
echo ""
echo "2. Verificar que el dashboard funciona:"
echo "   curl http://localhost:8080/api/admin/metrics/summary"
echo ""
echo "3. Probar conversación de prueba para verificar tracking"
echo ""
echo "📁 Backup guardado en: $backup_file"
echo ""