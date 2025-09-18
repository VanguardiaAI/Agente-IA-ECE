#!/usr/bin/env python3
"""
EVA GPT-5 Agent - Sistema Multi-Agente Inteligente
Agente principal que orquesta todo el flujo de conversación usando GPT-5
"""

import asyncio
import json
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Cargar variables de entorno PRIMERO
load_dotenv()  # Carga .env
load_dotenv("env.agent")  # Carga env.agent

# Agentes especializados
from .gpt5_agents import (
    IntentClassifier,
    SearchAnalyzer,
    QueryGenerator,
    ResultsValidator,
    SearchRefiner,
    SynonymManager,
    ConversationState,
    SearchState,
    UserIntent
)

# Servicios del sistema
from services.database import HybridDatabaseService
from services.embedding_service import EmbeddingService
from services.conversation_logger import conversation_logger
from services.woocommerce import WooCommerceService
from services.knowledge_base import knowledge_service
from services.conversation_memory import memory_service
from services.bot_config_service import bot_config_service
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity

# Utilidades
from src.utils.whatsapp_utils import format_escalation_message
from src.utils.whatsapp_product_formatter import format_products_for_whatsapp
from src.agent.escalation_detector import escalation_detector

logger = logging.getLogger(__name__)


class EvaGPT5Agent:
    """
    Agente principal EVA con GPT-5
    Orquesta todos los agentes especializados sin lógica mecánica
    """
    
    def __init__(self):
        # Cliente GPT-5 principal
        self.gpt5 = GPT5Client()
        self.model = "gpt-5"  # USAR GPT-5 SIEMPRE
        
        # Agentes especializados
        self.intent_classifier = IntentClassifier()
        self.search_analyzer = SearchAnalyzer()
        self.query_generator = QueryGenerator()
        self.results_validator = ResultsValidator()
        self.search_refiner = SearchRefiner()
        self.synonym_manager = SynonymManager()
        
        # Servicios - crear instancias nuevas
        self.db_service = HybridDatabaseService()
        self.embedding_service = EmbeddingService()
        self.conversation_logger = conversation_logger
        self.wc_service = None
        self.knowledge_service = knowledge_service
        self.memory_service = memory_service
        
        # Cliente MCP para herramientas
        self.mcp_client = None
        self.mcp_tools = None
        
        # Estados de conversación activos
        self.conversations: Dict[str, ConversationState] = {}
        
        # Configuración
        self.bot_name = "Eva"
        self.company_name = "El Corte Eléctrico"
        self.welcome_message = "Hola, ¿en qué puedo ayudarte hoy?"
        self.max_search_attempts = 1  # Solo un intento para búsquedas rápidas
        
        # Información de contacto y empresa para respuestas rápidas
        self.contact_info = """
INFORMACIÓN DE LA EMPRESA - EL CORTE ELÉCTRICO SOLUCIONES, S.L.:

SOBRE NOSOTROS:
- Especialistas en componentes eléctricos industriales y domésticos
- Más de 4,000 productos de marcas certificadas
- Envíos a toda España y Europa
- Asesoramiento técnico especializado

CONTACTO (Tienda EXCLUSIVAMENTE ONLINE):
- Web: https://elcorteelectrico.com
- Email: ventas@elcorteelectrico.com
- Teléfono: +34 614 21 81 22
- Consultas técnicas especializadas: +34 661 239 969
- Devoluciones: https://elcorteelectrico.com/devoluciones/

IMPORTANTE: NO tenemos tienda física. Calle Laguna de Marquesado 47 es solo oficinas/almacén.

MARCAS PRINCIPALES:
- Protección: Mersen, Cirprotec
- Automatización: B.E.G., Dinuy
- Iluminación: Jung, Normalux, Polylux
- Ventilación: Soler y Palau S&P
- Calefacción: Elnur Gabarrón
- SAI/UPS: Salicru
- Material eléctrico: Tekox, Saci, Cellpack

SERVICIOS:
- Envíos: Toda España y Europa (Nacex/DHL, seguro incluido)
- Tiempo entrega: Según disponibilidad (hasta 4-5 días)
- Métodos de pago: Transferencia, Tarjeta, Bizum, PayPal
- NO aceptamos contrareembolso

REDES SOCIALES:
- Facebook: https://www.facebook.com/people/El-Corte-Eléctrico/61552544680168/
- Instagram: @corte.electrico
- LinkedIn: https://www.linkedin.com/in/el-corte-electrico-ecommerce-ba60a5282

NOTA IMPORTANTE: Para información detallada sobre políticas de garantía, devoluciones, envíos, y FAQs técnicos, 
debo consultar la base de conocimiento para darte información precisa y actualizada.
"""
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Inicializa el agente y sus servicios"""
        self.logger.info("🚀 Inicializando EVA GPT-5 Agent...")
        
        try:
            # Cargar configuración del bot
            await self._load_bot_configuration()
            
            # Inicializar servicios base
            if not self.db_service.initialized:
                await self.db_service.initialize()
                
            if not self.embedding_service.initialized:
                await self.embedding_service.initialize()
                
            # Inicializar WooCommerce
            self.wc_service = WooCommerceService()
            
            # Cargar sinónimos
            self.synonym_manager.load_synonyms()
            
            # Inicializar cliente MCP
            await self._initialize_mcp_client()
            
            self.logger.info("✅ EVA GPT-5 Agent inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error inicializando EVA GPT-5 Agent: {e}")
            raise
            
    async def _load_bot_configuration(self):
        """Carga la configuración del bot"""
        try:
            self.bot_name = await bot_config_service.get_setting("bot_name", "Eva")
            self.company_name = await bot_config_service.get_setting("company_name", "El Corte Eléctrico")
            self.welcome_message = await bot_config_service.get_setting("welcome_message", self.welcome_message)
            self.logger.info(f"✅ Configuración cargada - Bot: {self.bot_name}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error cargando configuración: {e}")
            
    async def _initialize_mcp_client(self):
        """Inicializa el cliente MCP para usar las herramientas"""
        try:
            # Por ahora deshabilitamos MCP ya que no es crítico
            # TODO: Actualizar cuando tengamos la versión correcta de MultiServerMCPClient
            self.mcp_client = None
            self.mcp_tools = None
            self.logger.info("⚠️ Cliente MCP deshabilitado temporalmente")
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando cliente MCP: {e}")
            self.mcp_client = None
            self.mcp_tools = None
            
    async def process_message(
        self,
        message: str,
        user_id: str = "default",
        platform: str = "wordpress",
        session_id: Optional[str] = None
    ) -> str:
        """
        Procesa un mensaje del usuario usando el sistema multi-agente
        
        Args:
            message: Mensaje del usuario
            user_id: ID del usuario
            platform: Plataforma de origen
            session_id: ID de sesión (opcional)
            
        Returns:
            Respuesta formateada para el usuario
        """
        
        start_time = datetime.now()
        
        # Generar session_id si no se proporciona
        if not session_id:
            session_id = f"{user_id}_{int(start_time.timestamp())}"
        
        # No hacer corrección manual - dejar que la IA maneje errores ortográficos
            
        self.logger.info(f"👤 Usuario ({user_id}) [{platform}]: {message}")
        
        # Obtener o crear estado de conversación
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationState(
                session_id=session_id,
                user_id=user_id,
                platform=platform
            )
        
        conversation = self.conversations[session_id]
        conversation.add_message("user", message)
        
        try:
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
            
            # PASO 1: Clasificar intención
            # SIEMPRE usar IA para clasificar - no usar lógica mecánica
            intent_result = await self.intent_classifier.classify_intent(
                message,
                conversation.get_recent_messages()
            )
            
            conversation.current_intent = intent_result.intent
            conversation.intent_confidence = intent_result.confidence
            
            self.logger.info(
                f"📌 Intención: {intent_result.intent.value} "
                f"(confianza: {intent_result.confidence:.2f})"
            )
            
            # PASO 2: Procesar según intención
            if intent_result.intent == UserIntent.PRODUCT_SEARCH:
                response = await self._handle_product_search(
                    message, conversation, platform
                )
                
            elif intent_result.intent == UserIntent.TECHNICAL_INFO:
                response = await self._handle_technical_info(
                    message, conversation, platform
                )
                
            elif intent_result.intent == UserIntent.ORDER_INQUIRY:
                response = await self._handle_order_inquiry(
                    message, conversation, intent_result.entities, platform
                )
                
            elif intent_result.intent == UserIntent.GREETING:
                response = await self._handle_greeting(conversation, platform)
                
            else:
                response = await self._handle_general_question(
                    message, conversation, platform
                )
            
            # Registrar respuesta
            conversation.add_message("assistant", response)
            
            # Guardar en memoria si está habilitada
            # TODO: Reactivar cuando memory_service esté actualizado
            # try:
            #     await memory_service.save_conversation_turn(
            #         user_id=user_id,
            #         user_message=message,
            #         assistant_response=response,
            #         metadata={
            #             "intent": intent_result.intent.value,
            #             "confidence": intent_result.confidence,
            #             "platform": platform
            #         }
            #     )
            # except Exception as e:
            #     self.logger.warning(f"Error guardando en memoria: {e}")
            
            # Log de métricas
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"✅ Respuesta generada en {duration:.2f}s | "
                f"Intent: {intent_result.intent.value} | "
                f"Turnos: {conversation.turn_count}"
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error procesando mensaje: {e}", exc_info=True)
            
            # Log más detallado del error
            self.logger.error(f"Sesión: {session_id}")
            self.logger.error(f"Usuario: {user_id}")
            self.logger.error(f"Mensaje: {message}")
            if conversation:
                self.logger.error(f"Estado conversación: {conversation.search_state}")
                self.logger.error(f"Turnos: {conversation.turn_count}")
            
            error_response = (
                f"Lo siento, tuve un problema procesando tu solicitud. "
                f"¿Podrías reformular tu pregunta?"
            )
            
            conversation.add_message("assistant", error_response, {"error": str(e)})
            return error_response
            
    async def _handle_product_search(
        self,
        message: str,
        conversation: ConversationState,
        platform: str
    ) -> str:
        """
        Maneja búsquedas de productos con el flujo inteligente completo
        """
        
        # IMPORTANTE: Verificar si es una respuesta a una clarificación anterior
        if conversation.search_state == SearchState.NEEDS_INFO and conversation.search_context:
            # Es una respuesta a nuestra pregunta de clarificación
            self.logger.info("📝 Procesando respuesta a clarificación")
            
            # Combinar la información anterior con la nueva
            search_context = conversation.search_context
            previous_query = search_context.original_query
            combined_query = f"{previous_query} {message}"
            
            # Actualizar el contexto con la información combinada
            search_context.original_query = combined_query
            search_context.has_clarified = True
            search_context.clarification_count += 1
            
            # IMPORTANTE: Después de 1 clarificación, mostrar resultados siempre
            if search_context.clarification_count >= 1:
                self.logger.info("⚠️ Ya se pidió clarificación - mostrando resultados disponibles")
                search_context.missing_info = []  # Limpiar para forzar mostrar resultados
            
            # Resetear intentos de búsqueda para permitir nueva búsqueda
            search_context.search_attempts = []
            
            # Proceder directamente a búsqueda
            conversation.update_search_state(SearchState.SEARCHING)
            
        else:
            # Es una nueva búsqueda
            search_context = conversation.create_search_context(message)
            search_context.original_query = message
            conversation.update_search_state(SearchState.ANALYZING)
        
        # PASO 1: Analizar la búsqueda (solo si no es respuesta a clarificación)
        if conversation.search_state != SearchState.SEARCHING:
            self.logger.info("🔍 Analizando búsqueda de productos...")
            analysis = await self.search_analyzer.analyze_search(
                search_context.original_query,  # Usar query combinada si es respuesta
                conversation.get_recent_messages()
            )
            
            # Guardar información extraída
            search_context.extracted_info = {
                "product_type": analysis.product_type,
                "brand": analysis.brand,
                "specs": analysis.technical_specs,
                "has_enough_info": analysis.has_enough_info
            }
            # IMPORTANTE: Guardar missing_info para _handle_no_results
            if hasattr(analysis, 'missing_info') and analysis.missing_info:
                search_context.missing_info = analysis.missing_info
        else:
            # Si ya estamos buscando (respuesta a clarificación), crear análisis simple
            from dataclasses import dataclass
            @dataclass
            class SimpleAnalysis:
                product_type: str = ""
                brand: str = ""
                technical_specs: dict = None
                has_enough_info: bool = True
                clarification_needed: bool = False
                missing_info: list = None
            
            analysis = SimpleAnalysis(
                product_type=search_context.extracted_info.get("product_type", ""),
                has_enough_info=True  # Ya tenemos la info que pedimos
            )
        
        # Confiar en la IA - si dice que tiene suficiente info, proceder
        # No usar lógica mecánica para forzar clarificaciones
        if analysis.has_enough_info:
            self.logger.info("✅ La IA dice que tiene suficiente información - procediendo con búsqueda")
        else:
            self.logger.info("⚠️ La IA dice que falta información pero procederemos de todos modos")
            
        # PASO 2: Generar queries de búsqueda
        conversation.update_search_state(SearchState.SEARCHING)
        
        # Intentar búsqueda hasta max_attempts
        # REMOVIDO: Esta condición era redundante y bloqueaba búsquedas válidas
        # La IA ya determinó si puede buscar o no
        
        while search_context.can_retry(self.max_search_attempts):
            self.logger.info(
                f"🔎 Intento de búsqueda {len(search_context.search_attempts) + 1}/"
                f"{self.max_search_attempts}"
            )
            
            # Generar queries
            if len(search_context.search_attempts) == 0:
                # Primera búsqueda
                # Usar la query combinada si es una respuesta a clarificación
                query_to_use = search_context.original_query if search_context.has_clarified else message
                self.logger.info(f"🔎 Generando queries para: '{query_to_use}'")
                queries = await self.query_generator.generate_queries(
                    query_to_use,
                    search_context.extracted_info,
                    analysis.product_type
                )
                self.logger.info(f"📝 Query principal generada: '{queries.primary_query}'")
            else:
                # Búsquedas refinadas
                queries = await self.query_generator.optimize_for_retry(
                    [a["query"] for a in search_context.search_attempts],
                    search_context.refinement_feedback[-1] if search_context.refinement_feedback else "",
                    search_context.extracted_info
                )
            
            # Ejecutar búsqueda
            search_results = await self._execute_product_search(queries)
            
            # PASO 3: Validar resultados
            conversation.update_search_state(SearchState.VALIDATING)
            
            # DETECCIÓN INTELIGENTE DE BÚSQUEDAS GENERALES
            # 1. Contar resultados que son categorías vs productos
            category_results = [r for r in search_results if r.get('content_type') == 'category']
            product_results = [r for r in search_results if r.get('content_type') == 'product']
            
            # 2. Verificar si todos tienen el mismo score (señal de búsqueda general)
            scores = [r.get('score', r.get('rrf_score', 0)) for r in search_results[:10]]
            all_same_score = len(set(scores)) == 1 and len(scores) > 5
            
            # 3. Detectar si hay categorías con muchos productos
            has_large_categories = False
            for r in category_results:
                content = str(r.get('content', '')).lower()
                # Buscar patrones como "número de productos: X" o "X productos"
                import re
                match = re.search(r'(\d+)\s*producto', content)
                if match:
                    num_products = int(match.group(1))
                    if num_products >= 50:
                        has_large_categories = True
                        self.logger.info(f"📊 Categoría con {num_products} productos detectada")
                        break
            
            # SI: hay categorías grandes, todos tienen mismo score, y no especificó detalles
            # ENTONCES: es una búsqueda muy general
            is_too_general = (
                (len(category_results) >= 1 or len(product_results) >= 10) and 
                all_same_score and
                (has_large_categories or len(product_results) >= 15) and
                len(message.split()) <= 5  # Mensaje muy corto, probablemente sin especificaciones
            )
            
            if is_too_general and not search_context.has_clarified:
                # Necesita clarificación - la IA generará una pregunta específica
                self.logger.info("🎯 Detectada búsqueda muy general - solicitando clarificación")
                
                from dataclasses import dataclass
                @dataclass
                class GeneralSearchValidation:
                    is_valid: bool = False
                    relevance_score: float = 0.3
                    result_quality: str = "too_general"
                    issues: list = None
                    suggestions: list = None
                    best_matches: list = None
                    needs_refinement: bool = True
                    refinement_reason: str = "Búsqueda muy general con cientos de productos posibles"
                
                validation = GeneralSearchValidation()
                search_context.needs_clarification_for_general = True
                
            elif len(search_results) >= 1:
                # Proceder normal - no es demasiado general
                from dataclasses import dataclass
                @dataclass
                class QuickValidation:
                    is_valid: bool = True
                    relevance_score: float = 0.9
                    result_quality: str = "good"
                    issues: list = None
                    suggestions: list = None
                    best_matches: list = None
                    needs_refinement: bool = False
                    refinement_reason: str = None
                
                validation = QuickValidation(
                    best_matches=list(range(min(8, len(search_results))))
                )
                self.logger.info(f"✅ Búsqueda específica con {len(search_results)} resultados")
            else:
                # Validación completa solo si es necesario
                validation = await self.results_validator.validate_results(
                    message,
                    search_results,
                    search_context.extracted_info
                )
            
            # Registrar intento
            search_context.add_attempt(
                queries.primary_query,
                search_results,
                validation.is_valid,
                validation.refinement_reason or ""
            )
            
            # Si los resultados son buenos, devolver
            # CAMBIO: Aceptar también resultados "acceptable" si tenemos productos con buen score
            if validation.is_valid or (validation.result_quality in ["excellent", "good", "acceptable"] and len(search_results) > 0):
                conversation.update_search_state(SearchState.COMPLETED)
                
                # Seleccionar mejores resultados
                # Si validation.best_matches solo tiene pocos índices, expandir a más productos relevantes
                if len(validation.best_matches) < 5 and len(search_results) > 3:
                    # Tomar los mejores según validation + más productos con buen score
                    best_indices = set(validation.best_matches)
                    
                    # Añadir más productos con score alto
                    for i, result in enumerate(search_results[:10]):
                        if i not in best_indices and result.get('rrf_score', result.get('score', 0)) > 0.5:
                            best_indices.add(i)
                            if len(best_indices) >= 6:  # Mostrar hasta 6 productos
                                break
                    
                    best_results = [
                        search_results[i] for i in sorted(best_indices)
                        if i < len(search_results)
                    ][:10]
                else:
                    # Usar los índices de validation
                    best_results = [
                        search_results[i] for i in validation.best_matches
                        if i < len(search_results)
                    ][:10]  # Mostrar hasta 10 productos
                
                return await self._format_product_results(
                    best_results,
                    platform,
                    search_context
                )
            
            # PASO 4: Manejar búsquedas muy generales
            # Solo pedir clarificación si no hemos alcanzado el límite
            if validation.result_quality == "too_general" and not search_context.has_clarified and search_context.clarification_count < 1:
                # Es una búsqueda muy general - pedir clarificación específica
                conversation.update_search_state(SearchState.NEEDS_INFO)
                # NO marcar has_clarified aquí - se marca cuando el usuario responde
                
                # Usar la IA para generar una pregunta inteligente basada en los resultados
                clarification_prompt = f"""CONTEXTO: Somos El Corte Eléctrico, tienda de material eléctrico.

El usuario busca: "{message}"

Encontré {len(category_results)} categorías con cientos de productos y {len(product_results)} productos diferentes.

IMPORTANTE: 
- Si busca "automático" = interruptor magnetotérmico (protección eléctrica)
- Si busca "diferencial" = interruptor diferencial (protección contra fugas)
- SIEMPRE asume contexto de material eléctrico

Genera una pregunta breve y natural para ayudar a especificar qué tipo/características necesita."""
                
                clarification_response = await self.gpt5.create_response(
                    input_text=clarification_prompt,
                    model="gpt-5-mini",
                    reasoning_effort=ReasoningEffort.LOW,
                    verbosity=Verbosity.LOW,
                    max_completion_tokens=200
                )
                
                return clarification_response.content
                
            # PASO 5: Refinar si es necesario (pero no para búsquedas generales)
            elif validation.needs_refinement and search_context.can_retry() and validation.result_quality != "too_general":
                conversation.update_search_state(SearchState.REFINING)
                
                # Analizar qué tipo de refinamiento necesita
                refinement_analysis = await self.results_validator.analyze_refinement_needs(
                    validation,
                    search_context.search_attempts
                )
                
                # Refinar búsqueda
                refinement = await self.search_refiner.refine_search(
                    message,
                    search_context.extracted_info,
                    refinement_analysis,
                    search_context.search_attempts
                )
                
                # Guardar feedback para próxima iteración
                search_context.refinement_feedback.append(refinement.reasoning)
                
                self.logger.info(f"🔄 Refinando búsqueda: {refinement.new_approach}")
                
            else:
                # No se puede refinar más o ya tenemos buenos resultados
                break
        
        # Si llegamos aquí, no encontramos buenos resultados
        conversation.update_search_state(SearchState.FAILED)
        
        return await self._handle_no_results(
            message,
            search_context,
            platform
        )
        
    async def _execute_product_search(self, queries) -> List[Dict[str, Any]]:
        """Ejecuta búsqueda de productos usando las queries generadas"""
        
        all_results = []
        seen_ids = set()
        
        # Usar la query principal directamente sin procesamiento adicional
        # El QueryGenerator ya debería haber limpiado la query apropiadamente
        if queries.primary_query:
            self.logger.info(f"🔍 Búsqueda principal: '{queries.primary_query}'")
            results = await self._search_products(queries.primary_query)
            for r in results:
                if r.get('id') not in seen_ids:
                    all_results.append(r)
                    seen_ids.add(r.get('id'))
        
        # Si no hay suficientes resultados, intentar alternativas
        if len(all_results) < 5:
            for alt_query in queries.alternative_queries[:2]:
                if alt_query:
                    results = await self._search_products(alt_query)
                    for r in results:
                        if r.get('id') not in seen_ids:
                            all_results.append(r)
                            seen_ids.add(r.get('id'))
                            
                    if len(all_results) >= 10:
                        break
        
        return all_results[:20]  # Máximo 20 resultados
        
    async def _search_products(self, query: str) -> List[Dict[str, Any]]:
        """Ejecuta búsqueda usando las herramientas MCP"""
        
        try:
            if self.mcp_tools and 'search_products' in self.mcp_tools:
                # Usar herramienta MCP
                result = await self.mcp_tools['search_products'](
                    query=query,
                    limit=10,
                    use_hybrid=True
                )
                
                # Parsear resultado si es string
                if isinstance(result, str):
                    # Extraer productos del formato de texto
                    products = []
                    lines = result.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith('✨'):
                            # Parsear línea de producto
                            # Formato esperado: "1. Título - €XX.XX - ✓ En stock"
                            import re
                            match = re.match(r'^\d+\.\s+(.+?)\s+-\s+€([\d.]+)\s+-\s+(.+)$', line)
                            if match:
                                products.append({
                                    'title': match.group(1),
                                    'metadata': {
                                        'price': float(match.group(2)),
                                        'stock_status': 'instock' if '✓' in match.group(3) else 'outofstock'
                                    }
                                })
                    return products
                else:
                    return result
                    
            else:
                # Fallback: búsqueda SOLO DE TEXTO en base de datos
                # NO USAR EMBEDDINGS NI BÚSQUEDA HÍBRIDA
                self.logger.info(f"🔍 Usando búsqueda de SOLO TEXTO para: '{query}'")
                results = await self.db_service.text_search(
                    query_text=query,
                    content_types=['product'],
                    limit=15  # Más resultados para compensar
                )
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {e}")
            return []
            
    async def _format_product_results(
        self,
        products: List[Dict[str, Any]],
        platform: str,
        search_context: Any
    ) -> str:
        """Formatea los resultados de productos para el usuario"""
        
        if platform == "whatsapp":
            return format_products_for_whatsapp(products)
        else:
            # Formato HTML para web/wordpress
            from src.utils.wordpress_utils import format_product_search_response
            
            # Convertir productos al formato esperado por wordpress_utils
            wp_products = []
            for product in products:
                metadata = product.get('metadata', {})
                
                # Asegurar que las imágenes estén en el formato correcto
                images = metadata.get('images', [])
                if images and isinstance(images[0], str):
                    # Convertir URLs simples a formato dict
                    images = [{'src': img} for img in images if img]
                elif not images:
                    images = []
                    
                wp_product = {
                    'name': product.get('title', 'Producto'),
                    'price': str(metadata.get('price', 0)),
                    'regular_price': str(metadata.get('regular_price', metadata.get('price', 0))),
                    'sale_price': str(metadata.get('sale_price', '')),
                    'stock_status': metadata.get('stock_status', 'unknown'),
                    'permalink': metadata.get('permalink', ''),
                    'sku': metadata.get('sku', ''),
                    'images': images,
                    'relevance_score': product.get('rrf_score', product.get('score', 0))  # Para ordenar por relevancia
                }
                wp_products.append(wp_product)
                
            if wp_products:
                # Usar el formato HTML bonito
                return format_product_search_response(
                    wp_products, 
                    search_context.original_query if hasattr(search_context, 'original_query') else "tu búsqueda"
                )
            else:
                return "<p>Lo siento, encontré productos pero hubo un error al procesarlos.</p>"
            
    async def _handle_no_results(
        self,
        query: str,
        search_context: Any,
        platform: str
    ) -> str:
        """Maneja el caso cuando no se encuentran resultados satisfactorios"""
        
        # Si es porque falta información, generar pregunta de clarificación directa
        if search_context.missing_info and not search_context.has_clarified:
            # Usar el search_refiner para generar una pregunta natural
            clarification = await self.search_refiner.generate_user_clarification(
                search_context.extracted_info,
                search_context.missing_info
            )
            return clarification
        
        # Si ya clarificamos pero no hay resultados
        attempts_summary = []
        for attempt in search_context.search_attempts:
            attempts_summary.append(f"- {attempt['query']}: {attempt['results_count']} resultados")
        
        response = (
            f"Lo siento, no pude encontrar exactamente lo que buscas.\n\n"
        )
        
        if search_context.missing_info:
            response += (
                f"Para ayudarte mejor, necesitaría saber: "
                f"{', '.join(search_context.missing_info)}.\n\n"
            )
        
        response += "¿Podrías darme más detalles sobre lo que necesitas?"
        
        return response
        
    async def _handle_technical_info(
        self,
        message: str,
        conversation: ConversationState,
        platform: str
    ) -> str:
        """Maneja consultas técnicas sobre productos"""
        
        try:
            # Verificar si es sobre productos mostrados recientemente
            recent_messages = conversation.get_recent_messages()
            
            # Buscar si hay productos en el contexto reciente
            products_info = []
            products_context = None
            
            for msg in reversed(recent_messages[-3:]):
                if msg.get('role') == 'assistant' and 'eva-product-card' in msg.get('content', ''):
                    products_context = msg.get('content', '')
                    # Extraer información de productos del HTML
                    import re
                    
                    # Extraer títulos de productos (usan h3, no h5)
                    titles = re.findall(r'<h3[^>]*>([^<]+)</h3>', products_context)
                    
                    # Extraer precios (buscar el span con el precio final)
                    prices = re.findall(r'€(\d+(?:\.\d+)?)', products_context)
                    
                    # Extraer permalinks para más información
                    permalinks = re.findall(r'href="([^"]+)"[^>]*class="eva-product-link"', products_context)
                    
                    # Combinar información
                    for i in range(len(titles)):
                        product_info = {
                            'title': titles[i] if i < len(titles) else '',
                            'price': f"€{prices[i]}" if i < len(prices) else '',
                            'url': permalinks[i] if i < len(permalinks) else ''
                        }
                        products_info.append(product_info)
                    
                    break
            
            # Si pide explicar diferencias de productos mostrados
            if products_info and any(keyword in message.lower() for keyword in ['diferencias', 'diferencia', 'comparar', 'mejor', 'cuál', 'recomienda']):
                # Preparar información de productos para el prompt
                products_text = "\n\n".join([
                    f"Producto {i+1}: {p['title']}\n"
                    f"Precio: {p['price']}"
                    for i, p in enumerate(products_info[:10])  # Máximo 10 productos
                ])
                
                # Usar GPT-5 para analizar y comparar productos
                prompt = f"""Eres un experto en material eléctrico. El usuario acaba de ver estos productos y pregunta: "{message}"

PRODUCTOS MOSTRADOS:
{products_text}

IMPORTANTE: Estos son productos de El Corte Eléctrico, tienda de material eléctrico.

Genera una respuesta útil y práctica que:
- Si pide diferencias: compara características técnicas principales
- Si pide recomendación: sugiere el más adecuado según el caso de uso
- Si pregunta cuál es mejor: analiza pros/contras de cada uno
- Mantén un tono profesional y conocedor

Responde de forma clara y concisa."""

                response = await self.gpt5.create_response(
                    input_text=prompt,
                    model="gpt-5-mini",
                    reasoning_effort=ReasoningEffort.LOW,
                    verbosity=Verbosity.MEDIUM,
                    max_completion_tokens=600
                )
                
                return response.content
            
            # Si no es sobre productos mostrados, buscar en knowledge base
            # Buscar información técnica
            results = await self.knowledge_service.search_knowledge(
                query=message,
                limit=3
            )
            
            if results:
                # Usar GPT-5 para generar respuesta basada en el conocimiento
                context = "\n\n".join([r.get('content', '') for r in results[:2]])
                
                prompt = f"""Basándote en esta información técnica, responde la pregunta del usuario.

Pregunta: {message}

Información disponible:
{context}

IMPORTANTE - NUNCA INVENTES PRODUCTOS:
- NO generes listados de productos con precios, SKUs o stock
- NO inventes especificaciones de productos específicos
- SI el usuario busca productos, indica que debe usar la búsqueda de productos
- SOLO proporciona información técnica general basada en el conocimiento disponible

Genera una respuesta clara, concisa y técnicamente correcta.
Si la información no es suficiente, indícalo honestamente."""

                response = await self.gpt5.create_response(
                    input_text=prompt,
                    model=self.model,
                    reasoning_effort=ReasoningEffort.LOW,
                    verbosity=Verbosity.MEDIUM,
                    max_completion_tokens=500
                )
                
                return response.content
                
            else:
                return (
                    "No encontré información técnica específica sobre eso en nuestra base de conocimiento. "
                    "¿Podrías ser más específico o preguntarme sobre otro aspecto técnico?"
                )
                
        except Exception as e:
            self.logger.error(f"Error buscando información técnica: {e}")
            return (
                "Disculpa, tuve un problema buscando esa información técnica. "
                "¿Podrías reformular tu pregunta?"
            )
            
    async def _handle_order_inquiry(
        self,
        message: str,
        conversation: ConversationState,
        entities: Dict[str, Any],
        platform: str
    ) -> str:
        """Maneja consultas sobre pedidos"""
        
        try:
            # Extraer información del pedido
            order_info = await self.intent_classifier.extract_order_info(message)
            
            order_number = order_info.get('order_number') or entities.get('order_number')
            email = order_info.get('email')
            
            if not order_number:
                return (
                    "Para consultar tu pedido, necesito el número de pedido. "
                    "Por ejemplo: 'Mi pedido #1234' o 'Estado del pedido 1234'."
                )
            
            # Intentar obtener número limpio
            import re
            match = re.search(r'#?(\d+)', str(order_number))
            if match:
                order_id = int(match.group(1))
            else:
                return f"No pude identificar un número de pedido válido en '{order_number}'."
            
            # Usar herramienta MCP si está disponible
            if self.mcp_tools and 'get_order_with_validation' in self.mcp_tools:
                if not email:
                    return (
                        f"Para verificar tu pedido #{order_id}, necesito que me proporciones "
                        f"el email asociado a la compra por seguridad."
                    )
                
                result = await self.mcp_tools['get_order_with_validation'](
                    order_id=order_id,
                    customer_email=email
                )
                
                return result
                
            elif self.mcp_tools and 'get_order_status' in self.mcp_tools:
                # Sin validación de email
                result = await self.mcp_tools['get_order_status'](
                    order_id=order_id
                )
                
                return result
                
            else:
                return (
                    "Lo siento, no puedo acceder a la información de pedidos en este momento. "
                    "Por favor, contacta con atención al cliente."
                )
                
        except Exception as e:
            self.logger.error(f"Error consultando pedido: {e}")
            return (
                "Hubo un error al consultar tu pedido. "
                "Por favor, verifica el número e intenta nuevamente."
            )
            
    async def _handle_greeting(
        self,
        conversation: ConversationState,
        platform: str
    ) -> str:
        """Maneja saludos"""
        
        # Verificar si es primera interacción
        if conversation.turn_count <= 1:
            return self.welcome_message
        else:
            return "¡Hola de nuevo! ¿En qué puedo ayudarte?"
            
    async def _handle_general_question(
        self,
        message: str,
        conversation: ConversationState,
        platform: str
    ) -> str:
        """Maneja preguntas generales usando GPT-5"""
        
        # Usar GPT-5 para responder de forma inteligente
        context = f"""Eres {self.bot_name}, asistente virtual de {self.company_name}, 
una tienda de material eléctrico. Responde la siguiente pregunta de forma útil y profesional.

{self.contact_info}

Pregunta: {message}

IMPORTANTE: Si preguntan por contacto, ubicación, teléfono, email, redes sociales o tienda física, 
usa la información proporcionada arriba. NO inventes información."""

        try:
            response = await self.gpt5.create_response(
                input_text=context,
                model=self.model,
                reasoning_effort=ReasoningEffort.MEDIUM,
                verbosity=Verbosity.MEDIUM,
                max_completion_tokens=300
            )
            
            return response.content
            
        except:
            return (
                "Gracias por tu pregunta. Para información específica sobre horarios, "
                "envíos o políticas de la tienda, te recomiendo contactar directamente "
                "con nuestro servicio de atención al cliente."
            )
    


# Para compatibilidad con el sistema actual
hybrid_agent = EvaGPT5Agent()