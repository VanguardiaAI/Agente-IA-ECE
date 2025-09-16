"""
📝 Contexto Compartido entre Agentes
Memoria persistente y compartida para el pipeline de agentes
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

@dataclass
class SessionMemory:
    """Memoria de una sesión de usuario"""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Historia de conversación
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Productos mostrados previamente
    shown_products: List[str] = field(default_factory=list)
    
    # Preferencias detectadas
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Búsquedas realizadas
    search_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Refinamientos aplicados
    refinement_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Contexto actual
    current_context: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Añade un mensaje a la historia"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.last_activity = datetime.now()
    
    def add_search(self, query: str, results_count: int, metadata: Optional[Dict] = None):
        """Registra una búsqueda realizada"""
        self.search_history.append({
            "query": query,
            "results_count": results_count,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
    
    def add_shown_products(self, product_ids: List[str]):
        """Registra productos que ya se mostraron al usuario"""
        for pid in product_ids:
            if pid not in self.shown_products:
                self.shown_products.append(pid)
    
    def add_preference(self, key: str, value: Any):
        """Registra una preferencia del usuario"""
        self.preferences[key] = value
    
    def get_recent_context(self, minutes: int = 5) -> Dict[str, Any]:
        """Obtiene el contexto reciente de la conversación"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_messages = []
        for msg in reversed(self.conversation_history):
            msg_time = datetime.fromisoformat(msg['timestamp'])
            if msg_time < cutoff_time:
                break
            recent_messages.insert(0, msg)
        
        return {
            "recent_messages": recent_messages,
            "preferences": self.preferences,
            "current_context": self.current_context
        }
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Verifica si la sesión ha expirado"""
        return (datetime.now() - self.last_activity) > timedelta(minutes=timeout_minutes)
    
    def to_dict(self) -> Dict:
        """Convierte la memoria a diccionario"""
        data = asdict(self)
        # Convertir datetime a string
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data

class SharedContextManager:
    """
    Gestor de contexto compartido entre todos los agentes
    Mantiene la memoria de las sesiones y facilita el intercambio de información
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, SessionMemory] = {}
        self.session_timeout = session_timeout_minutes
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Conocimiento del dominio compartido
        self.domain_knowledge = self._load_domain_knowledge()
        
        self.logger.info("✅ Gestor de contexto compartido inicializado")
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Carga el conocimiento del dominio eléctrico"""
        return {
            "synonyms": {
                "automático": ["magnetotérmico", "PIA", "disyuntor", "breaker", "interruptor automático"],
                "diferencial": ["ID", "llave diferencial", "protección diferencial", "interruptor diferencial"],
                "lámpara": ["luminaria", "foco", "bombilla", "iluminación", "luz"],
                "cable": ["conductor", "manguera", "hilo", "cableado"],
                "ventilador": ["extractor", "ventilación", "aire"],
                "enrollacables": ["recoge cables", "organizador cables", "carrete"],
            },
            "brands": [
                "Schneider", "ABB", "Legrand", "Simon", "Hager", 
                "Siemens", "Chint", "Gewiss", "Jung", "Niessen"
            ],
            "categories": {
                "protecciones": ["diferencial", "magnetotérmico", "fusible", "sobretensión"],
                "iluminación": ["lámpara", "bombilla", "proyector", "luminaria", "campana"],
                "cables": ["unipolar", "manguera", "coaxial", "datos"],
                "mecanismos": ["interruptor", "enchufe", "pulsador", "dimmer"],
                "industrial": ["contactor", "variador", "transformador", "motor"]
            },
            "specifications": {
                "amperaje": ["10A", "16A", "20A", "25A", "32A", "40A", "63A"],
                "sensibilidad": ["30mA", "300mA", "500mA"],
                "voltaje": ["12V", "24V", "230V", "400V"],
                "sección_cable": ["1.5mm²", "2.5mm²", "4mm²", "6mm²", "10mm²"]
            }
        }
    
    def get_or_create_session(self, session_id: str, user_id: str) -> SessionMemory:
        """Obtiene o crea una sesión"""
        # Limpiar sesiones expiradas
        self._cleanup_expired_sessions()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMemory(
                session_id=session_id,
                user_id=user_id
            )
            self.logger.info(f"📝 Nueva sesión creada: {session_id}")
        
        return self.sessions[session_id]
    
    def _cleanup_expired_sessions(self):
        """Limpia sesiones expiradas"""
        expired = []
        for sid, session in self.sessions.items():
            if session.is_expired(self.session_timeout):
                expired.append(sid)
        
        for sid in expired:
            del self.sessions[sid]
            self.logger.info(f"🗑️ Sesión expirada eliminada: {sid}")
    
    def share_between_agents(self, session_id: str, key: str, value: Any):
        """
        Comparte información entre agentes
        
        Args:
            session_id: ID de la sesión
            key: Clave de la información
            value: Valor a compartir
        """
        session = self.get_or_create_session(session_id, "default")
        session.current_context[key] = value
        self.logger.debug(f"📤 Compartido '{key}' entre agentes")
    
    def get_shared_value(self, session_id: str, key: str, default=None) -> Any:
        """
        Obtiene un valor compartido entre agentes
        
        Args:
            session_id: ID de la sesión
            key: Clave de la información
            default: Valor por defecto si no existe
            
        Returns:
            El valor compartido o el default
        """
        if session_id in self.sessions:
            return self.sessions[session_id].current_context.get(key, default)
        return default
    
    def get_synonyms(self, word: str) -> List[str]:
        """Obtiene sinónimos de una palabra del dominio"""
        word_lower = word.lower()
        for key, synonyms in self.domain_knowledge["synonyms"].items():
            if word_lower == key or word_lower in synonyms:
                return [key] + synonyms
        return [word]
    
    def get_brands(self) -> List[str]:
        """Obtiene la lista de marcas conocidas"""
        return self.domain_knowledge["brands"]
    
    def get_category_keywords(self, category: str) -> List[str]:
        """Obtiene palabras clave de una categoría"""
        return self.domain_knowledge["categories"].get(category, [])
    
    def detect_specifications(self, text: str) -> Dict[str, Any]:
        """Detecta especificaciones técnicas en el texto"""
        specs = {}
        text_lower = text.lower()
        
        # Detectar amperaje
        for amp in self.domain_knowledge["specifications"]["amperaje"]:
            if amp.lower() in text_lower:
                specs["amperaje"] = amp
                break
        
        # Detectar sensibilidad
        for sens in self.domain_knowledge["specifications"]["sensibilidad"]:
            if sens.lower() in text_lower:
                specs["sensibilidad"] = sens
                break
        
        # Detectar voltaje
        for volt in self.domain_knowledge["specifications"]["voltaje"]:
            if volt.lower() in text_lower:
                specs["voltaje"] = volt
                break
        
        # Detectar sección de cable
        for section in self.domain_knowledge["specifications"]["sección_cable"]:
            if section.replace("²", "2") in text_lower or section in text_lower:
                specs["sección"] = section
                break
        
        return specs
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un resumen de la sesión"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "total_messages": len(session.conversation_history),
            "total_searches": len(session.search_history),
            "products_shown": len(session.shown_products),
            "preferences": session.preferences,
            "active_refinements": len(session.refinement_history)
        }

# Instancia singleton del gestor de contexto
shared_context = SharedContextManager()