# 🚀 Guía de Despliegue a Producción - Eva AI

Esta guía te ayudará a desplegar Eva AI en producción usando Docker con el dominio `ia.elcorteelectrico.com`.

## 📋 Prerequisitos

### Servidor
- Ubuntu 20.04+ o CentOS 8+
- Mínimo 4GB RAM (recomendado 8GB)
- 50GB+ de espacio en disco
- Docker y Docker Compose instalados
- Dominio configurado: `ia.elcorteelectrico.com`

### Credenciales Necesarias
- API Key de OpenAI
- Credenciales de WooCommerce (Consumer Key/Secret)
- API Key de WhatsApp Business (360Dialog)
- Certificados SSL para el dominio

## 🔧 Instalación Paso a Paso

### 1. Preparar el Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Crear usuario eva
sudo useradd -m -s /bin/bash eva
sudo usermod -aG docker eva

# Crear directorio de la aplicación
sudo mkdir -p /opt/eva-ai
sudo chown eva:eva /opt/eva-ai
```

### 2. Clonar y Configurar el Proyecto

```bash
# Cambiar al usuario eva
sudo su - eva

# Clonar repositorio (ajustar URL según tu repo)
cd /opt
git clone <tu-repo-url> eva-ai
cd eva-ai

# Crear directorios necesarios
mkdir -p backups logs nginx/ssl
```

### 3. Configurar Variables de Entorno

```bash
# Copiar template de producción
cp .env.production .env.production.local

# Editar configuración
nano .env.production.local
```

**Variables críticas a configurar:**

```env
# PostgreSQL
POSTGRES_PASSWORD=tu_password_seguro_aqui

# OpenAI
OPENAI_API_KEY=tu_openai_api_key

# WooCommerce
WOOCOMMERCE_CONSUMER_KEY=tu_consumer_key
WOOCOMMERCE_CONSUMER_SECRET=tu_consumer_secret

# WhatsApp 360Dialog
WHATSAPP_360DIALOG_API_KEY=tu_360dialog_api_key
WHATSAPP_PHONE_NUMBER=34123456789
WHATSAPP_WEBHOOK_VERIFY_TOKEN=token_seguro_unico

# Seguridad
SECRET_KEY=clave_muy_larga_y_segura_aqui
JWT_SECRET_KEY=otra_clave_muy_larga_aqui
ADMIN_PASSWORD=password_admin_seguro
```

### 4. Configurar Certificados SSL

```bash
# Opción A: Let's Encrypt con Certbot
sudo apt install certbot
sudo certbot certonly --standalone -d ia.elcorteelectrico.com

# Copiar certificados
sudo cp /etc/letsencrypt/live/ia.elcorteelectrico.com/fullchain.pem nginx/ssl/ia.elcorteelectrico.com.crt
sudo cp /etc/letsencrypt/live/ia.elcorteelectrico.com/privkey.pem nginx/ssl/ia.elcorteelectrico.com.key
sudo chown eva:eva nginx/ssl/*

# Opción B: Certificados propios
# Copia tus certificados a nginx/ssl/
```

### 5. Construir e Iniciar Servicios

```bash
# Hacer ejecutables los scripts
chmod +x scripts/*.sh

# Construir imágenes
docker-compose -f docker-compose.production.yml build

# Iniciar servicios
./scripts/docker-production.sh start
```

### 6. Verificar Despliegue

```bash
# Verificar estado de contenedores
docker-compose -f docker-compose.production.yml ps

# Verificar logs
docker-compose -f docker-compose.production.yml logs -f

# Probar endpoints
curl https://ia.elcorteelectrico.com/health
curl https://ia.elcorteelectrico.com/api/stats
```

### 7. Configurar WhatsApp para Producción

```bash
# Ejecutar script de configuración
python3 scripts/configure_production_whatsapp.py

# O manualmente:
# 1. Seleccionar opción 1 para configurar webhook
# 2. Verificar que apunte a ia.elcorteelectrico.com
```

### 8. Configurar Servicios del Sistema

```bash
# Instalar servicios systemd
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar servicios
sudo systemctl enable eva-ai.service
sudo systemctl enable eva-backup.timer

# Iniciar timer de backup
sudo systemctl start eva-backup.timer
```

### 9. Configurar Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable

# O iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## 🔍 Verificación Post-Despliegue

### Checklist de Verificación

- [ ] **Servicios activos**: `docker-compose ps` muestra todos los servicios "Up"
- [ ] **Base de datos**: Conexión PostgreSQL funcionando
- [ ] **API Health**: `https://ia.elcorteelectrico.com/health` responde OK
- [ ] **Dashboard**: `https://ia.elcorteelectrico.com/` carga correctamente
- [ ] **WhatsApp**: Webhook configurado y verificado
- [ ] **WooCommerce**: Sincronización de productos funciona
- [ ] **SSL**: Certificados válidos y HTTPS forzado
- [ ] **Backups**: Timer de backup activado

### Comandos de Verificación

```bash
# Verificar servicios
./scripts/docker-production.sh status

# Probar sincronización WooCommerce
curl -X POST https://ia.elcorteelectrico.com/api/sync/products

# Verificar backup automático
sudo systemctl status eva-backup.timer
```

## 📊 Monitoreo y Mantenimiento

### Logs Importantes

```bash
# Logs de aplicación
docker-compose -f docker-compose.production.yml logs web-app

# Logs de Nginx
docker-compose -f docker-compose.production.yml logs nginx

# Logs del sistema
sudo journalctl -u eva-ai.service -f
```

### Comandos de Mantenimiento

```bash
# Crear backup manual
./scripts/docker-production.sh backup

# Reiniciar servicios
./scripts/docker-production.sh restart

# Actualizar aplicación
./scripts/docker-production.sh update

# Ver estadísticas de recursos
docker stats
```

### Monitoreo de Rendimiento

```bash
# Estadísticas de Nginx
curl http://localhost:8090/nginx-status

# Estadísticas de la aplicación
curl https://ia.elcorteelectrico.com/api/stats

# Uso de base de datos
docker-compose -f docker-compose.production.yml exec postgres psql -U eva_user -d eva_db -c "SELECT count(*) FROM products;"
```

## 🚨 Solución de Problemas

### Problemas Comunes

#### Servicios no inician
```bash
# Verificar logs
docker-compose -f docker-compose.production.yml logs

# Verificar configuración
docker-compose -f docker-compose.production.yml config
```

#### Error de SSL
```bash
# Verificar certificados
openssl x509 -in nginx/ssl/ia.elcorteelectrico.com.crt -text -noout

# Renovar Let's Encrypt
sudo certbot renew
```

#### WhatsApp no funciona
```bash
# Verificar configuración
python3 scripts/configure_production_whatsapp.py

# Verificar webhook
curl -X GET "https://ia.elcorteelectrico.com/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=tu_token&hub.challenge=test"
```

#### Base de datos lenta
```bash
# Verificar conexiones
docker-compose -f docker-compose.production.yml exec postgres psql -U eva_user -d eva_db -c "SELECT count(*) FROM pg_stat_activity;"

# Reiniciar PostgreSQL
docker-compose -f docker-compose.production.yml restart postgres
```

## 🔄 Actualizaciones

### Proceso de Actualización

```bash
# 1. Crear backup
./scripts/docker-production.sh backup

# 2. Obtener últimos cambios
git pull origin main

# 3. Actualizar servicios
./scripts/docker-production.sh update

# 4. Verificar funcionamiento
./scripts/docker-production.sh status
```

### Rollback de Emergencia

```bash
# 1. Detener servicios
./scripts/docker-production.sh stop

# 2. Volver a versión anterior
git checkout <commit-anterior>

# 3. Reconstruir e iniciar
docker-compose -f docker-compose.production.yml build
./scripts/docker-production.sh start

# 4. Restaurar backup si es necesario
./scripts/docker-production.sh restore backups/backup_YYYYMMDD_HHMMSS.sql.gz
```

## 📞 Soporte

Para problemas técnicos:
1. Revisa los logs: `docker-compose logs`
2. Verifica la configuración: `.env.production`
3. Consulta la documentación en `CLAUDE.md`
4. Contacta al equipo de desarrollo

## 🎉 ¡Listo!

Tu instalación de Eva AI está lista para producción en `https://ia.elcorteelectrico.com`. El sistema incluye:

- ✅ API REST completa
- ✅ Chat en tiempo real via WebSocket
- ✅ Integración WhatsApp Business
- ✅ Sincronización WooCommerce
- ✅ Panel de administración
- ✅ Backups automáticos
- ✅ Monitoreo y métricas
- ✅ SSL/HTTPS configurado