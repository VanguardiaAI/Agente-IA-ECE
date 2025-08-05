"""
Servicio de logging de conversaciones usando PostgreSQL
Reemplaza el sistema anterior de MongoDB
"""

import asyncio
import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class PostgreSQLConversationLogger:
    """Logger de conversaciones usando PostgreSQL"""
    
    def __init__(self):
        self.pool = None
        self.enabled = settings.ENABLE_CONVERSATION_LOGGING
    
    async def initialize(self):
        """Inicializar el pool de conexiones y crear tablas si es necesario"""
        if not self.enabled:
            logger.info("Logging de conversaciones deshabilitado")
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            await self._create_tables()
            logger.info("✅ PostgreSQL conversation logger inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando PostgreSQL logger: {e}")
            self.enabled = False
    
    async def _create_tables(self):
        """Crear tablas necesarias para logging"""
        async with self.pool.acquire() as conn:
            # Tabla de conversaciones
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255),
                    message_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    strategy VARCHAR(100),
                    tools_used TEXT[],
                    satisfaction_score FLOAT
                );
            """)
            
            # Índices para optimizar consultas
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session_id 
                ON conversations(session_id);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
                ON conversations(timestamp);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                ON conversations(user_id);
            """)
    
    async def log_message(
        self,
        session_id: str,
        user_id: str,
        message_type: str,
        content: str,
        metadata: Dict[str, Any] = None,
        response_time_ms: int = None,
        strategy: str = None,
        tools_used: List[str] = None,
        satisfaction_score: float = None
    ):
        """Registrar un mensaje en la conversación"""
        if not self.enabled or not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversations (
                        session_id, user_id, message_type, content, metadata,
                        response_time_ms, strategy, tools_used, satisfaction_score
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                session_id, user_id, message_type, content, 
                json.dumps(metadata or {}), response_time_ms, 
                strategy, tools_used or [], satisfaction_score
                )
                
        except Exception as e:
            logger.error(f"Error logging message: {e}")
    
    async def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Obtener historial de conversación"""
        if not self.enabled or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM conversations 
                    WHERE session_id = $1 
                    ORDER BY timestamp ASC 
                    LIMIT $2
                """, session_id, limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Obtener conversaciones de un usuario"""
        if not self.enabled or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT DISTINCT session_id, MIN(timestamp) as start_time,
                           MAX(timestamp) as last_message, COUNT(*) as message_count
                    FROM conversations 
                    WHERE user_id = $1 
                    GROUP BY session_id
                    ORDER BY last_message DESC 
                    LIMIT $2
                """, user_id, limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            return []
    
    async def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Obtener analytics de conversaciones"""
        if not self.enabled or not self.pool:
            return {}
        
        try:
            async with self.pool.acquire() as conn:
                # Estadísticas básicas
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT session_id) as total_conversations,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(response_time_ms) as avg_response_time,
                        AVG(satisfaction_score) as avg_satisfaction
                    FROM conversations 
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '%d days'
                """, days)
                
                # Estrategias más usadas
                strategies = await conn.fetch("""
                    SELECT strategy, COUNT(*) as count
                    FROM conversations 
                    WHERE strategy IS NOT NULL 
                    AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%d days'
                    GROUP BY strategy 
                    ORDER BY count DESC
                """, days)
                
                # Herramientas más usadas
                tools = await conn.fetch("""
                    SELECT unnest(tools_used) as tool, COUNT(*) as count
                    FROM conversations 
                    WHERE tools_used IS NOT NULL 
                    AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%d days'
                    GROUP BY tool 
                    ORDER BY count DESC
                """, days)
                
                return {
                    "period_days": days,
                    "stats": dict(stats) if stats else {},
                    "top_strategies": [dict(row) for row in strategies],
                    "top_tools": [dict(row) for row in tools]
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}
    
    async def close(self):
        """Cerrar el pool de conexiones"""
        if self.pool:
            await self.pool.close()

# Instancia global del logger
conversation_logger = PostgreSQLConversationLogger() 