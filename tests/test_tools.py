#!/usr/bin/env python3
"""
Script para probar todas las herramientas MCP del agente
"""

import asyncio
import time
from services.woocommerce import WooCommerceService
from services.conversation_logger import conversation_logger

async def test_product_tools():
    """Probar herramientas de productos"""
    print("🛍️ PROBANDO HERRAMIENTAS DE PRODUCTOS")
    print("-" * 50)
    
    wc_service = WooCommerceService()
    
    # Test 1: Buscar productos
    print("1️⃣ Probando búsqueda de productos...")
    try:
        products = await wc_service.search_products("test", per_page=3)
        if products:
            print(f"   ✅ Encontrados {len(products)} productos")
            formatted = wc_service.format_product_list(products, "Resultados de prueba")
            print(f"   📝 Formato: {len(formatted)} caracteres")
        else:
            print("   ⚠️  No se encontraron productos (normal si la tienda está vacía)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Obtener categorías
    print("\n2️⃣ Probando obtención de categorías...")
    try:
        categories = await wc_service.get_product_categories()
        if categories:
            print(f"   ✅ Encontradas {len(categories)} categorías")
            for cat in categories[:3]:
                print(f"   📂 {cat.get('name', 'Sin nombre')} ({cat.get('count', 0)} productos)")
        else:
            print("   ⚠️  No se encontraron categorías")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Productos destacados
    print("\n3️⃣ Probando productos destacados...")
    try:
        featured = await wc_service.get_products(featured=True, per_page=3)
        if featured:
            print(f"   ✅ Encontrados {len(featured)} productos destacados")
        else:
            print("   ⚠️  No hay productos destacados configurados")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Productos en oferta
    print("\n4️⃣ Probando productos en oferta...")
    try:
        on_sale = await wc_service.get_products(on_sale=True, per_page=3)
        if on_sale:
            print(f"   ✅ Encontrados {len(on_sale)} productos en oferta")
        else:
            print("   ⚠️  No hay productos en oferta")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Detalles de producto (si existe alguno)
    print("\n5️⃣ Probando detalles de producto...")
    try:
        all_products = await wc_service.get_products(per_page=1)
        if all_products:
            product_id = all_products[0]['id']
            product = await wc_service.get_product(product_id)
            if product:
                print(f"   ✅ Detalles obtenidos para producto ID {product_id}")
                formatted = wc_service.format_product(product)
                print(f"   📝 Formato: {len(formatted)} caracteres")
            else:
                print(f"   ❌ No se pudo obtener producto ID {product_id}")
        else:
            print("   ⚠️  No hay productos para probar detalles")
    except Exception as e:
        print(f"   ❌ Error: {e}")

async def test_order_tools():
    """Probar herramientas de pedidos"""
    print("\n\n📦 PROBANDO HERRAMIENTAS DE PEDIDOS")
    print("-" * 50)
    
    wc_service = WooCommerceService()
    
    # Test 1: Obtener pedidos recientes
    print("1️⃣ Probando pedidos recientes...")
    try:
        orders = await wc_service.get_orders(per_page=3)
        if orders:
            print(f"   ✅ Encontrados {len(orders)} pedidos")
            formatted = wc_service.format_order_list(orders, "Pedidos de prueba")
            print(f"   📝 Formato: {len(formatted)} caracteres")
            
            # Probar detalles del primer pedido
            if orders:
                order_id = orders[0]['id']
                print(f"\n   🔍 Probando detalles del pedido #{order_id}...")
                order_details = await wc_service.get_order(order_id)
                if order_details:
                    formatted_order = wc_service.format_order(order_details)
                    print(f"   ✅ Detalles obtenidos: {len(formatted_order)} caracteres")
                else:
                    print(f"   ❌ No se pudieron obtener detalles del pedido #{order_id}")
        else:
            print("   ⚠️  No se encontraron pedidos")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Pedidos por estado
    print("\n2️⃣ Probando pedidos por estado...")
    statuses = ['pending', 'processing', 'completed']
    for status in statuses:
        try:
            status_orders = await wc_service.get_orders_by_status(status, per_page=2)
            if status_orders:
                print(f"   ✅ Estado '{status}': {len(status_orders)} pedidos")
            else:
                print(f"   ⚠️  Estado '{status}': Sin pedidos")
        except Exception as e:
            print(f"   ❌ Error con estado '{status}': {e}")

async def test_utility_tools():
    """Probar herramientas de utilidad"""
    print("\n\n🔧 PROBANDO HERRAMIENTAS DE UTILIDAD")
    print("-" * 50)
    
    # Test 1: Conexión WooCommerce
    print("1️⃣ Probando test_connection...")
    try:
        wc_service = WooCommerceService()
        products = await wc_service.get_products(per_page=1)
        if products:
            print("   ✅ Conexión WooCommerce exitosa")
        else:
            print("   ❌ Conexión WooCommerce fallida")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    # Test 2: Logging de conversaciones (si está habilitado)
    print("\n2️⃣ Probando conversation logging...")
    try:
        await conversation_logger.initialize()
        if conversation_logger.enabled:
            # Log de prueba
            await conversation_logger.log_message(
                session_id="test_session",
                user_id="test_user",
                message_type="test",
                content="User: ¿Cuáles son los productos disponibles?\nAssistant: Aquí tienes los productos disponibles...",
                metadata={"test_run": True, "tool_used": "search_products"},
                response_time_ms=1500
            )
            print("   ✅ Log de conversación guardado")
            
            # Obtener estadísticas
            stats = await conversation_logger.get_analytics(1)
            if stats:
                print(f"   📊 Estadísticas: {stats.get('total_messages', 0)} mensajes")
            else:
                print(f"   ⚠️  No se pudieron obtener estadísticas")
        else:
            print("   ⚠️  Logging de conversaciones deshabilitado")
    except Exception as e:
        print(f"   ❌ Error en logging: {e}")
    finally:
        await conversation_logger.close()

async def performance_test():
    """Probar rendimiento básico"""
    print("\n\n⚡ PRUEBA DE RENDIMIENTO")
    print("-" * 50)
    
    wc_service = WooCommerceService()
    
    # Test de velocidad de búsqueda
    print("🏃‍♂️ Probando velocidad de búsqueda...")
    start_time = time.time()
    try:
        products = await wc_service.search_products("test", per_page=5)
        end_time = time.time()
        duration = end_time - start_time
        print(f"   ⏱️  Búsqueda completada en {duration:.2f} segundos")
        if duration < 2.0:
            print("   ✅ Rendimiento bueno (< 2s)")
        elif duration < 5.0:
            print("   ⚠️  Rendimiento aceptable (2-5s)")
        else:
            print("   ❌ Rendimiento lento (> 5s)")
    except Exception as e:
        print(f"   ❌ Error en prueba de rendimiento: {e}")
    
    # Test de múltiples peticiones
    print("\n🔄 Probando múltiples peticiones...")
    start_time = time.time()
    try:
        tasks = [
            wc_service.get_products(per_page=2),
            wc_service.get_product_categories(),
            wc_service.get_orders(per_page=2)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        duration = end_time - start_time
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"   ⏱️  {success_count}/3 peticiones exitosas en {duration:.2f} segundos")
        
        if success_count == 3 and duration < 3.0:
            print("   ✅ Rendimiento concurrente excelente")
        elif success_count >= 2:
            print("   ⚠️  Rendimiento concurrente aceptable")
        else:
            print("   ❌ Problemas de rendimiento concurrente")
            
    except Exception as e:
        print(f"   ❌ Error en prueba concurrente: {e}")

async def main():
    """Función principal de pruebas"""
    print("🧪 INICIANDO PRUEBAS COMPLETAS DE HERRAMIENTAS MCP")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Ejecutar todas las pruebas
        await test_product_tools()
        await test_order_tools()
        await test_utility_tools()
        await performance_test()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("📋 RESUMEN DE PRUEBAS COMPLETADAS")
        print(f"⏱️  Tiempo total: {total_duration:.2f} segundos")
        print("✅ Todas las pruebas ejecutadas")
        print("\n💡 Notas:")
        print("   • Algunos warnings son normales si la tienda está vacía")
        print("   • El logging requiere configuración de MongoDB Atlas")
        print("   • El rendimiento depende de la conexión a internet")
        
    except Exception as e:
        print(f"\n❌ Error general en las pruebas: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 ¡Pruebas completadas exitosamente!")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa la configuración.") 