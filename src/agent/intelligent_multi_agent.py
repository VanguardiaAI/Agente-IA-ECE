#!/usr/bin/env python3
"""
Sistema Multi-Agente Inteligente con GPT-5
Orquestador principal que coordina todos los agentes especializados
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Importar agentes especializados
from src.agent.agents.intent_classifier import intent_classifier, UserIntent, IntentClassification
from src.agent.agents.search_refiner import search_refiner, SearchRefinement
from src.agent.agents.query_optimizer import query_optimizer, OptimizedQuery
from src.agent.agents.results_validator import results_validator, ValidationResult
from src.agent.agents.response_formatter import response_formatter, FormattedResponse

# Servicios del sistema
from services.database import db_service
from services.embedding_service import embedding_service
from services.knowledge_base import knowledge_service
from services.conversation_memory import memory_service
from services.woocommerce import WooCommerceService
from services.bot_config_service import bot_config_service
from services.conversation_logger import conversation_logger

# Utilidades
from src.utils.whatsapp_utils import format_escalation_message
from src.agent.escalation_detector import escalation_detector

logger = logging.getLogger(__name__)


class SearchState(str, Enum):
    """Estados del proceso de búsqueda"""
    INITIAL = "initial"
    REFINING = "refining"
    SEARCHING = "searching"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConversationContext:
    """Contexto de conversación"""
    session_id: str
    user_id: str
    platform: str = "wordpress"
    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_intent: Optional[UserIntent] = None
    search_state: SearchState = SearchState.INITIAL
    search_attempts: int = 0
    previous_queries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchContext:
    """Contexto específico de búsqueda"""
    original_query: str
    refined_query: Optional[str] = None
    optimized_queries: List[str] = field(default_factory=list)
    extracted_specs: Dict[str, Any] = field(default_factory=dict)
    search_results: List[Dict] = field(default_factory=list)
    validation_results: Optional[ValidationResult] = None
    total_attempts: int = 0
    max_attempts: int = 3


class IntelligentMultiAgent:
    """Sistema Multi-Agente Inteligente"""
    
    def __init__(self):
        # Agentes
        self.intent_classifier = intent_classifier
        self.search_refiner = search_refiner
        self.query_optimizer = query_optimizer
        self.results_validator = results_validator
        self.response_formatter = response_formatter
        
        # Servicios
        self.db_service = db_service
        self.embedding_service = embedding_service
        self.knowledge_service = knowledge_service
        self.memory_service = memory_service
        self.wc_service = WooCommerceService()
        self.conversation_logger = conversation_logger
        
        # Configuración
        self.bot_name = "Eva"
        self.company_name = "El Corte Eléctrico"
        self.welcome_message = "Hola, ¿en qué puedo ayudarte hoy?"
        
        # Contextos activos
        self.active_contexts: Dict[str, ConversationContext] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Inicializa el sistema multi-agente"""
        self.logger.info("🚀 Inicializando Sistema Multi-Agente Inteligente...")
        
        # Cargar configuración del bot
        await self._load_bot_configuration()
        
        # Verificar servicios base
        if not self.db_service.initialized:
            await self.db_service.initialize()
        
        if not self.embedding_service.initialized:
            await self.embedding_service.initialize()
        
        self.logger.info("✅ Sistema Multi-Agente Inteligente inicializado")
    
    async def _load_bot_configuration(self):
        """Carga la configuración del bot"""
        try:
            self.bot_name = await bot_config_service.get_setting("bot_name", "Eva")
            self.company_name = await bot_config_service.get_setting("company_name", "El Corte Eléctrico")
            self.welcome_message = await bot_config_service.get_setting("welcome_message", self.welcome_message)
            self.logger.info(f"✅ Configuración cargada - Bot: {self.bot_name}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error cargando configuración: {e}")
    
    async def process_message(
        self,
        message: str,
        user_id: str = "default",
        platform: str = "wordpress"
    ) -> str:
        """
        Procesa un mensaje usando el sistema multi-agente
        
        Args:
            message: Mensaje del usuario
            user_id: ID del usuario
            platform: Plataforma (wordpress, whatsapp)
            
        Returns:
            Respuesta formateada
        """
        
        start_time = datetime.now()
        session_id = f"session_{user_id}_{int(start_time.timestamp())}"
        
        self.logger.info(f"👤 Usuario ({user_id}) [{platform}]: {message}")
        
        # Verificar escalamiento
        should_escalate, reason, suggested_msg = escalation_detector.should_escalate(
            message=message,
            session_id=session_id,
            previous_response=None
        )
        
        if should_escalate:
            self.logger.info(f"🔴 Escalamiento detectado: {reason}")
            return format_escalation_message(
                reason=reason,
                context={"suggested_message": suggested_msg},
                platform=platform
            )
        
        # Obtener o crear contexto
        context = self._get_or_create_context(session_id, user_id, platform)
        context.messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # 1. CLASIFICAR INTENCIÓN
            intent_result = await self.intent_classifier.classify_intent(
                message,
                {"history": context.messages[-5:]}  # Últimos 5 mensajes
            )
            
            context.current_intent = intent_result.intent
            self.logger.info(f"📌 Intent: {intent_result.intent.value} (confianza: {intent_result.confidence})")
            
            # 2. PROCESAR SEGÚN INTENCIÓN
            if intent_result.intent == UserIntent.PRODUCT_SEARCH:
                response = await self._handle_product_search(message, context, platform)
            
            elif intent_result.intent == UserIntent.TECHNICAL_INFO:
                response = await self._handle_technical_info(message, context, platform)
            
            elif intent_result.intent == UserIntent.ORDER_INQUIRY:
                response = await self._handle_order_inquiry(message, context, platform)
            
            elif intent_result.intent == UserIntent.GREETING:
                formatted = await self.response_formatter.format_response(
                    "greeting", None, platform
                )
                response = formatted.content
            
            else:  # GENERAL_SUPPORT
                response = await self._handle_general_support(message, context, platform)
            
            # Actualizar contexto
            context.messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat(),
                "intent": intent_result.intent.value
            })
            
            # Log conversación
            await self._log_conversation(
                session_id, user_id, message, response,
                intent_result.intent.value, start_time, platform
            )
            
            self.logger.info(f"🤖 {self.bot_name}: {response[:100]}...")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}", exc_info=True)
            return self._get_error_response(platform)
    
    async def _handle_product_search(
        self,
        message: str,
        context: ConversationContext,
        platform: str
    ) -> str:
        """Maneja búsquedas de productos con el flujo completo de agentes"""
        
        search_context = SearchContext(original_query=message)
        
        # LOOP DE BÚSQUEDA (máximo 3 intentos)
        while search_context.total_attempts < search_context.max_attempts:
            search_context.total_attempts += 1
            self.logger.info(f"🔄 Intento de búsqueda {search_context.total_attempts}/{search_context.max_attempts}")
            
            # 2.1 REFINAR BÚSQUEDA
            refinement = await self.search_refiner.refine_search(
                message,
                {
                    "previous_products": search_context.search_results[:5] if search_context.search_results else [],
                    "conversation_history": [m["content"] for m in context.messages[-3:]]
                }
            )
            
            search_context.refined_query = refinement.refined_query
            search_context.extracted_specs = refinement.extracted_specs
            
            # Si necesita clarificación, preguntar al usuario
            if not refinement.is_complete and search_context.total_attempts == 1:
                self.logger.info("❓ Búsqueda necesita clarificación")
                clarification_msg = self.search_refiner.generate_clarification_message(refinement)
                
                formatted = await self.response_formatter.format_response(
                    "product_search",
                    {"relevant_products": []},
                    platform,
                    {"user_query": message}
                )
                
                formatted = self.response_formatter.add_clarification_request(
                    formatted,
                    refinement.clarification_questions,
                    platform
                )
                
                return formatted.content
            
            # 2.2 OPTIMIZAR QUERY
            optimized = await self.query_optimizer.optimize_query(
                refinement.refined_query,
                refinement.extracted_specs,
                refinement.search_strategy,
                search_context.previous_queries
            )
            
            search_context.optimized_queries = [optimized.primary_query] + optimized.alternative_queries
            search_context.previous_queries.extend(search_context.optimized_queries)
            
            # 2.3 EJECUTAR BÚSQUEDA
            all_results = []
            for query in search_context.optimized_queries[:3]:  # Máximo 3 queries
                results = await self._execute_search(query, optimized.filters)
                all_results.extend(results)
            
            # Eliminar duplicados
            seen_ids = set()
            unique_results = []
            for result in all_results:
                result_id = result.get("id")
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
            
            search_context.search_results = unique_results
            self.logger.info(f"🔍 Encontrados {len(unique_results)} productos únicos")
            
            # 2.4 VALIDAR RESULTADOS
            validation = await self.results_validator.validate_results(
                message,
                unique_results,
                refinement.extracted_specs,
                search_context.total_attempts
            )
            
            search_context.validation_results = validation
            
            # Si los resultados son buenos, terminar
            if validation.are_results_good or search_context.total_attempts >= search_context.max_attempts:
                self.logger.info(f"✅ Búsqueda completada: relevancia={validation.relevance_score:.2f}")
                break
            
            # Si no son buenos, ajustar estrategia
            self.logger.info(f"🔄 Resultados no óptimos, reintentando con feedback: {validation.feedback}")
            
            # Ajustar el optimizador con feedback
            if validation.retry_suggestion:
                optimized = self.query_optimizer.combine_with_feedback(
                    optimized,
                    self.results_validator.generate_retry_feedback(validation)
                )
        
        # 2.5 FORMATEAR RESPUESTA FINAL
        formatted = await self.response_formatter.format_response(
            "product_search",
            search_context.validation_results,
            platform,
            {"user_query": message}
        )
        
        return formatted.content
    
    async def _handle_technical_info(
        self,
        message: str,
        context: ConversationContext,
        platform: str
    ) -> str:
        """Maneja consultas de información técnica"""
        
        # Buscar en knowledge base
        results = await self.knowledge_service.search(
            query=message,
            limit=3,
            content_type="technical"
        )
        
        if results:
            # Formatear información técnica encontrada
            technical_content = "\n\n".join([
                f"{r.get('title', '')}: {r.get('content', '')[:200]}..."
                for r in results
            ])
        else:
            technical_content = "No encontré información técnica específica sobre eso."
        
        formatted = await self.response_formatter.format_response(
            "technical_info",
            technical_content,
            platform
        )
        
        return formatted.content
    
    async def _handle_order_inquiry(
        self,
        message: str,
        context: ConversationContext,
        platform: str
    ) -> str:
        """Maneja consultas sobre pedidos"""
        
        # Buscar email en el mensaje
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, message)
        
        if email_match:
            email = email_match.group(0)
            # Buscar pedidos por email
            orders = await self.wc_service.get_customer_orders(email)
            
            if orders:
                order_info = f"Encontré {len(orders)} pedido(s) para {email}:\n\n"
                for order in orders[:3]:  # Máximo 3 pedidos
                    order_info += f"Pedido #{order['id']} - Estado: {order['status']}\n"
                response = order_info
            else:
                response = f"No encontré pedidos asociados a {email}."
        else:
            response = "Para consultar tu pedido, por favor proporciona tu email o número de pedido."
        
        formatted = await self.response_formatter.format_response(
            "order_inquiry",
            response,
            platform
        )
        
        return formatted.content
    
    async def _handle_general_support(
        self,
        message: str,
        context: ConversationContext,
        platform: str
    ) -> str:
        """Maneja consultas generales"""
        
        # Buscar en knowledge base general
        results = await self.knowledge_service.search(
            query=message,
            limit=3
        )
        
        if results:
            content = results[0].get("content", "Lo siento, no tengo información sobre eso.")
        else:
            content = "¿En qué más puedo ayudarte? Puedo buscar productos, responder preguntas técnicas o ayudarte con tu pedido."
        
        formatted = await self.response_formatter.format_response(
            "general_support",
            content,
            platform
        )
        
        return formatted.content
    
    async def _execute_search(
        self,
        query: str,
        filters: Dict[str, Any]
    ) -> List[Dict]:
        """Ejecuta búsqueda en la base de datos"""
        
        try:
            # Generar embedding
            embedding = await self.embedding_service.generate_embedding(query)
            
            # Búsqueda híbrida
            results = await self.db_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                content_types=["product"],
                limit=20
            )
            
            # Aplicar filtros adicionales si existen
            if filters and results:
                filtered_results = []
                for result in results:
                    metadata = result.get("metadata", {})
                    match = True
                    
                    # Verificar cada filtro
                    for key, value in filters.items():
                        if key == "amperaje" and value:
                            # Buscar en descripción o título
                            content = f"{result.get('title', '')} {metadata.get('short_description', '')}"
                            if value.lower() not in content.lower():
                                match = False
                                break
                    
                    if match:
                        filtered_results.append(result)
                
                return filtered_results
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {e}")
            return []
    
    async def _log_conversation(
        self,
        session_id: str,
        user_id: str,
        message: str,
        response: str,
        intent: str,
        start_time: datetime,
        platform: str
    ):
        """Registra la conversación"""
        try:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self.conversation_logger.log_message(
                session_id=session_id,
                user_id=user_id,
                message_type="conversation",
                content=f"User: {message}\nAssistant: {response}",
                metadata={
                    "intent": intent,
                    "platform": platform,
                    "response_time_ms": response_time_ms,
                    "agent_system": "intelligent_multi_agent"
                },
                strategy=intent,
                response_time_ms=response_time_ms
            )
        except Exception as e:
            self.logger.error(f"Error logging conversation: {e}")
    
    def _get_or_create_context(
        self,
        session_id: str,
        user_id: str,
        platform: str
    ) -> ConversationContext:
        """Obtiene o crea contexto de conversación"""
        if session_id not in self.active_contexts:
            self.active_contexts[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                platform=platform
            )
        return self.active_contexts[session_id]
    
    def _get_error_response(self, platform: str) -> str:
        """Respuesta de error según plataforma"""
        if platform == "whatsapp":
            return "❌ Lo siento, ha ocurrido un error. Por favor, intenta de nuevo."
        else:
            return "Lo siento, ha ocurrido un error procesando tu solicitud. Por favor, intenta de nuevo."
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de conversaciones"""
        return {
            "active_contexts": len(self.active_contexts),
            "system": "intelligent_multi_agent",
            "agents": {
                "intent_classifier": "active",
                "search_refiner": "active",
                "query_optimizer": "active",
                "results_validator": "active",
                "response_formatter": "active"
            },
            "model": "gpt-5",
            "status": "active"
        }