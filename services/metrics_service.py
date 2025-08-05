"""
Servicio de métricas y análisis para el chatbot
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
                
                logger.info(f"Conversación iniciada: {conversation_id}")
                return conversation_id
                
            except Exception as e:
                logger.error(f"Error iniciando conversación: {e}")
                return conversation_id
    
    async def track_message(
        self,
        conversation_id: str,
        sender_type: str,  # 'user' o 'bot'
        content: str,
        intent: Optional[str] = None,
        entities: Optional[List[Dict]] = None,
        confidence: Optional[float] = None,
        tools_used: Optional[List[str]] = None,
        response_time_ms: Optional[int] = None
    ):
        """Registrar un mensaje en la conversación"""
        message_id = f"{conversation_id}_{uuid.uuid4().hex[:8]}"
        
        async with self.pool.acquire() as conn:
            try:
                # Insertar mensaje
                await conn.execute("""
                    INSERT INTO conversation_messages (
                        conversation_id, message_id, sender_type, content,
                        intent, entities, confidence, response_time_ms, tools_used
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, conversation_id, message_id, sender_type, content[:1000],  # Limitar contenido
                    intent, json.dumps(entities or []), confidence,
                    response_time_ms, json.dumps(tools_used or []))
                
                # Actualizar contadores en la conversación
                if sender_type == 'user':
                    update_col = 'user_messages_count'
                else:
                    update_col = 'bot_messages_count'
                
                await conn.execute(f"""
                    UPDATE conversations 
                    SET messages_count = messages_count + 1,
                        {update_col} = {update_col} + 1,
                        updated_at = NOW()
                    WHERE conversation_id = $1
                """, conversation_id)
                
                # Actualizar cache
                if conversation_id in self.active_conversations:
                    if response_time_ms:
                        self.active_conversations[conversation_id]['message_times'].append(response_time_ms)
                
            except Exception as e:
                logger.error(f"Error tracking mensaje: {e}")
    
    async def end_conversation(
        self,
        conversation_id: str,
        status: str = 'ended',  # 'ended' o 'abandoned'
        user_satisfaction: Optional[int] = None
    ):
        """Finalizar una conversación y calcular métricas finales"""
        async with self.pool.acquire() as conn:
            try:
                # Calcular tiempo promedio de respuesta
                avg_response_time = None
                if conversation_id in self.active_conversations:
                    times = self.active_conversations[conversation_id].get('message_times', [])
                    if times:
                        avg_response_time = sum(times) / len(times)
                
                await conn.execute("""
                    UPDATE conversations 
                    SET ended_at = NOW(),
                        status = $2,
                        user_satisfaction = $3,
                        avg_response_time_ms = $4,
                        updated_at = NOW()
                    WHERE conversation_id = $1
                """, conversation_id, status, user_satisfaction, avg_response_time)
                
                # Limpiar cache
                if conversation_id in self.active_conversations:
                    del self.active_conversations[conversation_id]
                
                logger.info(f"Conversación finalizada: {conversation_id}")
                
            except Exception as e:
                logger.error(f"Error finalizando conversación: {e}")
    
    async def track_tool_usage(
        self,
        tool_name: str,
        success: bool,
        execution_time_ms: int,
        error_message: Optional[str] = None
    ):
        """Registrar el uso de una herramienta MCP"""
        async with self.pool.acquire() as conn:
            try:
                today = datetime.now().date()
                
                await conn.execute("""
                    INSERT INTO tool_metrics (
                        date, tool_name, total_calls,
                        successful_calls, failed_calls,
                        avg_execution_time_ms, error_messages
                    ) VALUES ($1, $2, 1, $3, $4, $5, $6)
                    ON CONFLICT (date, tool_name) DO UPDATE
                    SET total_calls = tool_metrics.total_calls + 1,
                        successful_calls = tool_metrics.successful_calls + $3,
                        failed_calls = tool_metrics.failed_calls + $4,
                        avg_execution_time_ms = (
                            tool_metrics.avg_execution_time_ms * tool_metrics.total_calls + $5
                        ) / (tool_metrics.total_calls + 1),
                        error_messages = CASE 
                            WHEN $6 IS NOT NULL THEN 
                                tool_metrics.error_messages || $6::jsonb
                            ELSE tool_metrics.error_messages 
                        END,
                        updated_at = NOW()
                """, today, tool_name, 
                    1 if success else 0,
                    0 if success else 1,
                    execution_time_ms,
                    json.dumps([error_message]) if error_message else None)
                
            except Exception as e:
                logger.error(f"Error tracking herramienta: {e}")
    
    async def track_topic(
        self,
        topic: str,
        category: str,
        query: str,
        resolution_time_minutes: Optional[float] = None,
        success: bool = True
    ):
        """Registrar un tema o consulta popular"""
        async with self.pool.acquire() as conn:
            try:
                today = datetime.now().date()
                
                await conn.execute("""
                    INSERT INTO popular_topics (
                        date, topic, category, count,
                        sample_queries, avg_resolution_time_minutes, success_rate
                    ) VALUES ($1, $2, $3, 1, $4, $5, $6)
                    ON CONFLICT (date, topic) DO UPDATE
                    SET count = popular_topics.count + 1,
                        sample_queries = 
                            CASE 
                                WHEN jsonb_array_length(popular_topics.sample_queries) < 5 
                                THEN popular_topics.sample_queries || $4::jsonb
                                ELSE popular_topics.sample_queries
                            END,
                        avg_resolution_time_minutes = 
                            CASE 
                                WHEN $5 IS NOT NULL THEN
                                    (COALESCE(popular_topics.avg_resolution_time_minutes, 0) * popular_topics.count + $5) / (popular_topics.count + 1)
                                ELSE popular_topics.avg_resolution_time_minutes
                            END,
                        success_rate = 
                            (COALESCE(popular_topics.success_rate, 0) * popular_topics.count + $6) / (popular_topics.count + 1),
                        updated_at = NOW()
                """, today, topic, category,
                    json.dumps([query[:200]]),  # Limitar longitud de query
                    resolution_time_minutes,
                    100.0 if success else 0.0)
                
            except Exception as e:
                logger.error(f"Error tracking topic: {e}")
    
    async def log_event(
        self,
        event_type: str,
        title: str,
        description: str = None,
        severity: str = 'info',
        platform: str = None,
        conversation_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Registrar un evento especial (error, hito, alerta)"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO metric_events (
                        event_type, severity, title, description,
                        platform, conversation_id, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, event_type, severity, title, description,
                    platform, conversation_id, json.dumps(metadata or {}))
                
                logger.info(f"Evento registrado: {event_type} - {title}")
                
            except Exception as e:
                logger.error(f"Error logging event: {e}")
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas para el dashboard"""
        async with self.pool.acquire() as conn:
            try:
                # Estadísticas del día (considerando las últimas 24 horas como "hoy")
                today_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as conversations_today,
                        COUNT(DISTINCT user_id) as unique_users_today,
                        AVG(messages_count) as avg_messages,
                        AVG(avg_response_time_ms) as avg_response_time
                    FROM conversations 
                    WHERE started_at >= NOW() - INTERVAL '24 hours'
                """)
                
                # Distribución por plataforma (todas las conversaciones, no solo hoy)
                platform_stats_all = await conn.fetch("""
                    SELECT platform, COUNT(*) as count
                    FROM conversations
                    GROUP BY platform
                """)
                
                # Distribución por plataforma del día (usando últimas 24 horas)
                platform_stats_today = await conn.fetch("""
                    SELECT platform, COUNT(*) as count
                    FROM conversations
                    WHERE started_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY platform
                """)
                
                # Temas populares del día (o todos si no hay del día)
                top_topics = await conn.fetch("""
                    SELECT topic, category, count
                    FROM popular_topics
                    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY date DESC, count DESC
                    LIMIT 5
                """)
                
                # Estadísticas de herramientas
                tool_stats = await conn.fetch("""
                    SELECT tool_name, total_calls, successful_calls, avg_execution_time_ms
                    FROM tool_metrics
                    WHERE date = CURRENT_DATE
                    ORDER BY total_calls DESC
                    LIMIT 5
                """)
                
                # Conversaciones por hora (últimas 24 horas)
                hourly_stats = await conn.fetch("""
                    SELECT 
                        date_trunc('hour', started_at) as hour,
                        COUNT(*) as count
                    FROM conversations
                    WHERE started_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY hour
                    ORDER BY hour
                """)
                
                # Contar todas las conversaciones activas (no solo de hoy)
                total_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_conversations,
                        COUNT(DISTINCT user_id) as total_users
                    FROM conversations
                    WHERE started_at >= NOW() - INTERVAL '30 days'
                """)
                
                return {
                    'today': {
                        'conversations': int(today_stats['conversations_today'] or 0),
                        'unique_users': int(today_stats['unique_users_today'] or 0),
                        'avg_messages': float(today_stats['avg_messages'] or 0),
                        'avg_response_time_ms': float(today_stats['avg_response_time'] or 0)
                    },
                    'total': {
                        'conversations': int(total_stats['total_conversations'] or 0),
                        'users': int(total_stats['total_users'] or 0)
                    },
                    'platforms': {
                        row['platform']: row['count'] 
                        for row in platform_stats_today
                    },
                    'platforms_all': {
                        row['platform']: row['count'] 
                        for row in platform_stats_all
                    },
                    'top_topics': [
                        {
                            'topic': row['topic'],
                            'category': row['category'],
                            'count': row['count']
                        }
                        for row in top_topics
                    ],
                    'tool_usage': [
                        {
                            'name': row['tool_name'],
                            'calls': row['total_calls'],
                            'success_rate': (row['successful_calls'] / row['total_calls'] * 100) if row['total_calls'] > 0 else 0,
                            'avg_time_ms': float(row['avg_execution_time_ms'] or 0)
                        }
                        for row in tool_stats
                    ],
                    'hourly_conversations': [
                        {
                            'hour': row['hour'].isoformat(),
                            'count': row['count']
                        }
                        for row in hourly_stats
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas: {e}")
                return self._get_empty_stats()
    
    async def get_conversation_details(
        self,
        limit: int = 20,
        offset: int = 0,
        platform: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Obtener detalles de conversaciones recientes"""
        async with self.pool.acquire() as conn:
            try:
                query = """
                    SELECT 
                        conversation_id,
                        user_id,
                        platform,
                        started_at,
                        ended_at,
                        status,
                        messages_count,
                        user_messages_count,
                        bot_messages_count,
                        avg_response_time_ms,
                        user_satisfaction,
                        channel_details
                    FROM conversations
                    WHERE 1=1
                """
                params = []
                param_num = 1
                
                if platform:
                    query += f" AND platform = ${param_num}"
                    params.append(platform)
                    param_num += 1
                
                if date_from:
                    query += f" AND started_at >= ${param_num}"
                    params.append(date_from)
                    param_num += 1
                
                if date_to:
                    query += f" AND started_at <= ${param_num}"
                    params.append(date_to)
                    param_num += 1
                
                query += f" ORDER BY started_at DESC LIMIT ${param_num} OFFSET ${param_num + 1}"
                params.extend([limit, offset])
                
                rows = await conn.fetch(query, *params)
                
                return [
                    {
                        'conversation_id': row['conversation_id'],
                        'user_id': row['user_id'],
                        'platform': row['platform'],
                        'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                        'ended_at': row['ended_at'].isoformat() if row['ended_at'] else None,
                        'duration_minutes': (
                            (row['ended_at'] - row['started_at']).total_seconds() / 60
                            if row['ended_at'] and row['started_at'] else None
                        ),
                        'status': row['status'],
                        'messages_count': row['messages_count'],
                        'user_messages': row['user_messages_count'],
                        'bot_messages': row['bot_messages_count'],
                        'avg_response_time_ms': float(row['avg_response_time_ms']) if row['avg_response_time_ms'] else None,
                        'satisfaction': row['user_satisfaction'],
                        'channel_details': json.loads(row['channel_details']) if row['channel_details'] else {}
                    }
                    for row in rows
                ]
                
            except Exception as e:
                logger.error(f"Error obteniendo detalles de conversaciones: {e}")
                return []
    
    async def cleanup_old_data(self):
        """Limpiar datos antiguos según la política de retención"""
        async with self.pool.acquire() as conn:
            try:
                # Ejecutar función de limpieza en la base de datos
                await conn.execute("SELECT cleanup_old_metrics_data()")
                
                # Agregar métricas horarias
                await conn.execute("SELECT aggregate_hourly_metrics()")
                
                # Agregar métricas diarias
                await conn.execute("SELECT aggregate_daily_metrics()")
                
                logger.info("Limpieza de datos antiguos completada")
                
            except Exception as e:
                logger.error(f"Error en limpieza de datos: {e}")
    
    def _get_empty_stats(self) -> Dict[str, Any]:
        """Retornar estadísticas vacías en caso de error"""
        return {
            'today': {
                'conversations': 0,
                'unique_users': 0,
                'avg_messages': 0,
                'avg_response_time_ms': 0
            },
            'platforms': {},
            'top_topics': [],
            'tool_usage': [],
            'hourly_conversations': []
        }
    
    async def start_cleanup_scheduler(self):
        """Iniciar el scheduler para limpieza automática"""
        while True:
            try:
                # Ejecutar limpieza cada 24 horas a las 3 AM
                now = datetime.now()
                next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                await self.cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Error en scheduler de limpieza: {e}")
                await asyncio.sleep(3600)  # Esperar 1 hora en caso de error