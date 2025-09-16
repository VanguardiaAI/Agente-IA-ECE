"""
🎯 Intent Classifier Agent
Agente especializado en clasificar la intención del usuario usando IA
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from dotenv import load_dotenv

from .agent_interfaces import (
    IIntentClassifierAgent,
    IntentClassification,
    IntentClassificationError
)
from .shared_context import shared_context

# Cargar variables de entorno
load_dotenv("env.agent")

logger = logging.getLogger(__name__)

class IntentClassifierAgent(IIntentClassifierAgent):
    """
    Agente que clasifica la intención del mensaje del usuario
    usando IA para máxima precisión
    """
    
    def __init__(self):
        super().__init__(name="IntentClassifier")
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY no configurada")
        
        # Palabras de transición que siempre se deben filtrar
        self.transition_words = {
            "spanish": [
                "bien", "ok", "vale", "perfecto", "genial", "excelente",
                "ahora", "entonces", "además", "también", "igualmente",
                "bueno", "pues", "mira", "oye", "verás", "claro"
            ],
            "greetings": [
                "hola", "buenos días", "buenas tardes", "buenas noches",
                "buen día", "saludos", "qué tal", "cómo estás"
            ],
            "courtesy": [
                "por favor", "gracias", "muchas gracias", "te agradezco",
                "disculpa", "perdón", "con permiso"
            ]
        }
        
        # Intenciones soportadas
        self.supported_intents = [
            "product_search",      # Búsqueda de productos
            "order_inquiry",       # Consulta de pedidos
            "greeting",           # Saludo
            "confirmation",       # Confirmación/Acuerdo
            "refinement",         # Refinamiento de búsqueda anterior
            "price_inquiry",      # Consulta de precios
            "stock_inquiry",      # Consulta de stock
            "technical_support",  # Soporte técnico
            "complaint",          # Queja o reclamo
            "general_inquiry"     # Consulta general
        ]
        
        self.logger.info("✅ Intent Classifier Agent inicializado")
    
    async def process(self, input_data: Any, context: Dict[str, Any]) -> IntentClassification:
        """Procesa el mensaje y clasifica la intención"""
        if isinstance(input_data, str):
            message = input_data
        else:
            message = input_data.get("message", "")
        
        return await self.classify_intent(message, context)
    
    async def classify_intent(
        self, 
        message: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> IntentClassification:
        """
        Clasifica la intención del mensaje usando IA
        
        Args:
            message: Mensaje original del usuario
            session_context: Contexto de la sesión si existe
            
        Returns:
            Clasificación de intención con alta precisión
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🎯 Clasificando intención para: '{message[:50]}...'")
            
            # Preparar contexto para la IA
            context_info = self._prepare_context(session_context)
            
            # Llamar a la IA para clasificación
            classification = await self._classify_with_ai(message, context_info)
            
            # Limpiar mensaje de palabras de transición
            cleaned_message, removed_words = self._clean_message(message)
            classification["cleaned_message"] = cleaned_message
            classification["transition_words_removed"] = removed_words
            
            # Crear objeto de clasificación
            result = IntentClassification(
                intent=classification["intent"],
                confidence=classification["confidence"],
                cleaned_message=cleaned_message,
                transition_words_removed=removed_words,
                context_indicators=classification.get("context_indicators", {})
            )
            
            # Registrar métricas
            time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_metrics(time_ms, True)
            
            self.logger.info(f"✅ Intent clasificado: {result.intent} (confianza: {result.confidence:.2f})")
            self.logger.info(f"   Mensaje limpio: '{result.cleaned_message}'")
            if removed_words:
                self.logger.info(f"   Palabras removidas: {removed_words}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error clasificando intent: {e}")
            self.log_metrics(0, False)
            
            # Fallback básico
            return self._fallback_classification(message)
    
    async def _classify_with_ai(self, message: str, context_info: str) -> Dict[str, Any]:
        """Clasifica usando OpenAI API"""
        
        prompt = f'''
Eres un experto clasificador de intenciones para una tienda de material eléctrico.

MENSAJE DEL USUARIO: "{message}"

{context_info}

INTENCIONES DISPONIBLES:
1. product_search - Busca productos específicos
2. order_inquiry - Consulta sobre pedidos/órdenes
3. greeting - Saludo inicial
4. confirmation - Confirmación o acuerdo (ok, perfecto, vale)
5. refinement - Refinamiento de búsqueda anterior
6. price_inquiry - Pregunta específica sobre precios
7. stock_inquiry - Pregunta sobre disponibilidad
8. technical_support - Necesita ayuda técnica
9. complaint - Queja o problema
10. general_inquiry - Consulta general

REGLAS CRÍTICAS:
1. Si dice solo "ok", "perfecto", "vale", "bien" → confirmation
2. Si menciona productos eléctricos → product_search
3. Si menciona pedido, orden, factura → order_inquiry
4. Si es continuación de búsqueda anterior → refinement
5. Si pregunta precio sin buscar producto → price_inquiry
6. IGNORA palabras de transición para clasificar

ANALIZA y responde con JSON:
{{
    "intent": "la intención más probable",
    "confidence": 0.95,
    "reasoning": "explicación breve",
    "context_indicators": {{
        "has_product_mention": true/false,
        "has_greeting": true/false,
        "is_continuation": true/false,
        "has_technical_terms": true/false
    }},
    "secondary_intent": "segunda opción si aplica"
}}
'''

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Eres un clasificador experto de intenciones. SIEMPRE respondes con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,  # Baja para consistencia
                "max_tokens": 300,
                "response_format": {"type": "json_object"}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"Error en API: {error}")
                        raise IntentClassificationError(f"API error: {response.status}")
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    classification = json.loads(content)
                    self.logger.debug(f"Clasificación IA: {classification}")
                    
                    return classification
                    
        except Exception as e:
            logger.error(f"Error llamando a OpenAI: {e}")
            raise IntentClassificationError(str(e))
    
    def _clean_message(self, message: str) -> tuple[str, List[str]]:
        """
        Limpia el mensaje removiendo palabras de transición
        
        Returns:
            (mensaje_limpio, lista_palabras_removidas)
        """
        removed_words = []
        cleaned = message
        
        # Remover palabras de transición al inicio
        words_to_remove = []
        for category in self.transition_words.values():
            words_to_remove.extend(category)
        
        # Crear patrón para remover al inicio del mensaje
        for word in words_to_remove:
            # Buscar al inicio con posibles signos de puntuación
            pattern = rf'^{re.escape(word)}[\s,\.!¡\?¿]*'
            if re.match(pattern, cleaned.lower()):
                # Encontrar la coincidencia exacta para preservar caso
                match = re.match(pattern, cleaned, re.IGNORECASE)
                if match:
                    removed_part = cleaned[:match.end()]
                    cleaned = cleaned[match.end():].strip()
                    removed_words.append(word)
        
        # Remover comas o puntuación inicial sobrante
        cleaned = re.sub(r'^[,\.\s]+', '', cleaned).strip()
        
        # Si después de limpiar queda vacío, devolver el original sin saludos
        if not cleaned and message:
            # Buscar si hay algo más que solo palabras de transición
            remaining_words = []
            for word in message.lower().split():
                if word not in [w.lower() for w in words_to_remove]:
                    remaining_words.append(word)
            
            if remaining_words:
                cleaned = ' '.join(remaining_words)
            else:
                cleaned = ""  # Era solo palabras de transición
        
        return cleaned, removed_words
    
    def _prepare_context(self, session_context: Optional[Dict[str, Any]]) -> str:
        """Prepara información de contexto para la IA"""
        if not session_context:
            return "CONTEXTO: Primera interacción del usuario"
        
        context_parts = []
        
        # Mensajes recientes
        if "recent_messages" in session_context:
            recent = session_context["recent_messages"][-3:]  # Últimos 3
            if recent:
                context_parts.append("MENSAJES RECIENTES:")
                for msg in recent:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:100]
                    context_parts.append(f"  {role}: {content}")
        
        # Estado de refinamiento
        if session_context.get("in_refinement"):
            context_parts.append("ESTADO: Usuario está refinando búsqueda anterior")
        
        # Productos mostrados
        if session_context.get("products_shown"):
            count = len(session_context["products_shown"])
            context_parts.append(f"PRODUCTOS YA MOSTRADOS: {count}")
        
        return "\n".join(context_parts) if context_parts else "CONTEXTO: Sin contexto previo"
    
    def _fallback_classification(self, message: str) -> IntentClassification:
        """Clasificación de fallback sin IA"""
        message_lower = message.lower()
        
        # Detección simple basada en palabras clave
        if any(word in message_lower for word in ["hola", "buenos días", "buenas tardes"]):
            intent = "greeting"
        elif message_lower in ["ok", "perfecto", "vale", "bien", "gracias"]:
            intent = "confirmation"
        elif "@" in message or any(word in message_lower for word in ["pedido", "orden", "factura"]):
            intent = "order_inquiry"
        elif any(word in message_lower for word in ["precio", "cuesta", "valor", "€"]):
            intent = "price_inquiry"
        elif any(word in message_lower for word in ["stock", "disponible", "hay", "tienes"]):
            intent = "stock_inquiry"
        else:
            # Default a búsqueda de producto
            intent = "product_search"
        
        cleaned, removed = self._clean_message(message)
        
        return IntentClassification(
            intent=intent,
            confidence=0.6,  # Baja confianza en fallback
            cleaned_message=cleaned,
            transition_words_removed=removed,
            context_indicators={}
        )
    
    def get_supported_intents(self) -> List[str]:
        """Retorna la lista de intenciones soportadas"""
        return self.supported_intents.copy()

# Instancia singleton
intent_classifier = IntentClassifierAgent()