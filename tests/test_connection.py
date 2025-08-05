#!/usr/bin/env python3
"""
Script para probar las conexiones básicas del sistema
"""

import asyncio
import sys
from config.settings import settings
from services.woocommerce import WooCommerceService
from services.conversation_logger import conversation_logger

async def test_woocommerce_connection():
    """Probar conexión con WooCommerce"""
    print("🔍 Probando conexión con WooCommerce...")
    
    try:
        wc_service = WooCommerceService()
        
        # Probar obtener productos
        products = await wc_service.get_products(per_page=1)
        if products:
            print("✅ WooCommerce: Conexión exitosa")
            print(f"   📦 Productos disponibles: {len(products)}")
            if products:
                product = products[0]
                print(f"   🛍️ Producto de prueba: {product.get('name', 'Sin nombre')}")
            return True
        else:
            print("❌ WooCommerce: No se pudieron obtener productos")
            return False
            
    except Exception as e:
        print(f"❌ WooCommerce: Error de conexión - {str(e)}")
        return False

async def test_postgresql_connection():
    """Probar conexión con PostgreSQL"""
    print("\n🔍 Probando conexión con PostgreSQL...")
    
    if not settings.ENABLE_CONVERSATION_LOGGING:
        print("⚠️  PostgreSQL: Logging deshabilitado en configuración")
        return True
    
    if not settings.DATABASE_URL:
        print("⚠️  PostgreSQL: DATABASE_URL no configurada")
        return True
    
    try:
        await conversation_logger.initialize()
        
        if conversation_logger.enabled:
            print("✅ PostgreSQL: Conexión exitosa")
            
            # Probar insertar un log de prueba
            await conversation_logger.log_message(
                session_id="test_session",
                user_id="test_user",
                message_type="test",
                content="User: Test query\nAssistant: Test response",
                metadata={"test": True, "tool_used": "test_connection"},
                response_time_ms=100
            )
            print("   📝 Log de prueba insertado correctamente")
            
            # Probar obtener estadísticas
            stats = await conversation_logger.get_analytics(1)
            if stats:
                print(f"   📊 Estadísticas obtenidas: {stats.get('total_messages', 0)} mensajes")
            
            return True
        else:
            print("❌ PostgreSQL: No se pudo habilitar el logger")
            return False
            
    except Exception as e:
        print(f"❌ PostgreSQL: Error de conexión - {str(e)}")
        return False
    finally:
        await conversation_logger.close()

async def test_configuration():
    """Verificar configuración del sistema"""
    print("\n🔍 Verificando configuración...")
    
    config_ok = True
    
    # Verificar WooCommerce
    if not settings.WOOCOMMERCE_URL:
        print("❌ WOOCOMMERCE_URL no configurada")
        config_ok = False
    else:
        print(f"✅ WooCommerce URL: {settings.WOOCOMMERCE_URL}")
    
    if not settings.WOOCOMMERCE_CONSUMER_KEY:
        print("❌ WOOCOMMERCE_CONSUMER_KEY no configurada")
        config_ok = False
    else:
        print("✅ WooCommerce Consumer Key configurada")
    
    if not settings.WOOCOMMERCE_CONSUMER_SECRET:
        print("❌ WOOCOMMERCE_CONSUMER_SECRET no configurada")
        config_ok = False
    else:
        print("✅ WooCommerce Consumer Secret configurada")
    
    # Verificar PostgreSQL (opcional)
    if settings.ENABLE_CONVERSATION_LOGGING:
        if settings.DATABASE_URL:
            print("✅ PostgreSQL DATABASE_URL configurada")
        else:
            print("⚠️  PostgreSQL DATABASE_URL no configurada (logging deshabilitado)")
    else:
        print("ℹ️  PostgreSQL logging deshabilitado")
    
    print(f"ℹ️  Servidor MCP: {settings.MCP_SERVER_NAME}")
    print(f"ℹ️  Debug mode: {settings.DEBUG}")
    
    return config_ok

async def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del sistema Customer Service Assistant")
    print("=" * 60)
    
    # Verificar configuración
    config_ok = await test_configuration()
    
    if not config_ok:
        print("\n❌ Configuración incompleta. Revisa tu archivo .env")
        sys.exit(1)
    
    # Probar conexiones
    wc_ok = await test_woocommerce_connection()
    db_ok = await test_postgresql_connection()
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE PRUEBAS:")
    print(f"   🛍️  WooCommerce: {'✅ OK' if wc_ok else '❌ FALLO'}")
    print(f"   🗄️  PostgreSQL: {'✅ OK' if db_ok else '❌ FALLO'}")
    
    if wc_ok:
        print("\n🎉 ¡Sistema listo para usar!")
        print("   Puedes ejecutar: python main.py")
    else:
        print("\n⚠️  Revisa la configuración de WooCommerce antes de continuar")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 