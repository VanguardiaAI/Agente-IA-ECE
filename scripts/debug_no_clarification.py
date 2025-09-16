#!/usr/bin/env python3
"""
Debug por qué no pide clarificación correctamente
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
load_dotenv("env.agent")

from src.agent.eva_gpt5_agent import EvaGPT5Agent
from src.agent.gpt5_agents import SearchAnalyzer

async def test():
    # Primero verificar el análisis
    print("1. ANÁLISIS DE BÚSQUEDA")
    print("="*60)
    
    analyzer = SearchAnalyzer()
    analysis = await analyzer.analyze_search(
        "quiero un automático",
        []
    )
    
    print(f"Mensaje: 'quiero un automático'")
    print(f"Tipo producto: {analysis.product_type}")
    print(f"Tiene suficiente info: {analysis.has_enough_info}")
    print(f"Necesita clarificación: {analysis.clarification_needed}")
    print(f"Info faltante: {analysis.missing_info}")
    
    # Ahora probar el agente completo
    print("\n\n2. FLUJO COMPLETO DEL AGENTE")
    print("="*60)
    
    agent = EvaGPT5Agent()
    await agent.initialize()
    
    # Ver configuración
    print(f"Max intentos de búsqueda: {agent.max_search_attempts}")
    
    # Primera consulta
    response = await agent.process_message(
        message="quiero un automático",
        user_id="test_debug",
        session_id="debug_session_1",
        platform="test"
    )
    
    print(f"\nRespuesta:")
    print(response[:200] + "..." if len(response) > 200 else response)
    
    # Verificar estado
    conv = agent.conversations.get("debug_session_1")
    if conv:
        print(f"\nEstado conversación:")
        print(f"- search_state: {conv.search_state}")
        print(f"- search_context existe: {conv.search_context is not None}")
        if conv.search_context:
            print(f"- has_clarified: {conv.search_context.has_clarified}")
            print(f"- missing_info: {conv.search_context.missing_info}")
            print(f"- search_attempts: {len(conv.search_context.search_attempts)}")

if __name__ == "__main__":
    asyncio.run(test())