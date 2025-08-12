#!/usr/bin/env python3
"""
Script para diagnosticar por qué falla la selección de estrategia con ciertos productos
"""

import asyncio
import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv("env.agent")

import logging
logging.basicConfig(level=logging.INFO)

async def test_strategy_determination():
    from src.agent.hybrid_agent import HybridCustomerAgent
    
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    test_queries = [
        "quiero un ventilador industrial",
        "quiero un termo eléctrico",
        "busco un diferencial",
        "necesito cables",
        "hola",
        "gracias"
    ]
    
    print("\n=== PRUEBA DE DETERMINACIÓN DE ESTRATEGIA ===\n")
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 50)
        
        try:
            # Probar la determinación de estrategia
            strategy = await agent._determine_response_strategy(query)
            print(f"✅ Estrategia determinada: {strategy}")
            
            # También probar el fallback
            fallback = agent._fallback_strategy_selection(query)
            print(f"🔄 Estrategia fallback: {fallback}")
            
            # Clasificar tipo de consulta
            query_type = await agent._classify_query_type(query)
            print(f"📊 Tipo de consulta: {query_type}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_strategy_determination())