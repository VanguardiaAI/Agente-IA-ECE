#!/usr/bin/env python3
"""
Script de prueba para la integración MCP HTTP
"""

import asyncio
import os
from dotenv import load_dotenv
from simple_agent import SimpleCustomerAgent

async def test_mcp_integration():
    """Prueba la integración completa con MCP"""
    print("🔗 PRUEBA DE INTEGRACIÓN MCP HTTP")
    print("=" * 50)
    
    # Cargar configuración
    load_dotenv("env.agent")
    
    # Crear agente
    agent = SimpleCustomerAgent()
    
    # Intentar conectar al MCP
    print("🔌 Intentando conectar al servidor MCP...")
    mcp_client = await agent.initialize_mcp_client()
    
    if mcp_client:
        print("✅ ¡CONEXIÓN MCP EXITOSA!")
        print(f"   Herramientas disponibles: {len(agent.mcp_tools)}")
        
        # Listar herramientas disponibles
        if agent.mcp_tools:
            print("\n🛠️ Herramientas MCP disponibles:")
            for tool in agent.mcp_tools:
                print(f"   • {tool.name}: {tool.description}")
        
        # Probar una consulta real
        print("\n🧪 Probando consulta con datos reales...")
        response = await agent.process_message("Busco velas aromáticas de lavanda")
        print(f"🤖 Respuesta: {response[:200]}...")
        
    else:
        print("❌ No se pudo conectar al MCP")
        print("   Verificando servidor...")
        
        # Verificar si el servidor está corriendo
        import subprocess
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000/mcp/"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("   ✅ Servidor MCP responde")
                print(f"   📄 Respuesta: {result.stdout[:100]}...")
            else:
                print("   ❌ Servidor MCP no responde")
        except Exception as e:
            print(f"   ❌ Error verificando servidor: {e}")
    
    print("\n" + "=" * 50)
    return mcp_client is not None

if __name__ == "__main__":
    asyncio.run(test_mcp_integration()) 