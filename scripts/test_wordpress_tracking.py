#!/usr/bin/env python3
"""
Script para probar que las conversaciones de WordPress se registran correctamente
"""

import asyncio
import sys
import os
from pathlib import Path
import json
import websockets
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

async def test_wordpress_websocket():
    """Probar WebSocket de WordPress y verificar que se registre la conversación"""
    
    print("🌐 Probando WordPress WebSocket tracking...")
    
    client_id = f"test_wordpress_{int(datetime.now().timestamp())}"
    uri = f"ws://localhost:8080/ws/chat/{client_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Conectado a WebSocket: {client_id}")
            
            # Recibir mensaje de bienvenida
            welcome_msg = await websocket.recv()
            print(f"📨 Bienvenida: {json.loads(welcome_msg)['message']}")
            
            # Enviar mensaje de prueba
            test_message = {
                "message": "Hola, estoy probando desde WordPress",
                "platform": "wordpress",
                "clientId": client_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"📤 Enviado: {test_message['message']}")
            
            # Recibir respuesta
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📥 Respuesta: {response_data['message']}")
            
            # Enviar otro mensaje
            test_message2 = {
                "message": "¿Tienes productos de electricidad?",
                "platform": "wordpress",
                "clientId": client_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(test_message2))
            print(f"📤 Enviado: {test_message2['message']}")
            
            # Recibir respuesta
            response2 = await websocket.recv()
            response_data2 = json.loads(response2)
            print(f"📥 Respuesta: {response_data2['message'][:100]}...")
            
            print(f"\n✅ Prueba completada. Cliente: {client_id}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    return True

async def check_conversation_in_db():
    """Verificar que la conversación se registró en la base de datos"""
    
    import asyncpg
    from config.settings import settings
    
    print("\n🔍 Verificando conversaciones en base de datos...")
    
    try:
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )
        
        # Buscar conversaciones de WordPress de los últimos minutos
        recent_conversations = await conn.fetch("""
            SELECT 
                conversation_id,
                user_id,
                platform,
                started_at,
                messages_count,
                channel_details
            FROM conversations 
            WHERE platform = 'wordpress'
            AND started_at >= NOW() - INTERVAL '5 minutes'
            ORDER BY started_at DESC
            LIMIT 3
        """)
        
        print(f"📊 Encontradas {len(recent_conversations)} conversaciones WordPress recientes:")
        for conv in recent_conversations:
            print(f"   - {conv['user_id'][:20]}... | {conv['messages_count']} mensajes | {conv['started_at']}")
            
        # Contar total
        total_wordpress = await conn.fetchval("SELECT COUNT(*) FROM conversations WHERE platform = 'wordpress'")
        print(f"\n📈 Total conversaciones WordPress: {total_wordpress}")
        
        await conn.close()
        return len(recent_conversations) > 0
        
    except Exception as e:
        print(f"❌ Error verificando DB: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando test de tracking de WordPress...")
    
    async def main():
        # Probar WebSocket
        ws_success = await test_wordpress_websocket()
        
        if ws_success:
            # Esperar un poco para que se procese
            await asyncio.sleep(2)
            
            # Verificar en base de datos
            db_success = await check_conversation_in_db()
            
            if db_success:
                print("\n✅ ¡Éxito! Las conversaciones de WordPress se están registrando correctamente.")
            else:
                print("\n❌ Falló: Las conversaciones no se registraron en la base de datos.")
        else:
            print("\n❌ Falló: No se pudo conectar al WebSocket.")
    
    asyncio.run(main())