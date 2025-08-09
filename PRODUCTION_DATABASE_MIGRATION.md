# 🗄️ Migración de Base de Datos de Producción

## ⚠️ IMPORTANTE
La base de datos de producción necesita ser migrada para incluir las tablas de conversaciones y métricas necesarias para el nuevo sistema de tracking de WordPress y WhatsApp.

## 🚀 Scripts de Migración Disponibles

### 1. **Script Principal (Recomendado)**
```bash
./scripts/setup_production_db.sh
```
- ✅ Crea backup automático
- ✅ Verifica conexión a base de datos
- ✅ Aplica todas las migraciones necesarias
- ✅ Verifica que las tablas se crearon correctamente

### 2. **Script Python Avanzado**
```bash
# Simular migración (sin cambios)
python3 scripts/migrate_production_database.py --dry-run

# Ejecutar migración
python3 scripts/migrate_production_database.py --force
```

### 3. **Migración Manual**
Si prefieres ejecutar paso por paso:
```bash
# 1. Ejecutar setup básico
python3 scripts/setup_metrics.py

# 2. Ejecutar setup de admin (opcional)
python3 scripts/setup_admin_panel.py
```

## 📋 Tablas que se Crearán

### **Críticas para Conversaciones:**
- `conversations` - Registro de conversaciones
- `conversation_messages` - Mensajes individuales
- `metrics_hourly` - Métricas por hora
- `metrics_daily` - Métricas diarias

### **Adicionales:**
- `popular_topics` - Temas populares
- `metric_events` - Eventos del sistema
- `tool_metrics` - Rendimiento de herramientas
- `admin_users` - Usuarios admin
- `bot_settings` - Configuración del bot

## 🔄 Proceso de Migración de Producción

### **1. Preparación**
```bash
# En el servidor de producción
cd /ruta/a/tu/proyecto/MCP-WC

# Verificar variables de entorno
cat .env | grep POSTGRES
```

### **2. Ejecutar Migración**
```bash
# OPCIÓN A: Script automático (recomendado)
./scripts/setup_production_db.sh

# OPCIÓN B: Python con simulación previa
python3 scripts/migrate_production_database.py --dry-run
python3 scripts/migrate_production_database.py --force
```

### **3. Verificar Migración**
```bash
# Verificar que las tablas existen
python3 scripts/debug_conversations.py

# Probar API de métricas
curl http://localhost:8080/api/admin/metrics/summary
```

### **4. Reiniciar Servicios**
```bash
# Reiniciar para aplicar cambios de código
./scripts/docker-production.sh restart
```

## 🛡️ Seguridad

### **Backup Automático**
Los scripts crean backup automático antes de la migración:
- Archivo: `backup_production_YYYYMMDD_HHMMSS.sql`
- Contiene: Esquema de base de datos actual

### **Rollback Manual**
Si algo sale mal:
```bash
# Restaurar desde backup (cambiar fecha)
PGPASSWORD=$POSTGRES_PASSWORD psql \
  -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB \
  < backup_production_20250809_123456.sql
```

## 📊 Verificación Post-Migración

### **Dashboard debe mostrar:**
- ✅ Conversaciones registrándose correctamente
- ✅ Usuarios únicos históricos (no solo de hoy)
- ✅ Estadísticas por plataforma (WordPress, WhatsApp)
- ✅ Documentos KB correctos

### **Comandos de Verificación:**
```bash
# 1. Probar API de métricas
curl -s http://localhost:8080/api/admin/metrics/summary | python3 -m json.tool

# 2. Verificar conversaciones en DB
python3 scripts/debug_conversations.py

# 3. Probar nueva conversación WordPress
python3 scripts/test_wordpress_http.py
```

## ⚡ Problemas Comunes

### **Error: "relation does not exist"**
- **Causa**: Tablas no migradas
- **Solución**: Ejecutar `./scripts/setup_production_db.sh`

### **Error: "column does not exist"**
- **Causa**: Esquema desactualizado
- **Solución**: Verificar que se aplicaron todas las migraciones

### **Dashboard muestra 0 conversaciones**
- **Causa**: Tablas vacías después de migración (normal)
- **Solución**: Probar nueva conversación para verificar tracking

## 🎯 Resultado Esperado

**ANTES de la migración:**
```json
{
  "error": "relation 'conversations' does not exist"
}
```

**DESPUÉS de la migración:**
```json
{
  "metrics": {
    "today": {"conversations": 0, "unique_users": 0},
    "total": {"conversations": 0, "users": 0}, 
    "historical": {"unique_users": 0},
    "platforms": {},
    "platforms_all": {}
  }
}
```

El dashboard comenzará a mostrar datos reales cuando se registren nuevas conversaciones.