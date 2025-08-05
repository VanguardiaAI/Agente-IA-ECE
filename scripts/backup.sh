#!/bin/bash

# Script de backup automático para Eva AI
# Ejecutado diariamente por cron o Docker

set -e

# Configuración
BACKUP_DIR="/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/backup.log"

# Configuración de base de datos
DB_HOST=${POSTGRES_HOST:-postgres}
DB_NAME=${POSTGRES_DB:-eva_db}
DB_USER=${POSTGRES_USER:-eva_user}
DB_PASSWORD=${POSTGRES_PASSWORD}

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE"
}

success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" | tee -a "$LOG_FILE"
}

# Crear directorio de backup si no existe
mkdir -p "$BACKUP_DIR"

# Iniciar backup
log "Iniciando backup automático..."

# 1. Backup de la base de datos PostgreSQL
log "Creando backup de PostgreSQL..."
POSTGRES_BACKUP_FILE="$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"

export PGPASSWORD="$DB_PASSWORD"

if pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" --verbose --no-owner --no-privileges > "$POSTGRES_BACKUP_FILE"; then
    success "Backup de PostgreSQL creado: $POSTGRES_BACKUP_FILE"
    
    # Comprimir backup
    if gzip "$POSTGRES_BACKUP_FILE"; then
        success "Backup comprimido: ${POSTGRES_BACKUP_FILE}.gz"
        POSTGRES_BACKUP_FILE="${POSTGRES_BACKUP_FILE}.gz"
    else
        error "Error comprimiendo backup de PostgreSQL"
    fi
else
    error "Error creando backup de PostgreSQL"
    exit 1
fi

# 2. Backup de logs (últimos 7 días)
log "Creando backup de logs..."
LOGS_BACKUP_FILE="$BACKUP_DIR/logs_backup_$TIMESTAMP.tar.gz"

if find /app/logs -name "*.log" -mtime -7 -type f | tar -czf "$LOGS_BACKUP_FILE" -T -; then
    success "Backup de logs creado: $LOGS_BACKUP_FILE"
else
    log "No se encontraron logs recientes o error en backup de logs"
fi

# 3. Backup de configuraciones importantes
log "Creando backup de configuraciones..."
CONFIG_BACKUP_FILE="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"

# Crear archivo temporal con configuraciones
TEMP_CONFIG_DIR="/tmp/eva_config_$TIMESTAMP"
mkdir -p "$TEMP_CONFIG_DIR"

# Copiar archivos de configuración (sin credenciales)
if [ -f "/app/.env.production" ]; then
    # Crear una versión sanitizada del archivo .env
    grep -v -E "(PASSWORD|SECRET|KEY|TOKEN)" /app/.env.production > "$TEMP_CONFIG_DIR/env.template" || true
fi

# Copiar configuraciones de nginx si existen
if [ -d "/app/nginx" ]; then
    cp -r /app/nginx "$TEMP_CONFIG_DIR/" || true
fi

# Crear backup de configuraciones
if tar -czf "$CONFIG_BACKUP_FILE" -C /tmp "eva_config_$TIMESTAMP"; then
    success "Backup de configuraciones creado: $CONFIG_BACKUP_FILE"
    rm -rf "$TEMP_CONFIG_DIR"
else
    error "Error creando backup de configuraciones"
    rm -rf "$TEMP_CONFIG_DIR"
fi

# 4. Crear manifest del backup
log "Creando manifest del backup..."
MANIFEST_FILE="$BACKUP_DIR/backup_manifest_$TIMESTAMP.json"

cat > "$MANIFEST_FILE" << EOF
{
    "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "timestamp": "$TIMESTAMP",
    "version": "eva-ai-v1.0",
    "files": {
        "postgres": "$(basename "$POSTGRES_BACKUP_FILE")",
        "logs": "$(basename "$LOGS_BACKUP_FILE")",
        "config": "$(basename "$CONFIG_BACKUP_FILE")"
    },
    "database": {
        "name": "$DB_NAME",
        "host": "$DB_HOST",
        "user": "$DB_USER"
    },
    "sizes": {
        "postgres": "$(du -h "$POSTGRES_BACKUP_FILE" | cut -f1)",
        "logs": "$(du -h "$LOGS_BACKUP_FILE" 2>/dev/null | cut -f1 || echo 'N/A')",
        "config": "$(du -h "$CONFIG_BACKUP_FILE" 2>/dev/null | cut -f1 || echo 'N/A')"
    }
}
EOF

success "Manifest creado: $MANIFEST_FILE"

# 5. Limpiar backups antiguos
log "Limpiando backups antiguos (>$RETENTION_DAYS días)..."

DELETED_COUNT=0
for file in "$BACKUP_DIR"/*; do
    if [ -f "$file" ] && [ "$(find "$file" -mtime +$RETENTION_DAYS -print)" ]; then
        rm "$file"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done

if [ $DELETED_COUNT -gt 0 ]; then
    success "Eliminados $DELETED_COUNT archivos de backup antiguos"
else
    log "No se encontraron backups antiguos para eliminar"
fi

# 6. Estadísticas finales
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "*.gz" -o -name "*.json" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log "Backup completado exitosamente"
log "Total de archivos de backup: $TOTAL_BACKUPS"
log "Espacio total utilizado: $TOTAL_SIZE"

# 7. Opcional: Enviar notificación (si está configurado)
if [ -n "$BACKUP_NOTIFICATION_URL" ]; then
    log "Enviando notificación de backup..."
    
    NOTIFICATION_PAYLOAD=$(cat << EOF
{
    "text": "✅ Backup Eva AI completado",
    "details": {
        "timestamp": "$TIMESTAMP",
        "files": "$TOTAL_BACKUPS",
        "size": "$TOTAL_SIZE",
        "status": "success"
    }
}
EOF
)
    
    if curl -X POST -H "Content-Type: application/json" -d "$NOTIFICATION_PAYLOAD" "$BACKUP_NOTIFICATION_URL" &>/dev/null; then
        success "Notificación enviada"
    else
        log "Error enviando notificación (no crítico)"
    fi
fi

log "Proceso de backup terminado"
exit 0