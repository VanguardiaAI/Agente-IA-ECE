#!/usr/bin/env python3
"""
Script para debuggear la línea específica del error
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.woocommerce import WooCommerceService
from services.database import db_service

async def debug_specific_error():
    """Debug específico de la línea que causa el error"""
    print("🔍 DEBUG ESPECÍFICO DEL ERROR")
    print("=" * 60)
    
    # 1. Obtener un producto de WooCommerce
    wc_service = WooCommerceService()
    products = await wc_service.get_products(per_page=1)
    
    if not products:
        print("❌ No se pudieron obtener productos")
        return
    
    product = products[0]
    print(f"📦 Producto obtenido: {product.get('id')} - {product.get('name', 'Sin nombre')[:50]}...")
    
    # 2. Simular el código que falla línea por línea
    print(f"\n🔧 Simulando código que falla...")
    
    try:
        # Línea que funciona
        product_id = product.get('id')
        print(f"   ✅ product_id: {product_id} (tipo: {type(product_id)})")
        
        # Línea que funciona
        external_id = f"product_{product_id}"
        print(f"   ✅ external_id: {external_id} (tipo: {type(external_id)})")
        
        # Línea que puede fallar - verificar si ya existe
        print(f"   🔍 Verificando si existe en base de datos...")
        existing = await db_service.get_knowledge_by_external_id(external_id)
        print(f"   📊 existing: {type(existing)}")
        
        if existing:
            print(f"   📊 Contenido de existing: {existing}")
            print(f"   🔍 Intentando existing.get('updated_at')...")
            
            # Esta es la línea que puede estar fallando
            db_modified = existing.get('updated_at')
            print(f"   ✅ db_modified: {db_modified} (tipo: {type(db_modified)})")
        else:
            print(f"   ℹ️ No existe en base de datos")
        
        # Línea que puede fallar - fecha de modificación
        print(f"   🔍 Procesando fecha de modificación...")
        date_modified_raw = product.get('date_modified', '')
        print(f"   📊 date_modified_raw: '{date_modified_raw}' (tipo: {type(date_modified_raw)})")
        
        if date_modified_raw:
            # Esta línea puede estar fallando
            date_modified_processed = date_modified_raw.replace('Z', '+00:00')
            print(f"   ✅ date_modified_processed: '{date_modified_processed}' (tipo: {type(date_modified_processed)})")
            
            # Esta línea también puede fallar
            wc_modified = datetime.fromisoformat(date_modified_processed)
            print(f"   ✅ wc_modified: {wc_modified} (tipo: {type(wc_modified)})")
        else:
            print(f"   ⚠️ date_modified está vacío")
        
    except Exception as e:
        print(f"   ❌ Error en línea específica: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Probar el método _format_product_for_knowledge directamente
    print(f"\n🎨 Probando _format_product_for_knowledge...")
    
    try:
        from services.woocommerce_sync import WooCommerceSyncService
        sync_service = WooCommerceSyncService()
        
        product_content = sync_service._format_product_for_knowledge(product)
        print(f"   ✅ product_content generado correctamente")
        print(f"   📊 Tipo: {type(product_content)}")
        print(f"   📊 Keys: {list(product_content.keys())}")
        
    except Exception as e:
        print(f"   ❌ Error en _format_product_for_knowledge: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Función principal"""
    await debug_specific_error()

if __name__ == "__main__":
    asyncio.run(main()) 