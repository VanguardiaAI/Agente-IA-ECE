#!/usr/bin/env python3
"""
Script para debuggear el problema de carga de conversaciones en el admin
"""

import asyncio
import sys
import os
from pathlib import Path
import httpx
import json

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

async def test_admin_conversations_api():
    """Probar los endpoints de admin que usa el dashboard"""
    
    print("🔍 Debuggeando APIs del admin dashboard...")
    
    base_url = "http://localhost:8080"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # 1. Probar endpoint de métricas (este funciona)
            print("\n📊 1. Probando /api/admin/metrics/summary...")
            try:
                response = await client.get(f"{base_url}/api/admin/metrics/summary")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Status: {response.status_code}")
                    print(f"   📈 Conversaciones hoy: {data['metrics'].get('today', {}).get('conversations', 0)}")
                    print(f"   👥 Total usuarios: {data['metrics'].get('historical', {}).get('unique_users', 0)}")
                else:
                    print(f"   ❌ Status: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # 2. Probar endpoint de conversaciones (el problemático)
            print("\n💬 2. Probando /api/admin/conversations...")
            try:
                response = await client.get(f"{base_url}/api/admin/conversations")
                print(f"   📡 Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Respuesta exitosa")
                    print(f"   📋 Tipo de datos: {type(data)}")
                    
                    if isinstance(data, list):
                        print(f"   📊 Cantidad de conversaciones: {len(data)}")
                        if data:
                            # Mostrar primera conversación como ejemplo
                            first_conv = data[0]
                            print(f"   🔍 Primera conversación:")
                            print(f"      - ID: {first_conv.get('conversation_id', 'N/A')[:20]}...")
                            print(f"      - Usuario: {first_conv.get('user_id', 'N/A')[:20]}...")
                            print(f"      - Plataforma: {first_conv.get('platform', 'N/A')}")
                            print(f"      - Fecha: {first_conv.get('started_at', 'N/A')}")
                            print(f"      - Mensajes: {first_conv.get('messages_count', 0)}")
                    elif isinstance(data, dict):
                        print(f"   📋 Claves en respuesta: {list(data.keys())}")
                        if 'conversations' in data:
                            convs = data['conversations']
                            print(f"   📊 Conversaciones en 'conversations': {len(convs) if isinstance(convs, list) else 'N/A'}")
                else:
                    print(f"   ❌ Error HTTP: {response.status_code}")
                    print(f"   📄 Respuesta: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # 3. Probar endpoint con parámetros (como lo hace el frontend)
            print("\n🔍 3. Probando /api/admin/conversations con parámetros...")
            try:
                params = {
                    'limit': 10,
                    'offset': 0
                }
                response = await client.get(f"{base_url}/api/admin/conversations", params=params)
                print(f"   📡 Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Con parámetros funciona")
                    if isinstance(data, list):
                        print(f"   📊 Cantidad: {len(data)}")
                else:
                    print(f"   ❌ Con parámetros falla: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"   ❌ Error con parámetros: {e}")
            
            # 4. Verificar si hay problema de autenticación
            print("\n🔐 4. Verificando autenticación...")
            try:
                # Intentar sin autenticación
                response = await client.get(f"{base_url}/api/admin/conversations")
                if response.status_code == 401:
                    print("   ⚠️  Requiere autenticación - esto es normal")
                    print("   💡 El frontend debe estar enviando token de autenticación")
                elif response.status_code == 200:
                    print("   ⚠️  No requiere autenticación - posible problema de seguridad")
                else:
                    print(f"   ❓ Status inesperado: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error verificando auth: {e}")
            
            # 5. Verificar health check
            print("\n❤️  5. Verificando health del sistema...")
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Sistema saludable")
                    print(f"   📊 Servicios: {data.get('services', {})}")
                else:
                    print(f"   ❌ Health check falló: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error en health: {e}")
            
    except Exception as e:
        print(f"❌ Error general: {e}")

async def check_database_conversations():
    """Verificar conversaciones directamente en la base de datos"""
    
    print("\n🗄️  Verificando base de datos directamente...")
    
    try:
        import asyncpg
        from config.settings import settings
        
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Contar conversaciones
        total_conversations = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        print(f"   📊 Total conversaciones en BD: {total_conversations}")
        
        if total_conversations > 0:
            # Mostrar últimas conversaciones
            recent = await conn.fetch("""
                SELECT 
                    conversation_id, user_id, platform, started_at, 
                    messages_count, status
                FROM conversations 
                ORDER BY started_at DESC 
                LIMIT 5
            """)
            
            print(f"   📋 Últimas 5 conversaciones:")
            for i, conv in enumerate(recent, 1):
                print(f"      {i}. {conv['platform']} | {conv['user_id'][:15]}... | {conv['messages_count']} msgs | {conv['started_at']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"   ❌ Error accediendo BD: {e}")

if __name__ == "__main__":
    print("🚀 Debuggeando problema de carga de conversaciones en admin...")
    print("=" * 60)
    
    async def main():
        await test_admin_conversations_api()
        await check_database_conversations()
        
        print(f"\n📋 RESUMEN:")
        print(f"   • Si /api/admin/metrics/summary funciona pero /api/admin/conversations no,")
        print(f"     el problema está en el endpoint específico de conversaciones")
        print(f"   • Verificar logs del servidor para más detalles")
        print(f"   • Puede ser problema de autenticación o paginación")
    
    asyncio.run(main())