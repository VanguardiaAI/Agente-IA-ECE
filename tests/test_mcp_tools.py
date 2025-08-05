#!/usr/bin/env python3
"""
Script para verificar los nombres exactos de las herramientas MCP
"""

import asyncio
import os
from dotenv import load_dotenv
from simple_agent import SimpleCustomerAgent

async def test_mcp_tools():
    """Verifica los nombres exactos de las herramientas MCP"""
    print("🔍 VERIFICANDO HERRAMIENTAS MCP")
    print("=" * 50)
    
    # Cargar configuración
    load_dotenv("env.agent")
    
    # Crear agente
    agent = SimpleCustomerAgent()
    
    # Conectar al MCP
    mcp_client = await agent.initialize_mcp_client()
    
    if mcp_client and agent.mcp_tools:
        print(f"\n📋 HERRAMIENTAS DISPONIBLES ({len(agent.mcp_tools)}):")
        print("-" * 50)
        
        for i, tool in enumerate(agent.mcp_tools, 1):
            print(f"{i:2d}. Nombre: '{tool.name}'")
            print(f"    Descripción: {tool.description}")
            print(f"    Parámetros: {list(tool.inputSchema.get('properties', {}).keys()) if hasattr(tool, 'inputSchema') else 'N/A'}")
            print()
        
        # Probar una herramienta específica
        print("🧪 PROBANDO HERRAMIENTA DE BÚSQUEDA...")
        try:
            # Buscar herramienta de productos
            search_tool = None
            for tool in agent.mcp_tools:
                if "search" in tool.name.lower() and "product" in tool.name.lower():
                    search_tool = tool
                    break
            
            if search_tool:
                print(f"✅ Encontrada herramienta: '{search_tool.name}'")
                
                # Intentar llamarla
                result = await mcp_client.call_tool(search_tool.name, {
                    "query": "vela",
                    "limit": 3
                })
                print(f"📄 Resultado: {str(result)[:200]}...")
            else:
                print("❌ No se encontró herramienta de búsqueda de productos")
                
        except Exception as e:
            print(f"❌ Error probando herramienta: {e}")
    
    else:
        print("❌ No se pudo conectar al MCP o no hay herramientas disponibles")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools()) 