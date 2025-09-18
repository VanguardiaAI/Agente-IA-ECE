"""
Estado de conversación para el sistema EVA GPT-5
Mantiene el contexto completo de la interacción
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class SearchState(str, Enum):
    """Estados del proceso de búsqueda"""
    INITIAL = "initial"
    ANALYZING = "analyzing"
    NEEDS_INFO = "needs_info"
    SEARCHING = "searching"
    VALIDATING = "validating"
    REFINING = "refining"
    COMPLETED = "completed"
    FAILED = "failed"


class UserIntent(str, Enum):
    """Intenciones del usuario detectadas"""
    PRODUCT_SEARCH = "product_search"
    TECHNICAL_INFO = "technical_info"
    ORDER_INQUIRY = "order_inquiry"
    GREETING = "greeting"
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"


@dataclass
class SearchContext:
    """Contexto específico de búsqueda de productos"""
    original_query: str
    current_query: Optional[str] = None
    extracted_info: Dict[str, Any] = field(default_factory=dict)
    missing_info: List[str] = field(default_factory=list)
    search_attempts: List[Dict[str, Any]] = field(default_factory=list)
    current_results: List[Dict] = field(default_factory=list)
    refinement_feedback: List[str] = field(default_factory=list)
    synonyms_used: List[str] = field(default_factory=list)
    has_clarified: bool = False  # Track if we already asked for clarification
    clarification_count: int = 0  # Count how many times we've asked for clarification
    needs_clarification_for_general: bool = False  # Track if we asked due to general search
    
    def add_attempt(self, query: str, results: List[Dict], valid: bool, feedback: str = ""):
        """Registra un intento de búsqueda"""
        self.search_attempts.append({
            "query": query,
            "results_count": len(results),
            "valid": valid,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        })
        
    def needs_more_info(self) -> bool:
        """Determina si necesita más información del usuario"""
        return len(self.missing_info) > 0
        
    def can_retry(self, max_attempts: int = 3) -> bool:
        """Determina si puede intentar otra búsqueda"""
        return len(self.search_attempts) < max_attempts


@dataclass
class ConversationState:
    """Estado completo de la conversación"""
    session_id: str
    user_id: str
    platform: str = "wordpress"
    
    # Historial de mensajes
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Estado actual
    current_intent: Optional[UserIntent] = None
    intent_confidence: float = 0.0
    search_state: SearchState = SearchState.INITIAL
    
    # Contexto de búsqueda si aplica
    search_context: Optional[SearchContext] = None
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    turn_count: int = 0
    
    # Preferencias detectadas
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Añade un mensaje al historial"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "turn": self.turn_count
        }
        if metadata:
            message["metadata"] = metadata
            
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        if role == "user":
            self.turn_count += 1
            
    def get_recent_messages(self, count: int = 5) -> List[Dict[str, Any]]:
        """Obtiene los mensajes más recientes"""
        return self.messages[-count:] if self.messages else []
        
    def update_search_state(self, new_state: SearchState):
        """Actualiza el estado de búsqueda"""
        self.search_state = new_state
        self.last_activity = datetime.now()
        
    def create_search_context(self, query: str) -> SearchContext:
        """Crea o actualiza el contexto de búsqueda"""
        if self.search_context is None:
            # Primera búsqueda - crear nuevo contexto
            self.search_context = SearchContext(original_query=query)
        else:
            # Ya existe contexto - decidir si es nueva búsqueda o continuación
            if self.search_state == SearchState.NEEDS_INFO:
                # Estamos esperando clarificación - mantener contexto
                self.search_context.current_query = query
            else:
                # Nueva búsqueda - crear nuevo contexto
                self.search_context = SearchContext(original_query=query)
        return self.search_context
        
    def summary(self) -> Dict[str, Any]:
        """Genera un resumen del estado actual"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_intent": self.current_intent.value if self.current_intent else None,
            "search_state": self.search_state.value,
            "turn_count": self.turn_count,
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
            "has_search_context": self.search_context is not None,
            "search_attempts": len(self.search_context.search_attempts) if self.search_context else 0
        }