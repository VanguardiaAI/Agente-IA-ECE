#!/usr/bin/env python3
"""
Script para debuggear el problema de conversaciones que muestran 0 en el dashboard
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg
from config.settings import settings

async def debug_conversations():
    """Investigar el estado de las conversaciones en la base de datos"""
    print("🔍 Debugging conversaciones en la base de datos...")
    
    try:
        # Conectar a la base de datos
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )
        
        print("✅ Conexión exitosa a PostgreSQL")
        
        # 1. Verificar si las tablas existen
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('conversations', 'conversation_messages', 'metrics_daily', 'metrics_hourly')
        ORDER BY table_name;
        """
        
        tables = await conn.fetch(tables_query)
        print(f"\n📊 Tablas encontradas: {[t['table_name'] for t in tables]}")
        
        if not tables:
            print("❌ No se encontraron las tablas necesarias!")
            return
            
        # 2. Verificar estructura de la tabla conversations
        if any(t['table_name'] == 'conversations' for t in tables):
            columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'conversations'
            ORDER BY ordinal_position;
            """
            columns = await conn.fetch(columns_query)
            print(f"\n🏗️  Estructura de tabla 'conversations':")
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']}")
        
        # 3. Contar total de conversaciones
        total_conversations = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        print(f"\n📈 Total de conversaciones: {total_conversations}")
        
        if total_conversations == 0:
            print("❌ No hay conversaciones registradas!")
            print("\n🔍 Verificando si hay mensajes sin conversación...")
            if any(t['table_name'] == 'conversation_messages' for t in tables):
                total_messages = await conn.fetchval("SELECT COUNT(*) FROM conversation_messages")
                print(f"   Total de mensajes: {total_messages}")
        
        else:
            # 4. Distribución por plataforma
            platform_dist = await conn.fetch("""
                SELECT platform, COUNT(*) as count 
                FROM conversations 
                GROUP BY platform 
                ORDER BY count DESC
            """)
            print(f"\n🌐 Distribución por plataforma:")
            for row in platform_dist:
                print(f"   - {row['platform']}: {row['count']}")
            
            # 5. Conversaciones por día (últimos 7 días)
            daily_stats = await conn.fetch("""
                SELECT 
                    DATE(started_at) as date,
                    COUNT(*) as conversations,
                    COUNT(DISTINCT user_id) as unique_users,
                    STRING_AGG(DISTINCT platform, ', ') as platforms
                FROM conversations 
                WHERE started_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(started_at)
                ORDER BY date DESC
            """)
            print(f"\n📅 Conversaciones por día (últimos 7 días):")
            for row in daily_stats:
                print(f"   - {row['date']}: {row['conversations']} conversaciones, {row['unique_users']} usuarios únicos ({row['platforms']})")
            
            # 6. Conversaciones de hoy (últimas 24 horas)
            today_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as conversations_today,
                    COUNT(DISTINCT user_id) as unique_users_today,
                    STRING_AGG(DISTINCT platform, ', ') as platforms_today
                FROM conversations 
                WHERE started_at >= NOW() - INTERVAL '24 hours'
            """)
            print(f"\n🕐 Últimas 24 horas:")
            print(f"   - Conversaciones: {today_stats['conversations_today']}")
            print(f"   - Usuarios únicos: {today_stats['unique_users_today']}")
            print(f"   - Plataformas: {today_stats['platforms_today'] or 'Ninguna'}")
            
            # 7. Muestra de conversaciones recientes
            recent_conversations = await conn.fetch("""
                SELECT 
                    conversation_id,
                    user_id,
                    platform,
                    started_at,
                    ended_at,
                    messages_count,
                    status
                FROM conversations 
                ORDER BY started_at DESC 
                LIMIT 5
            """)
            print(f"\n🔎 Últimas 5 conversaciones:")
            for conv in recent_conversations:
                duration = "En curso" if not conv['ended_at'] else str(conv['ended_at'] - conv['started_at'])
                print(f"   - {conv['conversation_id'][:8]}... | {conv['platform']} | Usuario: {conv['user_id'][:12]}... | {conv['messages_count']} mensajes | {duration}")
                
        # 8. Verificar métricas calculadas
        if any(t['table_name'] == 'metrics_daily' for t in tables):
            daily_metrics = await conn.fetchval("SELECT COUNT(*) FROM metrics_daily")
            print(f"\n📊 Métricas diarias registradas: {daily_metrics}")
            
            if daily_metrics > 0:
                recent_metrics = await conn.fetch("""
                    SELECT date, total_conversations, unique_users, platforms_json
                    FROM metrics_daily
                    ORDER BY date DESC
                    LIMIT 3
                """)
                print("   Últimas métricas:")
                for metric in recent_metrics:
                    print(f"   - {metric['date']}: {metric['total_conversations']} conversaciones, {metric['unique_users']} usuarios")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Iniciando debug de conversaciones...")
    asyncio.run(debug_conversations())