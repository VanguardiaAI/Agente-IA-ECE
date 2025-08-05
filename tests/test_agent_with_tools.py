#!/usr/bin/env python3
"""
Script para probar el agente con mensajes que deberían activar herramientas
"""

import asyncio
import os
from dotenv import load_dotenv
from simple_agent import SimpleCustomerAgent

async def test_agent_with_tools():
    """Prueba el agente con mensajes específicos"""
    print("🧪 PRUEBA DEL AGENTE CON HERRAMIENTAS MCP")
    print("=" * 50)
    
    # Cargar configuración
    load_dotenv("env.agent")
    
    # Crear agente
    agent = SimpleCustomerAgent()
    
    # Conectar al MCP
    mcp_client = await agent.initialize_mcp_client()
    
    if not mcp_client or not agent.mcp_tools:
        print("❌ No se pudo conectar al MCP")
        return
    
    print(f"\n✅ Agente conectado con {len(agent.mcp_tools)} herramientas")
    
    # Mensajes específicos que deberían activar herramientas
    test_messages = [
        {
            "message": "Muéstrame los productos destacados de la tienda",
            "expected_tool": "get_featured_products"
        },
        {
            "message": "Busca productos de velas aromáticas",
            "expected_tool": "search_products"
        },
        {
            "message": "¿Qué categorías de productos tienen disponibles?",
            "expected_tool": "get_product_categories"
        },
        {
            "message": "Consulta el estado del pedido número 123",
            "expected_tool": "get_order_status"
        }
    ]
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"🧪 PRUEBA {i}: {test['expected_tool']}")
        print(f"{'='*60}")
        print(f"👤 Usuario: {test['message']}")
        
        try:
            response = await agent.process_message(test['message'])
            print(f"🤖 Agente: {response}")
            
            # Verificar si se usaron herramientas
            if "🔧 Ejecutando" in str(response) or "herramientas" in response.lower():
                print("✅ Herramientas ejecutadas correctamente")
            else:
                print("⚠️ No se detectó uso de herramientas")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_agent_with_tools()) 