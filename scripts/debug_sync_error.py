#!/usr/bin/env python3
"""
Script para debuggear el error específico de sincronización
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.woocommerce import WooCommerceService
from services.woocommerce_sync import WooCommerceSyncService

async def debug_sync_error():
    """Debug específico del error de sincronización"""
    print("🔍 DEBUG DEL ERROR DE SINCRONIZACIÓN")
    print("=" * 60)
    
    # 1. Obtener productos directamente de WooCommerce
    wc_service = WooCommerceService()
    print("\n📋 1. Obteniendo productos de WooCommerce...")
    
    products = await wc_service.get_products(per_page=5)
    print(f"   Tipo de respuesta: {type(products)}")
    
    if products:
        print(f"   Número de productos: {len(products)}")
        for i, product in enumerate(products):
            print(f"   Producto {i+1}:")
            print(f"     - Tipo: {type(product)}")
            if isinstance(product, dict):
                print(f"     - ID: {product.get('id', 'N/A')}")
                print(f"     - Nombre: {product.get('name', 'N/A')[:50]}...")
            else:
                print(f"     - Contenido: {str(product)[:100]}...")
    
    # 2. Probar el método _process_single_product directamente
    print(f"\n🔧 2. Probando procesamiento individual...")
    
    if products and len(products) > 0:
        first_product = products[0]
        print(f"   Procesando producto tipo: {type(first_product)}")
        
        if isinstance(first_product, dict):
            sync_service = WooCommerceSyncService()
            try:
                result = await sync_service._process_single_product(first_product)
                print(f"   ✅ Resultado: {result}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   ❌ Producto no es diccionario: {first_product}")
    
    # 3. Verificar el método get_products con paginación
    print(f"\n📄 3. Verificando paginación...")
    
    # Probar diferentes páginas para ver si hay inconsistencias
    for page in range(1, 4):
        print(f"   Página {page}:")
        page_products = await wc_service.get_products(per_page=3, page=page)
        
        if page_products:
            print(f"     - Tipo: {type(page_products)}")
            print(f"     - Elementos: {len(page_products)}")
            
            for i, product in enumerate(page_products):
                print(f"     - Elemento {i+1}: {type(product)}")
                if not isinstance(product, dict):
                    print(f"       ⚠️ NO ES DICCIONARIO: {product}")
        else:
            print(f"     - Sin productos en página {page}")
    
    # 4. Verificar el método _make_request directamente
    print(f"\n🌐 4. Verificando _make_request directamente...")
    
    raw_response = await wc_service._make_request("GET", "products", params={"per_page": 2})
    print(f"   Tipo de respuesta directa: {type(raw_response)}")
    
    if raw_response:
        print(f"   Es lista: {isinstance(raw_response, list)}")
        if isinstance(raw_response, list):
            print(f"   Elementos en lista: {len(raw_response)}")
            for i, item in enumerate(raw_response):
                print(f"     - Item {i+1}: {type(item)}")
        else:
            print(f"   Contenido: {str(raw_response)[:200]}...")

async def main():
    """Función principal"""
    await debug_sync_error()

if __name__ == "__main__":
    asyncio.run(main()) 