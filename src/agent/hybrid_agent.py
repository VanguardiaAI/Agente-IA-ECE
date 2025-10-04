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

# Importar el sistema multi-agente y el refinador de búsqueda
from .multi_agent_system import CustomerServiceMultiAgent, ConversationContext
from .search_refiner_agent import search_refiner, RefinementState

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
        self.model_name = os.getenv("MODEL_NAME", "gpt-5")  # Usar GPT-5
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
                # Inicializar MCP client y construir el grafo de agentes
                await self.multi_agent_system.initialize_mcp_client()
                await self.multi_agent_system.build_agent_graph()
                self.logger.info("✅ Sistema multi-agente inicializado y listo")
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
        if strategy == "multi_agent":
            # Log debug info
            self.logger.info(f"🔍 Multi-agent check: enabled={self.enable_multi_agent}, system={self.multi_agent_system is not None}")
            
            if self.enable_multi_agent and self.multi_agent_system:
                response = await self._process_with_multi_agent(message, platform)
            else:
                # Fallback: usar _process_with_multi_agent directamente sin multi_agent_system
                self.logger.info("⚠️ Multi-agent system no disponible, usando proceso directo con agente inteligente")
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
    
    async def _call_gpt5_responses_api(self, prompt: str, system_prompt: str = "", max_tokens: int = 100) -> Any:
        """Llama a la Responses API de GPT-5 correctamente"""
        import aiohttp
        import json
        
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Combinar system y user prompt
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        data = {
            "model": "gpt-5-mini",
            "input": full_prompt,
            "reasoning": {
                "effort": "minimal"  # Minimal para respuestas rápidas
            },
            "text": {
                "verbosity": "low"  # Respuestas concisas
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Error en Responses API: {response.status} - {error_text}")
                        # Devolver objeto similar a Chat Completions para compatibilidad
                        return type('obj', (object,), {
                            'choices': [type('obj', (object,), {
                                'message': type('obj', (object,), {'content': ''})
                            })()]
                        })()
                    
                    result = await response.json()
                    
                    # Extraer el contenido de la respuesta GPT-5
                    content = ''
                    output = result.get('output', [])
                    if output and len(output) > 1:
                        message = output[1]  # El mensaje es el segundo elemento
                        if message.get('type') == 'message' and message.get('content'):
                            content_array = message.get('content', [])
                            if content_array and isinstance(content_array, list):
                                for content_item in content_array:
                                    if content_item.get('type') == 'output_text':
                                        content = content_item.get('text', '')
                                        break
                    
                    # Devolver objeto similar a Chat Completions para compatibilidad
                    return type('obj', (object,), {
                        'choices': [type('obj', (object,), {
                            'message': type('obj', (object,), {'content': content})
                        })()]
                    })()
                    
        except Exception as e:
            self.logger.error(f"Error llamando a Responses API: {e}")
            # Devolver objeto vacío para compatibilidad
            return type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'message': type('obj', (object,), {'content': ''})
                })()]
            })()
    
    async def _determine_response_strategy(self, message: str) -> str:
        """Determina la estrategia de respuesta de forma simple y rápida"""
        
        # IMPORTANTE: Verificar primero si hay un contexto de refinamiento activo
        session_id = self.conversation_state.session_id or "default_session"
        refiner_context = search_refiner.contexts.get(session_id)
        
        if refiner_context and refiner_context.current_state.value != "idle":
            # Si estamos en medio de un refinamiento, SIEMPRE usar multi_agent
            self.logger.info(f"🔄 Contexto de refinamiento activo detectado - forzando estrategia multi_agent")
            return "multi_agent"
        
        # Validar mensaje de entrada
        if not message or not message.strip():
            return "quick_response"
            
        # SIMPLIFICACIÓN: Análisis rápido basado en palabras clave
        message_lower = message.lower()
        
        # Saludos simples
        if message_lower in ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'adiós', 'gracias']:
            return "quick_response"
            
        # Palabras clave que indican búsqueda de productos
        product_keywords = [
            'busco', 'necesito', 'quiero', 'dame', 'muéstrame', 'tienes',
            'cable', 'diferencial', 'magnetotérmico', 'automático', 'lámpara',
            'bombilla', 'enrollacables', 'termo', 'calentador', 'radiador',
            'interruptor', 'enchufe', 'caja', 'tubo', 'brida', 'cintillo',
            'fusible', 'contactor', 'variador', 'transformador', 'portero',
            'videoportero', 'telefonillo', 'proyector', 'campana', 'luminaria'
        ]
        
        # Si contiene alguna palabra clave de producto, usar multi_agent
        if any(keyword in message_lower for keyword in product_keywords):
            self.logger.info(f"🛒 Detectada búsqueda de productos - usando multi_agent")
            return "multi_agent"
            
        # Si menciona pedido o email, usar tool_assisted
        if '@' in message or any(word in message_lower for word in ['pedido', 'orden', 'compra', 'factura']):
            return "tool_assisted"
            
        # Por defecto, usar standard_response
        return "standard_response"
            
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

2. tool_assisted: Para cuando necesitas acceder a datos del sistema (NO productos)
   - Consultas de pedidos (cuando menciona email o número de pedido)
   - Preguntas frecuentes (FAQ) sobre políticas, horarios, envíos, devoluciones
   - Información de la base de conocimiento de la empresa

3. multi_agent: Para búsquedas de productos y consultas complejas
   - Búsqueda de productos NUEVOS (NO mencionados previamente)
   - Verificar stock o precios de productos NO mostrados aún
   - Consultas complejas con múltiples intenciones
   - Ejemplos: "cables", "diferenciales", "busco productos", "necesito un cable"

4. standard_response: Para responder sobre información YA PRESENTADA o disponible en contexto
   - Selección entre productos ya mostrados ("el más barato", "el primero", "el segundo")
   - Comparaciones entre productos mencionados previamente
   - Detalles sobre productos ya mostrados
   - Preguntas de seguimiento sobre la conversación
   - Cuando el usuario quiere elegir o preguntar sobre opciones ya presentadas

REGLAS CRÍTICAS:
- Si se mostraron productos y el usuario hace referencia a ellos, USA standard_response
- Referencias a productos mostrados incluyen: "el más barato", "el primero", "ese", "el de X precio", "quiero el", etc.
- Para búsquedas de productos NUEVOS usa multi_agent (para activar refinamiento si hay muchos resultados)
- Palabras clave de productos: "cable", "diferencial", "busco", "necesito", "quiero comprar", etc. → multi_agent
- Analiza TODO el contexto - si hay productos en la conversación reciente, probablemente se refiere a ellos

RESPONDE SOLO con el nombre de la estrategia: quick_response, tool_assisted, multi_agent, o standard_response
"""

        try:
            # Log para debug
            self.logger.info(f"🔍 Determinando estrategia para: '{message[:100]}...'")
            
            # Usar Responses API para GPT-5
            response = await self._call_gpt5_responses_api(
                prompt=strategy_prompt,
                system_prompt="Eres un experto en análisis de consultas de atención al cliente. Determina la mejor estrategia de respuesta basándote en el tipo y complejidad de la consulta.",
                max_tokens=50
            )
            
            # Log detallado de la respuesta
            self.logger.info(f"📡 Respuesta de OpenAI: {response}")
            
            # Validar que tenemos una respuesta válida
            if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                self.logger.warning("⚠️ Respuesta vacía de IA, reintentando...")
                # Reintentar una vez más
                await asyncio.sleep(1)
                response = await self._call_gpt5_responses_api(
                    prompt=f"Clasifica esta consulta: '{message}'",
                    system_prompt="Eres un experto en análisis de consultas. Responde SOLO con: quick_response, tool_assisted, multi_agent, o standard_response",
                    max_tokens=20
                )
            
            strategy_response = response.choices[0].message.content.strip() if response.choices and response.choices[0].message else ""
            
            # Log de la respuesta original
            self.logger.info(f"📝 Respuesta de IA: '{strategy_response}'")
            
            # Limpiar y validar respuesta
            strategy = strategy_response.lower().replace(".", "").replace(",", "").strip()
            
            # Validar que la estrategia sea válida
            valid_strategies = ["quick_response", "tool_assisted", "multi_agent", "standard_response"]
            if strategy in valid_strategies:
                self.logger.info(f"✅ IA recomienda estrategia: {strategy}")
                return strategy
            else:
                self.logger.warning(f"⚠️ Estrategia inválida de IA: '{strategy_response}', usando standard_response")
                # En lugar de fallback, usar standard_response que permite a la IA procesar con contexto
                return "standard_response"
                
        except Exception as e:
            self.logger.error(f"❌ Error en determinación de estrategia IA: {type(e).__name__}: {e}")
            # En caso de error, usar standard_response para que la IA procese el mensaje
            return "standard_response"
    
    # ELIMINADO: _fallback_strategy_selection - La IA siempre debe decidir, no usar fallbacks mecánicos
    
    async def _process_with_multi_agent(self, message: str, platform: str = "whatsapp") -> str:
        """Procesa búsquedas de productos con lógica de refinamiento integrada"""
        try:
            # Obtener session_id para mantener contexto
            session_id = self.conversation_state.session_id or "default_session"
            
            # PASO 1: Verificar si hay un contexto de refinamiento activo
            refiner_context = search_refiner.contexts.get(session_id)
            
            if refiner_context and refiner_context.current_state.value != "idle":
                # Estamos en medio de un refinamiento
                self.logger.info(f"🔄 Refinamiento activo detectado para sesión {session_id}")
                self.logger.info(f"   Estado: {refiner_context.current_state.value}")
                self.logger.info(f"   Query original: {refiner_context.original_query}")
                
                # Refinar la consulta con la respuesta del usuario
                refined_query = search_refiner.refine_query_with_response(
                    session_id=session_id,
                    user_response=message,
                    original_query=refiner_context.original_query
                )
                
                self.logger.info(f"🎯 Query refinada: '{refined_query}'")
                
                # Ahora buscar con la query refinada
                return await self._handle_refined_search(refined_query, platform, session_id)
            
            # PASO 2: Es una nueva búsqueda - usar el agente inteligente
            self.logger.info(f"🔍 Nueva búsqueda de productos: '{message}'")
            
            # Usar el nuevo agente inteligente para entender la petición
            from services.intelligent_search_agent import intelligent_search
            
            self.logger.info("🚀 INICIANDO ANÁLISIS INTELIGENTE CON IA")
            self.logger.info(f"   📝 Mensaje del usuario: '{message}'")
            
            # El agente inteligente entiende CUALQUIER petición del usuario
            user_analysis = await intelligent_search.understand_user_request(message)
            
            # Usar la query optimizada por la IA
            query_to_use = user_analysis.get('search_query', '')
            intent = user_analysis.get('intent', 'comprar')
            
            self.logger.info(f"🤖 ANÁLISIS INTELIGENTE COMPLETADO:")
            self.logger.info(f"   📝 Query original: {message}")
            self.logger.info(f"   🎯 Query optimizada: {query_to_use}")
            self.logger.info(f"   📦 Tipo de producto: {user_analysis.get('product_type', 'N/A')}")
            self.logger.info(f"   🏷️ Marca detectada: {user_analysis.get('brand', 'N/A')}")
            self.logger.info(f"   🔧 Especificaciones: {user_analysis.get('specifications', {})}")
            self.logger.info(f"   💡 Intención: {intent}")
            self.logger.info(f"   🏢 Contexto: {user_analysis.get('context', 'N/A')}")
            
            # VERIFICACIÓN CRÍTICA: Si no hay query o es una confirmación, NO buscar
            if not query_to_use or query_to_use.strip() == '' or intent == 'confirmación':
                self.logger.info("⚠️ No hay producto que buscar (confirmación o query vacía)")
                # Generar respuesta contextual sin buscar
                if intent == 'confirmación':
                    return "Perfecto, ¿hay algo más en lo que pueda ayudarte?"
                else:
                    return "No entendí qué producto buscas. ¿Podrías ser más específico?"
            
            # Generar embedding y buscar (incluir categorías para detectar matches de categorías)
            embedding = await self.embedding_service.generate_embedding(query_to_use)
            results = await self.db_service.hybrid_search(
                query_text=query_to_use,
                query_embedding=embedding,
                content_types=["product", "category"],  # Incluir categorías para detectar matches
                limit=30  # Buscar más para poder evaluar si hay demasiados
            )
            
            self.logger.info(f"📦 Encontrados {len(results)} productos")
            
            # PASO 3: Si el usuario especificó una marca, mostrar productos directamente
            if user_analysis.get('brand') and results:
                # Con marca específica, mostrar directamente los mejores resultados
                self.logger.info(f"✅ Marca detectada, mostrando {min(5, len(results))} productos directamente")
                # Tomar solo los primeros 5 resultados (ya vienen ordenados por score)
                top_results = results[:5]
                return self._format_product_results(top_results, message, platform)
            
            # PASO 4: Usar IA para decidir si refinar o mostrar productos
            # No más lógica rígida, la IA decide basándose en el contexto
            
            # Filtrar solo productos (quitar categorías)
            product_results = [r for r in results if r.get('content_type') != 'category']
            
            # PASO CRÍTICO: Validar que los productos sean relevantes
            from services.product_validator_agent import product_validator
            
            self.logger.info(f"🔍 Validando relevancia de {len(product_results)} productos...")
            validated_products, validation_message = await product_validator.validate_products(
                user_request=message,
                products=product_results,
                max_products=10
            )
            
            if not validated_products:
                # No hay productos relevantes
                self.logger.warning(f"⚠️ Ningún producto pasó la validación")
                if validation_message:
                    return validation_message
                else:
                    # Intentar con una búsqueda más amplia
                    return f"No encontré productos que coincidan exactamente con '{message}'. ¿Podrías ser más específico o usar otros términos?"
            
            self.logger.info(f"✅ {len(validated_products)} productos validados como relevantes")
            
            if len(validated_products) <= 5:
                # Pocos resultados relevantes, mostrar directamente
                self.logger.info(f"✅ Mostrando {len(validated_products)} productos directamente")
                return self._format_product_results(validated_products, message, platform)
            
            if len(validated_products) > 5:
                # Muchos resultados validados - dejar que la IA decida si refinar
                from services.intelligent_search_agent import intelligent_search
                
                needs_refinement, refinement_message = await intelligent_search.should_refine_results(
                    validated_products,
                    user_analysis
                )
                
                
                if needs_refinement and refinement_message:
                    self.logger.info(f"🔄 Iniciando refinamiento inteligente")
                    # Guardar contexto para el refinamiento
                    refiner_context = search_refiner.get_or_create_context(
                        session_id=session_id,
                        query=message
                    )
                    refiner_context.last_search_results = validated_products
                    refiner_context.original_query = message
                    return refinement_message
                else:
                    # La IA decidió mostrar productos directamente
                    self.logger.info(f"✅ Mostrando los 5 mejores de {len(validated_products)} productos validados")
                    return self._format_product_results(validated_products[:5], message, platform)
            
            # PASO 4: No necesita refinamiento o hay pocos resultados
            if not results:
                # Si no hay resultados, usar IA para generar una respuesta inteligente
                self.logger.info(f"❌ No se encontraron productos para '{message}'")
                
                # Usar el LLM para entender qué buscaba el usuario y sugerir alternativas
                return await self._generate_intelligent_not_found_response(message, platform)
            
            # Si encontramos productos irrelevantes, también informar claramente
            if results:
                # Primero, verificar si tenemos categorías con alta puntuación
                category_results = []
                product_results = []
                for result in results:
                    content_type = result.get('content_type', '')
                    if content_type == 'category':
                        category_results.append(result)
                    else:
                        product_results.append(result)
                
                # Si tenemos una categoría con puntuación muy alta (>900), es probable que sea lo que busca el usuario
                high_score_category = None
                for cat in category_results:
                    score = cat.get('_score', 0)
                    if score > 900:
                        high_score_category = cat
                        self.logger.info(f"✅ Encontrada categoría con alta puntuación ({score}): {cat.get('title')}")
                        break
                
                # Si encontramos una categoría relevante, buscar productos de esa categoría
                if high_score_category:
                    category_title = high_score_category.get('title', '')
                    self.logger.info(f"🔍 Buscando productos de la categoría: {category_title}")
                    
                    # Buscar productos de esta categoría específica
                    category_embedding = await self.embedding_service.generate_embedding(category_title)
                    category_products = await self.db_service.hybrid_search(
                        query_text=category_title,
                        query_embedding=category_embedding,
                        content_types=["product"],
                        limit=10
                    )
                    
                    if category_products:
                        self.logger.info(f"✅ Encontrados {len(category_products)} productos en la categoría {category_title}")
                        results = category_products
                    else:
                        # Si no hay productos en la categoría, seguir con la lógica original
                        self.logger.info(f"⚠️ No se encontraron productos en la categoría {category_title}")
                
                # Si no hay categoría con alta puntuación, verificar relevancia de productos
                if not high_score_category and product_results:
                    # Verificar si los resultados son relevantes
                    relevant_results = []
                    search_terms = message.lower().split()
                    
                    # Agregar sinónimos comunes para mejorar la búsqueda
                    synonym_map = {
                        "recoge": ["enrolla", "recoge", "carrete"],
                        "cables": ["cable", "cables"],
                        "recogecables": ["enrollacables", "recogecables", "carrete", "enrollador"],
                        "enrollacables": ["enrollacables", "recogecables", "carrete", "enrollador"]
                    }
                    
                    # Expandir términos de búsqueda con sinónimos
                    expanded_terms = []
                    for term in search_terms:
                        expanded_terms.append(term)
                        if term in synonym_map:
                            expanded_terms.extend(synonym_map[term])
                    
                    for result in product_results[:20]:
                        title_lower = result.get('title', '').lower()
                        content_lower = result.get('content', '').lower()
                        metadata = result.get('metadata', {})
                        
                        # Verificar con términos expandidos
                        if any(term in title_lower or term in content_lower for term in expanded_terms):
                            relevant_results.append(result)
                    
                    # Si no hay resultados relevantes, informar claramente
                    if not relevant_results:
                        self.logger.info(f"❌ Los {len(results)} productos encontrados no son relevantes para '{message}'")
                        if platform == "wordpress":
                            return f"<p>No encontré <strong>{message}</strong> en nuestro catálogo.</p><p>En El Corte Eléctrico tenemos:</p><ul><li>Cables eléctricos de todo tipo</li><li>Diferenciales y magnetotérmicos</li><li>Mecanismos (interruptores, enchufes)</li><li>Iluminación LED</li><li>Material de distribución</li></ul><p>¿Qué material eléctrico necesitas?</p>"
                        else:
                            return f"No encontré {message} en nuestro catálogo.\n\nTenemos:\n• Cables eléctricos\n• Diferenciales\n• Mecanismos\n• Iluminación LED\n• Material de distribución\n\n¿Qué material eléctrico necesitas?"
                    
                    # Usar solo resultados relevantes
                    results = relevant_results[:10]
            
            # Formatear y devolver resultados
            if len(results) > 5:
                results = await search_optimizer.optimize_search_results(message, results, limit=5)
            
            return self._format_product_results(results, message, platform)
            
        except Exception as e:
            self.logger.error(f"⚠️ Error en búsqueda con refinamiento: {e}")
            
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
    
    async def _handle_refined_search(self, refined_query: str, platform: str, session_id: str) -> str:
        """Maneja la búsqueda con la query refinada"""
        try:
            self.logger.info(f"🔍 Búsqueda refinada: '{refined_query}'")
            
            # Obtener el contexto de refinamiento que tiene los resultados originales
            refiner_context = search_refiner.contexts.get(session_id)
            
            if refiner_context and refiner_context.last_search_results:
                # En lugar de filtrar estrictamente, hacer una nueva búsqueda combinando la query original con el refinamiento
                self.logger.info(f"📦 Refinando búsqueda con {len(refiner_context.last_search_results)} resultados disponibles")
                
                # IMPORTANTE: Detectar marca tanto en la query original como en el refinamiento
                known_brands = {'legrand', 'schneider', 'jung', 'simon', 'siemens', 'ledme', 'saci', 'abb', 'gave', 'chint', 'hager'}
                original_lower = refiner_context.original_query.lower() if refiner_context.original_query else ""
                refined_lower = refined_query.lower()
                
                # Detectar marca en query original
                detected_brand_original = None
                for brand in known_brands:
                    if brand in original_lower:
                        detected_brand_original = brand
                        self.logger.info(f"🏷️ Marca detectada en query original: '{detected_brand_original}'")
                        break
                
                # Detectar marca en el refinamiento
                detected_brand_refined = None
                for brand in known_brands:
                    if brand in refined_lower:
                        detected_brand_refined = brand
                        self.logger.info(f"🏷️ Marca detectada en refinamiento: '{detected_brand_refined}'")
                        break
                
                # Usar la marca del refinamiento si existe, sino la original
                detected_brand = detected_brand_refined or detected_brand_original
                
                # Si se especificó una marca nueva que no estaba en los resultados originales
                new_brand_specified = False
                if detected_brand_refined and not detected_brand_original:
                    # Verificar si esta marca estaba en los resultados originales
                    brand_in_results = False
                    for result in refiner_context.last_search_results[:10]:  # Check first 10
                        if detected_brand_refined in result.get('title', '').lower():
                            brand_in_results = True
                            break
                    
                    if not brand_in_results:
                        new_brand_specified = True
                        self.logger.info(f"🆕 Nueva marca especificada que no estaba en resultados originales: '{detected_brand_refined}'")
                
                # NUEVO: Detectar si el refinamiento es una especificación técnica pura (números + unidades)
                import re
                is_technical_spec = bool(re.match(r'^[\d\s]+\s*(a|amperios?|mm|v|voltios?|w|watts?|ma|miliamperios?)?$', refined_query.lower()))
                
                # Si es una especificación técnica, PRIMERO filtrar los resultados originales
                if is_technical_spec and refiner_context.original_query:
                    self.logger.info(f"🔧 Refinamiento técnico detectado: '{refined_query}' para '{refiner_context.original_query}'")
                    
                    # Extraer números del refinamiento
                    numbers = re.findall(r'\d+', refined_query)
                    
                    # Filtrar resultados originales que contengan el producto original Y la especificación
                    filtered_results = []
                    original_term = refiner_context.original_query.lower()
                    
                    for result in refiner_context.last_search_results:
                        title_lower = result.get('title', '').lower()
                        content_lower = result.get('content', '').lower()
                        
                        # Verificar que contenga el término original (automático, diferencial, etc.)
                        has_original = any(word in title_lower or word in content_lower 
                                         for word in original_term.split())
                        
                        # Verificar que contenga la especificación técnica
                        has_spec = any(num in title_lower or num in content_lower 
                                      for num in numbers)
                        
                        # Si detectamos marca, verificar que el resultado sea de esa marca
                        if detected_brand:
                            has_brand = detected_brand in title_lower or detected_brand in content_lower
                            if has_original and has_spec and has_brand:
                                filtered_results.append(result)
                        else:
                            if has_original and has_spec:
                                filtered_results.append(result)
                    
                    if filtered_results:
                        self.logger.info(f"✅ Encontrados {len(filtered_results)} productos con especificación técnica")
                        results = filtered_results[:10]
                    else:
                        # Si no hay resultados filtrados, continuar con búsqueda combinada
                        self.logger.info("⚠️ No se encontraron productos con esa especificación, probando búsqueda combinada")
                        results = []
                else:
                    results = []
                
                # ESTRATEGIA 0: Si se especificó una marca nueva, buscar directamente con ella
                if not results and new_brand_specified:
                    self.logger.info(f"🎯 Estrategia 0: Nueva marca - búsqueda directa con refinamiento completo")
                    
                    # Combinar el producto original con el refinamiento completo
                    # Ej: "diferencial" + "schneider 25A" = "diferencial schneider 25A"
                    full_query = f"{refiner_context.original_query} {refined_query}"
                    self.logger.info(f"   Query completa: '{full_query}'")
                    
                    # Buscar con la query completa
                    embedding = await self.embedding_service.generate_embedding(full_query)
                    results = await self.db_service.hybrid_search(
                        query_text=full_query,
                        query_embedding=embedding,
                        content_types=["product"],
                        limit=20
                    )
                    
                    if results:
                        self.logger.info(f"   ✅ Encontrados {len(results)} productos con la nueva marca")
                        # Filtrar para asegurar que son de la marca especificada
                        if detected_brand_refined:
                            brand_filtered = [r for r in results if detected_brand_refined in r.get('title', '').lower()]
                            if brand_filtered:
                                results = brand_filtered
                                self.logger.info(f"   ✅ Filtrados {len(results)} productos de {detected_brand_refined}")
                
                # Si no hay resultados o no es especificación técnica, usar estrategia combinada
                if not results:
                    # ESTRATEGIA 1: Búsqueda combinada (original + refinamiento)
                    combined_query = f"{refiner_context.original_query} {refined_query}"
                    self.logger.info(f"🎯 Estrategia 1: Query combinada: '{combined_query}'")
                    
                    from services.search_optimizer import search_optimizer
                    search_analysis = await search_optimizer.analyze_product_query(combined_query)
                    optimized_query = search_analysis.get('search_query', combined_query)
                    
                    embedding = await self.embedding_service.generate_embedding(optimized_query)
                    results = await self.db_service.hybrid_search(
                        query_text=optimized_query,
                        query_embedding=embedding,
                        content_types=["product"],
                        limit=20
                    )
                    
                    # Filtrar por marca si se detectó una
                    if detected_brand and results:
                        brand_filtered = [r for r in results if detected_brand in r.get('title', '').lower() or detected_brand in r.get('content', '').lower()]
                        if brand_filtered:
                            results = brand_filtered
                            self.logger.info(f"   Filtrados {len(results)} productos de marca {detected_brand}")
                
                # ESTRATEGIA 2: Si no hay resultados, buscar con marca + refinamiento (si hay marca)
                if not results and detected_brand:
                    brand_refined_query = f"{detected_brand} {refined_query}"
                    self.logger.info(f"🔄 Estrategia 2: Búsqueda con marca + refinamiento: '{brand_refined_query}'")
                    
                    embedding = await self.embedding_service.generate_embedding(brand_refined_query)
                    results = await self.db_service.hybrid_search(
                        query_text=brand_refined_query,
                        query_embedding=embedding,
                        content_types=["product"],
                        limit=20
                    )
                
                # ESTRATEGIA 3: Si no hay resultados y NO hay marca, buscar solo con el refinamiento
                if not results and not detected_brand:
                    self.logger.info(f"🔄 Estrategia 3: Búsqueda solo con refinamiento: '{refined_query}'")
                    
                    # Buscar solo con el término de refinamiento
                    embedding = await self.embedding_service.generate_embedding(refined_query)
                    results = await self.db_service.hybrid_search(
                        query_text=refined_query,
                        query_embedding=embedding,
                        content_types=["product"],
                        limit=20
                    )
                
                # ESTRATEGIA 4: Búsqueda con sinónimos expandidos
                if not results:
                    self.logger.info("🔄 Estrategia 4: Búsqueda con sinónimos expandidos")
                    
                    # Expandir la consulta con sinónimos
                    expanded_queries = search_refiner.expand_query_with_synonyms(refiner_context.original_query)
                    
                    for expanded_query in expanded_queries[1:]:  # Saltar el primero que es el original
                        # Incluir marca si se detectó
                        if detected_brand:
                            full_query = f"{detected_brand} {expanded_query} {refined_query}"
                        else:
                            full_query = f"{expanded_query} {refined_query}"
                        self.logger.info(f"   Probando: '{full_query}'")
                        
                        embedding = await self.embedding_service.generate_embedding(full_query)
                        results = await self.db_service.hybrid_search(
                            query_text=full_query,
                            query_embedding=embedding,
                            content_types=["product"],
                            limit=20
                        )
                        
                        # Filtrar por marca si es necesario
                        if detected_brand and results:
                            brand_filtered = [r for r in results if detected_brand in r.get('title', '').lower() or detected_brand in r.get('content', '').lower()]
                            if brand_filtered:
                                results = brand_filtered
                        
                        if results:
                            self.logger.info(f"   ✅ Encontrados {len(results)} resultados con sinónimos")
                            break
                
                # ESTRATEGIA 5: Filtrado flexible en resultados originales
                if not results:
                    self.logger.info("🔄 Estrategia 5: Filtrado flexible en resultados originales")
                    
                    # Extraer números y especificaciones técnicas
                    import re
                    numbers = re.findall(r'\d+', refined_query)
                    
                    # Si hay números, buscar en los resultados originales
                    if numbers and refiner_context.last_search_results:
                        filtered_results = []
                        for result in refiner_context.last_search_results:
                            title = result.get('title', '').lower()
                            content = result.get('content', '').lower()
                            refined_lower = refined_query.lower()
                            
                            # Si hay marca detectada, verificar que el producto sea de esa marca
                            if detected_brand:
                                if detected_brand not in title and detected_brand not in content:
                                    continue  # Saltar productos que no son de la marca
                            
                            # Buscar números o términos del refinamiento
                            match_found = False
                            for num in numbers:
                                if num in title or num in content:
                                    match_found = True
                                    break
                            
                            # También buscar términos no numéricos del refinamiento
                            if not match_found:
                                words = refined_lower.split()
                                for word in words:
                                    if len(word) > 2 and (word in title or word in content):
                                        match_found = True
                                        break
                            
                            if match_found:
                                filtered_results.append(result)
                        
                        if filtered_results:
                            self.logger.info(f"✅ Encontrados {len(filtered_results)} productos con filtrado flexible")
                            results = filtered_results[:10]
                
                # Si aún no hay resultados, NO mostrar productos irrelevantes
                # Es mejor admitir que no hay productos de esa marca/especificación
                if not results and refiner_context.last_search_results:
                    self.logger.info("📋 No hay productos que coincidan con el refinamiento")
                    # NO mostrar productos aleatorios - mantener results vacío
                
                self.logger.info(f"✅ Total de resultados para mostrar: {len(results)}")
                
            else:
                # Si no hay contexto, hacer búsqueda normal
                self.logger.info("⚠️ No hay contexto de refinamiento, haciendo búsqueda normal")
                embedding = await self.embedding_service.generate_embedding(refined_query)
                results = await self.db_service.hybrid_search(
                    query_text=refined_query,
                    query_embedding=embedding,
                    content_types=["product"],
                    limit=10
                )
            
            # Limpiar el contexto de refinamiento ya que completamos el proceso
            if session_id in search_refiner.contexts:
                del search_refiner.contexts[session_id]
                self.logger.info(f"🧹 Contexto de refinamiento limpiado para sesión {session_id}")
            
            if not results:
                # Construir mensaje específico basado en el contexto
                if refiner_context and refiner_context.original_query:
                    original_product = refiner_context.original_query
                    if platform == "wordpress":
                        return f"<p>No encontré {original_product} con las características que especificaste ({refined_query}). Te sugiero revisar nuestro catálogo completo o contactarnos por WhatsApp para ayudarte a encontrar lo que necesitas.</p>"
                    else:
                        return f"No encontré {original_product} con las características que especificaste ({refined_query}). ¿Te puedo ayudar con otra búsqueda o prefieres que te muestre otras opciones disponibles?"
                else:
                    # Mensaje genérico si no hay contexto
                    if platform == "wordpress":
                        return f"<p>No encontré productos exactos con esas especificaciones. Te sugiero revisar nuestro catálogo completo o contactarnos por WhatsApp para ayudarte a encontrar lo que necesitas.</p>"
                    else:
                        return f"No encontré productos exactos con esas especificaciones. ¿Te puedo ayudar con otra búsqueda o prefieres que te muestre opciones similares?"
            
            # Formatear y devolver resultados
            return self._format_product_results(results, refined_query, platform)
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda refinada: {e}")
            return await self._process_standard_response(refined_query, platform)
    
    async def _generate_intelligent_not_found_response(self, query: str, platform: str) -> str:
        """Genera una respuesta inteligente cuando no se encuentran productos usando IA"""
        try:
            # Buscar categorías similares para sugerir
            embedding = await self.embedding_service.generate_embedding(query)
            similar_categories = await self.db_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                content_types=["category"],
                limit=5
            )
            
            # Preparar contexto para el LLM
            categories_context = ""
            if similar_categories:
                categories_context = "Categorías relacionadas disponibles: " + ", ".join(
                    [cat.get('title', '') for cat in similar_categories[:3]]
                )
            
            # Usar el LLM para generar una respuesta inteligente
            system_prompt = """Eres un asistente de ventas de El Corte Eléctrico, una tienda especializada en material eléctrico.
            
            Cuando un usuario busca un producto que no tenemos:
            1. Identifica qué tipo de producto buscaba
            2. Si es algo relacionado con electricidad, sugiere alternativas que sí vendemos
            3. Si no es material eléctrico, explica amablemente nuestro enfoque y sugiere qué sí tenemos
            4. Sé breve y útil (máximo 2-3 frases)
            5. NO inventes productos, solo sugiere categorías generales que vendemos
            
            Categorías principales que vendemos:
            - Cables y conductores eléctricos
            - Automatismos (diferenciales, magnetotérmicos)
            - Mecanismos (interruptores, enchufes)
            - Iluminación LED y convencional
            - Material de distribución eléctrica
            - Herramientas eléctricas
            - Domótica y control
            """
            
            user_prompt = f"""El usuario busca: "{query}"
            
            {categories_context}
            
            Genera una respuesta breve y útil explicando que no encontramos ese producto específico 
            y sugiriendo alternativas relevantes que sí vendemos."""
            
            # Generar respuesta con el LLM
            import openai
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Formatear según plataforma
            if platform == "wordpress":
                # Convertir a HTML
                ai_response = f"<p>{ai_response.replace(chr(10) + chr(10), '</p><p>').replace(chr(10), '<br>')}</p>"
            
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta inteligente: {e}")
            # Fallback a respuesta genérica
            if platform == "wordpress":
                return f"<p>No encontré productos que coincidan con '<strong>{query}</strong>'.</p><p>Como especialistas en material eléctrico, te sugiero explorar nuestras categorías principales o contactarnos para ayudarte a encontrar lo que necesitas.</p>"
            else:
                return f"No encontré productos que coincidan con '{query}'.\n\nComo especialistas en material eléctrico, te sugiero explorar nuestras categorías principales o contactarnos para ayudarte."
    
    def _calculate_relevance_score(self, query: str, result: Dict) -> float:
        """Calcula un score de relevancia mejorado basado en coincidencias de términos"""
        query_terms = set(query.lower().split())
        title_lower = result.get('title', '').lower()
        content_lower = result.get('content', '').lower()
        
        # Score basado en coincidencias exactas en título (peso 2x)
        title_terms = set(title_lower.split())
        exact_title_matches = len(query_terms & title_terms)
        
        # Score basado en coincidencias parciales en título
        partial_title_matches = sum(1 for qt in query_terms 
                                   if any(qt in tt for tt in title_terms))
        
        # Score basado en coincidencias en contenido (peso 0.5x)
        content_terms = set(content_lower.split())
        content_matches = len(query_terms & content_terms)
        
        # Calcular score normalizado
        if len(query_terms) > 0:
            score = (exact_title_matches * 2.0 + 
                    partial_title_matches * 1.0 + 
                    content_matches * 0.5) / (len(query_terms) * 2.0)
        else:
            score = 0.0
        
        # Bonus si todos los términos aparecen
        if exact_title_matches == len(query_terms):
            score *= 1.5
        
        return min(score, 1.0)  # Limitar a máximo 1.0
    
    def _format_product_results(self, results: list, query: str, platform: str) -> str:
        """Formatea los resultados de productos según la plataforma"""
        # Reordenar resultados por relevancia mejorada
        for result in results:
            result['improved_relevance'] = self._calculate_relevance_score(query, result)
        
        # Ordenar por relevancia mejorada combinada con score original
        results.sort(key=lambda x: (
            x.get('improved_relevance', 0) * 0.4 + 
            min(float(x.get('rrf_score', 0)) / 1000, 1.0) * 0.6
        ), reverse=True)
        
        if platform == "wordpress":
            from src.utils.wordpress_utils import format_product_search_response
            
            products = []
            for result in results[:5]:
                if isinstance(result, dict):
                    metadata = result.get('metadata', {})
                    # Asegurar que las imágenes estén en el formato correcto
                    images = metadata.get('images', [])
                    if images and isinstance(images[0], dict):
                        # Ya está en el formato correcto
                        pass
                    elif images and isinstance(images[0], str):
                        # Convertir URLs simples a formato dict
                        images = [{'src': img} for img in images if img]
                    
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
            
            if products:
                # Usar el formato HTML bonito de wordpress_utils
                return format_product_search_response(products, query)
            else:
                return f"<p>Lo siento, encontré productos pero hubo un error al procesarlos.</p>"
        else:
            # WhatsApp
            return format_products_for_whatsapp(results, query)
    
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
        """Clasifica el tipo de consulta del usuario usando IA"""
        
        # Obtener contexto reciente para mejor clasificación
        recent_context = self._get_recent_context_summary()
        
        classification_prompt = f"""
Analiza esta consulta y clasifícala en una de las categorías disponibles.

CONSULTA: "{message}"

{recent_context}

CATEGORÍAS:
1. order_inquiry - Consultas sobre pedidos existentes (estado, tracking, factura)
2. stock_check - SOLO cuando preguntan específicamente por stock/disponibilidad/unidades de un producto concreto
3. faq_inquiry - Preguntas sobre políticas, horarios, envíos, garantías, devoluciones, tienda física
4. product_search - Búsqueda de productos ("¿tenéis X?", "busco Y", "quiero Z") - NO es stock_check
5. general - Cualquier otra consulta

IMPORTANTE:
- Si el usuario se refiere a productos YA MOSTRADOS en la conversación, NO es product_search
- Solo clasifica como product_search cuando busca productos NUEVOS
- Considera el contexto completo de la conversación

Responde SOLO con la categoría: order_inquiry, stock_check, faq_inquiry, product_search o general
"""

        try:
            # Usar Responses API para clasificación rápida
            response = await self._call_gpt5_responses_api(
                prompt=classification_prompt,
                system_prompt="Eres un experto en clasificación de consultas de atención al cliente.",
                max_tokens=20
            )
            
            if response.choices and response.choices[0].message:
                classification = response.choices[0].message.content.strip().lower()
                
                # Validar que sea una categoría válida
                valid_categories = ["order_inquiry", "stock_check", "faq_inquiry", "product_search", "general"]
                if classification in valid_categories:
                    return classification
                else:
                    self.logger.warning(f"Categoría inválida de IA: '{classification}', usando 'general'")
                    return "general"
            else:
                return "general"
                
        except Exception as e:
            self.logger.error(f"Error en clasificación con IA: {e}")
            return "general"
    
    async def _handle_product_search(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Maneja búsquedas de productos usando búsqueda híbrida con optimización IA"""
        try:
            self.logger.info(f"🔍 BÚSQUEDA DE PRODUCTOS: '{message}'")
            
            # Usar el optimizador de búsqueda para analizar la consulta
            from services.search_optimizer import search_optimizer
            
            search_analysis = await search_optimizer.analyze_product_query(message)
            optimized_query = search_analysis.get('search_query', message)
            
            self.logger.info(f"🤖 Consulta optimizada: '{optimized_query}' (Original: '{message}')")
            self.logger.info(f"📊 Análisis: {search_analysis}")
            
            # Generar embedding para la consulta OPTIMIZADA
            embedding = await self.embedding_service.generate_embedding(optimized_query)
            
            # Realizar búsqueda inteligente pasando el análisis completo
            results = await self.db_service.intelligent_product_search(
                query_text=optimized_query,
                query_embedding=embedding,
                content_types=["product"],
                limit=20,  # Buscar más para luego filtrar con IA
                wc_service=self.wc_service,
                search_analysis=search_analysis  # Pasar el análisis completo que incluye detected_sku
            )
            
            # Si hay resultados, optimizarlos con IA
            if results and len(results) > 5:
                self.logger.info(f"🎯 Optimizando {len(results)} resultados con IA...")
                results = await search_optimizer.optimize_search_results(message, results, limit=5)
                self.logger.info(f"✅ Resultados optimizados a {len(results)} productos más relevantes")
            
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
            
            # Formatear respuesta usando el método unificado
            response = self._format_product_results(results, message, platform)
            
            # Agregar información adicional de knowledge base si existe (solo para WhatsApp)
            if platform == "whatsapp" and additional_info:
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
        """Maneja verificaciones de stock - SOLO cuando preguntan específicamente por disponibilidad"""
        # Si la pregunta es genérica tipo "¿tenéis X?", redirigir a búsqueda de productos
        message_lower = message.lower()
        if any(word in message_lower for word in ["tenéis", "tienen", "venden", "hay", "busco", "quiero"]) and \
           not any(word in message_lower for word in ["stock", "disponible", "disponibilidad", "unidades"]):
            # Es una búsqueda de productos, no una verificación de stock
            return await self._handle_product_search(message, platform, knowledge_context)
        
        try:
            # Para verificación real de stock de un producto específico
            embedding = await self.embedding_service.generate_embedding(message)
            
            results = await self.db_service.hybrid_search(
                query_text=message,
                query_embedding=embedding,
                content_types=["product"],
                limit=3
            )
            
            if not results:
                response = "No encontré ese producto. ¿Podrías ser más específico?"
                if platform == "wordpress":
                    return f"<p style='margin: 0; line-height: 1.5;'>{response}</p>"
                return response
            
            # Formatear respuesta de disponibilidad
            if platform == "wordpress":
                response = "<div style='margin: 0;'>"
                for result in results[:2]:
                    title = result.get('title', 'Producto')
                    metadata = result.get('metadata', {})
                    stock_status = metadata.get('stock_status', 'unknown')
                    permalink = metadata.get('permalink', '')
                    
                    if stock_status == 'instock':
                        status_text = "✅ Disponible"
                    else:
                        status_text = "❌ Sin stock"
                    
                    response += f"<p style='margin: 0 0 8px 0;'><strong>{title}</strong><br>"
                    response += f"{status_text}"
                    if permalink:
                        response += f" - <a href='{permalink}'>Ver producto</a>"
                    response += "</p>"
                
                response += "</div>"
                return response
            else:
                # WhatsApp
                response = ""
                for result in results[:2]:
                    title = result.get('title', 'Producto')
                    metadata = result.get('metadata', {})
                    stock_status = metadata.get('stock_status', 'unknown')
                    
                    if stock_status == 'instock':
                        response += f"✅ *{title}*\nDisponible\n\n"
                    else:
                        response += f"❌ *{title}*\nSin stock\n\n"
                
                return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error verificando stock: {e}")
            return await self._process_standard_response(message, platform)
    
    async def _handle_faq_inquiry(self, message: str, platform: str = "whatsapp", knowledge_context: str = "") -> str:
        """Maneja preguntas frecuentes usando la knowledge base"""
        try:
            self.logger.info(f"📚 CONSULTA FAQ: '{message}'")
            
            # Si no tenemos contexto, buscar en knowledge base
            if not knowledge_context:
                knowledge_context = await self._search_knowledge_base(message)
            
            # Usar _process_standard_response con el knowledge context
            # Esto permite que la IA procese y formatee la información correctamente
            return await self._process_standard_response(message, platform, knowledge_context)
                
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
                # Si la respuesta ya contiene HTML (generado por la IA), devolverla directamente
                import re
                if re.search(r'<[^>]+>', response.content):
                    return response.content
                else:
                    # Si es texto plano, formatearlo
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
        
        # Confiar en la decisión de la IA - si llegamos aquí es porque la IA determinó
        # que esta es la mejor estrategia para responder
        
        # Guardar la plataforma actual para el prompt
        self._current_platform = platform
        
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
                # Si la respuesta ya contiene HTML (generado por la IA), devolverla directamente
                import re
                if re.search(r'<[^>]+>', response.content):
                    return response.content
                else:
                    # Si es texto plano, formatearlo
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
        elif any(word in message.lower() for word in ["producto", "diferencial", "cable", "termo", "ventilador", "quiero", "busco", "necesito"]):
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
        
        # Determinar formato según plataforma
        platform = getattr(self, '_current_platform', 'whatsapp')
        format_instructions = ""
        
        if platform == "wordpress":
            format_instructions = """
FORMATO PARA WORDPRESS:
- USA HTML para enlaces: <a href="url">texto</a>
- NO uses formato Markdown [texto](url)
- Usa <strong> para negritas, NO asteriscos
- Usa <br> para saltos de línea si es necesario
- Los párrafos deben estar en <p> tags
"""
        else:
            format_instructions = """
FORMATO PARA WHATSAPP:
- Usa formato Markdown para enlaces: [texto](url)
- Usa *texto* para negritas
- Usa saltos de línea normales
"""
        
        return f"""
Eres {self.bot_name}, asistente virtual de {self.company_name}. Eres una asistente conversacional natural.

CONTEXTO DE LA CONVERSACIÓN:
{recent_context}

{format_instructions}

INFORMACIÓN CRÍTICA DE LA EMPRESA:
- ⚠️ NO HAY TIENDA FÍSICA. Somos una tienda EXCLUSIVAMENTE ONLINE. NO se puede visitar ninguna tienda.
- Dirección fiscal (NO es tienda): Calle Laguna de Marquesado 47, Nave D, 28021 Madrid (solo oficinas)
- Tenemos más de 4,500 productos eléctricos en nuestro catálogo online.
- Toda la venta es a través de la web: https://elcorteelectrico.com
- WhatsApp soporte: +34614218122
- Link directo WhatsApp: https://wa.me/34614218122

INSTRUCCIONES IMPORTANTES:
1. SÉ CONCISA: Responde en 2-3 líneas máximo, sin introducciones largas
2. NO INVENTES URLs ni categorías que no existen
3. Si no tienes un producto, dilo claramente y sugiere alternativas reales
4. NUNCA digas cosas como "tenemos una amplia gama de ventiladores" si no es verdad
5. Solo menciona productos que REALMENTE existen en el catálogo
6. NO menciones categorías inventadas como "Ventiladores industriales" si no existen
7. Si no tienes lo que buscan, di "No tenemos [producto] pero tenemos [alternativas reales]"
8. NUNCA prometas avisar cuando algo esté disponible
9. NO HAY TIENDA FÍSICA: Solo venta online
10. Para soporte usa SOLO el WhatsApp: +34 614 21 81 22

RECONOCIMIENTO DE REFERENCIAS SKU:
- Los electricistas profesionales suelen buscar por referencia/SKU (números como "10004922" o códigos alfanuméricos)
- Si el usuario proporciona SOLO números o códigos (sin palabras descriptivas), es muy probable que sea una referencia SKU
- Cuando detectes una búsqueda por SKU, di algo como: "Buscando la referencia [SKU]..." y muestra resultados exactos
- Los SKU son importantes para los profesionales porque identifican exactamente el producto que necesitan

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
        
        summary = "CONTEXTO DE CONVERSACIÓN RECIENTE:\n"
        products_shown = False
        product_details = []
        
        for msg in recent:
            role = "Usuario" if msg["role"] == "user" else self.bot_name
            content = msg["content"]
            
            # Detectar si se mostraron productos
            if role == self.bot_name:
                # Buscar patrones de productos mostrados
                import re
                
                # Buscar productos con formato HTML (WordPress)
                product_matches = re.findall(r'<strong>([^<]+)</strong>.*?(\d+[,.]?\d*)\s*€', content)
                if product_matches:
                    products_shown = True
                    for i, (name, price) in enumerate(product_matches[:5], 1):
                        product_details.append(f"  {i}. {name} - {price}€")
                
                # Buscar productos con formato WhatsApp
                wa_product_matches = re.findall(r'(?:\d+\.\s*)?(?:\*)?([^*\n]+?)(?:\*)?(?:\s*-\s*|\n).*?(\d+[,.]?\d*)\s*€', content)
                if wa_product_matches and not product_matches:
                    products_shown = True
                    for i, (name, price) in enumerate(wa_product_matches[:5], 1):
                        product_details.append(f"  {i}. {name.strip()} - {price}€")
                
                # Si encontramos productos, resumir
                if products_shown and product_details:
                    summary += f"- {role}: [MOSTRÓ {len(product_details)} PRODUCTOS]:\n"
                    for detail in product_details[:3]:  # Mostrar máximo 3 para contexto
                        summary += f"{detail}\n"
                    if len(product_details) > 3:
                        summary += f"  ... y {len(product_details) - 3} productos más\n"
                    product_details = []  # Limpiar para siguiente mensaje
                else:
                    # Mensaje normal sin productos
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    summary += f"- {role}: {content_preview}\n"
            else:
                # Mensaje del usuario
                content_preview = content[:100] + "..." if len(content) > 100 else content
                summary += f"- {role}: {content_preview}\n"
        
        if products_shown:
            summary += "\n⚠️ IMPORTANTE: Se mostraron productos recientemente. Si el usuario se refiere a 'el más barato', 'el primero', etc., se refiere a ESTOS productos.\n"
        
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