#!/usr/bin/env python
"""
Verificar si hay productos Schneider en la base de datos
y sincronizar desde WooCommerce si es necesario
"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import db_service

async def check_schneider_products():
    """Verificar productos Schneider en la BD"""
    
    print("🔍 VERIFICANDO PRODUCTOS SCHNEIDER EN LA BASE DE DATOS")
    print("=" * 60)
    
    # Inicializar BD
    await db_service.initialize()
    
    async with db_service.pool.acquire() as conn:
        # 1. Contar total de productos
        total = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM knowledge_base 
            WHERE content_type = 'product'
        """)
        print(f"\n📊 Total de productos en BD: {total}")
        
        # 2. Buscar productos con "schneider" en cualquier parte
        schneider_products = await conn.fetch("""
            SELECT id, title, external_id
            FROM knowledge_base 
            WHERE content_type = 'product'
            AND (
                LOWER(title) LIKE '%schneider%'
                OR LOWER(content) LIKE '%schneider%'
            )
            LIMIT 20
        """)
        
        print(f"\n🏷️ Productos con 'Schneider': {len(schneider_products)}")
        if schneider_products:
            print("\n📦 Productos Schneider encontrados:")
            for p in schneider_products[:10]:
                print(f"   - {p['title'][:60]}... (ID: {p['external_id']})")
        else:
            print("   ❌ No se encontraron productos Schneider")
        
        # 3. Buscar otras marcas para comparar
        print("\n🏷️ Análisis de marcas en títulos:")
        brands_to_check = ['Schneider', 'Legrand', 'Jung', 'Simon', 'ABB', 'Siemens']
        
        for brand in brands_to_check:
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM knowledge_base 
                WHERE content_type = 'product'
                AND LOWER(title) LIKE $1
            """, f'%{brand.lower()}%')
            
            if count > 0:
                print(f"   ✅ {brand}: {count} productos")
            else:
                print(f"   ❌ {brand}: 0 productos")
        
        # 4. Ver algunos productos aleatorios para entender qué hay
        print("\n📋 Muestra de productos en BD (primeros 10):")
        sample = await conn.fetch("""
            SELECT title, external_id
            FROM knowledge_base 
            WHERE content_type = 'product'
            ORDER BY title
            LIMIT 10
        """)
        
        for p in sample:
            print(f"   - {p['title'][:50]}... (ID: {p['external_id']})")
    
    # CONCLUSIÓN
    print("\n" + "=" * 60)
    print("💡 CONCLUSIÓN:")
    
    if total < 500:
        print(f"⚠️ Solo hay {total} productos en la BD (es una BD de prueba)")
        print("   La tienda real tiene 4,677+ productos")
        print("   Por eso no encuentra productos Schneider")
        print("\n📌 SOLUCIÓN: Sincronizar todos los productos desde WooCommerce")
        print("   Ejecutar: python scripts/sync_products.py")
    elif len(schneider_products) == 0:
        print("⚠️ Los productos Schneider no están sincronizados")
        print("   Necesitas sincronizar productos de esa marca")
    else:
        print(f"✅ Hay {len(schneider_products)} productos Schneider en la BD")
        print("   El problema debe estar en la búsqueda")

if __name__ == "__main__":
    asyncio.run(check_schneider_products())