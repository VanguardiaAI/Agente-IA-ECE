#!/usr/bin/env python3
"""
Script para verificar producto directamente en WooCommerce
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.woocommerce import WooCommerceService
from services.database import db_service

async def check_wc_product(wc_id: int):
    """Verificar producto en WooCommerce y comparar con DB"""
    try:
        # Inicializar servicios
        wc_service = WooCommerceService()
        await db_service.initialize()
        
        print(f"\n🔍 Consultando producto WC ID: {wc_id}")
        
        # Obtener de WooCommerce
        wc_product = await wc_service.get_product(wc_id)
        
        if wc_product:
            print(f"\n📦 Información de WooCommerce:")
            print(f"   Nombre: {wc_product.get('name', 'N/A')}")
            print(f"   SKU: {wc_product.get('sku', 'N/A')}")
            print(f"   💰 Precio: {wc_product.get('price', 'N/A')}€")
            print(f"   💰 Precio Regular: {wc_product.get('regular_price', 'N/A')}€")
            print(f"   💰 Precio Oferta: {wc_product.get('sale_price', 'N/A')}€")
            print(f"   Stock: {wc_product.get('stock_status', 'N/A')}")
            print(f"   Última modificación: {wc_product.get('date_modified', 'N/A')}")
            
            # Obtener de base de datos
            async with db_service.pool.acquire() as conn:
                db_result = await conn.fetchrow("""
                    SELECT 
                        title,
                        metadata,
                        updated_at,
                        content
                    FROM knowledge_base
                    WHERE external_id = $1
                """, f'product_{wc_id}')
                
                if db_result:
                    print(f"\n📊 Información en Base de Datos:")
                    print(f"   Título: {db_result['title']}")
                    print(f"   Última actualización: {db_result['updated_at']}")
                    
                    metadata = json.loads(db_result['metadata']) if isinstance(db_result['metadata'], str) else db_result['metadata']
                    print(f"   💰 Precio: {metadata.get('price', 'N/A')}€")
                    print(f"   💰 Precio Regular: {metadata.get('regular_price', 'N/A')}€")
                    print(f"   💰 Precio Oferta: {metadata.get('sale_price', 'N/A')}€")
                    
                    # Comparar
                    wc_price = float(wc_product.get('price', 0))
                    db_price = float(metadata.get('price', 0))
                    
                    print(f"\n📊 Comparación:")
                    if wc_price != db_price:
                        print(f"   ⚠️  DIFERENCIA DE PRECIOS:")
                        print(f"      WooCommerce: {wc_price}€")
                        print(f"      Base de datos: {db_price}€")
                        print(f"      Diferencia: {wc_price - db_price}€ ({((wc_price - db_price) / db_price * 100):.1f}%)")
                    else:
                        print(f"   ✅ Precios sincronizados: {wc_price}€")
                    
                    # Verificar fechas
                    print(f"\n📅 Análisis de fechas:")
                    wc_date = wc_product.get('date_modified', '')
                    print(f"   WC modificado: {wc_date}")
                    print(f"   DB actualizado: {db_result['updated_at']}")
                    
                    # Mostrar contenido para ver qué se guardó
                    print(f"\n📄 Contenido en DB (primeras líneas):")
                    content_lines = db_result['content'].split('\n')[:10]
                    for line in content_lines:
                        if line.strip():
                            print(f"   {line}")
                    
                else:
                    print(f"\n❌ Producto no encontrado en la base de datos")
        else:
            print(f"❌ No se pudo obtener el producto de WooCommerce")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    # Verificar el producto Gabarron v-25 dc
    asyncio.run(check_wc_product(25489))