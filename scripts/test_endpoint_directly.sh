#!/bin/bash

# Script para probar el endpoint directamente y ver el error real

CONV_ID="${1:-whatsapp_5215610830260_c04690ea}"

echo "🔍 Probando endpoint de mensajes directamente..."
echo "=============================================="

# 1. Probar con curl y mostrar respuesta completa
echo ""
echo "📡 1. Request con curl (sin autenticación):"
curl -v "http://localhost:8080/api/admin/conversations/$CONV_ID/messages" 2>&1 | grep -E "< HTTP|404|500|{" | tail -20

# 2. Ver logs del contenedor en tiempo real
echo ""
echo "📋 2. Últimos logs del contenedor (errores):"
docker logs eva-web-prod --tail 50 2>&1 | grep -i "error\|exception\|traceback\|$CONV_ID" | tail -20

# 3. Ejecutar prueba directa dentro del contenedor
echo ""
echo "🐳 3. Prueba directa en el contenedor:"
docker exec eva-web-prod python << EOF
import asyncio
from services.metrics_singleton import get_metrics_service

async def test():
    try:
        print("Obteniendo MetricsService...")
        ms = await get_metrics_service()
        print(f"✅ MetricsService obtenido: {ms}")
        print(f"   Pool: {ms.pool}")
        
        # Probar el método directamente
        conv_id = "$CONV_ID"
        print(f"\nBuscando conversación: {conv_id}")
        
        result = await ms.get_conversation_by_id(conv_id)
        if result:
            print(f"✅ Conversación encontrada: {result['conversation_id']}")
        else:
            print("❌ get_conversation_by_id retornó None")
            
            # Verificar directamente en BD
            async with ms.pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM conversations WHERE conversation_id = \$1)",
                    conv_id
                )
                print(f"   ¿Existe en BD? {exists}")
                
                if exists:
                    row = await conn.fetchrow(
                        "SELECT conversation_id, LENGTH(conversation_id) as len FROM conversations WHERE conversation_id = \$1",
                        conv_id
                    )
                    print(f"   ID en BD: '{row['conversation_id']}'")
                    print(f"   Longitud: {row['len']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
EOF

# 4. Verificar si el singleton está funcionando
echo ""
echo "🔍 4. Verificando singleton en múltiples llamadas:"
docker exec eva-web-prod python << 'EOF'
import asyncio
from services.metrics_singleton import get_metrics_service

async def test_singleton():
    # Obtener instancia múltiples veces
    ms1 = await get_metrics_service()
    ms2 = await get_metrics_service()
    ms3 = await get_metrics_service()
    
    print(f"Instancia 1: {id(ms1)}")
    print(f"Instancia 2: {id(ms2)}")
    print(f"Instancia 3: {id(ms3)}")
    print(f"¿Son la misma instancia? {ms1 is ms2 is ms3}")

asyncio.run(test_singleton())
EOF