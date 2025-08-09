#!/usr/bin/env python3
"""
Script para debuggear el problema del método get_conversation_by_id en producción
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from services.metrics_service import MetricsService
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_metrics_service():
    """Probar directamente el servicio de métricas"""
    
    conversation_id = sys.argv[1] if len(sys.argv) > 1 else "whatsapp_34661239969_f46b536d"
    
    print(f"🔍 Debuggeando MetricsService con conversación: {conversation_id}")
    print("=" * 60)
    
    try:
        # Inicializar servicio
        metrics_service = MetricsService()
        await metrics_service.initialize()
        print("✅ MetricsService inicializado")
        
        # Test 1: Probar get_conversation_by_id
        print(f"\n📋 Test 1: get_conversation_by_id('{conversation_id}')")
        conv = await metrics_service.get_conversation_by_id(conversation_id)
        
        if conv:
            print("✅ Conversación encontrada:")
            print(f"   - ID: {conv['conversation_id']}")
            print(f"   - Usuario: {conv['user_id']}")
            print(f"   - Plataforma: {conv['platform']}")
            print(f"   - Mensajes: {conv['messages_count']}")
        else:
            print("❌ Conversación NO encontrada por get_conversation_by_id")
            
            # Test 2: Query directo a la BD
            print(f"\n🗄️  Test 2: Query directo a la base de datos")
            async with metrics_service.pool.acquire() as conn:
                # Query simple
                row = await conn.fetchrow(
                    "SELECT * FROM conversations WHERE conversation_id = $1",
                    conversation_id
                )
                
                if row:
                    print("✅ Conversación SÍ existe en BD:")
                    print(f"   - ID en BD: '{row['conversation_id']}'")
                    print(f"   - Longitud ID: {len(row['conversation_id'])}")
                    print(f"   - Bytes ID: {row['conversation_id'].encode('utf-8')}")
                    
                    # Comparar con el ID buscado
                    print(f"\n🔍 Comparación de IDs:")
                    print(f"   - ID buscado: '{conversation_id}'")
                    print(f"   - Longitud: {len(conversation_id)}")
                    print(f"   - Bytes: {conversation_id.encode('utf-8')}")
                    print(f"   - ¿Son iguales? {row['conversation_id'] == conversation_id}")
                else:
                    print("❌ Conversación NO existe en BD")
                
                # Test 3: Buscar con LIKE
                print(f"\n🔍 Test 3: Buscar con LIKE")
                rows = await conn.fetch(
                    "SELECT conversation_id FROM conversations WHERE conversation_id LIKE $1",
                    f"%{conversation_id[-10:]}%"
                )
                
                if rows:
                    print(f"✅ Encontradas {len(rows)} conversaciones similares:")
                    for r in rows[:5]:
                        print(f"   - {r['conversation_id']}")
        
        # Test 4: Probar get_conversation_messages si la conversación fue encontrada
        if conv:
            print(f"\n💬 Test 4: get_conversation_messages")
            messages = await metrics_service.get_conversation_messages(conversation_id)
            print(f"✅ Mensajes encontrados: {len(messages)}")
            
            if messages:
                print("   Primeros mensajes:")
                for i, msg in enumerate(messages[:3], 1):
                    print(f"   {i}. {msg['sender_type']}: {msg['content'][:50]}...")
        
        await metrics_service.close()
        
    except Exception as e:
        logger.error(f"Error en test: {e}", exc_info=True)

if __name__ == "__main__":
    print("🚀 Test directo del MetricsService")
    asyncio.run(test_metrics_service())