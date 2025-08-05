#!/usr/bin/env python3
"""
Script con logging muy detallado para encontrar el error
"""

import asyncio
import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.woocommerce import WooCommerceService
from services.woocommerce_sync import WooCommerceSyncService

async def debug_detailed_error():
    """Debug con logging muy detallado"""
    print("🔍 DEBUG DETALLADO CON LOGGING")
    print("=" * 60)
    
    # 1. Obtener producto
    wc_service = WooCommerceService()
    products = await wc_service.get_products(per_page=1)
    
    if not products:
        print("❌ No se pudieron obtener productos")
        return
    
    product = products[0]
    print(f"📦 Producto: {product.get('id')} - {type(product)}")
    
    # 2. Crear servicio de sync y probar paso a paso
    sync_service = WooCommerceSyncService()
    
    print(f"\n🔧 Probando _process_single_product paso a paso...")
    
    try:
        # Validación inicial
        print(f"   1. Validando tipo de producto...")
        if not isinstance(product, dict):
            print(f"      ❌ Producto no es dict: {type(product)}")
            return
        print(f"      ✅ Producto es dict")
        
        # Obtener ID
        print(f"   2. Obteniendo ID...")
        product_id = product.get('id')
        print(f"      ✅ product_id: {product_id}")
        
        # External ID
        print(f"   3. Creando external_id...")
        external_id = f"product_{product_id}"
        print(f"      ✅ external_id: {external_id}")
        
        # Verificar existencia en BD
        print(f"   4. Verificando en base de datos...")
        from services.database import db_service
        existing = await db_service.get_knowledge_by_external_id(external_id)
        print(f"      ✅ existing: {type(existing)}")
        
        # Formatear producto
        print(f"   5. Formateando producto...")
        product_content = sync_service._format_product_for_knowledge(product)
        print(f"      ✅ product_content: {type(product_content)}")
        
        # Generar embedding
        print(f"   6. Generando embedding...")
        from services.embedding_service import embedding_service
        embedding = await embedding_service.generate_embedding(product_content["content"])
        print(f"      ✅ embedding: {type(embedding)} - length: {len(embedding) if embedding else 'None'}")
        
        # Insertar en BD
        print(f"   7. Insertando en base de datos...")
        await db_service.upsert_knowledge(
            content_type="product",
            title=product_content["title"],
            content=product_content["content"],
            embedding=embedding,
            external_id=external_id,
            metadata=product_content["metadata"]
        )
        print(f"      ✅ Insertado correctamente")
        
        print(f"   🎉 Proceso completado exitosamente")
        
    except Exception as e:
        print(f"   ❌ Error en paso: {e}")
        print(f"   📊 Traceback completo:")
        traceback.print_exc()
        
        # Vamos a probar cada método individualmente
        print(f"\n🔍 Probando métodos individuales...")
        
        try:
            print(f"   Probando _format_product_for_knowledge...")
            result = sync_service._format_product_for_knowledge(product)
            print(f"   ✅ _format_product_for_knowledge: OK")
        except Exception as e2:
            print(f"   ❌ Error en _format_product_for_knowledge: {e2}")
            traceback.print_exc()
        
        try:
            print(f"   Probando embedding_service.generate_embedding...")
            from services.embedding_service import embedding_service
            test_embedding = await embedding_service.generate_embedding("test content")
            print(f"   ✅ embedding_service: OK")
        except Exception as e3:
            print(f"   ❌ Error en embedding_service: {e3}")
            traceback.print_exc()

async def main():
    """Función principal"""
    await debug_detailed_error()

if __name__ == "__main__":
    asyncio.run(main()) 