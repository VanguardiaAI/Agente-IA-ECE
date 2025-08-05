#!/usr/bin/env python3
"""
Script para debuggear problemas de sincronización de productos
"""

import asyncio
import sys
from pathlib import Path
import json

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.woocommerce import WooCommerceService
from services.woocommerce_sync import wc_sync_service

async def check_product_by_name(product_name: str):
    """Verificar un producto por nombre"""
    try:
        # Inicializar base de datos
        await db_service.initialize()
        
        print(f"\n🔍 Buscando producto: {product_name}")
        
        # Buscar en base de datos
        async with db_service.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    external_id,
                    title,
                    content,
                    metadata,
                    updated_at,
                    is_active
                FROM knowledge_base
                WHERE content_type = 'product'
                AND (title ILIKE $1 OR content ILIKE $1)
                LIMIT 1
            """, f'%{product_name}%')
            
            if result:
                print("\n📦 Producto en Base de Datos:")
                print(f"   ID Externo: {result['external_id']}")
                print(f"   Título: {result['title']}")
                print(f"   Activo: {result['is_active']}")
                print(f"   Última actualización: {result['updated_at']}")
                
                # Parsear metadata
                metadata = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                print(f"\n💰 Información de Precios (DB):")
                print(f"   Precio: {metadata.get('price', 'N/A')}€")
                print(f"   Precio Regular: {metadata.get('regular_price', 'N/A')}€")
                print(f"   Precio Oferta: {metadata.get('sale_price', 'N/A')}€")
                
                # Obtener ID de WooCommerce
                wc_id = metadata.get('wc_id')
                if wc_id:
                    print(f"\n🔄 Consultando WooCommerce (ID: {wc_id})...")
                    
                    # Obtener de WooCommerce
                    wc_service = WooCommerceService()
                    wc_product = await wc_service.get_product(wc_id)
                    
                    if wc_product:
                        print(f"\n💰 Información de Precios (WooCommerce):")
                        print(f"   Precio: {wc_product.get('price', 'N/A')}€")
                        print(f"   Precio Regular: {wc_product.get('regular_price', 'N/A')}€")
                        print(f"   Precio Oferta: {wc_product.get('sale_price', 'N/A')}€")
                        print(f"   Última modificación: {wc_product.get('date_modified', 'N/A')}")
                        
                        # Comparar precios
                        db_price = float(metadata.get('price', 0))
                        wc_price = float(wc_product.get('price', 0))
                        
                        if db_price != wc_price:
                            print(f"\n⚠️  DIFERENCIA DE PRECIOS DETECTADA:")
                            print(f"   Base de datos: {db_price}€")
                            print(f"   WooCommerce: {wc_price}€")
                            print(f"   Diferencia: {wc_price - db_price}€")
                        else:
                            print(f"\n✅ Los precios están sincronizados")
                            
                        # Mostrar content para ver qué se está guardando
                        print(f"\n📄 Contenido guardado (primeros 500 caracteres):")
                        print(result['content'][:500])
                    else:
                        print(f"❌ No se pudo obtener el producto de WooCommerce")
                else:
                    print(f"❌ No se encontró ID de WooCommerce en metadata")
            else:
                print(f"❌ No se encontró el producto '{product_name}' en la base de datos")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

async def force_update_product(wc_id: int):
    """Forzar actualización de un producto específico"""
    try:
        # Inicializar servicios
        await db_service.initialize()
        await wc_sync_service.initialize()
        
        print(f"\n🔄 Forzando actualización del producto WC ID: {wc_id}")
        
        # Sincronizar producto específico
        success = await wc_sync_service.sync_single_product(wc_id)
        
        if success:
            print("✅ Producto actualizado exitosamente")
        else:
            print("❌ Error actualizando el producto")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug de sincronización de productos')
    parser.add_argument('--name', help='Buscar producto por nombre')
    parser.add_argument('--update', type=int, help='Forzar actualización de producto por WC ID')
    
    args = parser.parse_args()
    
    if args.name:
        asyncio.run(check_product_by_name(args.name))
    elif args.update:
        asyncio.run(force_update_product(args.update))
    else:
        print("Uso:")
        print("  python debug_product_sync.py --name 'nombre del producto'")
        print("  python debug_product_sync.py --update 12345")