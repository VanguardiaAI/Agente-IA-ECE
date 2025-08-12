#!/usr/bin/env python3
"""
Script para probar el flujo completo de búsqueda con el optimizador GPT-5
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

async def test_complete_flow():
    from src.agent.hybrid_agent import HybridCustomerAgent
    
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    test_queries = [
        "quiero un termo eléctrico",
        "busco un diferencial",
        "necesito un ventilador industrial"
    ]
    
    print("\n=== PRUEBA COMPLETA DE BÚSQUEDA CON OPTIMIZACIÓN GPT-5 ===\n")
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"📝 Consulta: '{query}'")
        print(f"{'='*60}\n")
        
        try:
            # Procesar mensaje completo
            response = await agent.process_message(query, "test_user", "wordpress")
            
            # Mostrar respuesta (truncada si es muy larga)
            if len(response) > 500:
                print(f"🤖 Respuesta:\n{response[:500]}...\n[Respuesta truncada]")
            else:
                print(f"🤖 Respuesta:\n{response}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Prueba completa finalizada")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())