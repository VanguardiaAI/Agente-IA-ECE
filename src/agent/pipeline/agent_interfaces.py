"""
🔌 Interfaces de Comunicación entre Agentes
Define los contratos que deben cumplir todos los agentes del pipeline
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# ============= Estructuras de Datos Compartidas =============

@dataclass
class IntentClassification:
    """Resultado de la clasificación de intención"""
    intent: str  # product_search, order_inquiry, greeting, refinement, confirmation
    confidence: float
    cleaned_message: str
    transition_words_removed: List[str]
    context_indicators: Dict[str, Any]

@dataclass 
class ProductUnderstanding:
    """Resultado del análisis de comprensión del producto"""
    search_query: str
    product_type: Optional[str]
    brand: Optional[str]
    specifications: Dict[str, Any]
    synonyms_applied: List[str]
    confidence: float

@dataclass
class SearchResults:
    """Resultados de búsqueda"""
    products: List[Dict[str, Any]]
    total_count: int
    search_strategy: str  # hybrid, exact, category, semantic
    query_used: str
    filters_applied: Dict[str, Any]

@dataclass
class ValidationResult:
    """Resultado de la validación de productos"""
    valid_products: List[Dict[str, Any]]
    invalid_products: List[Dict[str, Any]]
    needs_refinement: bool
    refinement_question: Optional[str]
    validation_score: float
    rejection_reasons: List[str]

@dataclass
class GeneratedResponse:
    """Respuesta generada para el usuario"""
    content: str
    response_type: str  # products, refinement, greeting, error, confirmation
    metadata: Dict[str, Any]
    suggested_actions: List[str]

# ============= Interfaces Base para Agentes =============

class BaseAgent(ABC):
    """Interfaz base para todos los agentes del pipeline"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Agent.{name}")
        self.metrics = {
            "processed": 0,
            "errors": 0,
            "avg_time_ms": 0
        }
    
    @abstractmethod
    async def process(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """
        Procesa la entrada y retorna el resultado
        
        Args:
            input_data: Datos de entrada específicos del agente
            context: Contexto compartido del pipeline
            
        Returns:
            Resultado del procesamiento
        """
        pass
    
    def log_metrics(self, time_ms: int, success: bool = True):
        """Registra métricas del agente"""
        self.metrics["processed"] += 1
        if not success:
            self.metrics["errors"] += 1
        
        # Actualizar promedio de tiempo
        current_avg = self.metrics["avg_time_ms"]
        total_processed = self.metrics["processed"]
        self.metrics["avg_time_ms"] = ((current_avg * (total_processed - 1)) + time_ms) / total_processed
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene las métricas del agente"""
        return self.metrics.copy()

# ============= Interfaces Específicas por Agente =============

class IIntentClassifierAgent(BaseAgent):
    """Interfaz para el Agente Clasificador de Intención"""
    
    @abstractmethod
    async def classify_intent(
        self, 
        message: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> IntentClassification:
        """
        Clasifica la intención del mensaje del usuario
        
        Args:
            message: Mensaje original del usuario
            session_context: Contexto de la sesión si existe
            
        Returns:
            Clasificación de intención
        """
        pass
    
    @abstractmethod
    def get_supported_intents(self) -> List[str]:
        """Retorna la lista de intenciones soportadas"""
        pass

class IProductUnderstandingAgent(BaseAgent):
    """Interfaz para el Agente de Comprensión de Productos"""
    
    @abstractmethod
    async def understand_product_request(
        self,
        cleaned_message: str,
        intent_details: Dict[str, Any]
    ) -> ProductUnderstanding:
        """
        Analiza y comprende la petición de producto
        
        Args:
            cleaned_message: Mensaje limpio sin palabras de transición
            intent_details: Detalles de la intención clasificada
            
        Returns:
            Comprensión estructurada del producto
        """
        pass
    
    @abstractmethod
    def get_domain_knowledge(self) -> Dict[str, Any]:
        """Retorna el conocimiento del dominio del agente"""
        pass

class ISmartSearchAgent(BaseAgent):
    """Interfaz para el Agente de Búsqueda Inteligente"""
    
    @abstractmethod
    async def search_products(
        self,
        understanding: ProductUnderstanding,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Busca productos basándose en la comprensión
        
        Args:
            understanding: Comprensión del producto
            filters: Filtros adicionales a aplicar
            
        Returns:
            Resultados de búsqueda
        """
        pass
    
    @abstractmethod
    async def search_by_category(self, category: str) -> SearchResults:
        """Busca productos por categoría"""
        pass
    
    @abstractmethod
    async def search_similar(self, product_id: str) -> SearchResults:
        """Busca productos similares a uno dado"""
        pass

class IResultsValidatorAgent(BaseAgent):
    """Interfaz para el Agente Validador de Resultados"""
    
    @abstractmethod
    async def validate_results(
        self,
        search_results: SearchResults,
        original_request: str,
        understanding: ProductUnderstanding
    ) -> ValidationResult:
        """
        Valida que los resultados sean relevantes
        
        Args:
            search_results: Resultados de la búsqueda
            original_request: Petición original del usuario
            understanding: Comprensión del producto
            
        Returns:
            Resultado de la validación
        """
        pass
    
    @abstractmethod
    def generate_refinement_question(
        self,
        products: List[Dict[str, Any]],
        understanding: ProductUnderstanding
    ) -> str:
        """Genera una pregunta de refinamiento apropiada"""
        pass

class IResponseGeneratorAgent(BaseAgent):
    """Interfaz para el Agente Generador de Respuestas"""
    
    @abstractmethod
    async def generate_response(
        self,
        validation_result: Optional[ValidationResult],
        intent: str,
        context: Dict[str, Any]
    ) -> GeneratedResponse:
        """
        Genera la respuesta final para el usuario
        
        Args:
            validation_result: Resultado de la validación si aplica
            intent: Intención clasificada
            context: Contexto completo del pipeline
            
        Returns:
            Respuesta generada
        """
        pass
    
    @abstractmethod
    def format_products(
        self,
        products: List[Dict[str, Any]],
        platform: str
    ) -> str:
        """Formatea productos para la plataforma específica"""
        pass
    
    @abstractmethod
    def get_response_templates(self) -> Dict[str, str]:
        """Retorna las plantillas de respuesta disponibles"""
        pass

# ============= Factory para Crear Agentes =============

class AgentFactory:
    """Factory para crear instancias de agentes"""
    
    _agents = {}
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: type):
        """Registra un tipo de agente"""
        cls._agents[agent_type] = agent_class
    
    @classmethod
    def create_agent(cls, agent_type: str, **kwargs) -> BaseAgent:
        """Crea una instancia de un agente"""
        if agent_type not in cls._agents:
            raise ValueError(f"Tipo de agente desconocido: {agent_type}")
        
        agent_class = cls._agents[agent_type]
        return agent_class(**kwargs)
    
    @classmethod
    def get_available_agents(cls) -> List[str]:
        """Retorna la lista de agentes disponibles"""
        return list(cls._agents.keys())

# ============= Protocolo de Comunicación =============

class AgentCommunicationProtocol:
    """
    Protocolo de comunicación entre agentes
    Define cómo los agentes intercambian información
    """
    
    @staticmethod
    def create_message(
        sender: str,
        receiver: str,
        message_type: str,
        payload: Any
    ) -> Dict[str, Any]:
        """Crea un mensaje estándar entre agentes"""
        return {
            "sender": sender,
            "receiver": receiver,
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def validate_message(message: Dict[str, Any]) -> bool:
        """Valida que un mensaje cumpla con el protocolo"""
        required_fields = ["sender", "receiver", "type", "payload", "timestamp"]
        return all(field in message for field in required_fields)
    
    @staticmethod
    def create_error_response(
        sender: str,
        error: str,
        original_message: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Crea una respuesta de error estándar"""
        return {
            "sender": sender,
            "receiver": "pipeline",
            "type": "error",
            "payload": {
                "error": error,
                "original_message": original_message
            },
            "timestamp": datetime.now().isoformat()
        }

# ============= Excepciones Personalizadas =============

class AgentException(Exception):
    """Excepción base para errores de agentes"""
    pass

class IntentClassificationError(AgentException):
    """Error en la clasificación de intención"""
    pass

class ProductUnderstandingError(AgentException):
    """Error en la comprensión del producto"""
    pass

class SearchError(AgentException):
    """Error en la búsqueda"""
    pass

class ValidationError(AgentException):
    """Error en la validación"""
    pass

class ResponseGenerationError(AgentException):
    """Error en la generación de respuesta"""
    pass