"""
Sistema de detección de escalamiento inteligente
Determina cuándo una consulta debe ser escalada a un agente humano
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class EscalationDetector:
    """Detecta cuándo escalar a un agente humano"""
    
    def __init__(self):
        # Patrones que indican necesidad de escalamiento
        self.escalation_patterns = {
            "complaint": [
                "queja", "reclamación", "reclamo", "problema grave", "muy mal",
                "pésimo", "terrible", "inaceptable", "vergonzoso", "desastre"
            ],
            "refund": [
                "devolver", "devolución", "reembolso", "recuperar dinero",
                "cancelar pedido", "anular compra", "quiero mi dinero"
            ],
            "warranty": [
                "reclamar garantía", "usar la garantía", "avería", "defectuoso", "roto", 
                "no funciona", "estropeado", "falla", "defecto de fábrica", "devolver por garantía"
            ],
            "custom_order": [
                "pedido especial", "personalizado", "a medida", "gran cantidad",
                "presupuesto", "descuento por volumen", "precio especial"
            ],
            "technical_support": [
                "instalación", "conectar", "configurar", "manual técnico",
                "esquema", "diagrama", "especificaciones técnicas"
            ],
            "urgent": [
                "urgente", "emergencia", "hoy mismo", "ahora mismo",
                "inmediatamente", "muy urgente", "crítico"
            ],
            "frustrated": [
                "no me ayudas", "no sirves", "quiero hablar con alguien",
                "humano", "persona real", "operador", "agente"
            ]
        }
        
        # Palabras que indican complejidad alta
        self.complex_indicators = [
            "factura con", "modificar pedido", "cambiar dirección",
            "error en el pago", "cobro duplicado", "no llegó",
            "llevo esperando", "hace días", "hace semanas"
        ]
        
        # Contador de intentos fallidos por sesión
        self.failed_attempts = {}
        
    def should_escalate(self, 
                       message: str, 
                       session_id: str,
                       previous_response: Optional[str] = None,
                       error_occurred: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        Determina si debe escalar la conversación
        
        Args:
            message: Mensaje del usuario
            session_id: ID de la sesión
            previous_response: Respuesta anterior del bot (para detectar loops)
            error_occurred: Si hubo un error técnico
            
        Returns:
            (should_escalate, reason, suggested_message)
        """
        message_lower = message.lower()
        
        # 1. Escalar si hubo error técnico
        if error_occurred:
            return True, "technical_error", None
            
        # 2. Detectar patrones de escalamiento
        for category, patterns in self.escalation_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                # Sugerir mensaje para el agente humano
                suggested_msg = self._get_suggested_message(category, message)
                return True, category, suggested_msg
                
        # 3. Detectar complejidad alta
        if any(indicator in message_lower for indicator in self.complex_indicators):
            return True, "complex_query", f"Consulta compleja: {message[:100]}"
            
        # 4. Detectar frustración por intentos repetidos
        if session_id in self.failed_attempts:
            if self.failed_attempts[session_id] >= 2:
                return True, "multiple_attempts", "El cliente ha intentado varias veces sin éxito"
                
        # 5. Detectar si el usuario pide explícitamente un humano
        human_request_patterns = [
            "hablar con alguien", "persona real", "agente humano",
            "operador", "atención personal", "no eres útil",
            "hablar con una persona", "necesito hablar", "quiero hablar",
            "contacto de un humano", "dame el contacto"
        ]
        if any(pattern in message_lower for pattern in human_request_patterns):
            return True, "human_requested", "El cliente solicita atención humana"
            
        # 6. Detectar loops (misma pregunta repetida)
        if previous_response and self._is_potential_loop(message, previous_response):
            self._increment_failed_attempts(session_id)
            if self.failed_attempts.get(session_id, 0) >= 2:
                return True, "conversation_loop", "Posible bucle en la conversación"
                
        return False, "", None
        
    def _get_suggested_message(self, category: str, original_message: str) -> str:
        """Genera un mensaje sugerido para el agente humano"""
        suggestions = {
            "complaint": f"Cliente con queja: {original_message[:100]}",
            "refund": f"Solicitud de devolución: {original_message[:100]}",
            "warranty": f"Consulta de garantía: {original_message[:100]}",
            "custom_order": f"Pedido especial: {original_message[:100]}",
            "technical_support": f"Soporte técnico: {original_message[:100]}",
            "urgent": f"URGENTE: {original_message[:100]}",
            "frustrated": "Cliente frustrado necesita atención"
        }
        return suggestions.get(category, f"Consulta: {original_message[:100]}")
        
    def _is_potential_loop(self, current_message: str, previous_response: str) -> bool:
        """Detecta si estamos en un loop conversacional"""
        # Simplificar mensajes para comparación
        current_clean = re.sub(r'[^\w\s]', '', current_message.lower()).strip()
        
        # Si el mensaje es muy similar al anterior, puede ser un loop
        if len(current_clean) > 10:  # Ignorar mensajes muy cortos
            return "no entiendo" in previous_response.lower() or \
                   "no tengo esa información" in previous_response.lower()
        return False
        
    def _increment_failed_attempts(self, session_id: str):
        """Incrementa el contador de intentos fallidos"""
        if session_id not in self.failed_attempts:
            self.failed_attempts[session_id] = 0
        self.failed_attempts[session_id] += 1
        
    def reset_session(self, session_id: str):
        """Resetea el contador de una sesión"""
        if session_id in self.failed_attempts:
            del self.failed_attempts[session_id]
            
    def analyze_conversation_quality(self, messages: List[Dict]) -> Dict:
        """
        Analiza la calidad de la conversación para determinar si escalar
        
        Args:
            messages: Lista de mensajes de la conversación
            
        Returns:
            Dict con análisis de calidad
        """
        if len(messages) < 2:
            return {"quality": "good", "should_escalate": False}
            
        # Detectar señales de mala calidad
        negative_signals = 0
        
        # Buscar repeticiones
        user_messages = [m["content"].lower() for m in messages if m["role"] == "user"]
        if len(user_messages) > len(set(user_messages)):
            negative_signals += 1
            
        # Buscar frustración creciente
        frustration_words = ["no", "mal", "error", "problema"]
        frustration_count = sum(
            1 for msg in user_messages[-3:] 
            if any(word in msg for word in frustration_words)
        )
        if frustration_count >= 2:
            negative_signals += 1
            
        # Determinar calidad
        if negative_signals >= 2:
            return {
                "quality": "poor",
                "should_escalate": True,
                "reason": "conversation_quality"
            }
            
        return {"quality": "good", "should_escalate": False}

# Instancia global del detector
escalation_detector = EscalationDetector()