#!/usr/bin/env python3
"""
Cliente para GPT-5 usando la nueva Responses API
Implementación completa según documentación oficial de OpenAI
"""

import os
import json
import logging
import aiohttp
from typing import Dict, Any, Optional, List, Literal, Union
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("env.agent")

logger = logging.getLogger(__name__)


class ReasoningEffort(str, Enum):
    """Niveles de esfuerzo de razonamiento"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Verbosity(str, Enum):
    """Niveles de verbosidad de respuesta"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class GPT5Response:
    """Respuesta estructurada de GPT-5"""
    content: str
    reasoning_summary: Optional[str] = None
    model: str = "gpt-5"
    usage: Optional[Dict[str, int]] = None
    response_id: str = ""
    raw_response: Optional[Dict] = None
    output_text: str = ""  # Helper field


class GPT5Client:
    """Cliente para GPT-5 usando Responses API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no configurada")
        
        # USAR ENDPOINT DE RESPONSES API, NO CHAT COMPLETIONS
        self.base_url = "https://api.openai.com/v1/responses"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Cache para mantener contexto entre conversaciones
        self.conversation_cache = {}
        
    async def create_response(
        self,
        input_text: Union[str, List[Dict[str, str]]],
        model: str = "gpt-5",  # USAR GPT-5 POR DEFECTO
        reasoning_effort: ReasoningEffort = ReasoningEffort.LOW,
        verbosity: Verbosity = Verbosity.MEDIUM,
        max_completion_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        store: bool = True,
        previous_response_id: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> GPT5Response:
        """
        Crea una respuesta usando la API de Responses de GPT-5
        """
        
        # Construir el payload según la documentación de Responses API
        payload = {
            "model": model,  # gpt-5, gpt-5-mini, gpt-5-nano
            "input": input_text,
            "reasoning": {
                "effort": reasoning_effort.value
            },
            "text": {
                "verbosity": verbosity.value
            },
            "store": store
        }
        
        # Agregar parámetros opcionales
        # NOTA: En la API de Responses de GPT-5 no existe max_output_tokens
        # El control de tokens se hace a través de verbosity
            
        if tools:
            payload["tools"] = tools
            
        if tool_choice:
            payload["tool_choice"] = tool_choice
            
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
            
        if instructions:
            payload["instructions"] = instructions
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error en GPT-5 API: {response.status} - {error_text}")
                        raise Exception(f"API Error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # Extraer contenido según estructura de Responses API
                    output_text = ""
                    content = ""
                    reasoning_summary = ""
                    
                    # La respuesta tiene un array 'output' con items
                    if "output" in result and isinstance(result["output"], list):
                        for item in result["output"]:
                            if item.get("type") == "message":
                                # Extraer texto del mensaje
                                if "content" in item and isinstance(item["content"], list):
                                    for content_item in item["content"]:
                                        if content_item.get("type") == "output_text":
                                            output_text = content_item.get("text", "")
                                            content = output_text
                            elif item.get("type") == "reasoning":
                                # Capturar resumen de razonamiento
                                if "summary" in item:
                                    reasoning_summary = " ".join(item["summary"])
                    
                    # Si hay output_text directo en la respuesta
                    if "output_text" in result:
                        output_text = result["output_text"]
                        content = output_text
                    
                    # Debug log para entender la estructura
                    if not content:
                        logger.warning(f"GPT-5 response sin content. Raw response keys: {list(result.keys())}")
                        if "output" in result:
                            logger.warning(f"Output structure: {result['output'][:200] if isinstance(result['output'], str) else 'not a string'}")
                    
                    return GPT5Response(
                        content=content,
                        reasoning_summary=reasoning_summary,
                        model=result.get("model", model),
                        usage=result.get("usage"),
                        response_id=result.get("id", ""),
                        raw_response=result,
                        output_text=output_text
                    )
                    
        except Exception as e:
            logger.error(f"Error llamando a GPT-5 API: {e}")
            raise
    
    async def create_conversational_response(
        self,
        message: str,
        conversation_id: str,
        system_prompt: Optional[str] = None,
        reasoning_effort: ReasoningEffort = ReasoningEffort.LOW,
        verbosity: Verbosity = Verbosity.MEDIUM,
        model: str = "gpt-5"  # GPT-5 por defecto
    ) -> GPT5Response:
        """
        Crea una respuesta manteniendo contexto conversacional
        """
        
        # Obtener el ID de respuesta previa si existe
        previous_response_id = self.conversation_cache.get(conversation_id)
        
        # Usar instructions para system prompt
        instructions = system_prompt if system_prompt and not previous_response_id else None
        
        # Crear respuesta
        response = await self.create_response(
            input_text=message,
            model=model,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
            previous_response_id=previous_response_id,
            instructions=instructions,
            store=True
        )
        
        # Guardar ID para próxima interacción
        if response.response_id:
            self.conversation_cache[conversation_id] = response.response_id
        
        return response
    
    async def create_agent_response(
        self,
        task: str,
        tools: List[Dict],
        reasoning_effort: ReasoningEffort = ReasoningEffort.LOW,
        verbosity: Verbosity = Verbosity.MEDIUM,
        allowed_tools: Optional[List[str]] = None,
        model: str = "gpt-5"  # GPT-5 por defecto
    ) -> GPT5Response:
        """
        Crea una respuesta para tareas de agente con herramientas
        """
        
        # Configurar tool_choice si hay allowed_tools
        tool_choice = None
        if allowed_tools:
            tool_choice = {
                "type": "allowed_tools",
                "mode": "auto",
                "tools": [{"type": "function", "name": name} for name in allowed_tools]
            }
        
        # Instrucciones optimizadas para agentes
        instructions = f"""Eres un agente inteligente con acceso a herramientas.
Tu tarea es: {task}

Antes de usar una herramienta, explica brevemente por qué la vas a usar.
Sé eficiente y preciso en tu razonamiento."""
        
        return await self.create_response(
            input_text=task,
            model=model,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
            tools=tools,
            tool_choice=tool_choice,
            instructions=instructions
        )


# Instancia global para uso sencillo
gpt5_client = GPT5Client()