# Guía de Despliegue en Producción - Eva AI Assistant

## Requisitos Previos

### Servidor VPS
- **Sistema Operativo**: Ubuntu 20.04 LTS o superior
- **RAM**: Mínimo 4GB (recomendado 8GB)
- **CPU**: 2 cores mínimo (recomendado 4 cores)
- **Almacenamiento**: 50GB mínimo
- **Dominio**: ia.elcorteelectrico.com apuntando al servidor

### Software Requerido
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- Certbot (para SSL)

## Proceso de Despliegue

### 1. Preparación del Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Instalar Git y otras utilidades
sudo apt install -y git certbot ufw
```

### 2. Clonar el Repositorio

```bash
# Crear directorio del proyecto
sudo mkdir -p /opt/eva
cd /opt/eva

# Clonar repositorio
sudo git clone <URL_DEL_REPOSITORIO> MCP-WC
cd MCP-WC
```

### 3. Configurar Archivos de Entorno

```bash
# Copiar archivos de ejemplo
sudo cp env.production.example .env.production
sudo cp env.agent.example env.agent

# Editar con las credenciales reales
sudo nano .env.production
sudo nano env.agent
```

**Valores importantes a configurar en `.env.production`:**
- `POSTGRES_PASSWORD`: Contraseña segura para PostgreSQL
- `OPENAI_API_KEY`: Tu API key de OpenAI
- `WOOCOMMERCE_URL`: URL de tu tienda WooCommerce
- `WOOCOMMERCE_CONSUMER_KEY`: Consumer key de WooCommerce
- `WOOCOMMERCE_CONSUMER_SECRET`: Consumer secret de WooCommerce
- `JWT_SECRET_KEY`: Clave secreta para JWT
- `CORS_ORIGINS`: https://elcorteelectrico.com,https://ia.elcorteelectrico.com

### 4. Ejecutar Script de Despliegue

```bash
# Hacer ejecutable el script
sudo chmod +x scripts/deploy.sh

# Ejecutar despliegue automático
sudo ./scripts/deploy.sh
```

El script realizará automáticamente:
- Verificación de requisitos
- Configuración de directorios
- Generación de certificados SSL
- Construcción y despliegue de contenedores
- Configuración de firewall
- Configuración de backups automáticos

### 5. Verificación Post-Despliegue

```bash
# Verificar estado de contenedores
docker-compose -f docker-compose.production.yml ps

# Ver logs
docker-compose -f docker-compose.production.yml logs -f

# Ejecutar health check
./scripts/monitor.sh check

# Verificar acceso HTTPS
curl -I https://ia.elcorteelectrico.com/health
```

## Gestión del Servicio

### Comandos Básicos

```bash
# Iniciar servicios
./scripts/docker-production.sh start

# Detener servicios
./scripts/docker-production.sh stop

# Reiniciar servicios
./scripts/docker-production.sh restart

# Ver logs
./scripts/docker-production.sh logs

# Crear backup manual
./scripts/docker-production.sh backup

# Restaurar desde backup
./scripts/docker-production.sh restore <archivo_backup>
```

### Monitoreo

```bash
# Health check único
./scripts/monitor.sh check

# Monitoreo continuo (cada 5 minutos)
./scripts/monitor.sh monitor

# Métricas en tiempo real
./scripts/monitor.sh metrics
```

### Actualización del Código

```bash
cd /opt/eva/MCP-WC

# Obtener últimos cambios
sudo git pull origin main

# Reconstruir y reiniciar servicios
sudo docker-compose -f docker-compose.production.yml build
sudo docker-compose -f docker-compose.production.yml up -d
```

## Configuración Adicional

### Configurar Webhooks de WhatsApp

```bash
# Configurar webhook en 360Dialog
python scripts/configure_360dialog_webhook.py --url https://ia.elcorteelectrico.com/api/webhooks/whatsapp
```

### Configurar Plugin de WordPress

1. Descargar el plugin desde `/eva-chatbot-widget/`
2. Subir a WordPress vía panel de administración
3. Configurar URL del servidor: `https://ia.elcorteelectrico.com`

### Backups Automáticos

Los backups se ejecutan automáticamente a las 2 AM cada día. Para verificar:

```bash
# Ver cron jobs
sudo crontab -l

# Ver logs de backups
tail -f /var/log/eva/backup.log

# Listar backups disponibles
ls -la /opt/eva/backups/
```

## Seguridad

### Firewall (UFW)

```bash
# Verificar reglas
sudo ufw status

# Solo están abiertos los puertos:
# - 22 (SSH)
# - 80 (HTTP - redirige a HTTPS)
# - 443 (HTTPS)
# - 8090 (Nginx status - solo interno)
```

### Certificados SSL

Los certificados se renuevan automáticamente. Para verificar:

```bash
# Ver certificados
sudo certbot certificates

# Renovar manualmente
sudo certbot renew --dry-run
```

### Acceso a Base de Datos

PostgreSQL solo es accesible desde localhost:
- Host: 127.0.0.1
- Puerto: 5432
- Usuario: eva_user
- Base de datos: eva_db

## Troubleshooting

### Contenedor no inicia

```bash
# Ver logs detallados
docker-compose -f docker-compose.production.yml logs <nombre-contenedor>

# Reiniciar contenedor específico
docker-compose -f docker-compose.production.yml restart <nombre-contenedor>
```

### Errores de permisos

```bash
# Ajustar permisos
sudo chown -R $USER:$USER /opt/eva/MCP-WC
sudo chmod -R 755 /opt/eva/MCP-WC
```

### Base de datos corrupta

```bash
# Restaurar desde backup más reciente
./scripts/docker-production.sh restore $(ls -t /opt/eva/backups/*.gz | head -1)
```

### Alto uso de recursos

```bash
# Verificar recursos
./scripts/monitor.sh metrics

# Limpiar Docker
docker system prune -a --volumes
```

## Contacto y Soporte

- **Desarrollador**: vanguardia.dev
- **Email**: contacto@vanguardia.dev
- **Documentación**: https://github.com/tu-usuario/MCP-WC

## Checklist de Producción

- [ ] Servidor VPS configurado con Ubuntu 20.04+
- [ ] Docker y Docker Compose instalados
- [ ] Dominio apuntando al servidor
- [ ] Repositorio clonado en `/opt/eva/MCP-WC`
- [ ] Archivos `.env.production` y `env.agent` configurados
- [ ] Script `deploy.sh` ejecutado exitosamente
- [ ] Certificados SSL generados
- [ ] Todos los contenedores funcionando
- [ ] Health check pasando sin errores
- [ ] Webhooks de WhatsApp configurados
- [ ] Plugin de WordPress instalado y configurado
- [ ] Backups automáticos verificados
- [ ] Monitoreo configurado