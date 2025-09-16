#!/usr/bin/env python3
"""
Sistema Multi-Agente para Atención al Cliente
Usando LangGraph para orquestación inteligente de agentes especializados
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Literal, Annotated
from enum import Enum
import logging

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from typing import TypedDict
from src.agent.search_refiner_agent import search_refiner, RefinementState, SearchContext, RefinementState

# Cargar variables de entorno
load_dotenv("env.agent")

@dataclass
class ConversationContext:
    """Contexto enriquecido de la conversación"""
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    order_number: Optional[str] = None
    preferred_products: List[str] = field(default_factory=list)
    conversation_stage: str = "greeting"
    active_intents: List[str] = field(default_factory=list)
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    conversation_summary: str = ""
    turn_count: int = 0
    last_agent_used: Optional[str] = None
    pending_actions: List[str] = field(default_factory=list)
    satisfaction_level: str = "unknown"  # unknown, satisfied, neutral, dissatisfied

class MultiAgentState(TypedDict):
    """Estado compartido entre todos los agentes"""
    messages: List[BaseMessage]
    context: ConversationContext
    current_intent: str
    confidence: float
    next_agent: Optional[str]
    agent_responses: Dict[str, str]
    tools_used: List[str]
    needs_human_handoff: bool
    # Estado del refinador de búsqueda
    search_context: Optional[SearchContext]
    needs_refinement: bool
    refinement_message: Optional[str]
    session_id: str

class IntentClassificationResult(BaseModel):
    """Resultado de clasificación de intención usando LLM"""
    primary_intent: str = Field(description="Intención principal detectada")
    secondary_intents: List[str] = Field(default_factory=list, description="Intenciones secundarias")
    confidence: float = Field(description="Confianza en la clasificación (0-1)")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entidades extraídas")
    urgency: str = Field(default="normal", description="Nivel de urgencia: low, normal, high, critical")
    sentiment: str = Field(default="neutral", description="Sentimiento: positive, neutral, negative")

class CustomerServiceMultiAgent:
    """Sistema multi-agente para atención al cliente"""
    
    def __init__(self, bot_name: str = "Eva", company_name: str = "El Corte Eléctrico"):
        self.bot_name = bot_name
        self.company_name = company_name
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai")
        self.model_name = os.getenv("MODEL_NAME", "gpt-5")
        self.temperature = float(os.getenv("TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4000"))
        self.mcp_server_host = os.getenv("MCP_SERVER_HOST", "localhost")
        self.mcp_server_port = int(os.getenv("MCP_SERVER_PORT", "8000"))
        
        # Inicializar LLMs
        self.main_llm = self._initialize_llm()
        self.classifier_llm = self._initialize_llm(temperature=0.0)  # Más determinístico para clasificación
        self.cheap_llm = self._initialize_cheap_llm()  # Para tareas simples
        
        # Cliente MCP
        self.mcp_client = None
        self.mcp_tools = None
        self.mcp_session = None  # Sesión persistente
        
        # Grafo de agentes
        self.agent_graph = None
        
    def _initialize_llm(self, temperature: Optional[float] = None):
        """Inicializa el LLM principal - siempre usa OpenAI"""
        temp = temperature if temperature is not None else self.temperature
        
        # GPT-5 solo soporta temperature 1.0 por ahora
        if self.model_name == "gpt-5":
            temp = 1.0
        
        return ChatOpenAI(
            model=self.model_name,
            temperature=temp,
            max_tokens=self.max_tokens
        )
    
    def _initialize_cheap_llm(self):
        """Inicializa un LLM más barato para tareas simples - usa gpt-5-mini para economía"""
        return ChatOpenAI(
            model="gpt-5-mini",
            temperature=1.0,  # GPT-5 y variantes solo soportan 1.0
            max_tokens=1000
        )
    
    async def initialize_mcp_client(self):
        """Inicializa el cliente MCP"""
        try:
            mcp_url = f"http://{self.mcp_server_host}:{self.mcp_server_port}/mcp/"
            
            mcp_client = MultiServerMCPClient({
                "woocommerce": {
                    "url": mcp_url,
                    "transport": "streamable_http"
                }
            })
            
            self.mcp_tools = await mcp_client.get_tools()
            self.mcp_client = mcp_client
            
            print("✅ Cliente MCP inicializado correctamente")
            print(f"   Herramientas disponibles: {len(self.mcp_tools) if self.mcp_tools else 0}")
            
        except Exception as e:
            print(f"⚠️ Error inicializando MCP: {e}")
            self.mcp_tools = None
    
    async def build_agent_graph(self):
        """Construye el grafo de agentes usando LangGraph"""
        
        # Crear el grafo
        builder = StateGraph(MultiAgentState)
        
        # Agregar nodos
        builder.add_node("supervisor", self.supervisor_agent)
        builder.add_node("classifier", self.intent_classifier_agent)
        builder.add_node("search_refiner", self.search_refiner_agent)
        builder.add_node("product_agent", self.product_specialist_agent)
        builder.add_node("order_agent", self.order_specialist_agent)
        builder.add_node("support_agent", self.general_support_agent)
        builder.add_node("synthesis_agent", self.synthesis_agent)
        
        # Definir flujo
        builder.add_edge(START, "classifier")
        builder.add_edge("classifier", "supervisor")
        # search_refiner now has conditional routing
        builder.add_edge("product_agent", "synthesis_agent")
        builder.add_edge("order_agent", "synthesis_agent")
        builder.add_edge("support_agent", "synthesis_agent")
        builder.add_edge("synthesis_agent", END)
        
        # El supervisor decide a qué agente especialista enviar
        builder.add_conditional_edges(
            "supervisor",
            self.route_to_specialist,
            {
                "search_refiner": "search_refiner",
                "product_agent": "product_agent",
                "order_agent": "order_agent", 
                "support_agent": "support_agent",
                "synthesis_agent": "synthesis_agent"
            }
        )
        
        # El search_refiner decide si necesita refinamiento o continuar con búsqueda
        builder.add_conditional_edges(
            "search_refiner",
            self.route_from_refiner,
            {
                "synthesis_agent": "synthesis_agent",  # Para mostrar pregunta de refinamiento
                "product_agent": "product_agent"  # Para búsqueda directa
            }
        )
        
        self.agent_graph = builder.compile()
        print("✅ Grafo de agentes construido correctamente")
    
    async def intent_classifier_agent(self, state: MultiAgentState) -> dict:
        """Agente clasificador de intenciones usando LLM"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        classification_prompt = f"""
Eres un experto clasificador de intenciones para un sistema de atención al cliente de una tienda online.

Analiza el siguiente mensaje del cliente y clasifica la intención principal y secundarias.

Mensaje del cliente: "{last_message}"

Contexto de la conversación:
- Nombre del cliente: {state['context'].customer_name or 'Desconocido'}
- Email: {state['context'].customer_email or 'Desconocido'}
- Número de pedido previo: {state['context'].order_number or 'Ninguno'}
- Productos de interés: {', '.join(state['context'].preferred_products) or 'Ninguno'}
- Etapa de conversación: {state['context'].conversation_stage}
- Turno de conversación: {state['context'].turn_count}

Intenciones posibles:
1. product_search - Buscar, consultar o recomendar productos
2. order_inquiry - Consultar estado, seguimiento o información de pedidos
3. payment_shipping - Información sobre pagos, envíos, costos
4. returns_refunds - Devoluciones, cambios, reembolsos
5. complaint - Quejas, problemas, insatisfacción
6. general_help - Ayuda general, información de la tienda
7. greeting - Saludos, presentaciones iniciales
8. goodbye - Despedidas, cierre de conversación

Responde SOLO con un JSON válido con esta estructura:
{{
    "primary_intent": "nombre_de_intencion",
    "secondary_intents": ["intencion2", "intencion3"],
    "confidence": 0.95,
    "entities": {{
        "email": "email_si_se_menciona",
        "order_number": "numero_si_se_menciona",
        "product_names": ["producto1", "producto2"],
        "customer_name": "nombre_si_se_menciona"
    }},
    "urgency": "normal",
    "sentiment": "neutral"
}}
"""
        
        try:
            response = await self.classifier_llm.ainvoke([SystemMessage(content=classification_prompt)])
            
            # Parsear respuesta JSON
            classification_text = response.content.strip()
            if classification_text.startswith("```json"):
                classification_text = classification_text.split("```json")[1].split("```")[0]
            elif classification_text.startswith("```"):
                classification_text = classification_text.split("```")[1].split("```")[0]
            
            classification = json.loads(classification_text)
            
            # Preparar actualización del contexto
            updated_context = state['context']
            updated_context.active_intents = [classification["primary_intent"]] + classification.get("secondary_intents", [])
            
            # Actualizar entidades en el contexto
            entities = classification.get("entities", {})
            if entities.get("email"):
                updated_context.customer_email = entities["email"]
            if entities.get("customer_name"):
                updated_context.customer_name = entities["customer_name"]
            if entities.get("order_number"):
                updated_context.order_number = entities["order_number"]
            if entities.get("product_names"):
                updated_context.preferred_products.extend(entities["product_names"])
            
            updated_context.extracted_entities.update(entities)
            
            print(f"🎯 Intención clasificada: {classification['primary_intent']} (confianza: {classification['confidence']:.2f})")
            
            # Retornar actualizaciones del estado
            return {
                'current_intent': classification["primary_intent"],
                'confidence': classification["confidence"],
                'context': updated_context
            }
            
        except Exception as e:
            print(f"⚠️ Error en clasificación: {e}")
            # Fallback a clasificación simple
            return {
                'current_intent': "general_help",
                'confidence': 0.5
            }
    
    async def supervisor_agent(self, state: MultiAgentState) -> Command:
        """Agente supervisor que orquesta el flujo"""
        
        intent = state['current_intent']
        confidence = state['confidence']
        
        # Debug del estado recibido
        print(f"   Estado recibido - Intent: {intent}, Confidence: {confidence}")
        
        # Lógica de enrutamiento inteligente
        if intent in ["product_search", "product_inquiry"]:
            # Para búsquedas de productos, usar el refinador primero
            next_agent = "search_refiner"
        elif intent in ["order_inquiry", "order_status", "tracking"]:
            next_agent = "order_agent"
        elif intent in ["complaint", "returns_refunds", "payment_shipping"]:
            next_agent = "support_agent"
        elif confidence < 0.6:
            # Si la confianza es baja, usar agente de soporte general
            next_agent = "support_agent"
        else:
            next_agent = "support_agent"
        
        state['next_agent'] = next_agent
        state['context'].last_agent_used = next_agent
        
        print(f"🎯 Supervisor enruta a: {next_agent}")
        
        return Command(goto=next_agent)
    
    def route_to_specialist(self, state: MultiAgentState) -> str:
        """Función de enrutamiento para el supervisor"""
        return state['next_agent'] or "support_agent"
    
    def route_from_refiner(self, state: MultiAgentState) -> str:
        """Función de enrutamiento desde el search_refiner"""
        # Si necesita refinamiento y hay un mensaje, ir a synthesis para mostrarlo
        if state.get('needs_refinement') and state.get('refinement_message'):
            return "synthesis_agent"
        # Si no, continuar con búsqueda normal en product_agent
        return "product_agent"
    
    async def search_refiner_agent(self, state: MultiAgentState) -> Command:
        """Agente que refina búsquedas de productos mediante interacción iterativa"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        session_id = state['session_id'] or "default"
        
        print(f"🔍 Search refiner agent - session: {session_id}, message: {last_message[:50]}...")
        
        # Verificar si es una respuesta de refinamiento basado en is_refinement_response
        if state.get('is_refinement_response'):
            print(f"   ✅ Es respuesta de refinamiento, pasando directamente a product_agent")
            print(f"   📦 Query refinada: '{last_message}'")
            # El mensaje ya fue refinado en process_message, ir directo a productos
            return Command(goto="product_specialist")
        
        # Si es una respuesta a una pregunta de refinamiento (caso legacy)
        if state['needs_refinement'] and state['refinement_message']:
            # El usuario está respondiendo a nuestra pregunta de refinamiento
            refined_query = search_refiner.refine_query_with_response(
                session_id=session_id,
                user_response=last_message,
                original_query=state['search_context'].original_query if state['search_context'] else last_message
            )
            
            # Actualizar el mensaje para la búsqueda
            state["messages"][-1] = HumanMessage(content=refined_query)
            state['needs_refinement'] = False
            state['refinement_message'] = None
            
            print(f"🔧 Consulta refinada: {refined_query}")
            
            # Continuar con el agente de productos - el routing condicional lo manejará
            return Command()
        
        # Primera búsqueda - hacer una búsqueda inicial para evaluar
        print(f"🔍 Evaluando necesidad de refinamiento para: {last_message}")
        
        # Realizar búsqueda inicial REAL usando las herramientas MCP
        initial_results = []
        result_count = 0
        
        print(f"🔍 Verificación MCP: self.mcp_tools = {len(self.mcp_tools) if self.mcp_tools else 0} herramientas")
        print(f"   self.mcp_client = {self.mcp_client is not None}")
        
        if self.mcp_tools:
            try:
                # IMPORTANTE: Usar un lock para evitar concurrencia
                if not hasattr(self, '_search_lock'):
                    self._search_lock = asyncio.Lock()
                
                async with self._search_lock:
                    # Esperar un momento para evitar problemas de concurrencia
                    await asyncio.sleep(0.2)
                    
                    # CRÍTICO: Usar agente inteligente para entender la petición
                    from services.intelligent_search_agent import intelligent_search
                    user_analysis = await intelligent_search.understand_user_request(last_message)
                    
                    # Verificar si hay algo que buscar
                    search_query = user_analysis.get('search_query', '')
                    intent = user_analysis.get('intent', 'comprar')
                    
                    print(f"🤖 Análisis inteligente: query='{search_query}', intent={intent}")
                    
                    # Si no hay query o es confirmación, no buscar
                    if not search_query or intent == 'confirmación':
                        print(f"⚠️ No hay producto que buscar (query vacía o confirmación)")
                        return Command()
                    
                    # Ejecutar búsqueda con la query optimizada
                    result = await self._call_mcp_tool("search_products", {"query": search_query, "limit": 100})
                    
                    # DEBUG: Log del resultado de MCP
                    print(f"🔍 MCP Search Result (raw): {result[:500] if isinstance(result, str) else result}")
                    
                    # Parsear la respuesta real del MCP tool
                    if isinstance(result, str):
                        import json
                        import re
                        
                        # Primero buscar el marcador de conteo que agregamos
                        count_match = re.search(r'<!-- PRODUCTS_COUNT:(\d+) -->', result)
                        if count_match:
                            result_count = int(count_match.group(1))
                            
                            # Si hay productos, extraer información básica para el refinador
                            if result_count > 0:
                                # Buscar productos por los iconos de fuente (🎯 o 🔍)
                                product_matches = re.findall(r'[🎯🔍]\s+\*\*([^*]+)\*\*', result)
                                
                                for i, product_name in enumerate(product_matches[:30]):  # Máximo 30 para el refinador
                                    # Extraer marca del nombre si es posible
                                    brand = ""
                                    for brand_name in ["Schneider", "ABB", "Legrand", "Simon", "Hager", "Siemens", "Chint", "Gewiss"]:
                                        if brand_name.lower() in product_name.lower():
                                            brand = brand_name
                                            break
                                    
                                    initial_results.append({
                                        "title": product_name.strip(),
                                        "metadata": {
                                            "brand": brand,
                                            "attributes": {}
                                        }
                                    })
                        else:
                            # Fallback: buscar "No se encontraron productos"
                            if "no se encontraron productos" in result.lower():
                                result_count = 0
                                initial_results = []
                            else:
                                # Si hay contenido pero no matches claros, asumir algunos resultados
                                # Contar líneas numeradas (formato alternativo)
                                numbered_items = re.findall(r'^\d+\.\s+', result, re.MULTILINE)
                                if numbered_items:
                                    result_count = len(numbered_items)
                                    for i in range(min(result_count, 30)):
                                        initial_results.append({
                                            "title": f"Producto {i+1}",
                                            "metadata": {}
                                        })
                                else:
                                    # Si hay contenido sustancial, asumir que hay resultados
                                    if len(result) > 200:
                                        result_count = 10
                                        initial_results = [{"title": f"Producto {i+1}", "metadata": {}} for i in range(10)]
                                    else:
                                        result_count = 0
                                        initial_results = []
                
                print(f"   📦 Búsqueda inicial: {result_count} productos encontrados")
                
            except Exception as e:
                print(f"⚠️ Error en búsqueda inicial: {e}")
                print(f"   Tipo de error: {type(e).__name__}")
                import traceback
                print(f"   Stack trace: {traceback.format_exc()}")
                # En caso de error, asumir búsqueda genérica
                initial_results = []
                result_count = 0
        
        # Evaluar si necesita refinamiento basado en los resultados parseados
        needs_refinement, refinement_msg = await search_refiner.should_refine_search(
            session_id=session_id,
            query=last_message,
            search_results=initial_results if initial_results else []
        )
        
        # Forzar refinamiento para búsquedas muy genéricas
        if not needs_refinement and result_count > 10:
            # Detectar consultas muy genéricas
            generic_terms = ["cable", "interruptor", "bombilla", "luz", "protección", "material"]
            query_lower = last_message.lower()
            
            # Si la consulta es muy corta y genérica, forzar refinamiento
            if len(query_lower.split()) <= 3 and any(term in query_lower for term in generic_terms):
                # Verificar que no tiene especificaciones técnicas
                import re
                has_specs = bool(re.search(r'\d+[AaVvWw]|mm2?|\d+ma', query_lower))
                has_brand = any(brand.lower() in query_lower for brand in ["schneider", "abb", "legrand", "simon"])
                
                if not has_specs and not has_brand:
                    needs_refinement = True
                    refinement_msg = (
                        f"He encontrado {result_count} resultados para '{last_message}'. "
                        f"Para mostrarte los más relevantes, ¿podrías especificar qué tipo necesitas "
                        f"o para qué uso lo requieres?"
                    )
                    print(f"   🔄 Forzando refinamiento para consulta genérica")
        
        if needs_refinement and refinement_msg:
            # Guardar estado para la próxima iteración
            state['needs_refinement'] = True
            state['refinement_message'] = refinement_msg
            state['search_context'] = search_refiner.get_or_create_context(session_id, last_message)
            
            # Agregar pregunta de refinamiento al historial
            state["messages"].append(AIMessage(content=refinement_msg))
            
            print(f"💬 Solicitando refinamiento: {refinement_msg[:100]}...")
            
            # Guardar mensaje de refinamiento para synthesis_agent
            state['agent_responses']["search_refiner"] = refinement_msg
            # El routing condicional se encargará de dirigir a synthesis_agent
            return Command()
        
        # No necesita refinamiento, continuar con búsqueda normal
        print(f"✅ Búsqueda directa sin refinamiento - Resultados manejables")
        # El routing condicional se encargará de dirigir a product_agent
        return Command()
    
    async def product_specialist_agent(self, state: MultiAgentState) -> Command:
        """Agente especialista en productos"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        print(f"🔍 Product agent - Mensaje: {last_message[:50]}...")
        print(f"🔧 MCP Tools disponibles: {len(self.mcp_tools) if self.mcp_tools else 0}")
        
        system_prompt = f"""
Eres {self.bot_name} de {self.company_name}, especialista en productos eléctricos.

INFORMACIÓN CRÍTICA:
- NO HAY TIENDA FÍSICA. Somos una tienda exclusivamente online.
- Tenemos más de 4,500 productos eléctricos en nuestro catálogo online.
- Web: https://elcorteelectrico.com

REGLAS CRÍTICAS:
1. SIEMPRE usa search_products para buscar productos cuando el cliente busque algo
2. Muestra PRODUCTOS REALES con precios y disponibilidad
3. Si encuentras menos de 10 productos, muéstralos TODOS
4. Si encuentras más de 10, muestra los 10 más relevantes
5. Incluye precio, disponibilidad y enlace de cada producto
6. NO inventes productos - usa SOLO los resultados de search_products

Cliente: {state['context'].customer_name or 'Cliente'}
Consulta: {last_message}

IMPORTANTE: Si la consulta menciona productos o cables, DEBES usar search_products.
"""
        
        # Obtener herramientas relevantes para productos
        relevant_tools = self._get_product_tools() if self.mcp_tools else []
        print(f"🛠️ Herramientas de productos encontradas: {len(relevant_tools)}")
        if relevant_tools:
            print(f"   Herramientas: {[t.name for t in relevant_tools]}")
        
        if relevant_tools:
            # Usar LLM con herramientas
            llm_with_tools = self.main_llm.bind_tools(relevant_tools)
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]  # Contexto limitado
            
            response = await llm_with_tools.ainvoke(messages)
            
            print(f"📝 LLM Response type: {type(response)}")
            print(f"📝 Has tool_calls: {hasattr(response, 'tool_calls')}")
            if hasattr(response, 'tool_calls'):
                print(f"📝 Tool calls: {response.tool_calls}")
            
            # Ejecutar herramientas si es necesario
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = await self._execute_tool_calls(response.tool_calls)
                
                # Generar respuesta final con resultados
                from langchain_core.messages import ToolMessage
                tool_messages = []
                for tool_call, result in zip(response.tool_calls, tool_results):
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    ))
                
                final_messages = messages + [response] + tool_messages
                final_response = await self.main_llm.ainvoke(final_messages)
                response_text = final_response.content
                
                # Registrar herramientas usadas
                state['tools_used'].extend([tc['name'] for tc in response.tool_calls])
            else:
                response_text = response.content
        else:
            # Sin herramientas, usar LLM solo
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
            response = await self.main_llm.ainvoke(messages)
            response_text = response.content
        
        # Guardar respuesta del agente
        print(f"📦 PRODUCT_AGENT: Guardando respuesta: {response_text[:200] if response_text else 'EMPTY'}...")
        state['agent_responses']["product_agent"] = response_text
        
        return Command(goto="synthesis_agent")
    
    async def order_specialist_agent(self, state: MultiAgentState) -> Command:
        """Agente especialista en pedidos"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        system_prompt = f"""
Eres {self.bot_name} de {self.company_name}, especialista en pedidos.

INFORMACIÓN CRÍTICA:
- NO HAY TIENDA FÍSICA. Solo vendemos online.
- Los pedidos se envían por mensajería.
- No hay recogida en tienda.

REGLAS:
1. Responde en 2-3 frases máximo
2. Para consultar pedidos NECESITAS: número de pedido Y email
3. Si no tienes ambos datos, pídelos brevemente
4. Si no puedes ayudar: "Contacta por WhatsApp: https://wa.me/34614218122"
5. NO inventes información sobre pedidos

Cliente: {state['context'].customer_name or 'Cliente'}
Consulta: {last_message}

Sé BREVE y directo.
"""
        
        # Obtener herramientas relevantes para pedidos
        relevant_tools = self._get_order_tools() if self.mcp_tools else []
        
        if relevant_tools:
            llm_with_tools = self.main_llm.bind_tools(relevant_tools)
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
            
            response = await llm_with_tools.ainvoke(messages)
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = await self._execute_tool_calls(response.tool_calls)
                
                from langchain_core.messages import ToolMessage
                tool_messages = []
                for tool_call, result in zip(response.tool_calls, tool_results):
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    ))
                
                final_messages = messages + [response] + tool_messages
                final_response = await self.main_llm.ainvoke(final_messages)
                response_text = final_response.content
                
                state['tools_used'].extend([tc['name'] for tc in response.tool_calls])
            else:
                response_text = response.content
        else:
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
            response = await self.main_llm.ainvoke(messages)
            response_text = response.content
        
        state['agent_responses']["order_agent"] = response_text
        
        return Command(goto="synthesis_agent")
    
    async def general_support_agent(self, state: MultiAgentState) -> Command:
        """Agente de soporte general"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        system_prompt = f"""
Eres {self.bot_name} de {self.company_name}, soporte general.

INFORMACIÓN CRÍTICA:
- NO HAY TIENDA FÍSICA. Somos 100% online.
- Más de 4,500 productos eléctricos disponibles.
- Web: https://elcorteelectrico.com

REGLAS:
1. Máximo 2-3 frases
2. Envío gratis > 100€ (península)
3. Devoluciones: 14 días (30 para profesionales)
4. Si no sabes: "Contacta por WhatsApp: https://wa.me/34614218122"
5. NO inventes información ni datos
6. Si preguntan por ubicación: somos solo online

Cliente: {state['context'].customer_name or 'Cliente'}

CONSULTA DEL CLIENTE: {last_message}

Responde de manera comprensiva y útil.
"""
        
        messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
        response = await self.main_llm.ainvoke(messages)
        
        state['agent_responses']["support_agent"] = response.content
        
        return Command(goto="synthesis_agent")
    
    async def synthesis_agent(self, state: MultiAgentState) -> Command:
        """Agente que sintetiza respuestas de múltiples agentes"""
        
        # Si solo hay una respuesta de agente, usarla directamente
        agent_responses = state['agent_responses']
        
        # DEBUG: Ver qué respuestas hay
        print(f"🎯 SYNTHESIS: agent_responses = {agent_responses}")
        print(f"🎯 SYNTHESIS: Número de respuestas: {len(agent_responses)}")
        for agent, response in agent_responses.items():
            print(f"   - {agent}: {response[:100] if response else 'EMPTY'}...")
        
        # PRIORIDAD 1: Si hay un mensaje de refinamiento, usarlo siempre
        if state.get('needs_refinement') and state.get('refinement_message'):
            final_response = state['refinement_message']
            print(f"✅ SYNTHESIS: Usando mensaje de refinamiento")
        elif "search_refiner" in agent_responses and agent_responses["search_refiner"]:
            # Si hay respuesta del search_refiner, usarla (es una pregunta de refinamiento)
            final_response = agent_responses["search_refiner"]
            print(f"✅ SYNTHESIS: Usando respuesta de search_refiner (refinamiento)")
        else:
            # Filtrar respuestas vacías
            valid_responses = {k: v for k, v in agent_responses.items() if v and v.strip()}
            
            if not valid_responses:
                # Si no hay respuestas válidas, generar una respuesta de fallback
                print("⚠️ SYNTHESIS: No hay respuestas válidas, generando fallback")
                final_response = "Lo siento, no pude procesar tu solicitud correctamente. ¿Podrías reformularla o darme más detalles?"
            elif len(valid_responses) == 1:
                # Si solo hay una respuesta válida, usarla directamente
                final_response = list(valid_responses.values())[0]
                print(f"✅ SYNTHESIS: Usando única respuesta de {list(valid_responses.keys())[0]}")
            elif "product_agent" in valid_responses and len(valid_responses.get("product_agent", "")) > 100:
                # Si el product_agent tiene una respuesta sustancial con productos, priorizarla
                final_response = valid_responses["product_agent"]
                print(f"✅ SYNTHESIS: Priorizando respuesta de product_agent con productos")
            else:
                # Sintetizar múltiples respuestas
                synthesis_prompt = f"""
Eres {self.bot_name}, y necesitas sintetizar las siguientes respuestas de agentes especialistas en una respuesta coherente y natural:

RESPUESTAS DE AGENTES:
{json.dumps(valid_responses, indent=2, ensure_ascii=False)}

CONTEXTO:
- Cliente: {state['context'].customer_name or 'Cliente'}
- Intención: {state['current_intent']}
- Herramientas usadas: {', '.join(state['tools_used']) if state['tools_used'] else 'Ninguna'}

INSTRUCCIONES:
- Combina la información de manera fluida y natural
- Evita repeticiones
- Mantén el tono amigable y profesional de Eva
- Si hay información contradictoria, prioriza la más específica
- Asegúrate de que la respuesta sea completa y útil

Genera una respuesta final coherente:
"""
            
            messages = [SystemMessage(content=synthesis_prompt)]
            response = await self.cheap_llm.ainvoke(messages)  # Usar LLM barato para síntesis
            final_response = response.content
            print(f"✅ SYNTHESIS: Sintetizadas {len(valid_responses)} respuestas")
        
        # Asegurarse de que final_response no esté vacío
        if not final_response or not final_response.strip():
            final_response = "Lo siento, hubo un problema procesando tu solicitud. ¿Podrías intentarlo de nuevo?"
            print("⚠️ SYNTHESIS: Respuesta final vacía, usando fallback")
        
        # Agregar respuesta final al historial
        state["messages"].append(AIMessage(content=final_response))
        
        # Actualizar contexto
        state['context'].turn_count += 1
        state['context'].conversation_summary += f" Respondió sobre {state['current_intent']}."
        
        return Command(goto=END)
    
    def _get_product_tools(self):
        """Obtiene herramientas relacionadas con productos"""
        if not self.mcp_tools:
            return []
        
        product_tool_names = [
            "search_products", "get_product_details", "check_product_stock",
            "get_product_categories", "get_products_by_category", 
            "get_featured_products", "get_products_on_sale"
        ]
        
        return [tool for tool in self.mcp_tools if tool.name in product_tool_names]
    
    def _get_order_tools(self):
        """Obtiene herramientas relacionadas con pedidos"""
        if not self.mcp_tools:
            return []
        
        order_tool_names = [
            "get_order_status", "track_order", "get_recent_orders",
            "get_orders_by_status", "search_orders_by_customer", "create_order_summary"
        ]
        
        return [tool for tool in self.mcp_tools if tool.name in order_tool_names]
    
    async def _execute_tool_calls(self, tool_calls):
        """Ejecuta llamadas a herramientas MCP"""
        results = []
        for tool_call in tool_calls:
            try:
                result = await self._call_mcp_tool(tool_call['name'], tool_call['args'])
                results.append(result)
            except Exception as e:
                print(f"❌ Error en herramienta {tool_call['name']}: {e}")
                results.append(f"Error consultando {tool_call['name']}: {str(e)}")
        return results
    
    async def _call_mcp_tool(self, tool_name: str, tool_args: dict):
        """Llama a una herramienta MCP"""
        if not self.mcp_client:
            raise Exception("Cliente MCP no disponible")
        
        try:
            # Crear nueva sesión para cada llamada (evita problemas de concurrencia)
            async with self.mcp_client.session("woocommerce") as session:
                result = await session.call_tool(tool_name, tool_args)
                
                if hasattr(result, 'content') and result.content:
                    if isinstance(result.content, list) and len(result.content) > 0:
                        first_content = result.content[0]
                        if hasattr(first_content, 'text'):
                            return first_content.text
                        else:
                            return str(first_content)
                    else:
                        return str(result.content)
                else:
                    return str(result)
                    
        except Exception as e:
            print(f"❌ Error ejecutando herramienta {tool_name}: {e}")
            raise
    
    async def process_message(self, message: str, session_id: str = None, conversation_history: list = None) -> str:
        """Procesa un mensaje usando el sistema multi-agente"""
        
        if not self.agent_graph:
            await self.build_agent_graph()
        
        print(f"\n👤 Usuario: {message}")
        
        # Generar session_id si no se proporciona
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Importar search_refiner para verificar contexto
        from src.agent.search_refiner_agent import search_refiner, RefinementState
        
        # Verificar si hay un contexto de refinamiento activo
        refiner_context = search_refiner.contexts.get(session_id)
        
        # Si hay un contexto de refinamiento activo, combinar el mensaje con la consulta original
        if refiner_context and refiner_context.current_state.value in ["asking_brand", "asking_attribute"]:
            # Refinar la consulta original con la respuesta del usuario
            refined_query = search_refiner.refine_query_with_response(
                session_id=session_id,
                user_response=message,
                original_query=refiner_context.original_query
            )
            print(f"🔄 Refinando búsqueda: '{refiner_context.original_query}' + '{message}' = '{refined_query}'")
            # Usar la consulta refinada para la búsqueda
            message_to_process = refined_query
        else:
            message_to_process = message
        
        # Crear estado inicial como diccionario
        initial_state = {
            "messages": [HumanMessage(content=message_to_process)],
            "context": ConversationContext(),
            "current_intent": "unknown",
            "confidence": 0.0,
            "next_agent": None,
            "agent_responses": {},
            "tools_used": [],
            "needs_human_handoff": False,
            "search_context": refiner_context,  # Pasar el contexto de refinamiento
            "needs_refinement": False,
            "refinement_message": None,
            "session_id": session_id,
            "original_message": message,  # Guardar el mensaje original
            "is_refinement_response": refiner_context is not None  # Indicar si es respuesta de refinamiento
        }
        
        try:
            # Ejecutar el grafo de agentes
            final_state = await self.agent_graph.ainvoke(initial_state)
            
            # Obtener la respuesta final
            final_message = final_state["messages"][-1]
            response_text = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            print(f"🤖 Eva: {response_text}")
            
            # Estadísticas
            print(f"📊 Intención: {final_state['current_intent']} (confianza: {final_state['confidence']:.2f})")
            if final_state['tools_used']:
                print(f"🔧 Herramientas usadas: {', '.join(final_state['tools_used'])}")
            
            return response_text
            
        except Exception as e:
            print(f"⚠️ Error en procesamiento multi-agente: {e}")
            return await self._fallback_response(message)
    
    async def _fallback_response(self, message: str) -> str:
        """Respuesta de fallback en caso de error"""
        fallback_prompt = f"""
Eres {self.bot_name}, asistente de atención al cliente de {self.company_name}. El sistema avanzado no está disponible, 
pero puedes ayudar de manera básica.

INFORMACIÓN IMPORTANTE:
- NO HAY TIENDA FÍSICA. Somos 100% online.
- Más de 4,500 productos eléctricos disponibles.
- Web: https://elcorteelectrico.com
- WhatsApp directo: https://wa.me/34614218122

Cliente dice: "{message}"

Responde de manera amigable y útil, ofreciendo ayuda general sobre nuestra tienda de material eléctrico.
"""
        
        try:
            response = await self.cheap_llm.ainvoke([SystemMessage(content=fallback_prompt)])
            return response.content
        except Exception as e:
            return "Disculpa, estoy teniendo dificultades técnicas. ¿Podrías intentar de nuevo en un momento? 😊"

# Función de prueba
async def test_multi_agent_system():
    """Prueba el sistema multi-agente"""
    print("🚀 Iniciando Sistema Multi-Agente...")
    
    system = CustomerServiceMultiAgent()
    await system.initialize_mcp_client()
    
    test_messages = [
        "Hola, busco velas de lavanda para relajarme",
        "También quiero saber sobre mi pedido #1817, mi email es cliente@test.com",
        "¿Cuánto cuesta el envío a Madrid?",
        "Tengo una queja sobre un producto que llegó dañado",
        "Gracias por tu ayuda, hasta luego"
    ]
    
    print("\n" + "="*60)
    print("🧪 PRUEBA DEL SISTEMA MULTI-AGENTE")
    print("="*60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- MENSAJE {i} ---")
        response = await system.process_message(message)
        print("\n" + "-"*40)

if __name__ == "__main__":
    asyncio.run(test_multi_agent_system())