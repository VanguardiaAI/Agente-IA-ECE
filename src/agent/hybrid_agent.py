#!/usr/bin/env python3
"""
Agente Híbrido de Atención al Cliente
Combina el sistema actual con capacidades multi-agente para mejor experiencia conversacional
ACTUALIZADO PARA FASE 3: Integrado con búsqueda híbrida y sistema FastAPI
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import logging

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Importar servicios del sistema existente (FASE 3 INTEGRATION)
from services.database import db_service
from services.embedding_service import embedding_service
from services.conversation_logger import conversation_logger
from services.woocommerce import WooCommerceService
from services.knowledge_base import knowledge_service
from services.conversation_memory import memory_service
from services.bot_config_service import bot_config_service

# Importar el sistema multi-agente
from .multi_agent_system import CustomerServiceMultiAgent, ConversationContext

# Importar utilidades de WhatsApp
from src.utils.whatsapp_utils import format_escalation_message
from src.utils.whatsapp_product_formatter import format_products_for_whatsapp

# Importar detector de escalamiento
from .escalation_detector import escalation_detector

# Cargar variables de entorno
load_dotenv("env.agent")

@dataclass
class HybridConversationState:
    """Estado de conversación híbrido que mantiene contexto persistente"""
    context: ConversationContext = field(default_factory=ConversationContext)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    session_id: str = ""
    last_response_time: datetime = field(default_factory=datetime.now)
    conversation_mode: str = "adaptive"  # adaptive, simple, multi_agent
    user_preference: str = "auto"  # auto, detailed, quick
    satisfaction_score: float = 0.0

class HybridCustomerAgent:
    """Agente híbrido que combina simplicidad con capacidades avanzadas"""
    
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai")
        self.model_name = os.getenv("MODEL_NAME", "gpt-5")
        self.temperature = float(os.getenv("TEMPERATURE", "1.0"))
        self.max_completion_tokens = int(os.getenv("MAX_TOKENS", "4000"))
        
        # Inicializar LLMs
        self.main_llm = self._initialize_llm()
        self.quick_llm = self._initialize_quick_llm()
        
        # Servicios integrados del sistema existente
        self.db_service = db_service
        self.embedding_service = embedding_service
        self.conversation_logger = conversation_logger
        self.knowledge_service = knowledge_service
        self.memory_service = memory_service
        self.wc_service = None
        
        # Sistemas de agentes
        self.multi_agent_system = None
        
        # Estado de conversación
        self.conversation_state = HybridConversationState()
        
        # Configuración adaptativa
        self.enable_multi_agent = True
        self.enable_smart_routing = True
        self.enable_context_memory = True
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Configuración del bot (se carga en initialize)
        self.bot_name = "Eva"  # Default
        self.company_name = "El Corte Eléctrico"  # Default
        self.welcome_message = "Hola, ¿en qué puedo ayudarte hoy?"  # Default
        
    def _initialize_llm(self):
        """Inicializa el LLM principal - siempre usa OpenAI"""
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_completion_tokens=self.max_completion_tokens
        )
    
    def _initialize_quick_llm(self):
        """Inicializa un LLM rápido para respuestas simples - usa gpt-5-mini para economía"""
        return ChatOpenAI(
            model="gpt-5-mini",
            temperature=1.0,
            max_completion_tokens=1500
        )
    
    async def initialize(self):
        """Inicializa todos los componentes del agente híbrido"""
        self.logger.info("🚀 Inicializando Agente Híbrido...")
        
        # Verificar que los servicios base estén inicializados
        if not self.db_service.initialized:
            await self.db_service.initialize()
            
        if not self.embedding_service.initialized:
            await self.embedding_service.initialize()
        
        # Cargar configuración del bot
        await self._load_bot_configuration()
        
        # Inicializar WooCommerce service
        self.wc_service = WooCommerceService()
        
        # Inicializar sistema multi-agente si está habilitado
        if self.enable_multi_agent:
            try:
                self.multi_agent_system = CustomerServiceMultiAgent(
                    bot_name=self.bot_name,
                    company_name=self.company_name
                )
                # Nota: Comentado temporalmente hasta revisar multi_agent_system
                # await self.multi_agent_system.initialize_mcp_client()
                self.logger.info("✅ Sistema multi-agente preparado")
            except Exception as e:
                self.logger.warning(f"⚠️ Error inicializando multi-agente: {e}")
                self.enable_multi_agent = False
        
        self.logger.info("✅ Agente Híbrido listo - Integrado con búsqueda híbrida")
    
    async def _load_bot_configuration(self):
        """Carga la configuración del bot desde el servicio de configuración"""
        try:
            # Cargar configuración básica del bot
            self.bot_name = await bot_config_service.get_setting("bot_name", "Eva")
            self.company_name = await bot_config_service.get_setting("company_name", "El Corte Eléctrico")
            self.welcome_message = await bot_config_service.get_setting("welcome_message", "Hola, ¿en qué puedo ayudarte hoy?")
            
            self.logger.info(f"✅ Configuración del bot cargada - Nombre: {self.bot_name}, Empresa: {self.company_name}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error cargando configuración del bot, usando valores por defecto: {e}")
            # Los valores por defecto ya están asignados en __init__
    
    async def process_message(self, message: str, user_id: str = "default", platform: str = "whatsapp") -> str:
        """Procesa un mensaje usando el enfoque híbrido adaptativo"""
        
        start_time = datetime.now()
        print(f"\n👤 Usuario ({user_id}) [{platform}]: {message}")
        
        # Verificar si debemos escalar antes de procesar
        session_id = self.conversation_state.session_id or f"session_{user_id}"
        previous_response = self.conversation_state.conversation_history[-1]["content"] if self.conversation_state.conversation_history else None
        
        should_escalate, reason, suggested_msg = escalation_detector.should_escalate(
            message=message,
            session_id=session_id,
            previous_response=previous_response
        )
        
        if should_escalate:
            self.logger.info(f"🔴 Escalamiento detectado: {reason}")
            return format_escalation_message(reason=reason, context={"suggested_message": suggested_msg}, platform=platform)
        
        # Actualizar historial
        self.conversation_state.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Análisis rápido del mensaje para determinar estrategia
        strategy = await self._determine_response_strategy(message)
        
        print(f"🎯 Estrategia seleccionada: {strategy}")
        
        # Procesar según la estrategia
        if strategy == "multi_agent" and self.enable_multi_agent and self.multi_agent_system:
            response = await self._process_with_multi_agent(message, platform)
        elif strategy == "tool_assisted":
            response = await self._process_with_tools(message, platform)
        elif strategy == "quick_response":
            response = await self._process_quick_response(message, platform)
        else:
            response = await self._process_standard_response(message, platform)
        
        # Actualizar historial con respuesta
        self.conversation_state.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy
        })
        
        # Actualizar contexto
        self._update_conversation_context(message, response)
        
        # Log a la base de datos
        try:
            await self.conversation_logger.log_message(
                session_id=self.conversation_state.session_id or f"session_{user_id}",
                user_id=user_id,
                message_type="conversation", 
                content=f"User: {message}\nAssistant: {response}",
                metadata={
                    "strategy": strategy,
                    "platform": platform,
                    "response_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                    "user_message": message,
                    "assistant_response": response
                },
                strategy=strategy,
                response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            print(f"Error logging conversation: {e}")
        
        self.logger.info(f"🤖 {self.bot_name} ({strategy}): {response[:100]}...")
        
        # Aplicar formateo final según la plataforma
        formatted_response = self._format_for_platform(response, platform)
        
        return formatted_response
    
    async def _determine_response_strategy(self, message: str) -> str:
        """Determina la estrategia de respuesta usando IA"""
        
        # Validar mensaje de entrada
        if not message or not message.strip():
            return "quick_response"
        
        # Truncar mensajes muy largos para el análisis
        analysis_message = message[:1000] + "..." if len(message) > 1000 else message
        
        # Obtener contexto de conversación reciente
        recent_context = self._get_recent_context_summary()
        
        strategy_prompt = f"""
Analiza la siguiente consulta de un cliente y determina la mejor estrategia de respuesta.

CONSULTA ACTUAL: "{analysis_message}"

{recent_context}

ESTRATEGIAS DISPONIBLES:

1. quick_response: Para saludos simples, despedidas, agradecimientos
   - Ejemplos: "Hola", "Gracias", "Adiós", "Buenos días"

2. tool_assisted: Para cuando necesitas acceder a datos del sistema
   - Búsqueda de productos
   - Consultas de pedidos (cuando menciona email o número de pedido)
   - Verificar stock o precios
   - Preguntas frecuentes (FAQ) sobre políticas, horarios, envíos, devoluciones
   - Información de la base de conocimiento de la empresa
   - Cualquier consulta que requiera datos de WooCommerce o knowledge base

3. multi_agent: Para consultas complejas con múltiples intenciones
   - Ejemplos: "Quiero comprar velas Y consultar mi pedido", consultas con múltiples preguntas

4. standard_response: Para responder preguntas sobre productos ya mostrados o información general
   - Comparaciones entre productos mencionados
   - Detalles sobre productos ya mostrados
   - Preguntas de seguimiento sobre la conversación
   - Aclaraciones o explicaciones

IMPORTANTE:
- Si preguntan sobre horarios, políticas, envíos, devoluciones, garantías, usa tool_assisted
- Si ya se mostraron productos y el usuario pregunta sobre ellos, usa standard_response
- Si el usuario pide "más información" sobre algo ya mencionado, usa standard_response
- Solo usa tool_assisted para búsquedas NUEVAS o consultas de políticas/FAQ

RESPONDE SOLO con el nombre de la estrategia: quick_response, tool_assisted, multi_agent, o standard_response
"""

        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI()
            
            response = await client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de consultas de atención al cliente. Determina la mejor estrategia de respuesta basándote en el tipo y complejidad de la consulta."},
                    {"role": "user", "content": strategy_prompt}
                ],
                temperature=1.0,
                max_completion_tokens=30
            )
            
            # Validar que tenemos una respuesta válida
            if not response.choices or not response.choices[0].message.content:
                print("⚠️ Respuesta vacía de IA, usando fallback")
                return self._fallback_strategy_selection(message)
            
            strategy_response = response.choices[0].message.content.strip()
            
            # Validar que la respuesta no esté vacía
            if not strategy_response:
                print("⚠️ Respuesta vacía de IA después de strip, usando fallback")
                return self._fallback_strategy_selection(message)
            
            # Limpiar y validar respuesta
            strategy = strategy_response.lower().replace(".", "").replace(",", "").strip()
            
            # Validar que la estrategia sea válida
            valid_strategies = ["quick_response", "tool_assisted", "multi_agent", "standard_response"]
            if strategy in valid_strategies:
                print(f"🤖 IA recomienda estrategia: {strategy}")
                return strategy
            else:
                print(f"⚠️ Estrategia inválida de IA: {strategy_response[:50]}{'...' if len(strategy_response) > 50 else ''}, usando fallback")
                return self._fallback_strategy_selection(message)
                
        except Exception as e:
            print(f"⚠️ Error en determinación de estrategia IA: {e}")
            return self._fallback_strategy_selection(message)
    
    def _fallback_strategy_selection(self, message: str) -> str:
        """Selección de estrategia de respaldo si falla la IA"""
        if not message or not message.strip():
            return "quick_response"
            
        message_lower = message.lower().strip()
        
        # Manejar mensajes muy largos
        if len(message) > 2000:
            return "standard_response"
        
        # Manejar mensajes solo con caracteres especiales o emojis
        if not any(c.isalpha() for c in message):
            return "standard_response"
        
        # Respuestas rápidas
        if any(greeting in message_lower for greeting in ["hola", "buenos", "buenas", "hi", "hello"]) and len(message_lower.split()) <= 3:
            return "quick_response"
        elif any(farewell in message_lower for farewell in ["adiós", "chao", "hasta", "bye", "gracias"]) and len(message_lower.split()) <= 3:
            return "quick_response"
        
        # Consultas que requieren herramientas
        elif any(keyword in message_lower for keyword in ["pedido", "orden", "producto", "vela", "perfume", "estado", "seguimiento", "busco", "necesito", "precio", "stock", 
                                                          "sobretensiones", "protector", "protección", "diferencial", "magnetotérmico", "cable", "enchufe", 
                                                          "interruptor", "lámpara", "bombilla", "led", "panel", "luminaria", "detector", "termostato", 
                                                          "radiador", "calefactor", "ventilador", "potencia", "voltaje", "amperios"]) or any(char.isdigit() for char in message) or "@" in message:
            return "tool_assisted"
        
        # Múltiples intenciones (detectar "y", "también", "además")
        elif any(connector in message_lower for connector in [" y ", " también", " además", " pero"]) and len(message_lower.split()) > 10:
            return "multi_agent"
        
        # Por defecto, respuesta estándar
        else:
            return "standard_response"
    
    async def _process_with_multi_agent(self, message: str, platform: str = "whatsapp") -> str:
        """Procesa usando el sistema multi-agente"""
        try:
            return await self.multi_agent_system.process_message(message)
        except Exception as e:
            print(f"⚠️ Error en multi-agente: {e}")
            
            # Si el usuario está pidiendo hablar con alguien, escalar directamente
            message_lower = message.lower()
            if any(phrase in message_lower for phrase in ["hablar con alguien", "tengo un problema", "necesito ayuda", "quiero hablar"]):
                session_id = self.conversation_state.session_id or "default"
                should_escalate, reason, suggested = escalation_detector.should_escalate(
                    message=message,
                    session_id=session_id
                )
                if should_escalate:
                    return format_escalation_message(reason=reason, context={"suggested_message": suggested}, platform=platform)
            
            return await self._process_standard_response(message, platform)
    
    async def _process_with_tools(self, message: str, platform: str = "whatsapp") -> str:
        """Procesa usando búsqueda híbrida directa y servicios del sistema"""
        
        try:
            # SIEMPRE buscar en knowledge base primero para contexto RAG
            knowledge_context = await self._search_knowledge_base(message)
            
            # Clasificar el tipo de consulta
            query_type = await self._classify_query_type(message)
            self.logger.info(f"📊 Tipo de consulta detectado: {query_type} para mensaje: '{message}'")
            
            if query_type == "product_search":
                return await self._handle_product_search(message, platform, knowledge_context)
            elif query_type == "order_inquiry":
                return await self._handle_order_inquiry(message, platform, knowledge_context)
            elif query_type == "stock_check":
                return await self._handle_stock_check(message, platform, knowledge_context)
            elif query_type == "faq_inquiry":
                return await self._handle_faq_inquiry(message, platform, knowledge_context)
            else:
                return await self._process_standard_response(message, platform, knowledge_context)
                
        except Exception as e:
            self.logger.error(f"Error en procesamiento con herramientas: {e}")
            # Verificar si debemos escalar debido al error
            session_id = self.conversation_state.session_id or "default"
            should_escalate, reason, _ = escalation_detector.should_escalate(
                message=message,
                session_id=session_id,
                error_occurred=True
            )
            if should_escalate:
                return format_escalation_message(reason="technical_error", context={"error": str(e)}, platform=platform)
            return await self._process_standard_response(message, platform)
    
    async def _classify_query_type(self, message: str) -> str:
        """Clasifica el tipo de consulta del usuario"""
        message_lower = message.lower()
        
        # Consulta de pedidos (verificar primero porque es más específico)
        order_keywords = ["pedido", "orden", "compra", "estado", "seguimiento", "envío", "factura", "mis pedidos"]
        # También detectar si menciona un email (patrón de email)
        has_email = "@" in message and "." in message.split("@")[-1] if "@" in message else False
        if any(keyword in message_lower for keyword in order_keywords) or has_email:
            return "order_inquiry"
        
        # Verificación de stock (también específico)
        stock_keywords = ["stock", "disponible", "disponibilidad", "hay", "quedan", "unidades"]
        if any(keyword in message_lower for keyword in stock_keywords):
            return "stock_check"
        
        # Preguntas frecuentes / FAQ / Políticas (alta prioridad)
        faq_keywords = ["horario", "horarios", "abierto", "cerrado", "abren", "cierran",
                       "devolver", "devolución", "devoluciones", "cambio", "cambios",
                       "garantía", "garantías", "política", "políticas",
                       "envío", "envíos", "entrega", "entregas", "cuánto tarda",
                       "forma de pago", "formas de pago", "pagar", "métodos de pago",
                       "contacto", "teléfono", "email", "dirección", "dónde están",
                       "reclamación", "reclamar", "queja"]
        if any(keyword in message_lower for keyword in faq_keywords):
            return "faq_inquiry"
        
        # Búsqueda de productos (más amplio)
        # Si menciona marcas conocidas o categorías de productos
        product_brands = ["gabarron", "ide", "simon", "bticino", "ledvance", "philips", "osram"]
        product_categories = ["ventilador", "calefactor", "lámpara", "bombilla", "interruptor", "enchufe", 
                            "cable", "led", "panel", "luminaria", "detector", "termostato", "radiador",
                            "diferencial", "magnetotérmico", "contactor", "relé", "transformador"]
        product_keywords = ["busco", "necesito", "quiero", "producto", "precio", "cuánto", "oferta", 
                          "descuento", "barato", "económico", "modelo", "referencia", "€", "dpn"]
        
        if (any(brand in message_lower for brand in product_brands) or
            any(category in message_lower for category in product_categories) or
            any(keyword in message_lower for keyword in product_keywords)):
            return "product_search"
        
        return "general"
    
    async def _handle_product_search(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Maneja búsquedas de productos usando búsqueda híbrida"""
        try:
            self.logger.info(f"🔍 BÚSQUEDA DE PRODUCTOS: '{message}'")
            
            # Generar embedding para la consulta
            embedding = await self.embedding_service.generate_embedding(message)
            
            # Realizar búsqueda híbrida
            results = await self.db_service.hybrid_search(
                query_text=message,
                query_embedding=embedding,
                content_types=["product"],
                limit=5
            )
            
            if not results:
                if platform == "wordpress":
                    return f"<p>Lo siento, no encontré productos que coincidan con '<strong>{message}</strong>'. ¿Podrías describir lo que buscas de otra manera?</p>"
                else:
                    return format_escalation_message(
                        reason="product_not_found",
                        context={"product_search": message},
                        platform=platform
                    )
            
            # Debug: Ver qué tipo de datos estamos recibiendo
            self.logger.info(f"Tipo de results: {type(results)}, Cantidad: {len(results)}")
            if results:
                self.logger.info(f"Tipo del primer resultado: {type(results[0])}")
                if isinstance(results[0], dict):
                    self.logger.info(f"Claves del primer resultado: {results[0].keys()}")
            
            # Agregar información relevante de knowledge base si existe
            additional_info = ""
            if knowledge_context:
                # Buscar información específica de envíos, garantías, etc.
                for doc in knowledge_context:
                    content = doc.get('content', '').lower()
                    if any(word in content for word in ['envío', 'envíos', 'entrega', 'garantía', 'devolución', 'cambio']):
                        additional_info = doc.get('content', '')[:300]  # Primeros 300 caracteres
                        break
            
            # Formatear respuesta según la plataforma
            if platform == "wordpress":
                # Importar utilidades de WordPress
                from src.utils.wordpress_utils import format_product_search_response
                
                # Convertir resultados al formato esperado por las utilidades
                products = []
                for result in results[:5]:
                    # Validar que result sea un diccionario
                    if isinstance(result, dict):
                        metadata = result.get('metadata', {})
                        images = metadata.get('images', [])
                        
                        # Debug images format
                        if images:
                            self.logger.info(f"Tipo de images: {type(images)}, Primer elemento: {type(images[0]) if images else 'empty'}")
                        
                        product = {
                            'name': result.get('title', 'Producto'),
                            'price': str(metadata.get('price', 0)),
                            'regular_price': str(metadata.get('regular_price', 0)),
                            'sale_price': str(metadata.get('sale_price', 0)),
                            'stock_status': metadata.get('stock_status', 'unknown'),
                            'permalink': metadata.get('permalink', ''),
                            'sku': metadata.get('sku', ''),
                            'images': images
                        }
                        products.append(product)
                    else:
                        self.logger.warning(f"Resultado inesperado tipo {type(result)}: {result}")
                
                if products:
                    return format_product_search_response(products, message)
                else:
                    return f"<p>Lo siento, encontré productos pero hubo un error al procesarlos. Por favor, intenta de nuevo.</p>"
            
            else:
                # Formato para WhatsApp - usar el formateador especializado
                # Convertir results al formato esperado por el formateador
                products = []
                for result in results:
                    if isinstance(result, dict):
                        products.append(result)
                
                # Usar el formateador especializado para WhatsApp
                response = format_products_for_whatsapp(products, message)
                
                # Agregar información adicional de knowledge base si existe
                if additional_info:
                    response += f"\n\n💡 *Información útil:*\n{additional_info}"
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda de productos: {e}", exc_info=True)
            if platform == "wordpress":
                return "<p>Lo siento, tuve un problema al buscar productos. ¿Podrías intentar de nuevo o ser más específico en tu búsqueda?</p>"
            else:
                return format_escalation_message(
                    reason="technical_error",
                    context={"error": str(e), "product_search": message},
                    platform=platform
                )
    
    async def _handle_order_inquiry(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Maneja consultas sobre pedidos usando las herramientas de WooCommerce"""
        try:
            # Extraer posible número de pedido o email
            import re
            
            # Buscar número de pedido
            order_numbers = re.findall(r'\b\d{3,}\b', message)
            
            # Buscar email
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
            
            # Guardar en contexto si encontramos datos
            if emails and self.conversation_state.context:
                self.conversation_state.context.customer_email = emails[0]
            if order_numbers and self.conversation_state.context:
                self.conversation_state.context.order_number = order_numbers[0]
            
            # Verificar si el usuario se refiere a un pedido mencionado anteriormente
            message_lower = message.lower()
            refers_to_previous = any(phrase in message_lower for phrase in [
                "ese pedido", "el pedido", "sobre ese", "cuando llega", "tiempo de entrega",
                "cuándo llegará", "fecha de entrega", "tracking", "seguimiento"
            ])
            
            # Si se refiere a un pedido anterior y tenemos contexto
            if refers_to_previous and self.conversation_state.context:
                # Buscar en el historial reciente si hay un pedido mencionado
                recent_messages = self.conversation_state.conversation_history[-6:] if self.conversation_state.conversation_history else []
                
                order_found = False
                no_orders_found = False
                saved_email = None
                
                for msg in recent_messages:
                    content = msg.get("content", "")
                    if msg.get("role") == "assistant":
                        # Verificar si se encontraron pedidos
                        if "Pedido #" in content:
                            # Extraer número de pedido del mensaje anterior
                            import re
                            pedido_match = re.search(r'Pedido #(\d+)', content)
                            if pedido_match:
                                order_id = pedido_match.group(1)
                                order_found = True
                                
                                # Responder sobre el tiempo de entrega
                                response = f"📦 Sobre el pedido #{order_id}:\n\n"
                                response += "Los pedidos en estado 'Procesando' normalmente se envían en 24-48 horas laborables.\n"
                                response += "Una vez enviado, recibirás un email con el número de seguimiento.\n\n"
                                response += "Tiempo estimado de entrega:\n"
                                response += "- Península: 24-72 horas desde el envío\n"
                                response += "- Baleares/Canarias: 3-5 días laborables\n\n"
                                response += "¿Necesitas más información sobre este pedido?"
                                
                                return response
                        
                        # Verificar si NO se encontraron pedidos
                        elif "No encontré pedidos" in content or "no encontré ningún pedido" in content.lower():
                            no_orders_found = True
                            # Intentar extraer el email mencionado
                            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
                            if email_match:
                                saved_email = email_match.group(1)
                
                # Si previamente no se encontraron pedidos
                if no_orders_found and saved_email:
                    response = f"Lo siento, pero como te mencioné antes, no encontré ningún pedido asociado al email {saved_email}. "
                    
                    # Respuesta específica según la pregunta
                    if "tracking" in message_lower or "seguimiento" in message_lower:
                        response += "Sin un pedido existente, no puedo proporcionarte información de tracking.\n\n"
                    elif "cuando" in message_lower or "llega" in message_lower or "entrega" in message_lower:
                        response += "Sin un pedido existente, no puedo proporcionarte información sobre tiempos de entrega.\n\n"
                    else:
                        response += "No tengo información adicional sobre pedidos para ese email.\n\n"
                    
                    response += "Si crees que esto es un error o realizaste el pedido con otro email, por favor contacta con nuestro equipo de soporte:\n\n"
                    response += "💬 WhatsApp: https://wa.me/34614218122\n\n"
                    response += "Ellos podrán ayudarte a localizar tu pedido y proporcionarte la información que necesitas."
                    
                    return response
                
                # Si tenemos email guardado en contexto, usar ese
                if hasattr(self.conversation_state.context, 'customer_email') and self.conversation_state.context.customer_email:
                    emails = [self.conversation_state.context.customer_email]
            
            # Si solo tenemos email, buscar pedidos del cliente
            if emails and not order_numbers:
                email = emails[0]
                try:
                    # Usar el servicio WooCommerce para buscar pedidos
                    if not self.wc_service:
                        self.wc_service = WooCommerceService()
                    
                    # Buscar pedidos del cliente
                    orders = await self.wc_service.search_orders_by_customer(email)
                    
                    if orders:
                        if platform == "wordpress":
                            from src.utils.wordpress_utils import format_text_response
                            response = f"He encontrado {len(orders)} pedido(s) asociados a {email}:\n\n"
                            for i, order in enumerate(orders[:5], 1):  # Máximo 5 pedidos
                                order_id = order.get('id', 'N/A')
                                status = order.get('status', 'unknown')
                                date = order.get('date_created', '')[:10]  # Solo fecha
                                total = order.get('total', '0')
                                
                                # Traducir estado
                                status_es = {
                                    'pending': 'Pendiente',
                                    'processing': 'Procesando',
                                    'completed': 'Completado',
                                    'cancelled': 'Cancelado',
                                    'on-hold': 'En espera'
                                }.get(status, status)
                                
                                response += f"{i}. Pedido #{order_id}\n"
                                response += f"   Fecha: {date}\n"
                                response += f"   Total: {total}€\n"
                                response += f"   Estado: {status_es}\n\n"
                            
                            response += "¿Sobre cuál pedido necesitas información?"
                            return format_text_response(response, preserve_breaks=True)
                        else:
                            response = f"He encontrado {len(orders)} pedido(s) asociados a {email}:\n\n"
                            for i, order in enumerate(orders[:5], 1):  # Máximo 5 pedidos
                                order_id = order.get('id', 'N/A')
                                status = order.get('status', 'unknown')
                                date = order.get('date_created', '')[:10]  # Solo fecha
                                total = order.get('total', '0')
                                
                                # Traducir estado
                                status_es = {
                                    'pending': 'Pendiente',
                                    'processing': 'Procesando',
                                    'completed': 'Completado',
                                    'cancelled': 'Cancelado',
                                    'on-hold': 'En espera'
                                }.get(status, status)
                                
                                response += f"{i}. Pedido #{order_id}\n"
                                response += f"   📅 Fecha: {date}\n"
                                response += f"   💰 Total: {total}€\n"
                                response += f"   📦 Estado: {status_es}\n\n"
                            
                            response += "¿Sobre cuál pedido necesitas información?"
                            return response
                    else:
                        # Si no encuentra pedidos, escalar para verificación manual
                        response = f"No encontré pedidos asociados al email {email} en mi sistema.\n\n" + format_escalation_message(
                            reason="order_help",
                            context={"email": email, "message": "Cliente busca pedidos con su email"},
                            platform=platform
                        )
                        if platform == "wordpress":
                            from src.utils.wordpress_utils import format_text_response
                            return format_text_response(response, preserve_breaks=True)
                        return response
                        
                except Exception as e:
                    self.logger.error(f"Error buscando pedidos: {e}")
                    return format_escalation_message(
                        reason="order_help",
                        context={"email": email},
                        platform=platform
                    )
            
            # Si tenemos ambos datos, buscar el pedido específico
            elif order_numbers and emails:
                order_id = order_numbers[0]
                email = emails[0]
                response = f"Buscando el pedido #{order_id} para {email}... Por seguridad, esta consulta requiere verificación adicional.\n\n" + format_escalation_message(
                    reason="order_help",
                    context={"order_id": order_id, "email": email},
                    platform=platform
                )
                if platform == "wordpress":
                    from src.utils.wordpress_utils import format_text_response
                    return format_text_response(response, preserve_breaks=True)
                return response
            
            # Si solo tenemos número de pedido
            elif order_numbers:
                response = f"Para consultar el pedido #{order_numbers[0]}, necesito verificar tu identidad. ¿Podrías proporcionarme el email asociado a la compra?"
                if platform == "wordpress":
                    from src.utils.wordpress_utils import format_text_response
                    return format_text_response(response, preserve_breaks=True)
                return response
            
            # Si no tenemos ningún dato
            else:
                response = "Para ayudarte con tu pedido, necesito:\n- El número de pedido, o\n- El email usado en la compra\n\n¿Podrías proporcionarme alguno de estos datos?"
                if platform == "wordpress":
                    from src.utils.wordpress_utils import format_text_response
                    return format_text_response(response, preserve_breaks=True)
                return response
                
        except Exception as e:
            self.logger.error(f"Error en consulta de pedidos: {e}")
            return format_escalation_message(
                reason="order_help",
                context={"error": str(e)},
                platform=platform
            )
    
    async def _handle_stock_check(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Maneja verificaciones de stock"""
        try:
            # Realizar búsqueda de productos primero
            embedding = await self.embedding_service.generate_embedding(message)
            
            results = await self.db_service.hybrid_search(
                query_text=message,
                query_embedding=embedding,
                content_types=["product"],
                limit=3
            )
            
            if not results:
                response = "No encontré ese producto. ¿Cuál buscas específicamente?"
                if platform == "wordpress":
                    from src.utils.wordpress_utils import format_text_response
                    return format_text_response(response, preserve_breaks=True)
                return response
            
            response = ""
            
            for result in results[:2]:  # Solo mostrar 2 primeros
                title = result.get('title', 'Producto')
                metadata = result.get('metadata', {})
                stock_status = metadata.get('stock_status', 'unknown')
                stock_quantity = metadata.get('stock_quantity', 0)
                
                if platform == "wordpress":
                    if stock_status == 'instock':
                        if stock_quantity > 0:
                            response += f"{title} - {stock_quantity} unidades disponibles\n"
                        else:
                            response += f"{title} - En stock\n"
                    else:
                        response += f"{title} - Sin stock\n"
                else:
                    if stock_status == 'instock':
                        if stock_quantity > 0:
                            response += f"✅ {title} - {stock_quantity} unidades\n"
                        else:
                            response += f"✅ {title} - En stock\n"
                    else:
                        response += f"❌ {title} - Sin stock\n"
            
            if platform == "wordpress":
                from src.utils.wordpress_utils import format_text_response
                return format_text_response(response.strip(), preserve_breaks=True)
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error verificando stock: {e}")
            return format_escalation_message(
                reason="stock_error",
                context={"error": str(e), "query": message},
                platform=platform
            )
    
    async def _handle_faq_inquiry(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Maneja preguntas frecuentes usando la knowledge base"""
        try:
            self.logger.info(f"📚 CONSULTA FAQ: '{message}'")
            
            # Si no tenemos contexto, buscar en knowledge base
            if not knowledge_context:
                knowledge_context = await self._search_knowledge_base(message)
            
            if not knowledge_context:
                # Si no encontramos nada en knowledge base, usar respuesta genérica
                return await self._process_standard_response(message, platform)
            
            # Construir respuesta basada en el contexto encontrado
            response = ""
            
            # Tomar el documento más relevante (el primero)
            most_relevant = knowledge_context[0]
            content = most_relevant.get('content', '')
            
            # Validar que tenemos contenido
            if not content or not content.strip():
                self.logger.warning(f"Empty content in knowledge base for query: '{message}'")
                return await self._process_standard_response(message, platform)
            
            # Formatear respuesta según plataforma
            if platform == "wordpress":
                from src.utils.wordpress_utils import format_text_response
                response = f"<h4>{most_relevant.get('title', 'Información')}</h4>\n"
                response += f"<p>{content}</p>"
                
                # Si hay más documentos relevantes, mencionarlos
                if len(knowledge_context) > 1:
                    response += "\n<p><em>También podría interesarte:</em></p>\n<ul>"
                    for doc in knowledge_context[1:3]:  # Máximo 2 adicionales
                        response += f"<li>{doc.get('title', 'Información adicional')}</li>"
                    response += "</ul>"
                
                return format_text_response(response, preserve_breaks=True)
            else:
                # WhatsApp
                response = f"📋 *{most_relevant.get('title', 'Información')}*\n\n"
                response += content
                
                # Si hay más documentos relevantes, mencionarlos
                if len(knowledge_context) > 1:
                    response += "\n\n💡 _También podría interesarte:_"
                    for doc in knowledge_context[1:3]:  # Máximo 2 adicionales
                        response += f"\n• {doc.get('title', 'Información adicional')}"
                
                return response
                
        except Exception as e:
            self.logger.error(f"Error en consulta FAQ: {e}")
            # Fallback a respuesta estándar
            return await self._process_standard_response(message, platform)
    
    async def _process_quick_response(self, message: str, platform: str = "whatsapp") -> str:
        """Procesa respuestas rápidas para consultas simples"""
        
        quick_prompt = f"""
Eres {self.bot_name}, asistente virtual de {self.company_name}.

INFORMACIÓN CRÍTICA:
- NO HAY TIENDA FÍSICA. Somos una tienda exclusivamente online.
- Tenemos más de 4,500 productos eléctricos online.
- Web: https://elcorteelectrico.com
- WhatsApp directo: https://wa.me/34614218122

REGLAS: 
- Responde en máximo 1-2 frases. Sé amable pero muy breve.
- NUNCA prometas avisar o notificar al cliente cuando algo esté disponible
- NO ofrezcas enviar recordatorios o avisos futuros
- NO INVENTES información que no tengas
Cliente: {self.conversation_state.context.customer_name or 'Cliente'}
"""
        
        try:
            messages = [
                SystemMessage(content=quick_prompt),
                HumanMessage(content=f"Cliente dice: {message}")
            ]
            response = await self.quick_llm.ainvoke(messages)
            
            # Validar respuesta
            if not response.content or response.content.strip() == "":
                self.logger.warning(f"Empty quick response for message: '{message}'")
                return f"¡Hola! Soy {self.bot_name} y estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?"
            
            # Formatear respuesta según la plataforma
            if platform == "wordpress":
                from src.utils.wordpress_utils import format_text_response
                return format_text_response(response.content, preserve_breaks=True)
            else:
                return response.content
        except Exception as e:
            self.logger.error(f"Error en respuesta rápida: {e}")
            return f"¡Hola! Soy {self.bot_name} y estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?"
    
    async def _search_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """Buscar información relevante en la base de conocimientos"""
        try:
            # Buscar en knowledge base primero
            knowledge_results = await self.knowledge_service.search_knowledge(
                query=query,
                limit=3
            )
            
            # Si no hay resultados en knowledge, buscar en productos
            if not knowledge_results:
                embedding = await self.embedding_service.generate_embedding(query)
                product_results = await self.db_service.hybrid_search(
                    query_text=query,
                    query_embedding=embedding,
                    content_types=["product"],
                    limit=2
                )
                return product_results
            
            return knowledge_results
            
        except Exception as e:
            self.logger.error(f"Error buscando en knowledge base: {e}")
            return []
    
    async def _process_standard_response(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Procesa usando el LLM principal con contexto de knowledge base"""
        
        # Verificar si es una búsqueda de productos que no fue detectada
        message_lower = message.lower()
        product_keywords = ["quiero", "busco", "necesito", "tienen", "precio", "costo", "cuánto", 
                          "comprar", "producto", "artículo", "disponible", "stock", "hay",
                          "muéstrame", "enséñame", "dame", "opciones", "alternativas",
                          # Términos eléctricos específicos
                          "termo", "termostato", "ventilador", "diferencial", "magnetotérmico",
                          "cable", "enchufe", "interruptor", "lámpara", "led", "bombilla",
                          "motor", "transformador", "fusible", "relé", "contactor"]
        
        # Si parece una búsqueda de productos, usar el handler específico
        if any(keyword in message_lower for keyword in product_keywords):
            # Verificar que no sea una pregunta sobre un pedido
            if not any(word in message_lower for word in ["pedido", "orden", "compra realizada", "factura"]):
                self.logger.info(f"Detectada búsqueda de productos en standard_response: {message}")
                return await self._handle_product_search(message, platform, knowledge_context)
        
        # Si no se pasó contexto, buscar información relevante
        if not knowledge_context:
            knowledge_context = await self._search_knowledge_base(message)
        
        # Crear prompt con contexto de knowledge base
        system_prompt = self._create_standard_prompt(message)
        
        # Añadir contexto de knowledge base si existe
        if knowledge_context:
            context_text = "\n\nINFORMACIÓN RELEVANTE DE LA BASE DE CONOCIMIENTOS:\n"
            for idx, doc in enumerate(knowledge_context, 1):
                doc_type = doc.get('doc_type', 'general')
                title = doc.get('title', 'Información')
                content = doc.get('content', '')
                
                # Limitar longitud del contenido
                if len(content) > 500:
                    content = content[:500] + "..."
                
                context_text += f"\n{idx}. [{doc_type.upper()}] {title}:\n{content}\n"
            
            system_prompt += context_text
            system_prompt += "\nUSA ESTA INFORMACIÓN PERO RESPONDE DE FORMA BREVE. Si el cliente quiere más detalles, los pedirá."
        
        try:
            # Recuperar contexto de memoria si hay user_id
            user_context = None
            if self.conversation_state.context.customer_email:
                user_context = await self.memory_service.retrieve_user_context(
                    user_id=self.conversation_state.context.customer_email,
                    current_query=message
                )
            
            # Añadir contexto de memoria al prompt si existe
            if user_context and user_context["interaction_count"] > 0:
                memory_prompt = self.memory_service.get_conversation_prompt(user_context)
                system_prompt = memory_prompt + "\n" + system_prompt
            
            messages = [SystemMessage(content=system_prompt)] + self._get_recent_context()
            messages.append(HumanMessage(content=message))
            
            # Filtrar mensajes vacíos
            valid_messages = []
            for msg in messages:
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    valid_messages.append(msg)
            
            if not valid_messages:
                return f"Hola, soy {self.bot_name}, tu asistente de atención al cliente. ¿En qué puedo ayudarte hoy?"
            
            response = await self.main_llm.ainvoke(valid_messages)
            
            # Validar respuesta
            if not response.content or response.content.strip() == "":
                self.logger.warning(f"Empty response from LLM for message: '{message}' - Using fallback")
                return self._get_fallback_response(message, platform)
            
            # Formatear respuesta según la plataforma
            if platform == "wordpress":
                from src.utils.wordpress_utils import format_text_response
                return format_text_response(response.content, preserve_breaks=True)
            else:
                return response.content
            
        except Exception as e:
            print(f"⚠️ Error en respuesta estándar: {e}")
            return self._get_fallback_response(message, platform)
    
    def _get_fallback_response(self, message: str, platform: str = "whatsapp") -> str:
        """Respuesta de emergencia cuando todo falla"""
        if "hola" in message.lower() or "buenos" in message.lower():
            response = f"¡Hola! Soy {self.bot_name} de {self.company_name}. ¿En qué puedo ayudarte?"
        elif "producto" in message.lower() or "diferencial" in message.lower() or "cable" in message.lower():
            response = "Tenemos más de 4,500 productos eléctricos. ¿Qué necesitas específicamente?"
        elif "pedido" in message.lower() or "orden" in message.lower():
            response = "Para consultar tu pedido necesito el número de pedido y email."
        else:
            response = format_escalation_message(reason="general", platform=platform)
        
        # Formatear según plataforma
        if platform == "wordpress":
            # Verificar si la respuesta contiene productos con formato markdown
            import re
            has_product_links = bool(re.search(r'\[.*?\]\(https?://.*?\)', response))
            
            if has_product_links:
                # Convertir markdown de productos a HTML
                from src.utils.wordpress_utils import convert_markdown_products_to_html
                return convert_markdown_products_to_html(response)
            else:
                # Respuesta normal sin productos
                from src.utils.wordpress_utils import format_text_response
                return format_text_response(response, preserve_breaks=True)
        else:
            return response
    

    
    def _create_standard_prompt(self, message: str) -> str:
        """Crea prompt para respuestas estándar"""
        
        # Obtener contexto reciente para mejor comprensión
        recent_context = self._get_recent_context_summary()
        
        return f"""
Eres {self.bot_name}, asistente virtual de {self.company_name}. Eres una asistente conversacional natural.

CONTEXTO DE LA CONVERSACIÓN:
{recent_context}

INFORMACIÓN CRÍTICA DE LA EMPRESA:
- NO HAY TIENDA FÍSICA. Somos una tienda exclusivamente online.
- Tenemos más de 4,500 productos eléctricos en nuestro catálogo online.
- Toda la venta es a través de la web: https://elcorteelectrico.com
- WhatsApp soporte: +34614218122
- Link directo WhatsApp: https://wa.me/34614218122

INSTRUCCIONES IMPORTANTES:
1. RESPONDE DE FORMA NATURAL Y CONVERSACIONAL, no como un robot
2. Si el usuario pregunta sobre productos YA MOSTRADOS, responde sobre ESOS productos específicos
3. NO busques nuevos productos si el usuario está preguntando sobre los que ya viste
4. Sé específica cuando hables de productos mostrados (usa nombres y precios)
5. Mantén la conversación fluida con preguntas naturales cuando sea apropiado
6. Solo escala a WhatsApp si realmente no puedes ayudar
7. NUNCA prometas avisar al cliente cuando algo esté listo o disponible
8. NO ofrezcas notificaciones, recordatorios o avisos futuros
9. Si preguntan por disponibilidad futura, sugiere que consulten más adelante o contacten por WhatsApp
10. NUNCA INVENTES INFORMACIÓN: Si no conoces un dato específico (como el SKU de un producto), di claramente "No tengo esa información específica" y ofrece buscar productos relacionados
11. NO HAY TIENDA FÍSICA: Si preguntan por la ubicación o si pueden visitar, aclara que somos solo online
12. Cuando el usuario pida más información sobre un producto específico, SIEMPRE proporciona el enlace del producto si está disponible

INFORMACIÓN DEL CLIENTE:
- Nombre: {self.conversation_state.context.customer_name or 'Cliente'}

DATOS BÁSICOS DE LA EMPRESA:
- Especialistas en material eléctrico  
- Más de 4,500 productos en catálogo
- Envío gratis > 100€ (península)
- Precios incluyen IVA (21%)
- WhatsApp soporte: +34 614 21 81 22
- Link directo WhatsApp: https://wa.me/34614218122
- NO INVENTES números de teléfono (como 900) ni emails (como ventas@)
- Para soporte SIEMPRE proporciona el link de WhatsApp: https://wa.me/34614218122
- NO HAY TIENDA FÍSICA - Solo venta online

CONSULTA ACTUAL: {message}

Responde de forma natural, como lo haría un vendedor experto y amable. Si el cliente pregunta sobre productos específicos que ya se mostraron, habla de ESOS productos, no busques otros nuevos. Si no tienes información específica sobre algo, sé honesta y dilo claramente.
"""
    
    def _get_recent_context(self) -> List:
        """Obtiene contexto reciente de la conversación"""
        recent_messages = []
        
        # Obtener últimos 4 mensajes para contexto
        for msg in self.conversation_state.conversation_history[-4:]:
            if msg["role"] == "user":
                recent_messages.append(HumanMessage(content=msg["content"]))
            else:
                recent_messages.append(AIMessage(content=msg["content"]))
        
        return recent_messages
    
    def _get_recent_context_summary(self) -> str:
        """Obtiene un resumen del contexto reciente de la conversación"""
        if not self.conversation_state.conversation_history:
            return "No hay contexto previo"
        
        # Tomar últimos 3 intercambios
        recent = self.conversation_state.conversation_history[-6:]  # 3 pares user/assistant
        
        summary = "Contexto reciente:\n"
        for msg in recent:
            role = "Usuario" if msg["role"] == "user" else self.bot_name
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            summary += f"- {role}: {content}\n"
        
        return summary
    
    def _update_conversation_context(self, message: str, response: str):
        """Actualiza el contexto de la conversación"""
        context = self.conversation_state.context
        
        # Extraer entidades básicas
        message_lower = message.lower()
        
        # Extraer email
        import re
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        emails = re.findall(email_pattern, message)
        if emails and not context.customer_email:
            context.customer_email = emails[0]
        
        # Extraer número de pedido
        order_pattern = r'\b#?(\d{3,6})\b'
        orders = re.findall(order_pattern, message)
        if orders and not context.order_number:
            context.order_number = orders[0]
        
        # Extraer productos mencionados
        product_keywords = ['vela', 'perfume', 'aroma', 'lavanda', 'vainilla', 'canela', 'rosa']
        mentioned_products = [p for p in product_keywords if p in message_lower]
        if mentioned_products:
            context.preferred_products.extend(mentioned_products)
            # Remover duplicados
            context.preferred_products = list(set(context.preferred_products))
        
        # Actualizar resumen
        context.turn_count += 1
        context.conversation_summary += f" Usuario: {message[:50]}... Respuesta: {response[:50]}..."
        
        # Mantener resumen manejable
        if len(context.conversation_summary) > 500:
            context.conversation_summary = context.conversation_summary[-400:]
    

    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la conversación"""
        
        # Obtener la última estrategia usada
        last_strategy = "unknown"
        if self.conversation_state.conversation_history:
            for msg in reversed(self.conversation_state.conversation_history):
                if msg.get("role") == "assistant" and "strategy" in msg:
                    last_strategy = msg["strategy"]
                    break
        
        return {
            "turn_count": len(self.conversation_state.conversation_history) // 2,
            "current_intent": getattr(self.conversation_state.context, 'current_intent', 'unknown'),
            "last_strategy_used": last_strategy,
            "customer_info": {
                "name": self.conversation_state.context.customer_name,
                "email": self.conversation_state.context.customer_email,
                "order_number": getattr(self.conversation_state.context, 'order_number', None)
            },
            "entities_extracted": len(self.conversation_state.context.extracted_entities),
            "search_system": "hybrid_integrated",
            "multi_agent_enabled": self.enable_multi_agent,
            "conversation_mode": self.conversation_state.conversation_mode
        }
    
    def _format_for_platform(self, response: str, platform: str) -> str:
        """
        Aplica formateo específico según la plataforma
        
        Args:
            response: Respuesta original
            platform: Plataforma destino (whatsapp, wordpress, etc.)
            
        Returns:
            Respuesta formateada para la plataforma
        """
        if not response:
            return response
        
        if platform == "whatsapp":
            # Eliminar tags HTML si existen
            import re
            
            # Eliminar todos los tags HTML
            response = re.sub(r'<[^>]+>', '', response)
            
            # Convertir entidades HTML
            response = response.replace('&nbsp;', ' ')
            response = response.replace('&quot;', '"')
            response = response.replace('&apos;', "'")
            response = response.replace('&lt;', '<')
            response = response.replace('&gt;', '>')
            response = response.replace('&amp;', '&')
            
            # Limitar longitud para WhatsApp (4096 caracteres)
            if len(response) > 4000:
                response = response[:3997] + "..."
            
            # Asegurar que no haya espacios múltiples (pero preservar saltos de línea)
            # Reemplazar múltiples espacios horizontales con uno solo
            response = re.sub(r'[ \t]+', ' ', response)
            # Reemplazar más de 2 saltos de línea consecutivos con solo 2
            response = re.sub(r'\n{3,}', '\n\n', response)
            # Limpiar espacios al final de las líneas
            response = re.sub(r' +\n', '\n', response)
            
            # Agregar emoji de marca si no hay emojis en la respuesta
            if not any(ord(char) > 127 for char in response[:50]):  # Check primeros 50 chars
                response = "💬 " + response
            
        elif platform == "wordpress":
            # Para WordPress, NO agregar tags HTML - el widget los manejará
            # Solo limpiar asteriscos que pueden venir de otros formatos
            import re
            
            # NO convertir asteriscos a HTML - dejarlos para que el widget los procese
            # Solo asegurar que el formato sea limpio
            
            # Reemplazar múltiples espacios horizontales con uno solo
            response = re.sub(r'[ \t]+', ' ', response)
            # Reemplazar más de 2 saltos de línea consecutivos con solo 2
            response = re.sub(r'\n{3,}', '\n\n', response)
            # Limpiar espacios al final de las líneas
            response = re.sub(r' +\n', '\n', response)
        
        return response.strip()
    
    def reset_conversation(self):
        """Reinicia la conversación"""
        self.conversation_state = HybridConversationState()
        print("🔄 Conversación reiniciada")

# Función de prueba
async def test_hybrid_agent():
    """Prueba el agente híbrido"""
    print("🚀 Iniciando Agente Híbrido...")
    
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    test_messages = [
        "Hola, soy María",
        "Busco velas de lavanda para mi casa",
        "¿Tienen productos en oferta?",
        "Quiero saber sobre mi pedido #1817, mi email es maria@test.com",
        "¿Cuánto cuesta el envío a Barcelona?",
        "Tengo una queja sobre un producto defectuoso",
        "Gracias por tu ayuda, adiós"
    ]
    
    print("\n" + "="*60)
    print("🧪 PRUEBA DEL AGENTE HÍBRIDO")
    print("="*60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- MENSAJE {i} ---")
        response = await agent.process_message(message, user_id="test_user")
        print("\n" + "-"*40)
    
    # Mostrar estadísticas finales
    stats = agent.get_conversation_stats()
    print(f"\n📊 Estadísticas finales:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_hybrid_agent())