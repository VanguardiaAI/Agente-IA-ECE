#!/bin/bash

# Script temporal para copiar los archivos nuevos al contenedor mientras se reconstruye

echo "🔧 Aplicando hotfix temporal..."
echo "=============================="

# 1. Copiar metrics_singleton.py al contenedor
echo "📋 1. Copiando metrics_singleton.py..."
docker cp services/metrics_singleton.py eva-web-prod:/app/services/

# 2. Copiar app.py actualizado
echo "📋 2. Copiando app.py actualizado..."
docker cp app.py eva-web-prod:/app/

# 3. Verificar que se copiaron
echo ""
echo "✅ Verificando archivos copiados:"
docker exec eva-web-prod ls -la services/metrics_singleton.py
docker exec eva-web-prod grep -c "get_metrics_service" app.py

# 4. Reiniciar el worker de uvicorn dentro del contenedor
echo ""
echo "🔄 Reiniciando workers de uvicorn..."
docker exec eva-web-prod pkill -HUP uvicorn || echo "Enviando señal de recarga..."

echo ""
echo "✅ Hotfix aplicado. Los cambios deberían estar activos en unos segundos."
echo ""
echo "⚠️  IMPORTANTE: Esta es una solución temporal."
echo "   Debes reconstruir la imagen con:"
echo "   docker-compose -f docker-compose.production.yml build --no-cache web-app"
echo "   docker-compose -f docker-compose.production.yml up -d"