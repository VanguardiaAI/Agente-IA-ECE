# Eva AI - Production Access Guide

## 🌐 URLs de Acceso

### Cliente Final
- **Chat Widget**: https://elcorteelectrico.com (integrado en WordPress)
- **Interfaz Web Directa**: https://ia.elcorteelectrico.com/chat

### Administración
- **Dashboard**: https://ia.elcorteelectrico.com/
- **Panel Admin**: https://ia.elcorteelectrico.com/admin/login
  - Usuario: admin@elcorteelectrico.com
  - Contraseña: EvaAdmin2025!ElCorte

### APIs y Webhooks
- **API Principal**: https://ia.elcorteelectrico.com/api/
- **WhatsApp Webhook**: https://ia.elcorteelectrico.com/api/webhooks/whatsapp
- **Health Check**: https://ia.elcorteelectrico.com/health

## 🛠️ Comandos Útiles

### Ver estado de servicios
```bash
cd /opt/eva/Agente-IA-ECE
docker-compose -f docker-compose.production.yml ps
```

### Ver logs en tiempo real
```bash
# Todos los servicios
docker-compose -f docker-compose.production.yml logs -f

# Solo web app
docker logs -f eva-web-prod

# Solo errores
docker logs eva-web-prod 2>&1 | grep ERROR
```

### Reiniciar servicios
```bash
docker-compose -f docker-compose.production.yml restart
```

### Sincronizar productos manualmente
```bash
curl -X POST https://ia.elcorteelectrico.com/api/sync/products \
  -H "Content-Type: application/json" \
  -d '{"force_update": false}'
```

### Backup manual
```bash
cd /opt/eva/Agente-IA-ECE
./scripts/backup.sh
```

## 🔍 Solución de Problemas

### Si el sitio no carga (502 Bad Gateway)
1. Esperar 30-60 segundos para que los servicios inicien
2. Verificar servicios: `./scripts/check_services_status.sh`
3. Reiniciar si es necesario: `docker-compose -f docker-compose.production.yml restart`

### Si hay errores de base de datos
1. Verificar conexión: `docker exec eva-postgres-prod pg_isready`
2. Ver logs: `docker logs eva-postgres-prod --tail 50`

### Si el chat no responde
1. Verificar MCP server: `docker logs eva-mcp-prod --tail 50`
2. Verificar API key de OpenAI en `.env`

## 📊 Monitoreo

### Métricas del sistema
- **Uso de CPU/Memoria**: `docker stats`
- **Espacio en disco**: `df -h`
- **Conexiones activas**: Ver en dashboard

### Logs importantes
- `/opt/eva/Agente-IA-ECE/logs/` - Logs de aplicación
- `/var/log/nginx/` - Logs de nginx
- `journalctl -u eva-*` - Logs del sistema

## 🔐 Seguridad

### Certificados SSL
- Renovación automática con Let's Encrypt
- Verificar: `certbot certificates`

### Firewall
- Puerto 80 (HTTP) - Redirige a HTTPS
- Puerto 443 (HTTPS) - Interfaz principal
- Puerto 8080 - Solo localhost (aplicación)
- Puerto 8000 - Solo localhost (MCP)
- Puerto 5432 - Solo localhost (PostgreSQL)

## 🚀 Actualizaciones

```bash
cd /opt/eva/Agente-IA-ECE
git pull
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

## 📞 Soporte

Para problemas técnicos relacionados con Eva AI:
- Repositorio: https://github.com/VanguardiaAI/Agente-IA-ECE
- Documentación: `/opt/eva/Agente-IA-ECE/docs/`