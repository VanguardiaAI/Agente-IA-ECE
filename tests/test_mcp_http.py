#!/usr/bin/env python3
"""
Test de conexión HTTP para el servidor MCP
Verifica que la configuración HTTP funcione correctamente
"""

import asyncio
import sys
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_mcp_http_connection():
    """Prueba la conexión HTTP al servidor MCP"""
    print("🧪 Probando conexión HTTP al servidor MCP...")
    print("=" * 50)
    
    try:
        # Configuración del cliente MCP
        mcp_config = {
            "woocommerce": {
                "url": "http://localhost:8000/mcp/",
                "transport": "streamable_http"
            }
        }
        
        print(f"🔗 Conectando a: {mcp_config['woocommerce']['url']}")
        
        # Crear cliente
        client = MultiServerMCPClient(mcp_config)
        
        # Obtener herramientas
        print("🛠️ Obteniendo herramientas disponibles...")
        tools = await client.get_tools()
        
        if tools:
            print(f"✅ Conexión exitosa! Herramientas encontradas: {len(tools)}")
            print("\n📋 Herramientas disponibles:")
            for i, tool in enumerate(tools, 1):
                print(f"   {i}. {tool.name} - {tool.description}")
                
            # Probar una herramienta simple
            print("\n🧪 Probando herramienta 'test_connection'...")
            try:
                result = await client.call_tool("test_connection", {})
                print(f"✅ Resultado: {result}")
            except Exception as e:
                print(f"⚠️ Error probando herramienta: {e}")
                
        else:
            print("⚠️ Conexión establecida pero no se encontraron herramientas")
            
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("\n💡 Posibles soluciones:")
        print("   1. Asegúrate de que el servidor MCP esté corriendo:")
        print("      python3 main.py")
        print("   2. Verifica que el puerto 8000 esté disponible")
        print("   3. Revisa la configuración en env.agent")
        return False

async def test_agent_integration():
    """Prueba la integración completa del agente"""
    print("\n🤖 Probando integración del agente...")
    print("=" * 50)
    
    try:
        # Crear agente
        agent = HybridCustomerAgent()
        
        # Inicializar cliente MCP
        await agent.initialize()
        
        print(f"✅ Agente inicializado correctamente")
        print(f"   Herramientas MCP disponibles: {len(agent.mcp_tools) if agent.mcp_tools else 0}")
        
        # Probar un mensaje simple
        test_message = "Hola, busco velas aromáticas"
        print(f"\n💬 Probando mensaje: '{test_message}'")
        
        response = await agent.process_message(test_message, user_id="test_integration")
        print(f"🤖 Respuesta: {response[:200]}...")
        
        return True
    except Exception as e:
        print(f"❌ Error en integración del agente: {e}")
        return False

async def main():
    """Función principal de pruebas"""
    print("🌟 Eva - Test de Configuración HTTP MCP")
    print("=" * 60)
    
    # Test 1: Conexión MCP
    mcp_ok = await test_mcp_http_connection()
    
    # Test 2: Integración del agente
    agent_ok = await test_agent_integration()
    
    # Resumen
    print("\n📊 Resumen de Pruebas")
    print("=" * 30)
    print(f"🔗 Conexión MCP HTTP: {'✅ OK' if mcp_ok else '❌ FALLO'}")
    print(f"🤖 Integración Agente: {'✅ OK' if agent_ok else '❌ FALLO'}")
    
    if mcp_ok and agent_ok:
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
        print("🚀 Puedes ejecutar: python3 start_services.py")
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisa la configuración.")
        
    return mcp_ok and agent_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 