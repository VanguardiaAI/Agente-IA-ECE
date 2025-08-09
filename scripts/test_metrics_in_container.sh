#!/bin/bash

# Script para probar MetricsService directamente en el contenedor

CONV_ID="${1:-whatsapp_34661239969_f46b536d}"

echo "🐳 Probando MetricsService en contenedor..."
echo "=========================================="

# Test 1: Crear instancia directa
echo ""
echo "📋 Test 1: Creando instancia directa de MetricsService"

docker exec eva-web-prod python << 'EOF'
import asyncio
from services.metrics_service import MetricsService
from config.settings import settings

async def test():
    print("Creando MetricsService con DATABASE_URL...")
    ms = MetricsService(settings.DATABASE_URL)
    await ms.initialize()
    print("✅ MetricsService creado e inicializado")
    
    # Contar conversaciones
    async with ms.pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        print(f"✅ Total conversaciones: {count}")
    
    await ms.close()

asyncio.run(test())
EOF

# Test 2: Verificar la variable global
echo ""
echo "📋 Test 2: Verificando variable global en app.py"

docker exec eva-web-prod python << 'EOF'
# Intentar diferentes formas de importar
print("1. Import directo de app:")
try:
    import app
    print(f"   metrics_service en app: {app.metrics_service}")
except Exception as e:
    print(f"   Error: {e}")

print("\n2. From import:")
try:
    from app import metrics_service
    print(f"   metrics_service: {metrics_service}")
except Exception as e:
    print(f"   Error: {e}")

print("\n3. Verificar __main__:")
try:
    import sys
    if 'app' in sys.modules:
        app_module = sys.modules['app']
        print(f"   app en sys.modules: {app_module}")
        print(f"   metrics_service attr: {hasattr(app_module, 'metrics_service')}")
        if hasattr(app_module, 'metrics_service'):
            print(f"   valor: {getattr(app_module, 'metrics_service')}")
except Exception as e:
    print(f"   Error: {e}")
EOF

# Test 3: Hacer request HTTP para verificar
echo ""
echo "📋 Test 3: Probando endpoint HTTP directamente"

curl -s "http://localhost:8080/api/admin/conversations/$CONV_ID/messages" | python3 -m json.tool 2>/dev/null || echo "Error en request HTTP"