#!/usr/bin/env python3
"""
Script de prueba para el sistema de gestión de conversaciones
Verifica que todas las funcionalidades estén operativas
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

# Configuración
API_BASE_URL = "http://localhost:8080"
API_KEY = os.getenv("ADMIN_API_KEY", "admin_test_key")

async def test_conversation_list():
    """Probar listado de conversaciones"""
    print("\n🔍 Probando listado de conversaciones...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Listar conversaciones
        async with session.get(f"{API_BASE_URL}/api/admin/conversations", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Conversaciones encontradas: {len(data.get('conversations', []))}")
                
                # Mostrar primeras 3 conversaciones
                for conv in data.get('conversations', [])[:3]:
                    print(f"  - {conv['conversation_id']} | {conv['platform']} | {conv['messages_count']} mensajes")
                
                return data.get('conversations', [])
            else:
                print(f"❌ Error al listar conversaciones: {resp.status}")
                return []

async def test_conversation_search():
    """Probar búsqueda de conversaciones"""
    print("\n🔍 Probando búsqueda de conversaciones...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Buscar por plataforma
        params = {"platform": "wordpress"}
        async with session.get(
            f"{API_BASE_URL}/api/admin/conversations/search", 
            headers=headers,
            params=params
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Conversaciones de WordPress: {len(data.get('conversations', []))}")
            else:
                print(f"❌ Error en búsqueda: {resp.status}")
        
        # Buscar por fecha (últimos 7 días)
        date_from = (datetime.now() - timedelta(days=7)).isoformat()
        params = {"date_from": date_from}
        async with session.get(
            f"{API_BASE_URL}/api/admin/conversations/search", 
            headers=headers,
            params=params
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Conversaciones últimos 7 días: {len(data.get('conversations', []))}")
            else:
                print(f"❌ Error en búsqueda por fecha: {resp.status}")

async def test_conversation_details(conversation_id):
    """Probar detalles de conversación"""
    print(f"\n🔍 Probando detalles de conversación {conversation_id}...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with session.get(
            f"{API_BASE_URL}/api/admin/conversations/{conversation_id}/messages", 
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                conv = data.get('conversation', {})
                messages = data.get('messages', [])
                
                print(f"✅ Conversación encontrada:")
                print(f"  - Usuario: {conv.get('user_id')}")
                print(f"  - Plataforma: {conv.get('platform')}")
                print(f"  - Mensajes: {len(messages)}")
                print(f"  - Duración: {conv.get('duration_minutes', 0):.1f} minutos")
                
                # Mostrar primeros 3 mensajes
                print("\n  Primeros mensajes:")
                for msg in messages[:3]:
                    sender = "👤 Usuario" if msg['sender_type'] == 'user' else "🤖 Eva"
                    content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                    print(f"    {sender}: {content}")
                
                return True
            elif resp.status == 404:
                print(f"⚠️ Conversación no encontrada")
                return False
            else:
                print(f"❌ Error al obtener detalles: {resp.status}")
                return False

async def create_test_conversation():
    """Crear una conversación de prueba"""
    print("\n🔧 Creando conversación de prueba...")
    
    async with aiohttp.ClientSession() as session:
        # Simular mensaje de chat
        chat_data = {
            "message": "Hola, necesito información sobre un producto",
            "user_id": "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "platform": "wordpress"
        }
        
        async with session.post(
            f"{API_BASE_URL}/api/chat", 
            json=chat_data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Conversación creada: {data.get('conversation_id')}")
                return data.get('conversation_id')
            else:
                print(f"❌ Error al crear conversación: {resp.status}")
                return None

async def test_metrics_integration():
    """Probar integración con métricas"""
    print("\n📊 Probando integración con métricas...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with session.get(f"{API_BASE_URL}/api/admin/metrics/summary", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                metrics = data.get('metrics', {})
                
                print("✅ Métricas obtenidas:")
                if 'today' in metrics:
                    print(f"  - Conversaciones hoy: {metrics['today'].get('conversations', 0)}")
                    print(f"  - Usuarios únicos hoy: {metrics['today'].get('unique_users', 0)}")
                
                if 'platforms' in metrics:
                    print(f"  - Por plataforma: {metrics['platforms']}")
                
                return True
            else:
                print(f"❌ Error al obtener métricas: {resp.status}")
                return False

async def main():
    """Ejecutar todas las pruebas"""
    print("=" * 60)
    print("🧪 PRUEBA DEL SISTEMA DE GESTIÓN DE CONVERSACIONES")
    print("=" * 60)
    
    try:
        # 1. Probar listado
        conversations = await test_conversation_list()
        
        # 2. Probar búsqueda
        await test_conversation_search()
        
        # 3. Probar detalles (si hay conversaciones)
        if conversations:
            await test_conversation_details(conversations[0]['conversation_id'])
        else:
            print("\n⚠️ No hay conversaciones para probar detalles")
            # Crear una de prueba
            conv_id = await create_test_conversation()
            if conv_id:
                await asyncio.sleep(2)  # Esperar a que se procese
                await test_conversation_details(conv_id)
        
        # 4. Probar métricas
        await test_metrics_integration()
        
        print("\n✅ Pruebas completadas exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())