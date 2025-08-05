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
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

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

class MultiAgentState(MessagesState):
    """Estado compartido entre todos los agentes"""
    context: ConversationContext = field(default_factory=ConversationContext)
    current_intent: str = "general"
    confidence: float = 0.0
    next_agent: Optional[str] = None
    agent_responses: Dict[str, str] = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    needs_human_handoff: bool = False

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
    
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai")
        self.model_name = os.getenv("MODEL_NAME", "gpt-4.1")
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
        
        # Grafo de agentes
        self.agent_graph = None
        
    def _initialize_llm(self, temperature: Optional[float] = None):
        """Inicializa el LLM principal - siempre usa OpenAI"""
        temp = temperature if temperature is not None else self.temperature
        
        return ChatOpenAI(
            model=self.model_name,
            temperature=temp,
            max_tokens=self.max_tokens
        )
    
    def _initialize_cheap_llm(self):
        """Inicializa un LLM más barato para tareas simples - usa gpt-4.1-mini para economía"""
        return ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.1,
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
        builder.add_node("product_agent", self.product_specialist_agent)
        builder.add_node("order_agent", self.order_specialist_agent)
        builder.add_node("support_agent", self.general_support_agent)
        builder.add_node("synthesis_agent", self.synthesis_agent)
        
        # Definir flujo
        builder.add_edge(START, "classifier")
        builder.add_edge("classifier", "supervisor")
        builder.add_edge("product_agent", "synthesis_agent")
        builder.add_edge("order_agent", "synthesis_agent")
        builder.add_edge("support_agent", "synthesis_agent")
        builder.add_edge("synthesis_agent", END)
        
        # El supervisor decide a qué agente especialista enviar
        builder.add_conditional_edges(
            "supervisor",
            self.route_to_specialist,
            {
                "product_agent": "product_agent",
                "order_agent": "order_agent", 
                "support_agent": "support_agent",
                "synthesis_agent": "synthesis_agent"
            }
        )
        
        self.agent_graph = builder.compile()
        print("✅ Grafo de agentes construido correctamente")
    
    async def intent_classifier_agent(self, state: MultiAgentState) -> Command:
        """Agente clasificador de intenciones usando LLM"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        classification_prompt = f"""
Eres un experto clasificador de intenciones para un sistema de atención al cliente de una tienda online.

Analiza el siguiente mensaje del cliente y clasifica la intención principal y secundarias.

Mensaje del cliente: "{last_message}"

Contexto de la conversación:
- Nombre del cliente: {state.context.customer_name or 'Desconocido'}
- Email: {state.context.customer_email or 'Desconocido'}
- Número de pedido previo: {state.context.order_number or 'Ninguno'}
- Productos de interés: {', '.join(state.context.preferred_products) or 'Ninguno'}
- Etapa de conversación: {state.context.conversation_stage}
- Turno de conversación: {state.context.turn_count}

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
            
            # Actualizar estado
            state.context.active_intents = [classification["primary_intent"]] + classification.get("secondary_intents", [])
            state.current_intent = classification["primary_intent"]
            state.confidence = classification["confidence"]
            
            # Actualizar entidades
            entities = classification.get("entities", {})
            if entities.get("email"):
                state.context.customer_email = entities["email"]
            if entities.get("customer_name"):
                state.context.customer_name = entities["customer_name"]
            if entities.get("order_number"):
                state.context.order_number = entities["order_number"]
            if entities.get("product_names"):
                state.context.preferred_products.extend(entities["product_names"])
            
            state.context.extracted_entities.update(entities)
            
            print(f"🎯 Intención clasificada: {classification['primary_intent']} (confianza: {classification['confidence']:.2f})")
            
        except Exception as e:
            print(f"⚠️ Error en clasificación: {e}")
            # Fallback a clasificación simple
            state.current_intent = "general_help"
            state.confidence = 0.5
        
        return Command(goto="supervisor")
    
    async def supervisor_agent(self, state: MultiAgentState) -> Command:
        """Agente supervisor que orquesta el flujo"""
        
        intent = state.current_intent
        confidence = state.confidence
        
        # Lógica de enrutamiento inteligente
        if intent in ["product_search", "product_inquiry"]:
            next_agent = "product_agent"
        elif intent in ["order_inquiry", "order_status", "tracking"]:
            next_agent = "order_agent"
        elif intent in ["complaint", "returns_refunds", "payment_shipping"]:
            next_agent = "support_agent"
        elif confidence < 0.6:
            # Si la confianza es baja, usar agente de soporte general
            next_agent = "support_agent"
        else:
            next_agent = "support_agent"
        
        state.next_agent = next_agent
        state.context.last_agent_used = next_agent
        
        print(f"🎯 Supervisor enruta a: {next_agent}")
        
        return Command(goto=next_agent)
    
    def route_to_specialist(self, state: MultiAgentState) -> str:
        """Función de enrutamiento para el supervisor"""
        return state.next_agent or "support_agent"
    
    async def product_specialist_agent(self, state: MultiAgentState) -> Command:
        """Agente especialista en productos"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        system_prompt = f"""
Eres Eva de El Corte Eléctrico, especialista en productos eléctricos.

REGLAS CRÍTICAS:
1. MÁXIMO 2-3 frases en respuestas normales
2. Solo detalles si los piden EXPLÍCITAMENTE
3. Si no sabes: "Llama al (+34) 614 21 81 22"
4. NO inventes información

Cliente: {state.context.customer_name or 'Cliente'}
Consulta: {last_message}

Responde BREVE y directo.
"""
        
        # Obtener herramientas relevantes para productos
        relevant_tools = self._get_product_tools() if self.mcp_tools else []
        
        if relevant_tools:
            # Usar LLM con herramientas
            llm_with_tools = self.main_llm.bind_tools(relevant_tools)
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]  # Contexto limitado
            
            response = await llm_with_tools.ainvoke(messages)
            
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
                state.tools_used.extend([tc['name'] for tc in response.tool_calls])
            else:
                response_text = response.content
        else:
            # Sin herramientas, usar LLM solo
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
            response = await self.main_llm.ainvoke(messages)
            response_text = response.content
        
        # Guardar respuesta del agente
        state.agent_responses["product_agent"] = response_text
        
        return Command(goto="synthesis_agent")
    
    async def order_specialist_agent(self, state: MultiAgentState) -> Command:
        """Agente especialista en pedidos"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        system_prompt = f"""
Eres Eva de El Corte Eléctrico, especialista en pedidos.

REGLAS:
1. Responde en 2-3 frases máximo
2. Para consultar pedidos NECESITAS: número de pedido Y email
3. Si no tienes ambos datos, pídelos brevemente
4. Si no puedes ayudar: "Llama al (+34) 614 21 81 22"

Cliente: {state.context.customer_name or 'Cliente'}
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
                
                state.tools_used.extend([tc['name'] for tc in response.tool_calls])
            else:
                response_text = response.content
        else:
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
            response = await self.main_llm.ainvoke(messages)
            response_text = response.content
        
        state.agent_responses["order_agent"] = response_text
        
        return Command(goto="synthesis_agent")
    
    async def general_support_agent(self, state: MultiAgentState) -> Command:
        """Agente de soporte general"""
        
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        system_prompt = f"""
Eres Eva de El Corte Eléctrico, soporte general.

REGLAS:
1. Máximo 2-3 frases
2. Envío gratis > 100€ (península)
3. Devoluciones: 14 días (30 para profesionales)
4. Si no sabes: "Llama al (+34) 614 21 81 22"
5. NO inventes información

Cliente: {state.context.customer_name or 'Cliente'}

CONSULTA DEL CLIENTE: {last_message}

Responde de manera comprensiva y útil.
"""
        
        messages = [SystemMessage(content=system_prompt)] + state["messages"][-3:]
        response = await self.main_llm.ainvoke(messages)
        
        state.agent_responses["support_agent"] = response.content
        
        return Command(goto="synthesis_agent")
    
    async def synthesis_agent(self, state: MultiAgentState) -> Command:
        """Agente que sintetiza respuestas de múltiples agentes"""
        
        # Si solo hay una respuesta de agente, usarla directamente
        agent_responses = state.agent_responses
        
        if len(agent_responses) == 1:
            final_response = list(agent_responses.values())[0]
        else:
            # Sintetizar múltiples respuestas
            synthesis_prompt = f"""
Eres Eva, y necesitas sintetizar las siguientes respuestas de agentes especialistas en una respuesta coherente y natural:

RESPUESTAS DE AGENTES:
{json.dumps(agent_responses, indent=2, ensure_ascii=False)}

CONTEXTO:
- Cliente: {state.context.customer_name or 'Cliente'}
- Intención: {state.current_intent}
- Herramientas usadas: {', '.join(state.tools_used) if state.tools_used else 'Ninguna'}

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
        
        # Agregar respuesta final al historial
        state["messages"].append(AIMessage(content=final_response))
        
        # Actualizar contexto
        state.context.turn_count += 1
        state.context.conversation_summary += f" Respondió sobre {state.current_intent}."
        
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
    
    async def process_message(self, message: str) -> str:
        """Procesa un mensaje usando el sistema multi-agente"""
        
        if not self.agent_graph:
            await self.build_agent_graph()
        
        print(f"\n👤 Usuario: {message}")
        
        # Crear estado inicial
        initial_state = MultiAgentState(
            messages=[HumanMessage(content=message)],
            context=ConversationContext(),
            current_intent="unknown",
            confidence=0.0,
            agent_responses={},
            tools_used=[]
        )
        
        try:
            # Ejecutar el grafo de agentes
            final_state = await self.agent_graph.ainvoke(initial_state)
            
            # Obtener la respuesta final
            final_message = final_state["messages"][-1]
            response_text = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            print(f"🤖 Eva: {response_text}")
            
            # Estadísticas
            print(f"📊 Intención: {final_state.current_intent} (confianza: {final_state.confidence:.2f})")
            if final_state.tools_used:
                print(f"🔧 Herramientas usadas: {', '.join(final_state.tools_used)}")
            
            return response_text
            
        except Exception as e:
            print(f"⚠️ Error en procesamiento multi-agente: {e}")
            return await self._fallback_response(message)
    
    async def _fallback_response(self, message: str) -> str:
        """Respuesta de fallback en caso de error"""
        fallback_prompt = f"""
Eres Eva, asistente de atención al cliente. El sistema avanzado no está disponible, 
pero puedes ayudar de manera básica.

Cliente dice: "{message}"

Responde de manera amigable y útil, ofreciendo ayuda general sobre nuestra tienda de velas aromáticas y perfumes.
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