"""
🤖 Pipeline de Agentes Inteligentes para Eva
Orquestador principal que coordina los 5 agentes especializados
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    """Etapas del pipeline de procesamiento"""
    INTENT_CLASSIFICATION = "intent_classification"
    PRODUCT_UNDERSTANDING = "product_understanding" 
    SMART_SEARCH = "smart_search"
    RESULTS_VALIDATION = "results_validation"
    RESPONSE_GENERATION = "response_generation"
    COMPLETED = "completed"

@dataclass
class PipelineContext:
    """Contexto compartido entre todos los agentes del pipeline"""
    # Información de sesión
    session_id: str
    user_id: str
    platform: str = "whatsapp"
    
    # Mensaje original y procesado
    original_message: str = ""
    cleaned_message: str = ""
    
    # Clasificación de intención
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    intent_details: Dict[str, Any] = field(default_factory=dict)
    
    # Comprensión del producto
    search_query: Optional[str] = None
    product_type: Optional[str] = None
    brand: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    understanding_confidence: float = 0.0
    
    # Resultados de búsqueda
    raw_results: List[Dict] = field(default_factory=list)
    search_strategy: Optional[str] = None
    total_found: int = 0
    
    # Validación
    validated_products: List[Dict] = field(default_factory=list)
    needs_refinement: bool = False
    refinement_question: Optional[str] = None
    validation_score: float = 0.0
    
    # Respuesta final
    final_response: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)
    
    # Metadata de procesamiento
    stage: PipelineStage = PipelineStage.INTENT_CLASSIFICATION
    processing_time_ms: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    
    # Historia de refinamientos
    refinement_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_processing_time(self, stage: str, time_ms: int):
        """Registra el tiempo de procesamiento de una etapa"""
        self.processing_time_ms[stage] = time_ms
    
    def add_error(self, error: str):
        """Registra un error durante el procesamiento"""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
        logger.error(f"Pipeline error: {error}")
    
    def is_refinement_iteration(self) -> bool:
        """Verifica si estamos en una iteración de refinamiento"""
        return self.iteration_count > 0
    
    def can_iterate(self) -> bool:
        """Verifica si podemos hacer otra iteración"""
        return self.iteration_count < self.max_iterations

class AgentPipeline:
    """
    Orquestador principal del pipeline de agentes
    Coordina el flujo entre los 5 agentes especializados
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Los agentes se inicializarán lazy
        self._intent_classifier = None
        self._product_understander = None
        self._smart_searcher = None
        self._results_validator = None
        self._response_generator = None
        
        # Contextos activos por sesión
        self.active_contexts: Dict[str, PipelineContext] = {}
        
        self.logger.info("✅ Pipeline de agentes inicializado")
    
    async def _get_or_create_context(self, session_id: str, user_id: str, platform: str) -> PipelineContext:
        """Obtiene o crea un contexto de pipeline para la sesión"""
        if session_id not in self.active_contexts:
            self.active_contexts[session_id] = PipelineContext(
                session_id=session_id,
                user_id=user_id,
                platform=platform
            )
            self.logger.info(f"📝 Nuevo contexto creado para sesión {session_id}")
        return self.active_contexts[session_id]
    
    async def process_message(
        self, 
        message: str, 
        session_id: str,
        user_id: str = "default",
        platform: str = "whatsapp"
    ) -> str:
        """
        Procesa un mensaje a través del pipeline completo de agentes
        
        Args:
            message: Mensaje del usuario
            session_id: ID de la sesión para mantener contexto
            user_id: ID del usuario
            platform: Plataforma de origen
            
        Returns:
            Respuesta final generada por el pipeline
        """
        start_time = datetime.now()
        
        # Obtener o crear contexto
        context = await self._get_or_create_context(session_id, user_id, platform)
        context.original_message = message
        
        self.logger.info(f"🚀 Iniciando pipeline para: '{message}'")
        self.logger.info(f"   Sesión: {session_id}")
        self.logger.info(f"   Iteración: {context.iteration_count + 1}/{context.max_iterations}")
        
        try:
            # Ejecutar pipeline
            await self._execute_pipeline(context)
            
            # Calcular tiempo total
            total_time = int((datetime.now() - start_time).total_seconds() * 1000)
            context.add_processing_time("total", total_time)
            
            self.logger.info(f"✅ Pipeline completado en {total_time}ms")
            self.logger.info(f"   Etapas procesadas: {list(context.processing_time_ms.keys())}")
            
            return context.final_response or "Lo siento, no pude procesar tu solicitud."
            
        except Exception as e:
            error_msg = f"Error en pipeline: {str(e)}"
            context.add_error(error_msg)
            self.logger.error(error_msg, exc_info=True)
            return "Disculpa, tuve un problema procesando tu solicitud. ¿Podrías intentarlo de nuevo?"
    
    async def _execute_pipeline(self, context: PipelineContext):
        """Ejecuta las etapas del pipeline en secuencia"""
        
        # Etapa 1: Clasificación de Intención
        await self._stage_intent_classification(context)
        
        # Si es confirmación o saludo, saltar directo a respuesta
        if context.intent in ["confirmation", "greeting"]:
            context.stage = PipelineStage.RESPONSE_GENERATION
            await self._stage_response_generation(context)
            return
        
        # Etapa 2: Comprensión del Producto (solo si es búsqueda)
        if context.intent == "product_search":
            await self._stage_product_understanding(context)
            
            # Etapa 3: Búsqueda Inteligente
            await self._stage_smart_search(context)
            
            # Etapa 4: Validación de Resultados
            await self._stage_results_validation(context)
            
            # Si necesita refinamiento y puede iterar
            if context.needs_refinement and context.can_iterate():
                context.iteration_count += 1
                context.refinement_history.append({
                    "iteration": context.iteration_count,
                    "question": context.refinement_question,
                    "previous_results": len(context.validated_products)
                })
                # La respuesta será la pregunta de refinamiento
                context.final_response = context.refinement_question
                return
        
        # Etapa 5: Generación de Respuesta
        await self._stage_response_generation(context)
    
    async def _stage_intent_classification(self, context: PipelineContext):
        """Etapa 1: Clasificación de Intención con IA"""
        stage_start = datetime.now()
        context.stage = PipelineStage.INTENT_CLASSIFICATION
        
        self.logger.info("🎯 Etapa 1: Clasificación de Intención")
        
        # Inicializar el Intent Classifier si no existe
        if not self._intent_classifier:
            from .intent_classifier_agent import IntentClassifierAgent
            self._intent_classifier = IntentClassifierAgent()
        
        try:
            # Preparar contexto de sesión
            session_context = {}
            if context.is_refinement_iteration():
                session_context["in_refinement"] = True
                session_context["refinement_history"] = context.refinement_history
            
            # Obtener mensajes recientes del contexto compartido
            if context.session_id in self.active_contexts:
                shared_session = self.active_contexts[context.session_id]
                if hasattr(shared_session, 'conversation_history'):
                    session_context["recent_messages"] = shared_session.conversation_history[-3:]
            
            # Clasificar con IA
            classification = await self._intent_classifier.classify_intent(
                context.original_message,
                session_context
            )
            
            # Actualizar contexto con los resultados
            context.intent = classification.intent
            context.intent_confidence = classification.confidence
            context.cleaned_message = classification.cleaned_message
            context.intent_details = {
                "transition_words_removed": classification.transition_words_removed,
                "context_indicators": classification.context_indicators
            }
            
            self.logger.info(f"   Intent: {context.intent} (confianza: {context.intent_confidence:.2f})")
            self.logger.info(f"   Mensaje limpio: '{context.cleaned_message}'")
            if classification.transition_words_removed:
                self.logger.info(f"   Palabras removidas: {classification.transition_words_removed}")
            
        except Exception as e:
            self.logger.error(f"Error en clasificación IA, usando fallback: {e}")
            # Fallback simple en caso de error
            context.intent = "product_search"
            context.cleaned_message = context.original_message
            context.intent_confidence = 0.5
        
        time_ms = int((datetime.now() - stage_start).total_seconds() * 1000)
        context.add_processing_time("intent_classification", time_ms)
    
    async def _stage_product_understanding(self, context: PipelineContext):
        """Etapa 2: Comprensión del Producto"""
        stage_start = datetime.now()
        context.stage = PipelineStage.PRODUCT_UNDERSTANDING
        
        self.logger.info("🧠 Etapa 2: Comprensión del Producto")
        
        # Inicializar Product Understanding Agent si no existe
        if not self._product_understander:
            from .product_understanding_agent import ProductUnderstandingAgent
            self._product_understander = ProductUnderstandingAgent()
        
        try:
            # Usar el Product Understanding Agent
            from .agent_interfaces import ProductUnderstanding
            
            understanding = await self._product_understander.understand_product(
                context.cleaned_message,
                context.intent,
                {"session_id": context.session_id}
            )
            
            # Actualizar contexto con los resultados
            context.search_query = understanding.search_query
            context.product_type = understanding.product_type
            context.brand = understanding.brand
            context.specifications = understanding.specifications
            context.understanding_confidence = understanding.confidence
            
            self.logger.info(f"   Query optimizada: '{context.search_query}'")
            self.logger.info(f"   Tipo: {context.product_type}")
            self.logger.info(f"   Marca: {context.brand}")
            self.logger.info(f"   Confianza: {context.understanding_confidence:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error en comprensión del producto: {e}")
            # Fallback: usar query limpia directamente
            context.search_query = context.cleaned_message
            context.understanding_confidence = 0.5
        
        time_ms = int((datetime.now() - stage_start).total_seconds() * 1000)
        context.add_processing_time("product_understanding", time_ms)
    
    async def _stage_smart_search(self, context: PipelineContext):
        """Etapa 3: Búsqueda Inteligente"""
        stage_start = datetime.now()
        context.stage = PipelineStage.SMART_SEARCH
        
        self.logger.info("🔍 Etapa 3: Búsqueda Inteligente")
        
        # Inicializar Smart Search Agent si no existe
        if not self._smart_searcher:
            from .agent_config import get_smart_search_agent
            self._smart_searcher = get_smart_search_agent()
        
        try:
            # Crear ProductUnderstanding para el agente
            from .agent_interfaces import ProductUnderstanding
            
            understanding = ProductUnderstanding(
                search_query=context.search_query,
                product_type=context.product_type,
                brand=context.brand,
                specifications=context.specifications,
                synonyms_applied=[],
                confidence=context.understanding_confidence
            )
            
            # Ejecutar búsqueda
            search_results = await self._smart_searcher.search_products(understanding)
            
            # Actualizar contexto con resultados
            context.raw_results = search_results.products
            context.search_strategy = search_results.search_strategy
            context.total_found = search_results.total_count
            
            self.logger.info(f"   Estrategia: {context.search_strategy}")
            self.logger.info(f"   Resultados: {context.total_found}")
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {e}")
            context.raw_results = []
            context.search_strategy = "error"
            context.total_found = 0
        
        time_ms = int((datetime.now() - stage_start).total_seconds() * 1000)
        context.add_processing_time("smart_search", time_ms)
    
    async def _stage_results_validation(self, context: PipelineContext):
        """Etapa 4: Validación de Resultados"""
        stage_start = datetime.now()
        context.stage = PipelineStage.RESULTS_VALIDATION
        
        self.logger.info("✅ Etapa 4: Validación de Resultados")
        
        # Inicializar Results Validator Agent si no existe
        if not self._results_validator:
            from .agent_config import get_results_validator_agent
            self._results_validator = get_results_validator_agent()
        
        try:
            # Crear estructuras necesarias
            from .agent_interfaces import SearchResults, ProductUnderstanding
            
            search_results = SearchResults(
                products=context.raw_results,
                total_count=context.total_found,
                search_strategy=context.search_strategy,
                query_used=context.search_query,
                filters_applied={}
            )
            
            understanding = ProductUnderstanding(
                search_query=context.search_query,
                product_type=context.product_type,
                brand=context.brand,
                specifications=context.specifications,
                synonyms_applied=[],
                confidence=context.understanding_confidence
            )
            
            # Validar resultados
            validation = await self._results_validator.validate_results(
                search_results,
                context.original_message,
                understanding
            )
            
            # Actualizar contexto
            context.validated_products = validation.valid_products
            context.needs_refinement = validation.needs_refinement
            context.refinement_question = validation.refinement_question
            context.validation_score = validation.validation_score
            
            self.logger.info(f"   Productos válidos: {len(context.validated_products)}")
            self.logger.info(f"   Necesita refinamiento: {context.needs_refinement}")
            if context.refinement_question:
                self.logger.info(f"   Pregunta: {context.refinement_question[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error en validación: {e}")
            context.validated_products = context.raw_results[:10]
            context.needs_refinement = False
            context.validation_score = 0.5
        
        time_ms = int((datetime.now() - stage_start).total_seconds() * 1000)
        context.add_processing_time("results_validation", time_ms)
    
    async def _stage_response_generation(self, context: PipelineContext):
        """Etapa 5: Generación de Respuesta"""
        stage_start = datetime.now()
        context.stage = PipelineStage.RESPONSE_GENERATION
        
        self.logger.info("💬 Etapa 5: Generación de Respuesta")
        
        # Inicializar Response Generator Agent si no existe
        if not self._response_generator:
            from .response_generator_agent import ResponseGeneratorAgent
            self._response_generator = ResponseGeneratorAgent()
        
        try:
            # Crear ValidationResult para el agente
            from .agent_interfaces import ValidationResult
            
            validation_result = ValidationResult(
                valid_products=context.validated_products,
                invalid_products=[],
                needs_refinement=context.needs_refinement,
                refinement_question=context.refinement_question,
                validation_score=context.validation_score,
                rejection_reasons=[]
            )
            
            # Generar respuesta
            response = await self._response_generator.generate_response(
                validation_result,
                context.intent,
                {
                    "session_id": context.session_id,
                    "platform": context.platform,
                    "iteration": context.iteration_count
                }
            )
            
            # Actualizar contexto con la respuesta
            context.final_response = response.content
            
            self.logger.info(f"   Tipo de respuesta: {response.response_type}")
            self.logger.info(f"   Respuesta generada ({len(context.final_response)} caracteres)")
            
            # Si hay acciones sugeridas, guardarlas en contexto
            if response.suggested_actions:
                context.suggested_actions = response.suggested_actions
                self.logger.info(f"   Acciones sugeridas: {len(response.suggested_actions)}")
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta: {e}")
            # Respuesta de fallback
            if context.intent == "greeting":
                context.final_response = "¡Hola! Soy Eva. ¿En qué puedo ayudarte?"
            elif context.validated_products:
                context.final_response = f"Encontré {len(context.validated_products)} productos."
            else:
                context.final_response = "¿En qué puedo ayudarte?"
        
        time_ms = int((datetime.now() - stage_start).total_seconds() * 1000)
        context.add_processing_time("response_generation", time_ms)
        
        context.stage = PipelineStage.COMPLETED
        self.logger.info(f"   Pipeline completado")

# Instancia singleton del pipeline
agent_pipeline = AgentPipeline()