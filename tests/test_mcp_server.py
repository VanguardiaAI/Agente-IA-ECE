#!/usr/bin/env python3
"""
Script para probar el servidor MCP completo simulando interacciones reales
"""

import asyncio
import json
import time
from typing import Dict, Any
from main import mcp
from services.conversation_logger import conversation_logger

class MCPTester:
    """Clase para probar el servidor MCP"""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
    
    async def run_tool_test(self, tool_name: str, args: Dict[str, Any], description: str):
        """Ejecutar una prueba de herramienta MCP"""
        self.total_tests += 1
        print(f"🔧 Probando: {description}")
        
        start_time = time.time()
        try:
            # Buscar la herramienta en el servidor MCP
            tool_func = None
            for tool in mcp._tools.values():
                if tool.name == tool_name:
                    tool_func = tool.func
                    break
            
            if not tool_func:
                raise Exception(f"Herramienta '{tool_name}' no encontrada")
            
            # Ejecutar la herramienta
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**args)
            else:
                result = tool_func(**args)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verificar que el resultado no sea un error
            if isinstance(result, str) and "❌" in result:
                print(f"   ⚠️  Resultado con warning: {result[:100]}...")
                status = "WARNING"
            else:
                print(f"   ✅ Éxito en {duration:.2f}s")
                status = "PASS"
                self.passed_tests += 1
            
            self.test_results.append({
                "tool": tool_name,
                "description": description,
                "status": status,
                "duration": duration,
                "result_length": len(str(result))
            })
            
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"   ❌ Error: {str(e)}")
            
            self.test_results.append({
                "tool": tool_name,
                "description": description,
                "status": "FAIL",
                "duration": duration,
                "error": str(e)
            })
            
            return None

async def test_basic_tools(tester: MCPTester):
    """Probar herramientas básicas"""
    print("🔧 PROBANDO HERRAMIENTAS BÁSICAS")
    print("-" * 50)
    
    # Test help
    await tester.run_tool_test(
        "get_help", 
        {}, 
        "Obtener ayuda del sistema"
    )
    
    # Test connection
    await tester.run_tool_test(
        "test_connection", 
        {}, 
        "Probar conexión con WooCommerce"
    )

async def test_product_tools(tester: MCPTester):
    """Probar herramientas de productos"""
    print("\n🛍️ PROBANDO HERRAMIENTAS DE PRODUCTOS")
    print("-" * 50)
    
    # Buscar productos
    await tester.run_tool_test(
        "search_products",
        {"query": "test", "limit": 5},
        "Buscar productos con término 'test'"
    )
    
    # Obtener categorías
    await tester.run_tool_test(
        "get_product_categories",
        {},
        "Obtener categorías de productos"
    )
    
    # Productos destacados
    await tester.run_tool_test(
        "get_featured_products",
        {"limit": 3},
        "Obtener productos destacados"
    )
    
    # Productos en oferta
    await tester.run_tool_test(
        "get_products_on_sale",
        {"limit": 3},
        "Obtener productos en oferta"
    )
    
    # Intentar obtener detalles de un producto (si existe)
    # Primero buscar un producto para obtener un ID válido
    search_result = await tester.run_tool_test(
        "search_products",
        {"query": "", "limit": 1},
        "Buscar cualquier producto para obtener ID"
    )
    
    # Si encontramos productos, probar detalles y stock
    if search_result and "ID" in str(search_result):
        # Intentar extraer un ID del resultado (esto es aproximado)
        try:
            # Buscar un número que podría ser un ID de producto
            import re
            ids = re.findall(r'ID[:\s]*(\d+)', str(search_result))
            if ids:
                product_id = int(ids[0])
                
                await tester.run_tool_test(
                    "get_product_details",
                    {"product_id": product_id},
                    f"Obtener detalles del producto ID {product_id}"
                )
                
                await tester.run_tool_test(
                    "check_product_stock",
                    {"product_id": product_id},
                    f"Verificar stock del producto ID {product_id}"
                )
        except:
            print("   ⚠️  No se pudo extraer ID de producto para pruebas detalladas")

async def test_order_tools(tester: MCPTester):
    """Probar herramientas de pedidos"""
    print("\n📦 PROBANDO HERRAMIENTAS DE PEDIDOS")
    print("-" * 50)
    
    # Pedidos recientes
    await tester.run_tool_test(
        "get_recent_orders",
        {"limit": 5},
        "Obtener pedidos recientes"
    )
    
    # Pedidos por estado
    statuses = ["pending", "processing", "completed"]
    for status in statuses:
        await tester.run_tool_test(
            "get_orders_by_status",
            {"status": status, "limit": 3},
            f"Obtener pedidos con estado '{status}'"
        )
    
    # Intentar obtener detalles de un pedido (si existe)
    recent_orders = await tester.run_tool_test(
        "get_recent_orders",
        {"limit": 1},
        "Buscar un pedido para obtener ID"
    )
    
    if recent_orders and "#" in str(recent_orders):
        try:
            # Intentar extraer un ID de pedido
            import re
            ids = re.findall(r'#(\d+)', str(recent_orders))
            if ids:
                order_id = int(ids[0])
                
                await tester.run_tool_test(
                    "get_order_status",
                    {"order_id": order_id},
                    f"Obtener estado del pedido #{order_id}"
                )
                
                await tester.run_tool_test(
                    "track_order",
                    {"order_id": order_id},
                    f"Rastrear pedido #{order_id}"
                )
                
                await tester.run_tool_test(
                    "create_order_summary",
                    {"order_id": order_id},
                    f"Crear resumen del pedido #{order_id}"
                )
        except:
            print("   ⚠️  No se pudo extraer ID de pedido para pruebas detalladas")

async def test_conversation_logging(tester: MCPTester):
    """Probar logging de conversaciones"""
    print("\n📊 PROBANDO LOGGING DE CONVERSACIONES")
    print("-" * 50)
    
    # Probar estadísticas
    await tester.run_tool_test(
        "get_conversation_stats",
        {"days": 7},
        "Obtener estadísticas de conversaciones (7 días)"
    )
    
    await tester.run_tool_test(
        "get_conversation_stats",
        {"days": 1},
        "Obtener estadísticas de conversaciones (1 día)"
    )

async def test_error_handling(tester: MCPTester):
    """Probar manejo de errores"""
    print("\n⚠️ PROBANDO MANEJO DE ERRORES")
    print("-" * 50)
    
    # ID de producto inexistente
    await tester.run_tool_test(
        "get_product_details",
        {"product_id": 999999},
        "Producto con ID inexistente (999999)"
    )
    
    # ID de pedido inexistente
    await tester.run_tool_test(
        "get_order_status",
        {"order_id": 999999},
        "Pedido con ID inexistente (999999)"
    )
    
    # Estado de pedido inválido
    await tester.run_tool_test(
        "get_orders_by_status",
        {"status": "invalid_status", "limit": 5},
        "Estado de pedido inválido"
    )
    
    # Email de cliente inexistente
    await tester.run_tool_test(
        "search_orders_by_customer",
        {"customer_email": "inexistente@test.com"},
        "Buscar pedidos de cliente inexistente"
    )

async def simulate_real_conversations(tester: MCPTester):
    """Simular conversaciones reales de atención al cliente"""
    print("\n💬 SIMULANDO CONVERSACIONES REALES")
    print("-" * 50)
    
    conversations = [
        {
            "scenario": "Cliente busca productos",
            "tools": [
                ("search_products", {"query": "velas", "limit": 5}),
                ("get_product_categories", {})
            ]
        },
        {
            "scenario": "Cliente consulta pedido",
            "tools": [
                ("get_recent_orders", {"limit": 3}),
                ("get_orders_by_status", {"status": "processing", "limit": 5})
            ]
        },
        {
            "scenario": "Cliente busca ofertas",
            "tools": [
                ("get_products_on_sale", {"limit": 5}),
                ("get_featured_products", {"limit": 5})
            ]
        }
    ]
    
    for conv in conversations:
        print(f"\n🎭 Escenario: {conv['scenario']}")
        for tool_name, args in conv['tools']:
            description = f"Ejecutar {tool_name} en escenario '{conv['scenario']}'"
            await tester.run_tool_test(tool_name, args, description)

def print_test_summary(tester: MCPTester):
    """Imprimir resumen de pruebas"""
    print("\n" + "=" * 60)
    print("📋 RESUMEN COMPLETO DE PRUEBAS")
    print("=" * 60)
    
    print(f"📊 Total de pruebas: {tester.total_tests}")
    print(f"✅ Pruebas exitosas: {tester.passed_tests}")
    print(f"⚠️  Pruebas con warnings: {len([r for r in tester.test_results if r.get('status') == 'WARNING'])}")
    print(f"❌ Pruebas fallidas: {len([r for r in tester.test_results if r.get('status') == 'FAIL'])}")
    
    success_rate = (tester.passed_tests / tester.total_tests) * 100 if tester.total_tests > 0 else 0
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")
    
    # Estadísticas de rendimiento
    durations = [r['duration'] for r in tester.test_results if 'duration' in r]
    if durations:
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        print(f"⏱️  Tiempo promedio: {avg_duration:.2f}s")
        print(f"⏱️  Tiempo máximo: {max_duration:.2f}s")
    
    # Herramientas más lentas
    slow_tests = [r for r in tester.test_results if r.get('duration', 0) > 2.0]
    if slow_tests:
        print(f"\n🐌 Herramientas lentas (>2s):")
        for test in slow_tests:
            print(f"   • {test['tool']}: {test['duration']:.2f}s")
    
    # Errores encontrados
    failed_tests = [r for r in tester.test_results if r.get('status') == 'FAIL']
    if failed_tests:
        print(f"\n❌ Errores encontrados:")
        for test in failed_tests:
            print(f"   • {test['tool']}: {test.get('error', 'Error desconocido')}")
    
    print("\n💡 Recomendaciones:")
    if success_rate >= 80:
        print("   🎉 ¡Excelente! El sistema está funcionando correctamente")
    elif success_rate >= 60:
        print("   ⚠️  Sistema funcional pero con algunos problemas menores")
    else:
        print("   🚨 Sistema requiere atención - múltiples errores detectados")
    
    if avg_duration > 3.0:
        print("   ⚡ Considera optimizar el rendimiento - respuestas lentas")
    
    print("   📚 Revisa los logs para más detalles sobre warnings y errores")

async def main():
    """Función principal de pruebas del servidor MCP"""
    print("🚀 INICIANDO PRUEBAS COMPLETAS DEL SERVIDOR MCP")
    print("=" * 60)
    
    tester = MCPTester()
    start_time = time.time()
    
    try:
        # Inicializar logging si está habilitado
        if conversation_logger.enabled:
            await conversation_logger.connect()
        
        # Ejecutar todas las pruebas
        await test_basic_tools(tester)
        await test_product_tools(tester)
        await test_order_tools(tester)
        await test_conversation_logging(tester)
        await test_error_handling(tester)
        await simulate_real_conversations(tester)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print(f"\n⏱️  Tiempo total de pruebas: {total_duration:.2f} segundos")
        
        # Mostrar resumen
        print_test_summary(tester)
        
        return tester.passed_tests >= (tester.total_tests * 0.6)  # 60% de éxito mínimo
        
    except Exception as e:
        print(f"\n❌ Error crítico en las pruebas: {e}")
        return False
    finally:
        # Limpiar recursos
        if conversation_logger.enabled:
            await conversation_logger.disconnect()

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 ¡Servidor MCP funcionando correctamente!")
        print("   Puedes ejecutar: python main.py")
    else:
        print("\n⚠️  El servidor MCP tiene problemas significativos.")
        print("   Revisa la configuración y los errores reportados.") 