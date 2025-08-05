#!/usr/bin/env python3
"""
Script para probar la creación de tablas de métricas paso a paso
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings


async def test_creation():
    """Probar creación de tablas paso a paso"""
    
    conn = None
    try:
        print("Conectando a la base de datos...")
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Primero, eliminar tablas si existen (en orden inverso por las foreign keys)
        print("\nEliminando tablas existentes si las hay...")
        
        await conn.execute("DROP TABLE IF EXISTS conversation_messages CASCADE")
        await conn.execute("DROP TABLE IF EXISTS conversations CASCADE")
        await conn.execute("DROP TABLE IF EXISTS metrics_hourly CASCADE")
        await conn.execute("DROP TABLE IF EXISTS metrics_daily CASCADE")
        await conn.execute("DROP TABLE IF EXISTS popular_topics CASCADE")
        await conn.execute("DROP TABLE IF EXISTS metric_events CASCADE")
        await conn.execute("DROP TABLE IF EXISTS tool_metrics CASCADE")
        await conn.execute("DROP VIEW IF EXISTS dashboard_stats CASCADE")
        
        print("Tablas eliminadas")
        
        # Crear tabla conversations primero
        print("\nCreando tabla conversations...")
        await conn.execute("""
            CREATE TABLE conversations (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(100) UNIQUE NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                channel_details JSONB DEFAULT '{}',
                started_at TIMESTAMP DEFAULT NOW(),
                ended_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active',
                messages_count INTEGER DEFAULT 0,
                user_messages_count INTEGER DEFAULT 0,
                bot_messages_count INTEGER DEFAULT 0,
                avg_response_time_ms INTEGER,
                user_satisfaction INTEGER,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ Tabla conversations creada")
        
        # Verificar que la tabla se creó correctamente
        result = await conn.fetchrow("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversations' 
            AND column_name = 'conversation_id'
        """)
        
        if result:
            print(f"✅ Columna conversation_id existe en conversations")
        else:
            print("❌ Columna conversation_id NO existe")
            return
        
        # Ahora crear conversation_messages con la foreign key
        print("\nCreando tabla conversation_messages...")
        await conn.execute("""
            CREATE TABLE conversation_messages (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(100) NOT NULL,
                message_id VARCHAR(100) UNIQUE,
                sender_type VARCHAR(20) NOT NULL,
                content TEXT,
                intent VARCHAR(100),
                entities JSONB DEFAULT '[]',
                confidence FLOAT,
                response_time_ms INTEGER,
                tools_used JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            )
        """)
        print("✅ Tabla conversation_messages creada")
        
        # Crear el resto de las tablas
        print("\nCreando otras tablas de métricas...")
        
        # Ejecutar el resto del script SQL
        sql_file = Path(__file__).parent / "create_metrics_tables.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            
        # Extraer solo las partes que necesitamos (sin las tablas ya creadas)
        # Buscar desde metrics_hourly en adelante
        start_idx = sql_content.find("CREATE TABLE IF NOT EXISTS metrics_hourly")
        if start_idx > 0:
            remaining_sql = sql_content[start_idx:]
            
            # Ejecutar el resto del SQL
            await conn.execute(remaining_sql)
            print("✅ Todas las tablas de métricas creadas")
        
        # Verificar todas las tablas
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN (
                'conversations', 
                'conversation_messages', 
                'metrics_hourly',
                'metrics_daily',
                'popular_topics',
                'metric_events',
                'tool_metrics'
            )
            ORDER BY tablename
        """)
        
        print(f"\n📊 Tablas creadas exitosamente ({len(tables)}):")
        for table in tables:
            print(f"  ✅ {table['tablename']}")
        
        print("\n✨ Creación de tablas completada exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if conn:
            await conn.close()
            print("\nConexión cerrada")


if __name__ == "__main__":
    asyncio.run(test_creation())