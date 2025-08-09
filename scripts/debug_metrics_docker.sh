#!/bin/bash

# Script para debuggear MetricsService usando el contenedor Docker

CONV_ID="${1:-whatsapp_34661239969_f46b536d}"

echo "🐳 Debuggeando MetricsService en contenedor Docker..."
echo "===================================================="
echo "Conversación: $CONV_ID"
echo ""

# Ejecutar el script Python dentro del contenedor
docker exec -i eva-web-prod python << EOF
import asyncio
import logging
from services.metrics_service import MetricsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_metrics():
    conversation_id = "$CONV_ID"
    print(f"🔍 Probando con conversación: {conversation_id}")
    
    try:
        # Inicializar servicio
        metrics_service = MetricsService()
        await metrics_service.initialize()
        print("✅ MetricsService inicializado")
        
        # Probar get_conversation_by_id
        print(f"\\n📋 Llamando get_conversation_by_id('{conversation_id}')")
        conv = await metrics_service.get_conversation_by_id(conversation_id)
        
        if conv:
            print("✅ Conversación encontrada:")
            print(f"   - ID: {conv['conversation_id']}")
            print(f"   - Usuario: {conv['user_id']}")
            print(f"   - Mensajes: {conv['messages_count']}")
            
            # Probar get_conversation_messages
            messages = await metrics_service.get_conversation_messages(conversation_id)
            print(f"\\n💬 Mensajes encontrados: {len(messages)}")
        else:
            print("❌ Conversación NO encontrada")
            
            # Query directo
            print("\\n🗄️  Verificando con query directo...")
            async with metrics_service.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT conversation_id, LENGTH(conversation_id) as len FROM conversations WHERE conversation_id = \$1",
                    conversation_id
                )
                if row:
                    print(f"✅ Query directo SÍ encuentra la conversación")
                    print(f"   - ID: '{row['conversation_id']}'")
                    print(f"   - Longitud: {row['len']}")
                else:
                    print("❌ Query directo NO encuentra la conversación")
                    
                # Buscar conversaciones similares
                print("\\n🔍 Buscando conversaciones que terminen con los últimos 10 caracteres...")
                similar = await conn.fetch(
                    "SELECT conversation_id FROM conversations WHERE conversation_id LIKE \$1 LIMIT 5",
                    f"%{conversation_id[-10:]}"
                )
                if similar:
                    print(f"Encontradas {len(similar)} conversaciones similares:")
                    for r in similar:
                        print(f"   - '{r['conversation_id']}'")
        
        await metrics_service.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_metrics())
EOF

echo ""
echo "🔍 Verificando si el problema es de inicialización del servicio..."

# Verificar si metrics_service está inicializado en la app
docker exec eva-web-prod python << 'EOF'
try:
    from app import metrics_service
    if metrics_service:
        print("✅ metrics_service está inicializado en app.py")
    else:
        print("❌ metrics_service es None en app.py")
except Exception as e:
    print(f"❌ Error importando metrics_service: {e}")
EOF