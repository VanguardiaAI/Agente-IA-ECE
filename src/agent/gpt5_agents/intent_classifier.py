"""
Clasificador de intención usando GPT-5-mini
Determina con precisión qué quiere hacer el usuario
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
from .conversation_state import UserIntent

logger = logging.getLogger(__name__)


@dataclass
class IntentClassification:
    """Resultado de la clasificación de intención"""
    intent: UserIntent
    confidence: float
    entities: Dict[str, Any]
    reasoning: str
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None


class IntentClassifier:
    """Clasificador de intención inteligente con GPT-5-mini"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.model = "gpt-5-mini"  # USAR GPT-5-MINI PARA INTENT
        
    async def classify_intent(
        self, 
        message: str, 
        context: Optional[List[Dict[str, str]]] = None
    ) -> IntentClassification:
        """
        Clasifica la intención del usuario con alta precisión
        
        Args:
            message: Mensaje del usuario
            context: Historial de conversación (opcional)
            
        Returns:
            IntentClassification con los resultados
        """
        
        # Construir el prompt con contexto si está disponible
        context_str = ""
        if context:
            context_str = "\nContexto de conversación:\n"
            for msg in context[-3:]:  # Últimos 3 mensajes
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                context_str += f"{role}: {content}\n"
        
        prompt = f"""Eres un clasificador de intención para El Corte Eléctrico, tienda especializada en MATERIAL ELÉCTRICO.

CONTEXTO: Vendemos productos eléctricos para instalaciones (automáticos, diferenciales, cables, lámparas, etc.).
Cuando alguien dice "quiero un automático" se refiere a un interruptor magnetotérmico, NO a un coche automático.

ABREVIACIONES COMUNES DE PRODUCTOS:
- "ID" = Interruptor Diferencial → PRODUCT_SEARCH
- "PIA" = Pequeño Interruptor Automático → PRODUCT_SEARCH
- "IAR" = Interruptor Automático de Reenganche → PRODUCT_SEARCH
- Si el usuario dice "quiero un [abreviación]" es SIEMPRE una búsqueda de producto

ANALIZA el siguiente mensaje y determina la intención del usuario.{context_str}

Mensaje actual: "{message}"

REGLAS CRÍTICAS DE CLASIFICACIÓN:

1. Si pregunta por CONTACTO o INFORMACIÓN DE LA TIENDA:
   - "teléfono", "email", "contacto", "whatsapp" → GENERAL_QUESTION
   - "tienda física", "ubicación", "dirección" → GENERAL_QUESTION
   - "instagram", "facebook", "redes sociales" → GENERAL_QUESTION
   - "horario", "abierto", "cerrado" → GENERAL_QUESTION
   - "qué marcas", "marcas que venden", "marcas disponibles" → GENERAL_QUESTION
   - "formas de pago", "métodos de pago", "cómo pagar" → GENERAL_QUESTION
   - "envíos", "entregan en", "tiempo de entrega" → GENERAL_QUESTION
   - "sobre la empresa", "quiénes son" → GENERAL_QUESTION
   
2. Si el contexto muestra que YA se mostraron productos y ahora pide:
   - "explícame las diferencias" → TECHNICAL_INFO
   - "cuál es mejor" → TECHNICAL_INFO
   - "compárame estos" → TECHNICAL_INFO
   - "dame más detalles" → TECHNICAL_INFO
   - Cualquier pregunta SOBRE los productos mostrados → TECHNICAL_INFO

3. Si el contexto NO muestra productos previos:
   - "busco/quiero/necesito [producto]" → PRODUCT_SEARCH
   - "muéstrame [producto]" → PRODUCT_SEARCH
   - "qué [producto] tienes" → PRODUCT_SEARCH

INTENCIONES POSIBLES:
1. PRODUCT_SEARCH: El usuario quiere COMPRAR o está BUSCANDO productos NUEVOS
   - "necesito un automático", "busco cable", "quiero comprar"
   - Preguntas sobre disponibilidad o precios de productos NO mostrados
   - NUNCA si está preguntando sobre productos YA mostrados

2. TECHNICAL_INFO: El usuario quiere INFORMACIÓN o EXPLICACIONES
   - "cómo funciona", "qué es", "para qué sirve"
   - "explícame las diferencias" (especialmente si hay productos en contexto)
   - "cuál es mejor", "compara", "ventajas y desventajas"
   - Cualquier pregunta técnica o comparativa
   - SIEMPRE si pregunta sobre productos YA mostrados en el contexto

3. ORDER_INQUIRY: Consultas sobre pedidos existentes
   - "mi pedido", "estado del envío", números de orden

4. GREETING: Saludos
   - "hola", "buenos días", etc.

5. GENERAL_QUESTION: Preguntas sobre la tienda, contacto o información general
   - "¿cuál es el teléfono?", "¿tienen tienda física?", "¿dónde están ubicados?"
   - "email de contacto", "redes sociales", "instagram", "facebook", "whatsapp"
   - Horarios, métodos de pago, garantías, políticas
   - Cualquier pregunta sobre contacto o información de la empresa

ANÁLISIS CONTEXTUAL:
- PRIMERO revisa si hay productos en el contexto reciente
- Si los hay Y el usuario pregunta sobre ellos → TECHNICAL_INFO
- Si NO hay productos O pide productos nuevos → PRODUCT_SEARCH

Responde SOLO con JSON válido, sin texto adicional antes o después.

{{
    "intent": "INTENT_AQUÍ",
    "confidence": 0.0-1.0,
    "reasoning": "explicación breve de por qué elegiste esta intención",
    "entities": {{
        "product_mentioned": "producto si lo menciona",
        "order_number": "número si lo menciona",
        "technical_terms": ["términos técnicos encontrados"]
    }},
    "needs_clarification": false,
    "clarification_prompt": null
}}"""

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=500
            )
            
            # Parsear la respuesta JSON
            import json
            result = json.loads(response.content)
            
            # Mapear la intención
            intent_map = {
                "PRODUCT_SEARCH": UserIntent.PRODUCT_SEARCH,
                "TECHNICAL_INFO": UserIntent.TECHNICAL_INFO,
                "ORDER_INQUIRY": UserIntent.ORDER_INQUIRY,
                "GREETING": UserIntent.GREETING,
                "GENERAL_QUESTION": UserIntent.GENERAL_QUESTION
            }
            
            intent = intent_map.get(result["intent"], UserIntent.UNKNOWN)
            
            return IntentClassification(
                intent=intent,
                confidence=float(result.get("confidence", 0.8)),
                entities=result.get("entities", {}),
                reasoning=result.get("reasoning", ""),
                needs_clarification=result.get("needs_clarification", False),
                clarification_prompt=result.get("clarification_prompt")
            )
            
        except Exception as e:
            logger.error(f"Error clasificando intención: {e}")
            
            # Fallback básico basado en palabras clave
            message_lower = message.lower()
            
            if any(word in message_lower for word in ["pedido", "orden", "envío", "compra #"]):
                intent = UserIntent.ORDER_INQUIRY
            elif any(word in message_lower for word in ["hola", "buenos días", "buenas"]):
                intent = UserIntent.GREETING
            elif any(word in message_lower for word in ["necesito", "busco", "quiero", "precio"]):
                intent = UserIntent.PRODUCT_SEARCH
            elif any(word in message_lower for word in ["qué es", "cómo funciona", "para qué"]):
                intent = UserIntent.TECHNICAL_INFO
            else:
                intent = UserIntent.UNKNOWN
                
            return IntentClassification(
                intent=intent,
                confidence=0.5,
                entities={},
                reasoning="Clasificación por fallback debido a error",
                needs_clarification=intent == UserIntent.UNKNOWN
            )
            
    async def extract_order_info(self, message: str) -> Dict[str, Any]:
        """Extrae información de pedido del mensaje"""
        prompt = f"""Extrae información de pedido del siguiente mensaje:
"{message}"

Busca:
- Números de pedido (#1234, orden 5678, etc.)
- Email del cliente
- Referencias a "mi pedido", "mi compra"

Responde en JSON:
{{
    "order_number": "número si lo encuentra",
    "email": "email si lo menciona",
    "has_order_reference": true/false
}}"""

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=200
            )
            
            import json
            return json.loads(response.content)
            
        except:
            return {
                "order_number": None,
                "email": None,
                "has_order_reference": False
            }


# Instancia global
intent_classifier = IntentClassifier()