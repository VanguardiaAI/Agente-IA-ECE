#!/bin/bash

# Script de despliegue automatizado para Eva AI Assistant
# Autor: vanguardia.dev
# Fecha: 2025-01-08

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables de configuración
PROJECT_NAME="eva-ai"
DOMAIN="ia.elcorteelectrico.com"
PROJECT_DIR="/opt/eva/ECE-AI-Agent"
BACKUP_DIR="/opt/eva/backups"
SSL_DIR="/opt/eva/ssl"
LOG_FILE="/var/log/eva-deploy.log"

# Función para imprimir mensajes
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[ADVERTENCIA]${NC} $1" | tee -a "$LOG_FILE"
}

# Verificar si se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   error "Este script debe ejecutarse como root"
fi

# Función para verificar requisitos
check_requirements() {
    log "Verificando requisitos del sistema..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado. Por favor instale Docker primero."
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose no está instalado. Por favor instale Docker Compose primero."
    fi
    
    # Verificar Git
    if ! command -v git &> /dev/null; then
        error "Git no está instalado. Por favor instale Git primero."
    fi
    
    # Verificar Certbot para SSL
    if ! command -v certbot &> /dev/null; then
        warning "Certbot no está instalado. Se instalará ahora..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    log "✓ Todos los requisitos están instalados"
}

# Función para configurar directorios
setup_directories() {
    log "Configurando directorios del proyecto..."
    
    # Crear directorios necesarios
    mkdir -p "$PROJECT_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$SSL_DIR"
    mkdir -p "/var/log/eva"
    
    # Configurar permisos
    chmod 755 "$PROJECT_DIR"
    chmod 755 "$BACKUP_DIR"
    chmod 755 "$SSL_DIR"
    
    log "✓ Directorios configurados"
}

# Función para clonar o actualizar el repositorio
setup_repository() {
    log "Configurando repositorio..."
    
    if [ -d "$PROJECT_DIR/.git" ]; then
        log "Actualizando repositorio existente..."
        cd "$PROJECT_DIR"
        git fetch --all
        git reset --hard origin/main
        git clean -fd
    else
        log "Clonando repositorio..."
        # Solicitar URL del repositorio si no existe
        read -p "Ingrese la URL del repositorio Git: " REPO_URL
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    
    log "✓ Repositorio configurado"
}

# Función para configurar archivos de entorno
setup_environment() {
    log "Configurando archivos de entorno..."
    
    # Verificar si existe .env.production
    if [ ! -f "$PROJECT_DIR/.env.production" ]; then
        if [ -f "$PROJECT_DIR/env.production.example" ]; then
            cp "$PROJECT_DIR/env.production.example" "$PROJECT_DIR/.env.production"
            warning "Se ha creado .env.production desde el ejemplo. Por favor edítelo con sus valores reales."
            
            # Abrir editor para configurar
            read -p "¿Desea editar .env.production ahora? (s/n): " EDIT_ENV
            if [[ $EDIT_ENV =~ ^[Ss]$ ]]; then
                nano "$PROJECT_DIR/.env.production"
            else
                error "Debe configurar .env.production antes de continuar."
            fi
        else
            error "No se encontró env.production.example"
        fi
    fi
    
    # Verificar si existe env.agent
    if [ ! -f "$PROJECT_DIR/env.agent" ]; then
        if [ -f "$PROJECT_DIR/env.agent.example" ]; then
            cp "$PROJECT_DIR/env.agent.example" "$PROJECT_DIR/env.agent"
            warning "Se ha creado env.agent desde el ejemplo. Por favor edítelo con sus API keys."
            
            # Abrir editor para configurar
            read -p "¿Desea editar env.agent ahora? (s/n): " EDIT_AGENT
            if [[ $EDIT_AGENT =~ ^[Ss]$ ]]; then
                nano "$PROJECT_DIR/env.agent"
            else
                error "Debe configurar env.agent antes de continuar."
            fi
        else
            error "No se encontró env.agent.example"
        fi
    fi
    
    log "✓ Archivos de entorno configurados"
}

# Función para configurar SSL
setup_ssl() {
    log "Configurando certificados SSL..."
    
    # Verificar si ya existen certificados
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        log "Ya existen certificados SSL para $DOMAIN"
        
        # Crear enlaces simbólicos
        ln -sf "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/$DOMAIN.crt"
        ln -sf "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/$DOMAIN.key"
    else
        log "Generando certificados SSL con Let's Encrypt..."
        
        # Detener nginx temporalmente si está corriendo
        docker-compose -f "$PROJECT_DIR/docker-compose.production.yml" stop nginx 2>/dev/null || true
        
        # Generar certificados
        certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email admin@elcorteelectrico.com
        
        if [ $? -eq 0 ]; then
            # Crear enlaces simbólicos
            ln -sf "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/$DOMAIN.crt"
            ln -sf "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/$DOMAIN.key"
            log "✓ Certificados SSL generados exitosamente"
        else
            error "Error al generar certificados SSL"
        fi
    fi
    
    # Configurar renovación automática
    if ! crontab -l | grep -q "certbot renew"; then
        (crontab -l 2>/dev/null; echo "0 0,12 * * * certbot renew --quiet --post-hook 'docker-compose -f $PROJECT_DIR/docker-compose.production.yml restart nginx'") | crontab -
        log "✓ Configurada renovación automática de SSL"
    fi
}

# Función para construir y levantar contenedores
deploy_containers() {
    log "Desplegando contenedores Docker..."
    
    cd "$PROJECT_DIR"
    
    # Crear red Docker si no existe
    docker network create eva_network 2>/dev/null || true
    
    # Construir imágenes
    log "Construyendo imágenes Docker..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    # Detener contenedores existentes
    log "Deteniendo contenedores existentes..."
    docker-compose -f docker-compose.production.yml down
    
    # Levantar contenedores
    log "Levantando contenedores..."
    docker-compose -f docker-compose.production.yml up -d
    
    # Esperar a que los servicios estén listos
    log "Esperando a que los servicios estén listos..."
    sleep 10
    
    # Verificar estado
    docker-compose -f docker-compose.production.yml ps
    
    log "✓ Contenedores desplegados exitosamente"
}

# Función para configurar firewall
setup_firewall() {
    log "Configurando firewall..."
    
    # Instalar ufw si no está instalado
    if ! command -v ufw &> /dev/null; then
        apt-get update
        apt-get install -y ufw
    fi
    
    # Configurar reglas
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8090/tcp  # Nginx status
    
    # Habilitar firewall
    ufw --force enable
    
    log "✓ Firewall configurado"
}

# Función para configurar backups automáticos
setup_backups() {
    log "Configurando backups automáticos..."
    
    # Crear script de backup si no existe
    if [ ! -f "$PROJECT_DIR/scripts/backup.sh" ]; then
        warning "Script de backup no encontrado. Se usará el backup integrado en Docker Compose."
    fi
    
    # Configurar cron para backups diarios
    if ! crontab -l | grep -q "docker-production.sh backup"; then
        (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/scripts/docker-production.sh backup >> /var/log/eva/backup.log 2>&1") | crontab -
        log "✓ Configurados backups automáticos diarios a las 2 AM"
    fi
}

# Función para verificar servicios
verify_deployment() {
    log "Verificando despliegue..."
    
    # Verificar contenedores
    CONTAINERS_UP=$(docker-compose -f "$PROJECT_DIR/docker-compose.production.yml" ps | grep "Up" | wc -l)
    CONTAINERS_EXPECTED=6  # postgres, mcp-server, web-app, nginx, redis, backup
    
    if [ $CONTAINERS_UP -lt $CONTAINERS_EXPECTED ]; then
        warning "Solo $CONTAINERS_UP de $CONTAINERS_EXPECTED contenedores están activos"
    else
        log "✓ Todos los contenedores están activos"
    fi
    
    # Verificar endpoints
    log "Verificando endpoints..."
    
    # Health check interno
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
        log "✓ Web app respondiendo correctamente"
    else
        warning "Web app no responde al health check"
    fi
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
        log "✓ MCP server respondiendo correctamente"
    else
        warning "MCP server no responde al health check"
    fi
    
    # Verificar HTTPS
    if curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health -k | grep -q "200"; then
        log "✓ HTTPS funcionando correctamente"
    else
        warning "HTTPS no responde correctamente"
    fi
}

# Función para mostrar información post-despliegue
show_deployment_info() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}     DESPLIEGUE COMPLETADO CON ÉXITO    ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Información del despliegue:${NC}"
    echo -e "• Dominio: https://$DOMAIN"
    echo -e "• Panel admin: https://$DOMAIN/admin"
    echo -e "• Logs: docker-compose -f $PROJECT_DIR/docker-compose.production.yml logs -f"
    echo -e "• Estado: docker-compose -f $PROJECT_DIR/docker-compose.production.yml ps"
    echo ""
    echo -e "${YELLOW}Próximos pasos:${NC}"
    echo -e "1. Verificar que el sitio esté accesible en https://$DOMAIN"
    echo -e "2. Configurar el webhook de WhatsApp si es necesario"
    echo -e "3. Probar el chat widget en el sitio web"
    echo -e "4. Revisar los logs para asegurarse de que todo funcione correctamente"
    echo ""
    echo -e "${GREEN}Para administrar el servicio:${NC}"
    echo -e "• Iniciar: $PROJECT_DIR/scripts/docker-production.sh start"
    echo -e "• Detener: $PROJECT_DIR/scripts/docker-production.sh stop"
    echo -e "• Reiniciar: $PROJECT_DIR/scripts/docker-production.sh restart"
    echo -e "• Backup: $PROJECT_DIR/scripts/docker-production.sh backup"
    echo ""
}

# Función principal
main() {
    log "Iniciando despliegue de Eva AI Assistant..."
    
    check_requirements
    setup_directories
    setup_repository
    setup_environment
    setup_ssl
    deploy_containers
    setup_firewall
    setup_backups
    verify_deployment
    show_deployment_info
    
    log "Despliegue completado exitosamente"
}

# Ejecutar función principal
main "$@"