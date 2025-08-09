#!/bin/bash

# Script simple para verificar si metrics_service está inicializado

echo "🔍 Verificando inicialización de metrics_service..."
echo "================================================="

# Verificar logs del contenedor para errores de inicialización
echo ""
echo "📋 Buscando errores de inicialización en logs..."
docker logs eva-web-prod 2>&1 | grep -i "metrics\|MetricsService" | tail -20

echo ""
echo "🐳 Verificando dentro del contenedor..."

# Verificar si el servicio está inicializado
docker exec eva-web-prod python -c "
try:
    from app import metrics_service
    if metrics_service is not None:
        print('✅ metrics_service está inicializado')
        print(f'   Pool: {metrics_service.pool}')
        if metrics_service.pool:
            print('   ✅ Pool de conexiones existe')
        else:
            print('   ❌ Pool de conexiones es None')
    else:
        print('❌ metrics_service es None')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "💡 Si metrics_service es None o el pool es None, hay un problema de inicialización"