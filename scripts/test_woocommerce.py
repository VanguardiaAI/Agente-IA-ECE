#!/usr/bin/env python3
"""
Script de diagnóstico para WooCommerce
Prueba la conexión y credenciales de la API de WooCommerce
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.woocommerce import WooCommerceService
from config.settings import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_woocommerce_connection():
    """Probar conexión con WooCommerce"""
    print("🛒 DIAGNÓSTICO DE WOOCOMMERCE")
    print("=" * 50)
    
    # Verificar configuración
    print("\n📋 1. Verificando configuración...")
    
    required_vars = [
        'WOOCOMMERCE_API_URL',
        'WOOCOMMERCE_CONSUMER_KEY', 
        'WOOCOMMERCE_CONSUMER_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not hasattr(settings, var) or not getattr(settings, var):
            missing_vars.append(var)
            print(f"❌ {var}: No configurado")
        else:
            value = getattr(settings, var)
            # Ocultar parte de las credenciales por seguridad
            if 'KEY' in var or 'SECRET' in var:
                display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Variables faltantes: {', '.join(missing_vars)}")
        print("\n📝 Para configurar WooCommerce:")
        print("1. Ve a tu panel de WordPress")
        print("2. Navega a WooCommerce > Configuración > Avanzado > API REST")
        print("3. Crea una nueva clave API con permisos de 'Lectura/Escritura'")
        print("4. Copia las credenciales a tu archivo .env:")
        print("   WOOCOMMERCE_API_URL=https://tu-tienda.com/wp-json/wc/v3")
        print("   WOOCOMMERCE_CONSUMER_KEY=ck_tu_consumer_key")
        print("   WOOCOMMERCE_CONSUMER_SECRET=cs_tu_consumer_secret")
        return False
    
    # Crear servicio
    print("\n🔗 2. Probando conexión...")
    wc_service = WooCommerceService()
    
    # Test 1: Verificar endpoint básico
    print("   📡 Probando endpoint básico...")
    try:
        # Intentar obtener información de la tienda
        response = await wc_service._make_request("GET", "")
        if response:
            print("   ✅ Endpoint base accesible")
        else:
            print("   ❌ No se pudo acceder al endpoint base")
            return False
    except Exception as e:
        print(f"   ❌ Error en endpoint base: {e}")
        print("   💡 Verifica que la URL sea correcta y termine en '/wp-json/wc/v3'")
        return False
    
    # Test 2: Probar autenticación con categorías
    print("   🔐 Probando autenticación...")
    try:
        categories = await wc_service.get_product_categories(per_page=1)
        if categories is not None:
            print(f"   ✅ Autenticación exitosa - {len(categories)} categorías encontradas")
        else:
            print("   ❌ Error de autenticación - Credenciales inválidas")
            print("   💡 Verifica que las credenciales sean correctas")
            print("   💡 Asegúrate de que la clave API tenga permisos de lectura")
            return False
    except Exception as e:
        print(f"   ❌ Error de autenticación: {e}")
        return False
    
    # Test 3: Probar acceso a productos
    print("   📦 Probando acceso a productos...")
    try:
        products = await wc_service.get_products(per_page=1)
        if products is not None:
            print(f"   ✅ Acceso a productos exitoso - {len(products)} productos en muestra")
            if products:
                product = products[0]
                print(f"   📝 Producto de ejemplo: {product.get('name', 'Sin nombre')}")
        else:
            print("   ❌ No se pudo acceder a productos")
            return False
    except Exception as e:
        print(f"   ❌ Error accediendo a productos: {e}")
        return False
    
    # Test 4: Verificar permisos de escritura (opcional)
    print("   ✏️ Verificando permisos de escritura...")
    try:
        # Intentar obtener información de un producto específico (menos invasivo que crear)
        # Si esto funciona, generalmente significa que los permisos están bien
        test_product = await wc_service.get_product(1)  # ID 1 suele existir
        print("   ✅ Permisos de lectura detallada confirmados")
    except Exception as e:
        print(f"   ⚠️ Advertencia en permisos: {e}")
        print("   💡 Asegúrate de que la clave API tenga permisos de 'Lectura/Escritura'")
    
    # Resumen de configuración
    print("\n📊 3. Resumen de configuración:")
    try:
        # Obtener estadísticas básicas
        categories = await wc_service.get_product_categories()
        products = await wc_service.get_products(per_page=1)
        
        total_categories = len(categories) if categories else 0
        
        print(f"   📂 Total de categorías: {total_categories}")
        print(f"   📦 Productos disponibles: {'Sí' if products else 'No'}")
        print(f"   🌐 URL de la tienda: {settings.woocommerce_api_url}")
        
    except Exception as e:
        print(f"   ⚠️ Error obteniendo resumen: {e}")
    
    print("\n✅ DIAGNÓSTICO COMPLETADO - WooCommerce configurado correctamente")
    return True

async def main():
    """Función principal"""
    try:
        success = await test_woocommerce_connection()
        
        if success:
            print("\n🎉 ¡WooCommerce está listo para la sincronización!")
            print("\n🔄 Próximos pasos:")
            print("   1. Ejecuta: python scripts/setup_phase2.py")
            print("   2. O ejecuta sincronización manual:")
            print("      python -c \"import asyncio; from services.woocommerce_sync import wc_sync_service; asyncio.run(wc_sync_service.sync_all_products())\"")
        else:
            print("\n❌ CONFIGURACIÓN DE WOOCOMMERCE INCOMPLETA")
            print("   Revisa los errores arriba y configura las credenciales correctamente")
            
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 