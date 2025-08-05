#!/usr/bin/env python3
"""
Script para verificar qué datos reales tenemos en WooCommerce
"""

import asyncio
import os
from dotenv import load_dotenv
from simple_agent import SimpleCustomerAgent

async def test_woocommerce_data():
    """Verifica qué datos reales tenemos en WooCommerce"""
    print("📊 VERIFICANDO DATOS DE WOOCOMMERCE")
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
    
    # Probar diferentes herramientas para ver qué datos tenemos
    tests = [
        ("test_connection", {}),
        ("get_product_categories", {}),
        ("search_products", {"query": "producto", "limit": 5}),
        ("search_products", {"query": "vela", "limit": 5}),
        ("search_products", {"query": "", "limit": 10}),  # Buscar todos
        ("get_featured_products", {"limit": 5}),
        ("get_products_on_sale", {"limit": 5}),
        ("get_recent_orders", {"limit": 3}),
    ]
    
    for tool_name, args in tests:
        print(f"\n🔧 Probando {tool_name} con {args}...")
        try:
            result = await agent._call_mcp_tool(tool_name, args)
            print(f"📄 Resultado:")
            print(f"   {str(result)[:300]}...")
            if len(str(result)) > 300:
                print(f"   ... (truncado, total: {len(str(result))} caracteres)")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_woocommerce_data()) 