#!/usr/bin/env python3
"""
Script de prueba para verificar que el agente use las herramientas MCP
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.hybrid_agent import HybridCustomerAgent
from dotenv import load_dotenv

async def test_agent_with_tools():
    """Probar el agente con consultas que requieren herramientas MCP"""
    print('🚀 Iniciando prueba del agente mejorado con herramientas MCP...')
    
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    print(f"✅ Agente inicializado")
    print(f"   Herramientas MCP: {len(agent.mcp_tools) if agent.mcp_tools else 0}")
    
    # Verificar que las herramientas estén disponibles
    if not agent.mcp_tools:
        print("❌ ERROR: No se detectaron herramientas MCP")
        return
    
    print(f"✅ Herramientas MCP detectadas: {len(agent.mcp_tools)}")
    for tool in agent.mcp_tools:
        print(f"   - {tool.name}")
    
    # Casos de prueba específicos
    test_cases = [
        "Hola, busco velas aromáticas de lavanda",
        "¿Cuál es el estado de mi pedido #1817?",
        "Quiero ver productos en oferta",
        "Mi email es test@ejemplo.com, busca mis pedidos recientes"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 PRUEBA {i}: {message}")
        print('='*60)
        
        try:
            response = await agent.process_message(message, user_id=f"test_user_{i}")
            print(f"✅ Respuesta exitosa:")
            print(f"   {response[:300]}...")
            
        except Exception as e:
            print(f"❌ Error en prueba {i}: {e}")

    # ... existing code ...

if __name__ == "__main__":
    asyncio.run(test_agent_with_tools()) 