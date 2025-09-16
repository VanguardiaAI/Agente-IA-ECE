"""
💬 Response Generator Agent
Agente especializado en generar respuestas conversacionales
naturales y bien formateadas para el usuario
"""

import os
import json
import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from .agent_interfaces import (
    IResponseGeneratorAgent,
    GeneratedResponse,
    ValidationResult,
    ResponseGenerationError
)
from .shared_context import shared_context

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Tipos de respuesta soportados"""
    PRODUCTS = "products"              # Mostrar productos
    REFINEMENT = "refinement"          # Pregunta de refinamiento
    GREETING = "greeting"               # Saludo
    CONFIRMATION = "confirmation"      # Confirmación
    NO_RESULTS = "no_results"          # Sin resultados
    ERROR = "error"                    # Error
    HELP = "help"                      # Ayuda
    ORDER_STATUS = "order_status"      # Estado de pedido

class ResponseGeneratorAgent(IResponseGeneratorAgent):
    """
    Agente que genera respuestas conversacionales naturales
    basándose en los resultados validados y el contexto
    """
    
    def __init__(self):
        super().__init__(name="ResponseGenerator")
        
        # Templates conversacionales por tipo
        self.templates = {
            ResponseType.PRODUCTS: {
                "intro": [
                    "Encontré estos productos para ti:",
                    "Aquí están los productos que coinciden con tu búsqueda:",
                    "Te muestro los productos disponibles:",
                    "Estos son los productos que tenemos:"
                ],
                "single": [
                    "Encontré exactamente lo que buscas:",
                    "Tengo el producto perfecto para ti:",
                    "Este producto coincide con tu búsqueda:"
                ],
                "many": [
                    "Encontré {count} productos que podrían interesarte:",
                    "Tengo {count} opciones disponibles:",
                    "Te muestro los {count} mejores resultados:"
                ],
                "outro": [
                    "¿Alguno de estos productos es lo que buscas?",
                    "¿Te interesa alguno de estos productos?",
                    "¿Necesitas más información sobre algún producto?",
                    "¿Quieres ver más detalles de alguno?"
                ]
            },
            ResponseType.REFINEMENT: {
                "templates": [
                    "{question}",
                    "Para ayudarte mejor, {question}",
                    "Una pregunta: {question}",
                    "Necesito saber: {question}"
                ]
            },
            ResponseType.GREETING: {
                "templates": [
                    "¡Hola! 👋 Soy Eva, tu asistente de El Corte Eléctrico. ¿En qué puedo ayudarte hoy?",
                    "¡Bienvenido a El Corte Eléctrico! Soy Eva. ¿Qué producto estás buscando?",
                    "¡Hola! Estoy aquí para ayudarte a encontrar el material eléctrico que necesitas. ¿Qué buscas?",
                    "¡Buenos días! Soy Eva, tu asistente virtual. ¿Cómo puedo ayudarte?"
                ]
            },
            ResponseType.CONFIRMATION: {
                "templates": [
                    "Perfecto, ¿hay algo más en lo que pueda ayudarte?",
                    "Entendido. ¿Necesitas algo más?",
                    "De acuerdo. ¿Puedo ayudarte con otra cosa?",
                    "Muy bien. ¿Buscas algún otro producto?"
                ]
            },
            ResponseType.NO_RESULTS: {
                "templates": [
                    "Lo siento, no encontré productos que coincidan exactamente con tu búsqueda. ¿Podrías describir el producto de otra forma?",
                    "No tengo resultados para esa búsqueda. ¿Puedes darme más detalles o buscar algo similar?",
                    "No encontré lo que buscas. ¿Quieres intentar con otros términos?",
                    "Disculpa, no hay productos disponibles con esas características. ¿Buscamos algo diferente?"
                ]
            },
            ResponseType.ERROR: {
                "templates": [
                    "Disculpa, tuve un problema procesando tu solicitud. ¿Podrías intentarlo de nuevo?",
                    "Lo siento, ocurrió un error. Por favor, intenta nuevamente.",
                    "Hubo un problema técnico. ¿Puedes reformular tu búsqueda?",
                    "Perdón, algo salió mal. Intentémoslo otra vez."
                ]
            },
            ResponseType.HELP: {
                "templates": [
                    "Puedo ayudarte a encontrar productos eléctricos. Solo dime qué necesitas: lámparas, cables, automáticos, etc.",
                    "Estoy aquí para ayudarte con:\n• Búsqueda de productos\n• Información de precios\n• Disponibilidad\n• Especificaciones técnicas\n¿Qué necesitas?",
                    "Soy Eva, tu asistente para encontrar material eléctrico. Puedes preguntarme por productos específicos, marcas o categorías."
                ]
            }
        }
        
        # Formateo de productos
        self.product_format = {
            "compact": "📦 **{name}**\n   💰 ${price}\n   🏷️ SKU: {sku}",
            "normal": "📦 **{name}**\n   {description}\n   💰 Precio: ${price}\n   🏷️ SKU: {sku}\n   📊 Stock: {stock}",
            "detailed": "📦 **{name}**\n   {description}\n   🏢 Marca: {brand}\n   💰 Precio: ${price}\n   🏷️ SKU: {sku}\n   📊 Stock: {stock} unidades\n   🔧 {specs}"
        }
        
        # Emojis por categoría
        self.category_emojis = {
            "iluminación": "💡",
            "cables": "🔌",
            "protecciones": "⚡",
            "automatización": "🤖",
            "herramientas": "🔧",
            "instalación": "🏗️",
            "domótica": "🏠",
            "industrial": "🏭"
        }
        
        self.logger.info("✅ Response Generator Agent inicializado")
    
    async def process(self, input_data: Any, context: Dict[str, Any]) -> GeneratedResponse:
        """Procesa los resultados validados y genera respuesta"""
        
        # Extraer datos necesarios
        if isinstance(input_data, ValidationResult):
            validation_result = input_data
        else:
            # Crear ValidationResult desde dict
            validation_result = ValidationResult(
                valid_products=input_data.get("valid_products", []),
                invalid_products=input_data.get("invalid_products", []),
                needs_refinement=input_data.get("needs_refinement", False),
                refinement_question=input_data.get("refinement_question"),
                validation_score=input_data.get("validation_score", 0.5),
                rejection_reasons=input_data.get("rejection_reasons", [])
            )
        
        intent = context.get("intent", "product_search")
        
        return await self.generate_response(validation_result, intent, context)
    
    async def generate_response(
        self,
        validation_result: ValidationResult,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedResponse:
        """
        Genera una respuesta conversacional basada en los resultados
        
        Args:
            validation_result: Resultados validados
            intent: Intención del usuario
            context: Contexto adicional
            
        Returns:
            Respuesta generada y formateada
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"💬 Generando respuesta para intent: {intent}")
            
            # Determinar tipo de respuesta
            response_type = self._determine_response_type(
                validation_result,
                intent,
                context
            )
            
            self.logger.info(f"   Tipo de respuesta: {response_type.value}")
            
            # Generar contenido según el tipo
            if response_type == ResponseType.PRODUCTS:
                content = await self._generate_products_response(validation_result, context)
                
            elif response_type == ResponseType.REFINEMENT:
                content = await self._generate_refinement_response(validation_result, context)
                
            elif response_type == ResponseType.GREETING:
                content = self._generate_greeting_response()
                
            elif response_type == ResponseType.CONFIRMATION:
                content = self._generate_confirmation_response()
                
            elif response_type == ResponseType.NO_RESULTS:
                content = self._generate_no_results_response(validation_result, context)
                
            elif response_type == ResponseType.ERROR:
                content = self._generate_error_response(context)
                
            elif response_type == ResponseType.HELP:
                content = self._generate_help_response()
                
            else:
                content = "¿En qué puedo ayudarte?"
            
            # Generar acciones sugeridas
            suggested_actions = self._generate_suggested_actions(
                response_type,
                validation_result,
                context
            )
            
            # Preparar metadata
            metadata = {
                "response_type": response_type.value,
                "products_shown": len(validation_result.valid_products),
                "needs_refinement": validation_result.needs_refinement,
                "validation_score": validation_result.validation_score,
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
            
            # Crear respuesta
            response = GeneratedResponse(
                content=content,
                response_type=response_type.value,
                metadata=metadata,
                suggested_actions=suggested_actions
            )
            
            # Registrar métricas
            self.log_metrics(metadata["processing_time_ms"], True)
            
            self.logger.info(f"✅ Respuesta generada ({len(content)} caracteres)")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta: {e}")
            self.log_metrics(0, False)
            
            # Respuesta de error por defecto
            return GeneratedResponse(
                content="Disculpa, tuve un problema generando la respuesta. ¿Podrías intentarlo de nuevo?",
                response_type=ResponseType.ERROR.value,
                metadata={"error": str(e)},
                suggested_actions=["Reintentar búsqueda", "Contactar soporte"]
            )
    
    def _determine_response_type(
        self,
        validation_result: ValidationResult,
        intent: str,
        context: Optional[Dict[str, Any]]
    ) -> ResponseType:
        """Determina el tipo de respuesta a generar"""
        
        # Por intención
        if intent == "greeting":
            return ResponseType.GREETING
        
        if intent == "confirmation":
            return ResponseType.CONFIRMATION
        
        if intent == "help" or intent == "general_inquiry":
            return ResponseType.HELP
        
        if intent == "order_inquiry":
            return ResponseType.ORDER_STATUS
        
        # Por resultados de validación
        if validation_result.needs_refinement and validation_result.refinement_question:
            return ResponseType.REFINEMENT
        
        if not validation_result.valid_products:
            return ResponseType.NO_RESULTS
        
        if validation_result.valid_products:
            return ResponseType.PRODUCTS
        
        # Por defecto
        return ResponseType.ERROR
    
    async def _generate_products_response(
        self,
        validation_result: ValidationResult,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Genera respuesta mostrando productos"""
        
        products = validation_result.valid_products
        count = len(products)
        
        # Seleccionar intro apropiada
        if count == 1:
            intro = random.choice(self.templates[ResponseType.PRODUCTS]["single"])
        elif count > 10:
            intro = random.choice(self.templates[ResponseType.PRODUCTS]["many"]).format(count=count)
        else:
            intro = random.choice(self.templates[ResponseType.PRODUCTS]["intro"])
        
        # Formatear productos
        product_list = []
        format_style = "normal" if count <= 5 else "compact"
        
        for i, product in enumerate(products[:10], 1):  # Máximo 10 productos
            formatted = self._format_product(product, format_style)
            product_list.append(f"\n{i}. {formatted}")
        
        # Agregar outro si hay muchos productos
        outro = ""
        if count > 1:
            outro = "\n\n" + random.choice(self.templates[ResponseType.PRODUCTS]["outro"])
        
        # Si hay más productos de los mostrados
        if count > 10:
            outro = f"\n\n📋 *Mostrando 10 de {count} productos disponibles.*" + outro
        
        # Construir respuesta completa
        response = intro + "\n" + "\n".join(product_list) + outro
        
        return response
    
    async def _generate_refinement_response(
        self,
        validation_result: ValidationResult,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Genera respuesta de refinamiento contextual"""
        
        # Usar la pregunta específica generada por el validador
        if validation_result.refinement_question:
            question = validation_result.refinement_question
            
            # Si hay productos válidos, agregar contexto
            if validation_result.valid_products:
                count = len(validation_result.valid_products)
                if count <= 5:
                    # Pocos productos, mostrar algunos y preguntar
                    products_preview = "\n".join([
                        f"• {p.get('name', 'Sin nombre')[:50]}" 
                        for p in validation_result.valid_products[:3]
                    ])
                    return f"Encontré estos productos:\n{products_preview}\n\n{question}"
                else:
                    # Muchos productos, solo preguntar
                    return f"Tengo {count} opciones disponibles. {question}"
            else:
                # Sin productos, usar pregunta directamente
                return question
        
        # Fallback solo si no hay pregunta específica
        return "¿Podrías especificar qué características necesitas para el producto?"
    
    def _generate_greeting_response(self) -> str:
        """Genera respuesta de saludo"""
        return random.choice(self.templates[ResponseType.GREETING]["templates"])
    
    def _generate_confirmation_response(self) -> str:
        """Genera respuesta de confirmación"""
        return random.choice(self.templates[ResponseType.CONFIRMATION]["templates"])
    
    def _generate_no_results_response(
        self,
        validation_result: ValidationResult,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Genera respuesta cuando no hay resultados"""
        
        # Si hay pregunta de refinamiento específica, usarla
        if validation_result.refinement_question:
            return validation_result.refinement_question
        
        return random.choice(self.templates[ResponseType.NO_RESULTS]["templates"])
    
    def _generate_error_response(self, context: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta de error"""
        return random.choice(self.templates[ResponseType.ERROR]["templates"])
    
    def _generate_help_response(self) -> str:
        """Genera respuesta de ayuda"""
        return random.choice(self.templates[ResponseType.HELP]["templates"])
    
    def _format_product(self, product: Dict[str, Any], style: str = "normal") -> str:
        """Formatea un producto para mostrar"""
        
        # Preparar datos del producto
        name = product.get("name", "Producto sin nombre")
        description = (product.get("description", "") or "")[:100]
        price = product.get("price", 0)
        sku = product.get("sku", "N/A")
        stock = product.get("stock", 0)
        brand = product.get("brand", "Sin marca")
        
        # Formatear especificaciones si existen
        specs = ""
        if product.get("specifications"):
            spec_list = []
            for key, value in product.get("specifications", {}).items():
                spec_list.append(f"{key}: {value}")
            specs = " | ".join(spec_list[:3])  # Máximo 3 specs
        
        # Agregar emoji de categoría si existe
        category = product.get("category", "").lower()
        emoji = ""
        for cat_key, cat_emoji in self.category_emojis.items():
            if cat_key in category:
                emoji = cat_emoji + " "
                break
        
        # Aplicar formato según estilo
        if style == "compact":
            template = self.product_format["compact"]
        elif style == "detailed":
            template = self.product_format["detailed"]
        else:
            template = self.product_format["normal"]
        
        # Reemplazar variables
        formatted = template.format(
            name=emoji + name,
            description=description,
            price=f"{price:.2f}",
            sku=sku,
            stock=stock,
            brand=brand,
            specs=specs or "Sin especificaciones"
        )
        
        # Agregar score de relevancia si está disponible
        if product.get("relevance_score"):
            score = product["relevance_score"]
            if score >= 0.9:
                formatted += " ⭐ *Mejor coincidencia*"
            elif score >= 0.8:
                formatted += " ✨ *Recomendado*"
        
        return formatted
    
    def _generate_suggested_actions(
        self,
        response_type: ResponseType,
        validation_result: ValidationResult,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Genera acciones sugeridas para el usuario"""
        
        actions = []
        
        if response_type == ResponseType.PRODUCTS:
            if len(validation_result.valid_products) > 1:
                actions.append("Ver más detalles")
                actions.append("Comparar productos")
            if len(validation_result.valid_products) > 5:
                actions.append("Filtrar por marca")
                actions.append("Ordenar por precio")
            actions.append("Nueva búsqueda")
            
        elif response_type == ResponseType.REFINEMENT:
            actions.append("Responder pregunta")
            actions.append("Nueva búsqueda")
            actions.append("Ver todos los productos")
            
        elif response_type == ResponseType.NO_RESULTS:
            actions.append("Buscar producto similar")
            actions.append("Ver categorías")
            actions.append("Contactar soporte")
            
        elif response_type == ResponseType.GREETING:
            actions.append("Buscar producto")
            actions.append("Ver categorías")
            actions.append("Ayuda")
            
        elif response_type == ResponseType.ERROR:
            actions.append("Reintentar")
            actions.append("Contactar soporte")
            
        return actions[:4]  # Máximo 4 acciones
    
    async def format_products_list(
        self,
        products: List[Dict[str, Any]],
        style: str = "normal"
    ) -> str:
        """
        Formatea una lista de productos para mostrar
        Implementación de la interfaz
        """
        formatted_products = []
        
        for i, product in enumerate(products[:10], 1):
            formatted = self._format_product(product, style)
            formatted_products.append(f"{i}. {formatted}")
        
        intro = random.choice(self.templates[ResponseType.PRODUCTS]["intro"])
        
        return intro + "\n\n" + "\n\n".join(formatted_products)
    
    def generate_greeting(self, user_name: Optional[str] = None) -> str:
        """
        Genera un saludo personalizado
        Implementación de la interfaz
        """
        greeting = random.choice(self.templates[ResponseType.GREETING]["templates"])
        
        if user_name:
            greeting = greeting.replace("Hola", f"Hola {user_name}")
        
        return greeting
    
    def format_products(
        self,
        products: List[Dict[str, Any]],
        platform: str
    ) -> str:
        """
        Formatea productos para la plataforma específica
        Implementación de la interfaz
        """
        # Adaptar formato según plataforma
        if platform == "whatsapp":
            # WhatsApp tiene límites de caracteres
            style = "compact" if len(products) > 5 else "normal"
        elif platform == "web":
            style = "detailed"
        else:
            style = "normal"
        
        formatted_products = []
        for i, product in enumerate(products[:10], 1):
            formatted = self._format_product(product, style)
            formatted_products.append(f"{i}. {formatted}")
        
        return "\n\n".join(formatted_products)
    
    def get_response_templates(self) -> Dict[str, str]:
        """
        Retorna las plantillas de respuesta disponibles
        Implementación de la interfaz
        """
        # Convertir templates a formato simple
        simple_templates = {}
        
        for response_type, templates in self.templates.items():
            key = response_type.value if isinstance(response_type, ResponseType) else response_type
            
            if isinstance(templates, dict):
                # Aplanar estructura anidada
                for subkey, subtemplates in templates.items():
                    if isinstance(subtemplates, list):
                        simple_templates[f"{key}_{subkey}"] = subtemplates[0] if subtemplates else ""
                    else:
                        simple_templates[f"{key}_{subkey}"] = str(subtemplates)
            elif isinstance(templates, list):
                simple_templates[key] = templates[0] if templates else ""
            else:
                simple_templates[key] = str(templates)
        
        return simple_templates

# Instancia singleton
response_generator = ResponseGeneratorAgent()