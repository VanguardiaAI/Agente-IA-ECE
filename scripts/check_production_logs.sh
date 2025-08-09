#!/bin/bash

# Script para capturar logs del error 500 en tiempo real

echo "🔍 Monitoreando logs de error en producción..."
echo "============================================="

# 1. Limpiar logs anteriores
docker exec eva-web-prod truncate -s 0 /proc/1/fd/1 2>/dev/null || echo "No se pudo limpiar stdout"
docker exec eva-web-prod truncate -s 0 /proc/1/fd/2 2>/dev/null || echo "No se pudo limpiar stderr"

# 2. Iniciar monitoreo de logs en background
echo "📋 Iniciando monitoreo de logs..."
docker logs eva-web-prod -f 2>&1 | grep -E "(ERROR|Exception|Traceback|500|knowledge|document)" &
LOGS_PID=$!

echo "🧪 Ahora reproduce el error en el navegador"
echo "   - Ve a: https://ia.elcorteelectrico.com/admin"
echo "   - Abre Base de conocimientos"
echo "   - Intenta editar store_info.md"
echo "   - Presiona Guardar"
echo ""
echo "⏰ Monitoreando por 30 segundos..."

sleep 30

# 3. Detener monitoreo
kill $LOGS_PID 2>/dev/null

echo ""
echo "📋 Logs recientes del contenedor:"
docker logs eva-web-prod --tail 20 2>&1 | grep -A 10 -B 5 -E "(ERROR|Exception|knowledge|document|500)"

echo ""
echo "🔍 Probando endpoint directamente:"
docker exec eva-web-prod python /tmp/test_knowledge_endpoint.py