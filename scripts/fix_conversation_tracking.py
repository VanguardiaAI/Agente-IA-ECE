#!/usr/bin/env python3
"""
Script to fix conversation tracking issue where each message creates a new conversation.
This script updates the metrics service to support finding active conversations.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.metrics_service import MetricsService
import asyncio
import asyncpg
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL to add new method to find active conversations
ADD_METHOD_SQL = """
-- Add index for efficient lookup of active conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user_platform_status 
ON conversations(user_id, platform, status, updated_at DESC);

-- Function to find active conversation for a user
CREATE OR REPLACE FUNCTION find_active_conversation(
    p_user_id VARCHAR(255),
    p_platform VARCHAR(50),
    p_timeout_minutes INTEGER DEFAULT 30
) RETURNS TABLE (
    conversation_id VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE,
    messages_count INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.conversation_id,
        c.started_at,
        c.messages_count,
        c.updated_at as last_updated
    FROM conversations c
    WHERE c.user_id = p_user_id 
        AND c.platform = p_platform
        AND c.status = 'active'
        AND c.updated_at >= NOW() - INTERVAL '1 minute' * p_timeout_minutes
    ORDER BY c.updated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
"""

async def update_metrics_service():
    """Add method to find or create conversation"""
    
    # Create a new file with the updated MetricsService
    updated_service = '''"""
Servicio de métricas y análisis para el chatbot - ACTUALIZADO
"""

import asyncio
import asyncpg
import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class MetricsService:
    """Servicio para recopilar y gestionar métricas del chatbot"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
        self.active_conversations = {}  # Cache de conversaciones activas
        self.conversation_timeout_minutes = 30  # Timeout por defecto
        
    async def initialize(self):
        """Inicializar el pool de conexiones"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10
            )
            logger.info("MetricsService inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando MetricsService: {e}")
            raise
    
    async def close(self):
        """Cerrar el pool de conexiones"""
        if self.pool:
            await self.pool.close()
    
    async def find_or_create_conversation(
        self,
        user_id: str,
        platform: str = "wordpress",
        channel_details: Dict[str, Any] = None,
        timeout_minutes: Optional[int] = None
    ) -> str:
        """Buscar conversación activa o crear una nueva si no existe o expiró"""
        
        if timeout_minutes is None:
            timeout_minutes = self.conversation_timeout_minutes
            
        async with self.pool.acquire() as conn:
            try:
                # Buscar conversación activa
                result = await conn.fetchrow("""
                    SELECT conversation_id, started_at, messages_count, updated_at
                    FROM conversations
                    WHERE user_id = $1 
                        AND platform = $2
                        AND status = 'active'
                        AND updated_at >= NOW() - INTERVAL '1 minute' * $3
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, user_id, platform, timeout_minutes)
                
                if result:
                    conversation_id = result['conversation_id']
                    logger.info(f"Conversación existente encontrada: {conversation_id} (mensajes: {result['messages_count']})")
                    
                    # Actualizar timestamp de última actividad
                    await conn.execute("""
                        UPDATE conversations 
                        SET updated_at = NOW()
                        WHERE conversation_id = $1
                    """, conversation_id)
                    
                    # Actualizar cache
                    if conversation_id not in self.active_conversations:
                        self.active_conversations[conversation_id] = {
                            'user_id': user_id,
                            'platform': platform,
                            'started_at': result['started_at'],
                            'message_times': []
                        }
                    
                    return conversation_id
                else:
                    # Crear nueva conversación
                    return await self.start_conversation(user_id, platform, channel_details)
                    
            except Exception as e:
                logger.error(f"Error en find_or_create_conversation: {e}")
                # En caso de error, crear nueva conversación
                return await self.start_conversation(user_id, platform, channel_details)
    
    async def start_conversation(
        self,
        user_id: str,
        platform: str = "wordpress",
        channel_details: Dict[str, Any] = None
    ) -> str:
        """Iniciar el tracking de una nueva conversación"""
        conversation_id = f"{platform}_{user_id}_{uuid.uuid4().hex[:8]}"
        
        async with self.pool.acquire() as conn:
            try:
                # Cerrar conversaciones anteriores del mismo usuario
                await conn.execute("""
                    UPDATE conversations 
                    SET status = 'ended', 
                        ended_at = NOW(),
                        updated_at = NOW()
                    WHERE user_id = $1 
                        AND platform = $2 
                        AND status = 'active'
                """, user_id, platform)
                
                # Usar NOW() de PostgreSQL para consistencia de timezone
                await conn.execute("""
                    INSERT INTO conversations (
                        conversation_id, user_id, platform, 
                        channel_details, started_at, status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, NOW(), 'active', NOW(), NOW())
                    ON CONFLICT (conversation_id) DO UPDATE
                    SET status = 'active', updated_at = NOW()
                """, conversation_id, user_id, platform, 
                    json.dumps(channel_details or {}))
                
                # Guardar en cache
                self.active_conversations[conversation_id] = {
                    'user_id': user_id,
                    'platform': platform,
                    'started_at': datetime.now(),
                    'message_times': []
                }
                
                logger.info(f"Nueva conversación iniciada: {conversation_id}")
                return conversation_id
                
            except Exception as e:
                logger.error(f"Error iniciando conversación: {e}")
                return conversation_id
'''

    # Continuar con el resto de los métodos sin cambios
    with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/services/metrics_service_updated.py', 'w') as f:
        f.write(updated_service)
    
    logger.info("✅ Archivo metrics_service_updated.py creado con el método find_or_create_conversation")

async def add_database_function():
    """Add database function for finding active conversations"""
    from config.settings import settings
    
    try:
        # Connect to database
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Execute SQL to add index and function
        await conn.execute(ADD_METHOD_SQL)
        
        logger.info("✅ Database function and index created successfully")
        
        # Test the function
        test_result = await conn.fetchrow("""
            SELECT * FROM find_active_conversation('test_user', 'wordpress', 30)
        """)
        
        logger.info(f"Function test result: {test_result}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        raise

async def main():
    """Main function"""
    logger.info("🔧 Fixing conversation tracking issue...")
    
    # Step 1: Create updated metrics service file
    await update_metrics_service()
    
    # Step 2: Add database function
    await add_database_function()
    
    logger.info("""
✅ Fix prepared! Now you need to:

1. Review the changes in metrics_service_updated.py
2. Update app.py to use find_or_create_conversation instead of start_conversation:

   # In the /api/chat endpoint, replace:
   conversation_id = await metrics_service.start_conversation(
       user_id=chat_message.user_id,
       platform=chat_message.platform,
       channel_details={...}
   )
   
   # With:
   conversation_id = await metrics_service.find_or_create_conversation(
       user_id=chat_message.user_id,
       platform=chat_message.platform,
       channel_details={...},
       timeout_minutes=30  # Conversations timeout after 30 minutes of inactivity
   )

3. Copy the find_or_create_conversation method from metrics_service_updated.py to metrics_service.py
4. Restart the application

This will ensure conversations continue across multiple messages instead of creating new ones.
""")

if __name__ == "__main__":
    asyncio.run(main())