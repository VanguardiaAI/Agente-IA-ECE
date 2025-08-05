#!/usr/bin/env python3
"""
Script para probar directamente las herramientas MCP
"""

import asyncio
import os
from dotenv import load_dotenv
from simple_agent import SimpleCustomerAgent

async def test_tools_directly():
    """Prueba las herramientas MCP directamente"""
    print("🔧 PRUEBA DIRECTA DE HERRAMIENTAS MCP")
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
    
    print(f"\n✅ Conectado con {len(agent.mcp_tools)} herramientas")
    
    # Probar herramientas específicas
    tests = [
        {
            "name": "Buscar productos",
            "tool": "search_products",
            "params": {"query": "vela", "limit": 3}
        },
        {
            "name": "Productos destacados",
            "tool": "get_featured_products", 
            "params": {"limit": 3}
        },
        {
            "name": "Categorías de productos",
            "tool": "get_product_categories",
            "params": {}
        },
        {
            "name": "Probar conexión",
            "tool": "test_connection",
            "params": {}
        }
    ]
    
    for test in tests:
        print(f"\n🧪 {test['name']}...")
        try:
            # Buscar la herramienta
            tool = None
            for t in agent.mcp_tools:
                if t.name == test['tool']:
                    tool = t
                    break
            
            if not tool:
                print(f"❌ Herramienta '{test['tool']}' no encontrada")
                continue
            
            print(f"✅ Herramienta encontrada: {tool.name}")
            print(f"📝 Descripción: {tool.description}")
            
            # Intentar ejecutar con LangChain
            from langchain_core.messages import HumanMessage
            llm_with_tool = agent.llm.bind_tools([tool])
            
            # Crear mensaje que debería activar la herramienta
            if test['tool'] == 'search_products':
                message = "Busca productos de velas"
            elif test['tool'] == 'get_featured_products':
                message = "Muéstrame los productos destacados"
            elif test['tool'] == 'get_product_categories':
                message = "¿Qué categorías de productos tienes?"
            else:
                message = "Prueba la conexión"
            
            response = await llm_with_tool.ainvoke([HumanMessage(content=message)])
            
            print(f"📄 Respuesta del LLM:")
            print(f"   Tipo: {type(response)}")
            print(f"   Contenido: {str(response.content)[:200]}...")
            
            # Verificar si hay tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🔧 Tool calls detectados: {len(response.tool_calls)}")
                for tool_call in response.tool_calls:
                    print(f"   - {tool_call}")
            else:
                print("⚠️ No se generaron tool calls")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_tools_directly()) 