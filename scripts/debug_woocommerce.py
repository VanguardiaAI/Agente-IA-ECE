#!/usr/bin/env python3
"""
Script de debug detallado para WooCommerce
Identifica el problema exacto en las peticiones HTTP
"""

import asyncio
import sys
import os
import httpx

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.woocommerce import WooCommerceService
from config.settings import settings
import logging

# Configurar logging detallado
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_woocommerce():
    """Debug detallado de WooCommerce"""
    print("🔍 DEBUG DETALLADO DE WOOCOMMERCE")
    print("=" * 60)
    
    # 1. Verificar configuración
    print("\n📋 1. Configuración actual:")
    print(f"   URL: {settings.woocommerce_api_url}")
    print(f"   Consumer Key: {settings.WOOCOMMERCE_CONSUMER_KEY[:10]}...")
    print(f"   Consumer Secret: {settings.WOOCOMMERCE_CONSUMER_SECRET[:10]}...")
    
    # 2. Crear servicio
    wc_service = WooCommerceService()
    print(f"\n🔧 2. Servicio WooCommerce:")
    print(f"   Base URL: {wc_service.base_url}")
    print(f"   Auth: {wc_service.auth[0][:10]}... / {wc_service.auth[1][:10]}...")
    print(f"   Timeout: {wc_service.timeout}")
    
    # 3. Petición HTTP manual detallada
    print(f"\n🌐 3. Petición HTTP manual:")
    url = f"{wc_service.base_url}/products/categories"
    params = {"per_page": 1}
    
    print(f"   URL completa: {url}")
    print(f"   Parámetros: {params}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"   Realizando petición...")
            
            response = await client.get(
                url=url,
                params=params,
                auth=wc_service.auth
            )
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            print(f"   URL final: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Éxito: {len(data)} categorías obtenidas")
                if data:
                    print(f"   Primera categoría: {data[0].get('name', 'Sin nombre')}")
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Contenido: {response.text[:500]}")
                
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. Usar el método del servicio
    print(f"\n🛠️ 4. Usando método del servicio:")
    try:
        categories = await wc_service.get_product_categories(per_page=1)
        if categories:
            print(f"   ✅ Éxito: {len(categories)} categorías")
            print(f"   Primera categoría: {categories[0].get('name', 'Sin nombre')}")
        else:
            print(f"   ❌ Falló: categories = {categories}")
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Debug del método _make_request
    print(f"\n🔧 5. Debug del método _make_request:")
    try:
        result = await wc_service._make_request("GET", "products/categories", params={"per_page": 1})
        print(f"   Resultado: {type(result)}")
        if result:
            print(f"   ✅ Éxito: {len(result)} elementos")
        else:
            print(f"   ❌ Falló: result = {result}")
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Probar endpoint de productos
    print(f"\n📦 6. Probando endpoint de productos:")
    try:
        products = await wc_service.get_products(per_page=1)
        if products:
            print(f"   ✅ Éxito: {len(products)} productos")
            if products:
                print(f"   Primer producto: {products[0].get('name', 'Sin nombre')}")
        else:
            print(f"   ❌ Falló: products = {products}")
    except Exception as e:
        print(f"   ❌ Excepción: {e}")

async def main():
    """Función principal"""
    await debug_woocommerce()

if __name__ == "__main__":
    asyncio.run(main()) 