#!/usr/bin/env python3
"""
Prueba con datos reales de pedidos
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.hybrid_agent import HybridCustomerAgent
from dotenv import load_dotenv

async def test_real_order():
    """Probar consulta de pedido real con datos específicos"""
    print('🚀 Probando consulta de pedido real...')
    
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    print(f"✅ Agente inicializado")
    print(f"   Herramientas MCP: {len(agent.mcp_tools) if agent.mcp_tools else 0}")
    
    if not agent.mcp_tools:
        print("❌ ERROR: No se detectaron herramientas MCP")
        return
    
    print(f"✅ Herramientas MCP disponibles: {len(agent.mcp_tools)}")
    
    # Casos de prueba con datos reales
    test_cases = [
        "Hola, soy Pablo Luque y quiero consultar mi pedido #1817",
        "Mi email es pablo.ar.luque@gmail.com, ¿puedes buscar mis pedidos?",
        "¿Cuál es el estado del pedido 1817?",
        "Busca pedidos para el email pablo.ar.luque@gmail.com"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"🧪 PRUEBA {i}: {message}")
        print('='*70)
        
        try:
            response = await agent.process_message(message, user_id="pablo_test")
            print(f"✅ Respuesta:")
            print(f"   {response}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-"*50)

if __name__ == "__main__":
    asyncio.run(test_real_order()) 