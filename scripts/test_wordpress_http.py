#!/usr/bin/env python3
"""
Script para probar que las conversaciones de WordPress se registran correctamente via HTTP API
"""

import asyncio
import sys
import os
from pathlib import Path
import json
import httpx
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

async def test_wordpress_http():
    """Probar API HTTP de WordPress y verificar que se registre la conversación"""
    
    print("🌐 Probando WordPress HTTP API tracking...")
    
    client_id = f"test_wordpress_http_{int(datetime.now().timestamp())}"
    
    try:
        async with httpx.AsyncClient() as client:
            # Enviar mensaje de prueba
            test_message = {
                "message": "Hola, estoy probando desde WordPress via HTTP",
                "user_id": client_id,
                "platform": "wordpress"
            }
            
            response = await client.post(
                "http://localhost:8080/api/chat",
                json=test_message,
                headers={"X-Platform": "wordpress"},
                timeout=30.0
            )
            
            print(f"📤 Enviado: {test_message['message']}")
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"📥 Respuesta: {response_data['response'][:100]}...")
                
                # Enviar otro mensaje
                test_message2 = {
                    "message": "¿Tienes productos de electricidad?",
                    "user_id": client_id,
                    "platform": "wordpress"
                }
                
                response2 = await client.post(
                    "http://localhost:8080/api/chat",
                    json=test_message2,
                    headers={"X-Platform": "wordpress"},
                    timeout=30.0
                )
                
                print(f"📤 Enviado: {test_message2['message']}")
                print(f"📊 Status: {response2.status_code}")
                
                if response2.status_code == 200:
                    response_data2 = response2.json()
                    print(f"📥 Respuesta: {response_data2['response'][:100]}...")
                    
                print(f"\n✅ Prueba HTTP completada. Cliente: {client_id}")
                return True
            else:
                print(f"❌ Error HTTP: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

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
            print(f"   - {conv['user_id'][:30]}... | {conv['messages_count']} mensajes | {conv['started_at']}")
            if conv['channel_details']:
                source = conv['channel_details'].get('source', 'unknown')
                print(f"     Source: {source}")
            
        # Contar total por plataforma
        platform_counts = await conn.fetch("""
            SELECT platform, COUNT(*) as count
            FROM conversations
            GROUP BY platform
            ORDER BY count DESC
        """)
        
        print(f"\n📈 Distribución por plataforma:")
        for row in platform_counts:
            print(f"   - {row['platform']}: {row['count']}")
        
        await conn.close()
        return len(recent_conversations) > 0
        
    except Exception as e:
        print(f"❌ Error verificando DB: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando test de tracking de WordPress via HTTP...")
    
    async def main():
        # Probar HTTP API
        http_success = await test_wordpress_http()
        
        if http_success:
            # Esperar un poco para que se procese
            await asyncio.sleep(2)
            
            # Verificar en base de datos
            db_success = await check_conversation_in_db()
            
            if db_success:
                print("\n✅ ¡Éxito! Las conversaciones de WordPress se están registrando correctamente.")
            else:
                print("\n❌ Falló: Las conversaciones no se registraron en la base de datos.")
        else:
            print("\n❌ Falló: No se pudo conectar a la API HTTP.")
    
    asyncio.run(main())