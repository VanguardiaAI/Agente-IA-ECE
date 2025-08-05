#!/usr/bin/env python3
"""
Script para buscar productos y ver su información
"""

import asyncio
import sys
from pathlib import Path
import json

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service

async def search_products(search_term: str):
    """Buscar productos por término"""
    try:
        # Inicializar base de datos
        await db_service.initialize()
        
        print(f"\n🔍 Buscando productos con: '{search_term}'\n")
        
        # Buscar en base de datos
        async with db_service.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    external_id,
                    title,
                    metadata,
                    updated_at,
                    substring(content, 1, 200) as content_preview
                FROM knowledge_base
                WHERE content_type = 'product'
                AND is_active = true
                AND (
                    title ILIKE $1 
                    OR content ILIKE $1
                    OR metadata::text ILIKE $1
                )
                ORDER BY title
                LIMIT 10
            """, f'%{search_term}%')
            
            if results:
                print(f"📦 Encontrados {len(results)} productos:\n")
                
                for idx, result in enumerate(results, 1):
                    print(f"{idx}. {result['title']}")
                    print(f"   ID: {result['external_id']}")
                    print(f"   Actualizado: {result['updated_at']}")
                    
                    # Parsear metadata
                    try:
                        metadata = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                        print(f"   💰 Precio: {metadata.get('price', 'N/A')}€")
                        print(f"   💰 Precio Regular: {metadata.get('regular_price', 'N/A')}€")
                        print(f"   💰 Precio Oferta: {metadata.get('sale_price', 'N/A')}€")
                        print(f"   SKU: {metadata.get('sku', 'N/A')}")
                        print(f"   WC ID: {metadata.get('wc_id', 'N/A')}")
                    except Exception as e:
                        print(f"   ⚠️  Error parseando metadata: {e}")
                    
                    print(f"   📄 Vista previa: {result['content_preview'][:100]}...")
                    print("-" * 80)
            else:
                print(f"❌ No se encontraron productos con '{search_term}'")
                
                # Intentar buscar sin considerar mayúsculas/minúsculas y acentos
                print("\n🔍 Intentando búsqueda más amplia...")
                
                results2 = await conn.fetch("""
                    SELECT DISTINCT
                        substring(title, 1, 100) as title_preview,
                        content_type,
                        count(*) as count
                    FROM knowledge_base
                    WHERE is_active = true
                    AND content_type = 'product'
                    GROUP BY substring(title, 1, 100), content_type
                    ORDER BY count DESC
                    LIMIT 5
                """)
                
                if results2:
                    print("\n📋 Algunos productos en la base de datos:")
                    for r in results2:
                        print(f"   - {r['title_preview']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

async def show_price_samples():
    """Mostrar algunos ejemplos de precios"""
    try:
        await db_service.initialize()
        
        print(f"\n💰 Muestra de productos con precios:\n")
        
        async with db_service.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    title,
                    metadata,
                    external_id
                FROM knowledge_base
                WHERE content_type = 'product'
                AND is_active = true
                AND metadata::text LIKE '%price%'
                ORDER BY updated_at DESC
                LIMIT 5
            """)
            
            for result in results:
                print(f"📦 {result['title']}")
                try:
                    metadata = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                    print(f"   Precio: {metadata.get('price', 'N/A')}€")
                    print(f"   Regular: {metadata.get('regular_price', 'N/A')}€")
                    print(f"   Oferta: {metadata.get('sale_price', 'N/A')}€")
                    print(f"   ID: {result['external_id']}")
                except:
                    pass
                print("-" * 50)
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_service.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Buscar productos en la base de datos')
    parser.add_argument('search_term', nargs='?', help='Término de búsqueda')
    parser.add_argument('--prices', action='store_true', help='Mostrar muestra de precios')
    
    args = parser.parse_args()
    
    if args.prices:
        asyncio.run(show_price_samples())
    elif args.search_term:
        asyncio.run(search_products(args.search_term))
    else:
        # Por defecto buscar "Gabarron"
        asyncio.run(search_products("Gabarron"))