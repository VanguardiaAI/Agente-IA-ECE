#!/usr/bin/env python3
"""
Script para actualizar el esquema de la base de datos
"""

import asyncio
import sys
from pathlib import Path
import asyncpg

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings

async def fix_schema():
    """Actualizar el esquema de la base de datos"""
    
    # Conectar a la base de datos
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        print("🔧 Actualizando esquema de base de datos...")
        
        # Verificar si la tabla conversation_logs existe
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'conversation_logs'
            )
        """)
        
        if table_exists:
            # Verificar si la columna session_id existe
            column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'conversation_logs' 
                    AND column_name = 'session_id'
                )
            """)
            
            if not column_exists:
                print("   Agregando columna session_id...")
                await conn.execute("""
                    ALTER TABLE conversation_logs 
                    ADD COLUMN IF NOT EXISTS session_id VARCHAR(100)
                """)
                print("   ✅ Columna session_id agregada")
            else:
                print("   ✅ Columna session_id ya existe")
        else:
            print("   ⚠️  Tabla conversation_logs no existe, creándola...")
            
            # Crear tabla conversation_logs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100),
                    user_id VARCHAR(255),
                    platform VARCHAR(50),
                    message TEXT,
                    response TEXT,
                    intent VARCHAR(100),
                    entities JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    tools_used TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crear índices
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_logs_session_id 
                ON conversation_logs(session_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_id 
                ON conversation_logs(user_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_logs_timestamp 
                ON conversation_logs(timestamp DESC)
            """)
            
            print("   ✅ Tabla conversation_logs creada")
        
        # Verificar y crear otras tablas necesarias si no existen
        
        # Tabla de métricas de conversaciones
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id VARCHAR(100) PRIMARY KEY,
                user_id VARCHAR(255),
                platform VARCHAR(50),
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active',
                messages_count INTEGER DEFAULT 0,
                user_messages_count INTEGER DEFAULT 0,
                bot_messages_count INTEGER DEFAULT 0,
                avg_response_time_ms NUMERIC,
                user_satisfaction INTEGER,
                channel_details JSONB,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla conversations verificada")
        
        # Tabla de mensajes de conversación
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(100) REFERENCES conversations(conversation_id),
                sender_type VARCHAR(20),
                content TEXT,
                intent VARCHAR(100),
                entities JSONB,
                confidence NUMERIC,
                response_time_ms INTEGER,
                tools_used JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Tabla conversation_messages verificada")
        
        # Crear índices para conversation_messages
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id 
            ON conversation_messages(conversation_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at 
            ON conversation_messages(created_at DESC)
        """)
        
        print("\n✅ Esquema de base de datos actualizado correctamente")
        
    except Exception as e:
        print(f"\n❌ Error actualizando esquema: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_schema())