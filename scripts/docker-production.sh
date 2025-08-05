#!/bin/bash

# Script de gestión de Docker para producción
# Eva AI - Customer Service Assistant
# URL de producción: ia.elcorteelectrico.com

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_NAME="eva-ai"
PRODUCTION_URL="ia.elcorteelectrico.com"
BACKUP_DIR="./backups"
DOCKER_COMPOSE_FILE="docker-compose.production.yml"

# Función para imprimir mensajes con color
print_message() {
    echo -e "${2}${1}${NC}"
}

# Función de logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Función para verificar prerequisitos
check_prerequisites() {
    print_message "🔍 Verificando prerequisitos..." "$BLUE"
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        print_message "❌ Docker no está instalado" "$RED"
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_message "❌ Docker Compose no está instalado" "$RED"
        exit 1
    fi
    
    # Verificar archivo de configuración de producción
    if [ ! -f ".env.production" ]; then
        print_message "⚠️  Archivo .env.production no encontrado. Creando desde template..." "$YELLOW"
        if [ -f "env.production.example" ]; then
            cp env.production.example .env.production
        fi
        print_message "📝 Por favor, edita .env.production con las credenciales de producción" "$YELLOW"
        exit 1
    fi
    
    # Crear directorio de backups si no existe
    mkdir -p "$BACKUP_DIR"
    
    print_message "✅ Prerequisitos verificados" "$GREEN"
}

# Función para crear archivo .env si no existe
setup_env() {
    if [ ! -f .env ]; then
        if [ -f env.production.example ]; then
            log "Creando archivo .env desde env.production.example"
            cp env.production.example .env
            warning "IMPORTANTE: Edita el archivo .env con tus credenciales reales"
            warning "Especialmente: POSTGRES_PASSWORD, OPENAI_API_KEY, WOOCOMMERCE_*"
        else
            error "No se encontró env.production.example"
            exit 1
        fi
    else
        log "Archivo .env ya existe"
    fi
}

# Función para iniciar servicios
start() {
    log "Iniciando servicios en modo producción..."
    
    # Verificar que el archivo .env existe
    setup_env
    
    # Crear directorios necesarios
    mkdir -p docker/postgres/data
    mkdir -p docker/postgres/backups
    
    # Dar permisos al script de backup
    chmod +x docker/postgres/backup-script.sh
    
    # Iniciar servicios
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Esperar a que PostgreSQL esté listo
    log "Esperando a que PostgreSQL esté listo..."
    sleep 10
    
    # Verificar estado de servicios
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        success "Servicios iniciados correctamente"
        log "PostgreSQL disponible en: localhost:5432"
        log "Base de datos: ${POSTGRES_DB:-eva_db}"
        log "Usuario: ${POSTGRES_USER:-eva_user}"
    else
        error "Error al iniciar servicios"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs
        exit 1
    fi
}

# Función para detener servicios
stop() {
    log "Deteniendo servicios..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    success "Servicios detenidos"
}

# Función para reiniciar servicios
restart() {
    log "Reiniciando servicios..."
    stop
    start
}

# Función para ver logs
logs() {
    if [ -z "$2" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
    else
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f "$2"
    fi
}

# Función para hacer backup manual
backup() {
    log "Realizando backup manual..."
    
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps postgres | grep -q "Up"; then
        error "PostgreSQL no está corriendo"
        exit 1
    fi
    
    BACKUP_FILE="docker/postgres/backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec postgres pg_dump -U ${POSTGRES_USER:-eva_user} ${POSTGRES_DB:-eva_db} > "$BACKUP_FILE"; then
        success "Backup creado: $BACKUP_FILE"
        
        # Comprimir backup
        gzip "$BACKUP_FILE"
        success "Backup comprimido: $BACKUP_FILE.gz"
    else
        error "Error creando backup"
        exit 1
    fi
}

# Función para restaurar backup
restore() {
    if [ -z "$2" ]; then
        error "Uso: $0 restore <archivo_backup>"
        exit 1
    fi
    
    BACKUP_FILE="$2"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        error "Archivo de backup no encontrado: $BACKUP_FILE"
        exit 1
    fi
    
    warning "¿Estás seguro de restaurar la base de datos? Esto eliminará todos los datos actuales."
    read -p "Escribe 'SI' para continuar: " confirm
    
    if [ "$confirm" != "SI" ]; then
        log "Operación cancelada"
        exit 0
    fi
    
    log "Restaurando backup: $BACKUP_FILE"
    
    # Si el archivo está comprimido, descomprimirlo temporalmente
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        TEMP_FILE="${BACKUP_FILE%.gz}"
        gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
        BACKUP_FILE="$TEMP_FILE"
        CLEANUP_TEMP=true
    fi
    
    # Restaurar backup
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres psql -U ${POSTGRES_USER:-eva_user} -d ${POSTGRES_DB:-eva_db} < "$BACKUP_FILE"; then
        success "Backup restaurado correctamente"
    else
        error "Error restaurando backup"
        exit 1
    fi
    
    # Limpiar archivo temporal si se creó
    if [ "$CLEANUP_TEMP" = true ]; then
        rm "$TEMP_FILE"
    fi
}

# Función para ver estado de servicios
status() {
    log "Estado de servicios:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    log "Uso de recursos:"
    docker stats --no-stream
}

# Función para actualizar servicios
update() {
    log "Actualizando servicios..."
    
    # Hacer backup antes de actualizar
    backup
    
    # Detener servicios
    stop
    
    # Actualizar imágenes
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull
    
    # Iniciar servicios
    start
    
    success "Servicios actualizados"
}

# Función para mostrar ayuda
help() {
    echo "Script de gestión Docker para Chatbot en Producción"
    echo ""
    echo "Uso: $0 <comando>"
    echo ""
    echo "Comandos disponibles:"
    echo "  start     - Iniciar servicios"
    echo "  stop      - Detener servicios"
    echo "  restart   - Reiniciar servicios"
    echo "  status    - Ver estado de servicios"
    echo "  logs      - Ver logs (opcional: logs <servicio>)"
    echo "  backup    - Crear backup manual"
    echo "  restore   - Restaurar backup (restore <archivo>)"
    echo "  update    - Actualizar servicios"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 start"
    echo "  $0 logs postgres"
    echo "  $0 restore docker/postgres/backups/backup_20250101.sql.gz"
}

# Función principal
main() {
    case "$1" in
        start)
            check_prerequisites
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        status)
            status
            ;;
        logs)
            logs
            ;;
        build)
            check_prerequisites
            build
            ;;
        backup)
            backup
            ;;
        restore)
            restore "$2"
            ;;
        update)
            check_prerequisites
            update
            ;;
        exec)
            shift
            exec_cmd $@
            ;;
        cleanup)
            cleanup
            ;;
        install-service)
            install_service
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_message "❌ Comando no reconocido: $1" "$RED"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Ejecutar función principal con todos los argumentos
main "$@" 