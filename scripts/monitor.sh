#!/bin/bash

# Script de monitoreo y healthcheck para Eva AI Assistant
# Autor: vanguardia.dev
# Fecha: 2025-01-08

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
PROJECT_DIR="/opt/eva/MCP-WC"
DOMAIN="ia.elcorteelectrico.com"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
EMAIL_ALERT="${ALERT_EMAIL:-admin@elcorteelectrico.com}"

# Función para logging
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Función para enviar alertas
send_alert() {
    local level=$1
    local message=$2
    local details=$3
    
    # Log local
    echo "[ALERT-$level] $message - $details" >> /var/log/eva/alerts.log
    
    # Slack webhook si está configurado
    if [ ! -z "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 *Eva AI Alert [$level]*\n$message\n\`\`\`$details\`\`\`\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null
    fi
    
    # Email si mail está instalado
    if command -v mail &> /dev/null && [ ! -z "$EMAIL_ALERT" ]; then
        echo -e "Nivel: $level\nMensaje: $message\nDetalles:\n$details" | \
            mail -s "Eva AI Alert: $level - $message" "$EMAIL_ALERT"
    fi
}

# Función para verificar servicio
check_service() {
    local service_name=$1
    local url=$2
    local expected_code=${3:-200}
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" -m 5)
    
    if [ "$response" == "$expected_code" ]; then
        echo -e "${GREEN}✓${NC} $service_name: OK (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name: FALLO (HTTP $response)"
        return 1
    fi
}

# Función para verificar contenedor Docker
check_container() {
    local container_name=$1
    
    if docker ps --format "table {{.Names}}" | grep -q "^$container_name$"; then
        # Verificar si está healthy
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
        
        if [ "$health" == "healthy" ] || [ "$health" == "none" ]; then
            echo -e "${GREEN}✓${NC} Container $container_name: Running"
            return 0
        else
            echo -e "${YELLOW}⚠${NC} Container $container_name: Running but $health"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} Container $container_name: Not running"
        return 2
    fi
}

# Función para verificar uso de recursos
check_resources() {
    log "Verificando recursos del sistema..."
    
    # CPU
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "CPU Usage: ${cpu_usage}%"
    
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        warning "Alto uso de CPU: ${cpu_usage}%"
    fi
    
    # Memoria
    mem_usage=$(free | grep Mem | awk '{print ($2-$7)/$2 * 100.0}')
    echo "Memory Usage: ${mem_usage}%"
    
    if (( $(echo "$mem_usage > 80" | bc -l) )); then
        warning "Alto uso de memoria: ${mem_usage}%"
    fi
    
    # Disco
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "Disk Usage: ${disk_usage}%"
    
    if [ $disk_usage -gt 80 ]; then
        warning "Alto uso de disco: ${disk_usage}%"
    fi
    
    # Docker
    docker_disk=$(docker system df --format "table {{.Type}}\t{{.Size}}" | grep Images | awk '{print $2}')
    echo "Docker Images: $docker_disk"
}

# Función para verificar base de datos
check_database() {
    log "Verificando base de datos PostgreSQL..."
    
    # Intentar conectar y ejecutar query simple
    if docker exec eva-postgres-prod psql -U eva_user -d eva_db -c "SELECT 1;" &>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL: Conexión OK"
        
        # Verificar tamaño de la base de datos
        db_size=$(docker exec eva-postgres-prod psql -U eva_user -d eva_db -t -c "SELECT pg_size_pretty(pg_database_size('eva_db'));" | xargs)
        echo "  Tamaño DB: $db_size"
        
        # Contar registros importantes
        product_count=$(docker exec eva-postgres-prod psql -U eva_user -d eva_db -t -c "SELECT COUNT(*) FROM products;" 2>/dev/null | xargs || echo "0")
        echo "  Productos: $product_count"
        
        return 0
    else
        echo -e "${RED}✗${NC} PostgreSQL: Conexión FALLIDA"
        return 1
    fi
}

# Función para verificar logs de errores
check_error_logs() {
    log "Verificando logs de errores recientes..."
    
    # Verificar logs de los últimos 5 minutos
    since="5 minutes ago"
    
    # Logs de contenedores
    for container in eva-mcp-prod eva-web-prod eva-nginx-prod; do
        errors=$(docker logs --since "$since" "$container" 2>&1 | grep -iE "error|exception|critical" | wc -l)
        if [ $errors -gt 0 ]; then
            warning "$container tiene $errors errores en los últimos 5 minutos"
            
            # Mostrar últimos errores
            echo "Últimos errores de $container:"
            docker logs --since "$since" "$container" 2>&1 | grep -iE "error|exception|critical" | tail -3
        fi
    done
}

# Función principal de healthcheck
perform_healthcheck() {
    log "=== Iniciando Health Check de Eva AI ==="
    
    failed_checks=0
    
    # 1. Verificar contenedores
    log "Verificando contenedores Docker..."
    containers=("eva-postgres-prod" "eva-mcp-prod" "eva-web-prod" "eva-nginx-prod" "eva-redis-prod")
    
    for container in "${containers[@]}"; do
        if ! check_container "$container"; then
            ((failed_checks++))
            send_alert "ERROR" "Container $container no está funcionando correctamente" "El contenedor $container está caído o no es saludable"
        fi
    done
    
    # 2. Verificar endpoints HTTP
    log "Verificando endpoints HTTP..."
    
    if ! check_service "Web App (Local)" "http://localhost:8080/health"; then
        ((failed_checks++))
        send_alert "ERROR" "Web App no responde" "El endpoint de salud de la aplicación web no responde"
    fi
    
    if ! check_service "MCP Server (Local)" "http://localhost:8000/health"; then
        ((failed_checks++))
        send_alert "ERROR" "MCP Server no responde" "El servidor MCP no responde al health check"
    fi
    
    if ! check_service "Website (HTTPS)" "https://$DOMAIN/health"; then
        ((failed_checks++))
        send_alert "CRITICAL" "Sitio web no accesible" "El sitio web no es accesible desde internet"
    fi
    
    # 3. Verificar base de datos
    if ! check_database; then
        ((failed_checks++))
        send_alert "CRITICAL" "Base de datos no accesible" "No se puede conectar a PostgreSQL"
    fi
    
    # 4. Verificar recursos
    check_resources
    
    # 5. Verificar logs de errores
    check_error_logs
    
    # Resumen
    echo ""
    log "=== Resumen del Health Check ==="
    
    if [ $failed_checks -eq 0 ]; then
        echo -e "${GREEN}✓ Todos los servicios están funcionando correctamente${NC}"
        return 0
    else
        echo -e "${RED}✗ Se encontraron $failed_checks problemas${NC}"
        return 1
    fi
}

# Función para monitoreo continuo
continuous_monitor() {
    local interval=${1:-300}  # Default: 5 minutos
    
    log "Iniciando monitoreo continuo (intervalo: ${interval}s)"
    
    while true; do
        clear
        perform_healthcheck
        
        echo ""
        echo "Próxima verificación en $interval segundos..."
        echo "Presiona Ctrl+C para detener el monitoreo"
        
        sleep $interval
    done
}

# Función para mostrar métricas en tiempo real
show_metrics() {
    log "Mostrando métricas en tiempo real..."
    
    # Usar docker stats para mostrar métricas
    docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" \
        eva-postgres-prod eva-mcp-prod eva-web-prod eva-nginx-prod eva-redis-prod
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [comando] [opciones]"
    echo ""
    echo "Comandos:"
    echo "  check       - Ejecutar health check una vez"
    echo "  monitor     - Monitoreo continuo (default: cada 5 min)"
    echo "  metrics     - Mostrar métricas en tiempo real"
    echo "  help        - Mostrar esta ayuda"
    echo ""
    echo "Opciones:"
    echo "  -i, --interval <segundos>  - Intervalo para monitoreo continuo"
    echo ""
    echo "Ejemplos:"
    echo "  $0 check"
    echo "  $0 monitor --interval 60"
    echo "  $0 metrics"
}

# Procesar argumentos
case "$1" in
    check)
        perform_healthcheck
        ;;
    monitor)
        interval=300
        if [ "$2" == "-i" ] || [ "$2" == "--interval" ]; then
            interval=$3
        fi
        continuous_monitor $interval
        ;;
    metrics)
        show_metrics
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        perform_healthcheck
        ;;
esac