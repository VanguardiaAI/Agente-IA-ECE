#!/usr/bin/env python3
"""
Intent Classifier Agent
Identifica con precisión la intención del usuario
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    """Intenciones posibles del usuario"""
    PRODUCT_SEARCH = "product_search"  # Buscar/comprar productos
    TECHNICAL_INFO = "technical_info"  # Información técnica sobre productos
    ORDER_INQUIRY = "order_inquiry"    # Consultas sobre pedidos
    GENERAL_SUPPORT = "general_support"  # Otras consultas generales
    GREETING = "greeting"  # Saludos/despedidas


@dataclass
class IntentClassification:
    """Resultado de clasificación de intención"""
    intent: UserIntent
    confidence: float
    sub_intent: Optional[str] = None
    entities: Dict[str, Any] = None
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


class IntentClassifierAgent:
    """Agente para clasificar la intención del usuario"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    async def classify_intent(self, message: str, context: Optional[Dict] = None) -> IntentClassification:
        """
        Clasifica la intención del mensaje del usuario
        
        Args:
            message: Mensaje del usuario
            context: Contexto de la conversación (historial, etc.)
            
        Returns:
            IntentClassification con la intención identificada
        """
        
        # Preparar contexto de conversación si existe
        context_str = ""
        if context and context.get("history"):
            recent_messages = context["history"][-3:]  # Últimos 3 mensajes
            context_str = "\nHistorial reciente:\n"
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]
                context_str += f"- {role}: {content}\n"
        
        # Prompt optimizado para distinguir intenciones
        classification_prompt = f"""Analiza el siguiente mensaje de un cliente de una tienda de material eléctrico y determina su intención PRINCIPAL.

MENSAJE DEL CLIENTE: "{message}"
{context_str}

INTENCIONES POSIBLES:

1. PRODUCT_SEARCH: El cliente quiere BUSCAR o COMPRAR productos
   - Palabras clave: busco, necesito, quiero, dame, muéstrame, tienes, precio de, cuánto cuesta
   - Menciona productos específicos: cables, diferenciales, automáticos, lámparas, etc.
   - Pregunta por disponibilidad, stock o precios
   - Quiere comparar productos o ver opciones

2. TECHNICAL_INFO: El cliente quiere INFORMACIÓN TÉCNICA sobre productos (NO comprar)
   - Pregunta CÓMO funciona algo
   - Pregunta PARA QUÉ sirve
   - Diferencias técnicas entre productos
   - Instrucciones de instalación
   - Compatibilidad técnica
   - Especificaciones técnicas detalladas

3. ORDER_INQUIRY: Consultas sobre pedidos existentes
   - Menciona número de pedido
   - Pregunta por estado de envío
   - Menciona que ya compró
   - Proporciona email para consultar pedido
   - Pregunta cuándo llega su pedido

4. GREETING: Saludos o despedidas simples
   - Hola, buenos días, adiós, gracias
   - Sin contenido adicional

5. GENERAL_SUPPORT: Otras consultas
   - Horarios de tienda
   - Políticas de devolución
   - Formas de pago
   - Ubicación
   - Otros temas no relacionados con productos específicos

REGLAS CRÍTICAS:
- "¿Qué es un diferencial?" → TECHNICAL_INFO (quiere saber QUÉ ES)
- "Necesito un diferencial" → PRODUCT_SEARCH (quiere COMPRAR)
- "¿Para qué sirve un magnetotérmico?" → TECHNICAL_INFO (quiere información)
- "Busco magnetotérmicos de 16A" → PRODUCT_SEARCH (quiere comprar)
- "¿Cómo instalo un diferencial?" → TECHNICAL_INFO (instrucciones)
- "¿Cuál es la diferencia entre X e Y?" → TECHNICAL_INFO (comparación técnica)
- "¿Qué precio tiene X?" → PRODUCT_SEARCH (interés en comprar)

Responde con JSON:
{{
    "intent": "INTENT_PRINCIPAL",
    "confidence": 0.0-1.0,
    "sub_intent": "detalle_opcional",
    "entities": {{
        "product_mentioned": "si menciona algún producto",
        "technical_terms": ["términos técnicos mencionados"],
        "order_reference": "si menciona pedido o email"
    }},
    "reasoning": "breve explicación de por qué elegiste esta intención"
}}"""

        try:
            response = await self.gpt5.create_response(
                input_text=classification_prompt,
                model="gpt-5",
                reasoning_effort=ReasoningEffort.MEDIUM,
                verbosity=Verbosity.LOW
            )
            
            # Parsear respuesta
            import json
            try:
                result = json.loads(response.content)
                
                # Validar y convertir intent
                intent_str = result.get("intent", "GENERAL_SUPPORT")
                try:
                    intent = UserIntent(intent_str.lower())
                except ValueError:
                    # Si no es válido, intentar mapear
                    intent_map = {
                        "product_search": UserIntent.PRODUCT_SEARCH,
                        "technical_info": UserIntent.TECHNICAL_INFO,
                        "order_inquiry": UserIntent.ORDER_INQUIRY,
                        "greeting": UserIntent.GREETING,
                        "general_support": UserIntent.GENERAL_SUPPORT
                    }
                    intent = intent_map.get(intent_str.lower(), UserIntent.GENERAL_SUPPORT)
                
                classification = IntentClassification(
                    intent=intent,
                    confidence=float(result.get("confidence", 0.8)),
                    sub_intent=result.get("sub_intent"),
                    entities=result.get("entities", {})
                )
                
                self.logger.info(f"Intent clasificado: {intent.value} (confianza: {classification.confidence})")
                
                # Verificar si necesita clarificación
                if classification.confidence < 0.7:
                    classification.requires_clarification = True
                    classification.clarification_prompt = self._generate_clarification_prompt(
                        message, intent, result.get("reasoning", "")
                    )
                
                return classification
                
            except json.JSONDecodeError:
                self.logger.error("Error parseando respuesta JSON")
                # Fallback basado en palabras clave
                return self._fallback_classification(message)
                
        except Exception as e:
            self.logger.error(f"Error en clasificación de intent: {e}")
            return self._fallback_classification(message)
    
    def _generate_clarification_prompt(self, message: str, intent: UserIntent, reasoning: str) -> str:
        """Genera un prompt de clarificación si la confianza es baja"""
        
        if intent == UserIntent.PRODUCT_SEARCH:
            return "¿Estás buscando algún producto en particular para comprar?"
        elif intent == UserIntent.TECHNICAL_INFO:
            return "¿Necesitas información técnica o instrucciones sobre algún producto?"
        elif intent == UserIntent.ORDER_INQUIRY:
            return "¿Tienes alguna consulta sobre un pedido? Por favor, proporciona tu email o número de pedido."
        else:
            return "¿En qué puedo ayudarte específicamente?"
    
    def _fallback_classification(self, message: str) -> IntentClassification:
        """Clasificación básica por palabras clave como fallback"""
        
        message_lower = message.lower()
        
        # Palabras clave para cada intención
        product_keywords = [
            'busco', 'necesito', 'quiero', 'dame', 'muéstrame', 'precio',
            'cuánto cuesta', 'tienes', 'hay', 'stock', 'disponible',
            'cable', 'diferencial', 'automático', 'magnetotérmico', 'lámpara',
            'bombilla', 'led', 'interruptor', 'enchufe', 'regleta'
        ]
        
        technical_keywords = [
            'qué es', 'para qué sirve', 'cómo funciona', 'cómo instalar',
            'diferencia entre', 'compatible', 'especificaciones', 'manual',
            'instrucciones', 'tutorial'
        ]
        
        order_keywords = [
            'pedido', 'orden', 'envío', 'compré', 'comprado', 'factura',
            'seguimiento', 'track', '@'  # Email
        ]
        
        greeting_keywords = [
            'hola', 'buenos días', 'buenas tardes', 'buenas noches',
            'adiós', 'gracias', 'hasta luego'
        ]
        
        # Contar coincidencias
        product_score = sum(1 for kw in product_keywords if kw in message_lower)
        technical_score = sum(1 for kw in technical_keywords if kw in message_lower)
        order_score = sum(1 for kw in order_keywords if kw in message_lower)
        greeting_score = sum(1 for kw in greeting_keywords if kw in message_lower)
        
        # Determinar intención por mayor score
        scores = {
            UserIntent.PRODUCT_SEARCH: product_score,
            UserIntent.TECHNICAL_INFO: technical_score,
            UserIntent.ORDER_INQUIRY: order_score,
            UserIntent.GREETING: greeting_score
        }
        
        # Si es solo saludo y nada más
        if greeting_score > 0 and len(message.split()) <= 3:
            intent = UserIntent.GREETING
            confidence = 0.9
        else:
            # Obtener intención con mayor score
            intent = max(scores.items(), key=lambda x: x[1])[0]
            max_score = scores[intent]
            
            # Si no hay coincidencias claras
            if max_score == 0:
                intent = UserIntent.GENERAL_SUPPORT
                confidence = 0.5
            else:
                confidence = min(0.9, max_score * 0.3)
        
        return IntentClassification(
            intent=intent,
            confidence=confidence,
            entities={}
        )


# Instancia singleton
intent_classifier = IntentClassifierAgent()