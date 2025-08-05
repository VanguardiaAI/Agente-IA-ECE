#!/bin/sh
# Script de backup automático para PostgreSQL
# Se ejecuta diariamente a las 2:00 AM

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/chatbot_backup_$DATE.sql"
LOG_FILE="$BACKUP_DIR/backup_log_$(date +%Y%m).log"

# Función de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

log "Iniciando backup de base de datos"

# Realizar backup
if pg_dump -h postgres -U chatbot_user -d knowledge_base > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    log "Backup exitoso: $BACKUP_FILE"
    
    # Comprimir backup
    if gzip "$BACKUP_FILE"; then
        log "Backup comprimido: $BACKUP_FILE.gz"
        BACKUP_FILE="$BACKUP_FILE.gz"
    fi
    
    # Eliminar backups antiguos (mantener últimos 7 días)
    find "$BACKUP_DIR" -name "chatbot_backup_*.sql.gz" -mtime +7 -delete
    log "Backups antiguos eliminados"
    
    # Verificar integridad del backup
    BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    if [ "$BACKUP_SIZE" -gt 1000 ]; then
        log "Backup verificado correctamente (tamaño: $BACKUP_SIZE bytes)"
    else
        log "ERROR: Backup parece estar corrupto o vacío"
    fi
    
else
    log "ERROR: Falló el backup de la base de datos"
fi

log "Proceso de backup finalizado"

# Configurar cron para ejecutar diariamente a las 2:00 AM
echo "0 2 * * * /backup-script.sh" > /etc/crontabs/root 