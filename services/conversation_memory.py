"""
Servicio de Memoria Conversacional Persistente
Extiende el conversation_logger para mantener contexto entre sesiones
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

from services.conversation_logger import conversation_logger
from services.embedding_service import embedding_service
from config.settings import settings

logger = logging.getLogger(__name__)

class ConversationMemoryService:
    """Servicio de memoria conversacional con persistencia y recuperación inteligente"""
    
    def __init__(self):
        self.conversation_logger = conversation_logger
        self.embedding_service = embedding_service
        self.enabled = True
        self.memory_cache = {}  # Cache en memoria para sesiones activas
        
    async def initialize(self):
        """Inicializar el servicio de memoria"""
        try:
            # Asegurarse de que el logger está inicializado
            if not self.conversation_logger.pool:
                await self.conversation_logger.initialize()
            
            # Crear tablas adicionales para memoria
            await self._create_memory_tables()
            logger.info("✅ Servicio de memoria conversacional inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando memoria conversacional: {e}")
            self.enabled = False
    
    async def _create_memory_tables(self):
        """Crear tablas adicionales para gestión de memoria"""
        pool = self.conversation_logger.pool
        if not pool:
            return
            
        async with pool.acquire() as conn:
            # Tabla de resúmenes de conversación
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    session_id VARCHAR(255),
                    summary TEXT NOT NULL,
                    key_topics TEXT[],
                    sentiment VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW(),
                    embedding vector(1536)
                );
            """)
            
            # Tabla de preferencias del usuario
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id VARCHAR(255) PRIMARY KEY,
                    preferences JSONB DEFAULT '{}',
                    interaction_count INTEGER DEFAULT 0,
                    last_interaction TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Índices
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_summaries_user_id 
                ON conversation_summaries(user_id);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_summaries_embedding 
                ON conversation_summaries USING ivfflat (embedding vector_l2_ops)
                WITH (lists = 100);
            """)
    
    async def save_conversation_memory(
        self, 
        session_id: str, 
        user_id: str,
        messages: List[Dict[str, str]]
    ) -> bool:
        """Guardar memoria de la conversación actual"""
        try:
            if not messages or len(messages) < 2:
                return True
            
            # Generar resumen de la conversación
            summary = await self._generate_conversation_summary(messages)
            if not summary:
                return False
            
            # Extraer temas clave
            key_topics = await self._extract_key_topics(messages)
            
            # Analizar sentimiento
            sentiment = await self._analyze_sentiment(messages)
            
            # Generar embedding del resumen
            embedding = await self.embedding_service.generate_embedding(summary)
            
            # Guardar en base de datos
            pool = self.conversation_logger.pool
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversation_summaries 
                    (user_id, session_id, summary, key_topics, sentiment, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, user_id, session_id, summary, key_topics, sentiment, embedding)
                
                # Actualizar contador de interacciones
                await conn.execute("""
                    INSERT INTO user_preferences (user_id, interaction_count)
                    VALUES ($1, 1)
                    ON CONFLICT (user_id) DO UPDATE SET
                        interaction_count = user_preferences.interaction_count + 1,
                        last_interaction = NOW(),
                        updated_at = NOW()
                """, user_id)
            
            logger.info(f"✅ Memoria guardada para sesión {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando memoria: {e}")
            return False
    
    async def retrieve_user_context(
        self, 
        user_id: str, 
        current_query: Optional[str] = None,
        limit: int = 3
    ) -> Dict[str, Any]:
        """Recuperar contexto relevante del usuario"""
        try:
            pool = self.conversation_logger.pool
            context = {
                "previous_interactions": [],
                "preferences": {},
                "interaction_count": 0,
                "relevant_summaries": []
            }
            
            async with pool.acquire() as conn:
                # Obtener preferencias del usuario
                prefs_row = await conn.fetchrow("""
                    SELECT * FROM user_preferences WHERE user_id = $1
                """, user_id)
                
                if prefs_row:
                    context["preferences"] = json.loads(prefs_row["preferences"])
                    context["interaction_count"] = prefs_row["interaction_count"]
                
                # Si hay una consulta actual, buscar conversaciones relevantes
                if current_query:
                    query_embedding = await self.embedding_service.generate_embedding(current_query)
                    if query_embedding:
                        # Búsqueda por similitud semántica
                        relevant_rows = await conn.fetch("""
                            SELECT session_id, summary, key_topics, sentiment,
                                   1 - (embedding <=> $1) as similarity
                            FROM conversation_summaries
                            WHERE user_id = $2 AND embedding IS NOT NULL
                            ORDER BY embedding <=> $1
                            LIMIT $3
                        """, query_embedding, user_id, limit)
                        
                        for row in relevant_rows:
                            if row["similarity"] > 0.7:  # Umbral de relevancia
                                context["relevant_summaries"].append({
                                    "session_id": row["session_id"],
                                    "summary": row["summary"],
                                    "topics": row["key_topics"],
                                    "sentiment": row["sentiment"],
                                    "relevance": float(row["similarity"])
                                })
                
                # Obtener últimas conversaciones
                recent_rows = await conn.fetch("""
                    SELECT session_id, summary, key_topics, created_at
                    FROM conversation_summaries
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, user_id, limit)
                
                for row in recent_rows:
                    context["previous_interactions"].append({
                        "session_id": row["session_id"],
                        "summary": row["summary"],
                        "topics": row["key_topics"],
                        "date": row["created_at"].isoformat()
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Error recuperando contexto: {e}")
            return {"previous_interactions": [], "preferences": {}, "interaction_count": 0}
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        new_preferences: Dict[str, Any]
    ) -> bool:
        """Actualizar preferencias del usuario basadas en la conversación"""
        try:
            pool = self.conversation_logger.pool
            async with pool.acquire() as conn:
                # Obtener preferencias actuales
                current = await conn.fetchrow("""
                    SELECT preferences FROM user_preferences WHERE user_id = $1
                """, user_id)
                
                if current:
                    existing_prefs = json.loads(current["preferences"])
                    # Mezclar con nuevas preferencias
                    existing_prefs.update(new_preferences)
                    final_prefs = existing_prefs
                else:
                    final_prefs = new_preferences
                
                # Actualizar en base de datos
                await conn.execute("""
                    INSERT INTO user_preferences (user_id, preferences)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET
                        preferences = $2,
                        updated_at = NOW()
                """, user_id, json.dumps(final_prefs))
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando preferencias: {e}")
            return False
    
    async def _generate_conversation_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generar un resumen conciso de la conversación"""
        # Por ahora, una implementación simple
        # En producción, esto usaría un LLM para generar resúmenes mejores
        topics = []
        for msg in messages:
            if msg.get("role") == "user":
                # Extraer primeras palabras clave
                words = msg["content"].lower().split()[:10]
                topics.extend([w for w in words if len(w) > 4])
        
        unique_topics = list(set(topics))[:5]
        summary = f"Conversación sobre: {', '.join(unique_topics)}"
        
        return summary
    
    async def _extract_key_topics(self, messages: List[Dict[str, str]]) -> List[str]:
        """Extraer temas clave de la conversación"""
        # Implementación simple, mejorar con NLP
        topics = set()
        keywords = ["pedido", "envío", "producto", "garantía", "precio", "stock", 
                   "instalación", "devolución", "factura", "descuento"]
        
        for msg in messages:
            content = msg.get("content", "").lower()
            for keyword in keywords:
                if keyword in content:
                    topics.add(keyword)
        
        return list(topics)
    
    async def _analyze_sentiment(self, messages: List[Dict[str, str]]) -> str:
        """Analizar el sentimiento general de la conversación"""
        # Implementación básica
        positive_words = ["gracias", "perfecto", "excelente", "genial", "bien"]
        negative_words = ["problema", "error", "mal", "no funciona", "queja"]
        
        positive_count = 0
        negative_count = 0
        
        for msg in messages:
            content = msg.get("content", "").lower()
            for word in positive_words:
                if word in content:
                    positive_count += 1
            for word in negative_words:
                if word in content:
                    negative_count += 1
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def get_conversation_prompt(self, context: Dict[str, Any]) -> str:
        """Generar prompt con contexto histórico para el LLM"""
        prompt_parts = []
        
        # Información del cliente
        if context["interaction_count"] > 0:
            prompt_parts.append(f"Este cliente ha interactuado {context['interaction_count']} veces antes.")
        
        # Preferencias conocidas
        if context["preferences"]:
            prefs_str = ", ".join([f"{k}: {v}" for k, v in context["preferences"].items()])
            prompt_parts.append(f"Preferencias conocidas: {prefs_str}")
        
        # Resúmenes relevantes
        if context["relevant_summaries"]:
            prompt_parts.append("Conversaciones anteriores relevantes:")
            for summary in context["relevant_summaries"][:2]:
                prompt_parts.append(f"- {summary['summary']}")
        
        # Interacciones recientes
        if context["previous_interactions"]:
            prompt_parts.append("Últimas interacciones:")
            for interaction in context["previous_interactions"][:2]:
                topics = ", ".join(interaction["topics"]) if interaction["topics"] else "general"
                prompt_parts.append(f"- {interaction['date'][:10]}: {topics}")
        
        if prompt_parts:
            return "CONTEXTO DEL CLIENTE:\n" + "\n".join(prompt_parts) + "\n"
        else:
            return ""

# Instancia global del servicio
memory_service = ConversationMemoryService()