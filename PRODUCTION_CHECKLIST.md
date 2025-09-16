# Lista de Verificación para Producción - Eva MCP-WC

## 🔒 Seguridad

- [ ] Verificar que `.env` NO esté en el repositorio
- [ ] Verificar que `env.agent` NO esté en el repositorio  
- [ ] Verificar que `/docker/postgres/data/` NO esté en el repositorio
- [ ] Cambiar todas las contraseñas predeterminadas en producción
- [ ] Configurar HTTPS/SSL para todos los endpoints
- [ ] Habilitar CORS solo para dominios autorizados
- [ ] Configurar rate limiting en la API

## 🧹 Limpieza

- [ ] Ejecutar `./scripts/clean_for_production.sh` para eliminar archivos de desarrollo
- [ ] Eliminar todos los archivos `.log`
- [ ] Eliminar scripts de test (`test_*.py`)
- [ ] Eliminar archivos temporales de documentación
- [ ] Verificar que `.gitignore` esté actualizado

## 📝 Configuración

- [ ] Crear `.env` basándose en `.env.example`
- [ ] Crear `env.agent` basándose en `env.agent.example`
- [ ] Configurar variables de producción en `.env`:
  - [ ] `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - [ ] `WOOCOMMERCE_URL`, `WOOCOMMERCE_KEY`, `WOOCOMMERCE_SECRET`
  - [ ] `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
  - [ ] `WHATSAPP_360DIALOG_API_KEY` (si se usa WhatsApp)
  - [ ] `WEBHOOK_SECRET` con valor seguro
  - [ ] `CORS_ORIGINS` con dominios específicos

## 🚀 Deployment

- [ ] Configurar Docker con `docker-compose -f docker-compose.production.yml`
- [ ] Inicializar la base de datos PostgreSQL con pgvector
- [ ] Cargar productos iniciales: `python scripts/sync_wc_products.py`
- [ ] Cargar base de conocimiento: `python scripts/load_knowledge.py`
- [ ] Configurar backup automático de base de datos
- [ ] Configurar actualizaciones automáticas: `./scripts/setup_auto_updates.sh`
- [ ] Configurar monitoreo y alertas

## ✅ Verificación Final

- [ ] Probar conexión a WooCommerce: `python scripts/test_woocommerce.py`
- [ ] Probar conexión a PostgreSQL: `python scripts/test_postgres.py`
- [ ] Verificar que el MCP server responda: `curl http://localhost:8000/health`
- [ ] Verificar que la interfaz web funcione: `http://localhost:8080`
- [ ] Probar el chat con una consulta simple
- [ ] Verificar logs sin errores críticos

## 📊 Monitoreo Post-Deployment

- [ ] Configurar logs centralizados
- [ ] Monitorear uso de recursos (CPU, memoria, disco)
- [ ] Configurar alertas para errores críticos
- [ ] Revisar métricas de rendimiento
- [ ] Backup diario de base de datos funcionando

## 🔄 Mantenimiento

- [ ] Documentar proceso de actualización
- [ ] Establecer calendario de actualizaciones
- [ ] Plan de rollback en caso de problemas
- [ ] Proceso de actualización de productos automatizado
- [ ] Revisión periódica de logs y métricas

## 📞 Contactos de Emergencia

- Documentar contactos técnicos clave
- Procedimiento de escalación
- Acceso a sistemas críticos