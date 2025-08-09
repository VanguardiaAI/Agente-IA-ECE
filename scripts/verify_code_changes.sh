#!/bin/bash

# Script para verificar que los cambios se aplicaron correctamente

echo "🔍 Verificando cambios en el código..."
echo "======================================"

# 1. Verificar que el archivo metrics_singleton.py existe
echo ""
echo "📋 1. Verificando archivo metrics_singleton.py:"
docker exec eva-web-prod ls -la services/metrics_singleton.py 2>&1 || echo "❌ Archivo no encontrado"

# 2. Verificar el contenido del endpoint en app.py
echo ""
echo "📋 2. Verificando cambios en app.py (líneas del endpoint):"
docker exec eva-web-prod grep -A 5 "conversations/{conversation_id}/messages" app.py | head -20

# 3. Verificar si hay errores de importación
echo ""
echo "📋 3. Probando importación del singleton:"
docker exec eva-web-prod python -c "
try:
    from services.metrics_singleton import get_metrics_service
    print('✅ Importación exitosa')
except Exception as e:
    print(f'❌ Error de importación: {e}')
"

# 4. Verificar el contenido del archivo en el contenedor
echo ""
echo "📋 4. Contenido de metrics_singleton.py (primeras 20 líneas):"
docker exec eva-web-prod head -20 services/metrics_singleton.py 2>&1 || echo "❌ No se puede leer el archivo"

# 5. Verificar si el contenedor se reinició después de los cambios
echo ""
echo "📋 5. Tiempo de ejecución del contenedor:"
docker ps -f name=eva-web-prod --format "table {{.Names}}\t{{.Status}}"

# 6. Forzar recarga del código si es necesario
echo ""
echo "💡 Si los archivos no están actualizados, ejecuta:"
echo "   docker-compose -f docker-compose.production.yml down"
echo "   docker-compose -f docker-compose.production.yml up -d"