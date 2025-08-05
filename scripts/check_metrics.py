#!/usr/bin/env python3
"""
Script para verificar el estado de las métricas en la base de datos
"""

import asyncio
import asyncpg
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings


async def check_metrics():
    """Verificar el estado actual de las métricas"""
    
    conn = None
    try:
        print("🔍 Verificando métricas en la base de datos...\n")
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # 1. Contar todas las conversaciones
        total_conversations = await conn.fetchval("""
            SELECT COUNT(*) FROM conversations
        """)
        print(f"📊 Total de conversaciones en BD: {total_conversations}")
        
        # 2. Conversaciones de hoy
        today_conversations = await conn.fetchval("""
            SELECT COUNT(*) FROM conversations
            WHERE started_at >= CURRENT_DATE
            AND started_at < CURRENT_DATE + INTERVAL '1 day'
        """)
        print(f"📅 Conversaciones de hoy: {today_conversations}")
        
        # 3. Conversaciones de las últimas 24 horas
        last_24h = await conn.fetchval("""
            SELECT COUNT(*) FROM conversations
            WHERE started_at >= NOW() - INTERVAL '24 hours'
        """)
        print(f"⏰ Conversaciones últimas 24h: {last_24h}")
        
        # 4. Distribución por plataforma
        print("\n🌐 Distribución por plataforma:")
        platforms = await conn.fetch("""
            SELECT platform, COUNT(*) as count,
                   MIN(started_at) as first_conversation,
                   MAX(started_at) as last_conversation
            FROM conversations
            GROUP BY platform
            ORDER BY count DESC
        """)
        
        for p in platforms:
            print(f"  - {p['platform']}: {p['count']} conversaciones")
            if p['last_conversation']:
                print(f"    Última: {p['last_conversation'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not platforms:
            print("  (No hay conversaciones registradas)")
        
        # 5. Últimas 5 conversaciones
        print("\n📝 Últimas 5 conversaciones:")
        recent = await conn.fetch("""
            SELECT conversation_id, user_id, platform, 
                   started_at, status, messages_count
            FROM conversations
            ORDER BY started_at DESC
            LIMIT 5
        """)
        
        for r in recent:
            print(f"  - ID: {r['conversation_id'][:30]}...")
            print(f"    Usuario: {r['user_id'][:20]}...")
            print(f"    Plataforma: {r['platform']}")
            print(f"    Inicio: {r['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Estado: {r['status']}")
            print(f"    Mensajes: {r['messages_count']}")
            print()
        
        # 6. Verificar mensajes
        total_messages = await conn.fetchval("""
            SELECT COUNT(*) FROM conversation_messages
        """)
        print(f"💬 Total de mensajes registrados: {total_messages}")
        
        # 7. Verificar temas populares
        topics = await conn.fetch("""
            SELECT topic, category, SUM(count) as total
            FROM popular_topics
            GROUP BY topic, category
            ORDER BY total DESC
            LIMIT 5
        """)
        
        if topics:
            print("\n🏷️ Temas populares:")
            for t in topics:
                print(f"  - {t['topic']} ({t['category']}): {t['total']} veces")
        
        # 8. Verificar timezone
        server_time = await conn.fetchval("SELECT NOW()")
        current_date = await conn.fetchval("SELECT CURRENT_DATE")
        print(f"\n⏱️ Hora del servidor: {server_time}")
        print(f"📅 Fecha actual en BD: {current_date}")
        print(f"🖥️ Hora local Python: {datetime.now()}")
        
        # 9. Debug: Ver una conversación completa
        if total_conversations > 0:
            sample = await conn.fetchrow("""
                SELECT * FROM conversations
                ORDER BY started_at DESC
                LIMIT 1
            """)
            print("\n🔍 Muestra de conversación (última):")
            for key, value in dict(sample).items():
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if conn:
            await conn.close()
            print("\n✅ Verificación completada")


async def create_test_conversation():
    """Crear una conversación de prueba"""
    
    print("\n🧪 Creando conversación de prueba...")
    
    from services.metrics_service import MetricsService
    
    try:
        metrics = MetricsService(settings.DATABASE_URL)
        await metrics.initialize()
        
        # Crear conversación de prueba
        conversation_id = await metrics.start_conversation(
            user_id="test_user_" + datetime.now().strftime("%H%M%S"),
            platform="wordpress",
            channel_details={"source": "test_script"}
        )
        
        print(f"✅ Conversación creada: {conversation_id}")
        
        # Agregar algunos mensajes
        await metrics.track_message(
            conversation_id=conversation_id,
            sender_type="user",
            content="Mensaje de prueba del usuario"
        )
        
        await metrics.track_message(
            conversation_id=conversation_id,
            sender_type="bot",
            content="Respuesta de prueba del bot",
            response_time_ms=150
        )
        
        # Finalizar conversación
        await metrics.end_conversation(
            conversation_id=conversation_id,
            status="ended"
        )
        
        print("✅ Conversación de prueba completada")
        
        await metrics.close()
        
    except Exception as e:
        print(f"❌ Error creando conversación de prueba: {e}")


async def main():
    """Función principal"""
    
    # Verificar métricas actuales
    await check_metrics()
    
    # Preguntar si crear conversación de prueba
    print("\n" + "="*50)
    response = input("¿Deseas crear una conversación de prueba? (s/n): ")
    
    if response.lower() == 's':
        await create_test_conversation()
        print("\nVerificando métricas nuevamente...")
        await check_metrics()


if __name__ == "__main__":
    asyncio.run(main())