#!/usr/bin/env python3
"""
Script para verificar que las estadísticas del dashboard son correctas
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

async def verify_dashboard_statistics():
    """Verificar todas las estadísticas del dashboard"""
    print("🔍 Verificando estadísticas del dashboard...")
    
    try:
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )
        
        print("✅ Conexión exitosa a PostgreSQL")
        
        # 1. CONVERSACIONES HOY (últimas 24 horas)
        conversations_today = await conn.fetchrow("""
            SELECT 
                COUNT(*) as conversations_today,
                COUNT(DISTINCT user_id) as unique_users_today
            FROM conversations 
            WHERE started_at >= NOW() - INTERVAL '24 hours'
        """)
        
        print(f"\n📊 CONVERSACIONES HOY (últimas 24 horas):")
        print(f"   ✓ Conversaciones: {conversations_today['conversations_today']}")
        print(f"   ✓ Usuarios únicos hoy: {conversations_today['unique_users_today']}")
        
        # 2. USUARIOS ÚNICOS HISTÓRICO (total de todos los tiempos)
        users_historical = await conn.fetchval("""
            SELECT COUNT(DISTINCT user_id) 
            FROM conversations
        """)
        
        print(f"\n👥 USUARIOS ÚNICOS HISTÓRICO:")
        print(f"   ✓ Total usuarios histórico: {users_historical}")
        
        # 3. DOCUMENTOS DE KNOWLEDGE BASE
        # Verificar si existe la tabla de knowledge base
        kb_tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%knowledge%' OR table_name LIKE '%document%'
            ORDER BY table_name;
        """)
        
        print(f"\n📚 KNOWLEDGE BASE:")
        print(f"   📋 Tablas relacionadas: {[t['table_name'] for t in kb_tables]}")
        
        kb_count = 0
        if kb_tables:
            for table_info in kb_tables:
                table_name = table_info['table_name']
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    print(f"   ✓ {table_name}: {count} registros")
                    if 'knowledge' in table_name.lower() or 'document' in table_name.lower():
                        kb_count += count
                except Exception as e:
                    print(f"   ❌ Error en tabla {table_name}: {e}")
        
        # Verificar también en la tabla de embeddings (productos y knowledge)
        try:
            embeddings_info = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_embeddings,
                    COUNT(*) FILTER (WHERE content_type = 'knowledge') as knowledge_embeddings,
                    COUNT(*) FILTER (WHERE content_type = 'product') as product_embeddings
                FROM embeddings
            """)
            
            if embeddings_info:
                print(f"   ✓ Total embeddings: {embeddings_info['total_embeddings']}")
                print(f"   ✓ Knowledge embeddings: {embeddings_info['knowledge_embeddings'] or 0}")
                print(f"   ✓ Product embeddings: {embeddings_info['product_embeddings'] or 0}")
                kb_count = embeddings_info['knowledge_embeddings'] or 0
                
        except Exception as e:
            print(f"   ⚠️ No se pudo acceder a embeddings: {e}")
            
        print(f"   📊 Documentos KB estimados: {kb_count}")
        
        # 4. TOTAL CONVERSACIONES (30 días)
        total_30_days = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_conversations_30d,
                COUNT(DISTINCT user_id) as total_users_30d
            FROM conversations 
            WHERE started_at >= NOW() - INTERVAL '30 days'
        """)
        
        print(f"\n📈 TOTAL (30 días):")
        print(f"   ✓ Conversaciones (30 días): {total_30_days['total_conversations_30d']}")
        print(f"   ✓ Usuarios únicos (30 días): {total_30_days['total_users_30d']}")
        
        # 5. DISTRIBUCIÓN TEMPORAL DE CONVERSACIONES
        print(f"\n📅 DISTRIBUCIÓN TEMPORAL:")
        
        # Por fecha
        daily_distribution = await conn.fetch("""
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
        
        for row in daily_distribution:
            print(f"   - {row['date']}: {row['conversations']} conversaciones, {row['unique_users']} usuarios ({row['platforms']})")
            
        # Por plataforma
        platform_distribution = await conn.fetch("""
            SELECT 
                platform,
                COUNT(*) as total_conversations,
                COUNT(DISTINCT user_id) as unique_users,
                MIN(started_at) as first_conversation,
                MAX(started_at) as last_conversation
            FROM conversations 
            GROUP BY platform 
            ORDER BY total_conversations DESC
        """)
        
        print(f"\n🌐 DISTRIBUCIÓN POR PLATAFORMA:")
        for row in platform_distribution:
            print(f"   - {row['platform']}: {row['total_conversations']} conversaciones, {row['unique_users']} usuarios")
            print(f"     Primera: {row['first_conversation']}, Última: {row['last_conversation']}")
        
        # 6. COMPARACIÓN CON API DEL DASHBOARD
        print(f"\n🔄 COMPARANDO CON API DASHBOARD:")
        
        # Simular la lógica del dashboard
        dashboard_metrics = {
            'today': {
                'conversations': int(conversations_today['conversations_today'] or 0),
                'unique_users_today': int(conversations_today['unique_users_today'] or 0),
                'unique_users_historical': int(users_historical or 0)
            },
            'total': {
                'conversations_30d': int(total_30_days['total_conversations_30d'] or 0),
                'users_30d': int(total_30_days['total_users_30d'] or 0)
            },
            'knowledge_base': {
                'documents': kb_count
            }
        }
        
        print(f"   Dashboard debería mostrar:")
        print(f"   ✓ Conversaciones Hoy: {dashboard_metrics['today']['conversations']}")
        print(f"   ✓ Usuarios Únicos (hoy): {dashboard_metrics['today']['unique_users_today']}")
        print(f"   ✓ Usuarios Únicos (histórico): {dashboard_metrics['today']['unique_users_historical']}")
        print(f"   ✓ Documentos KB: {dashboard_metrics['knowledge_base']['documents']}")
        print(f"   ✓ Total (30 días): {dashboard_metrics['total']['conversations_30d']}")
        
        await conn.close()
        
        return dashboard_metrics
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Iniciando verificación de estadísticas del dashboard...")
    asyncio.run(verify_dashboard_statistics())