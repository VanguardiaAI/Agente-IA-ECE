#!/usr/bin/env python
"""
Verificar cuántos productos hay realmente en la BD
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import db_service

async def check_products():
    print("🔍 VERIFICANDO PRODUCTOS EN LA BASE DE DATOS")
    print("=" * 60)
    
    await db_service.initialize()
    
    async with db_service.pool.acquire() as conn:
        # Contar por tipo
        result = await conn.fetch("""
            SELECT 
                content_type,
                COUNT(*) as total
            FROM knowledge_base 
            GROUP BY content_type
            ORDER BY total DESC
        """)
        
        print("\n📊 Contenido en la BD:")
        total_all = 0
        for row in result:
            print(f"   {row['content_type']}: {row['total']}")
            total_all += row['total']
        
        print(f"\n   TOTAL: {total_all} entradas")
        
        # Verificar productos específicamente
        product_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM knowledge_base 
            WHERE content_type = 'product'
        """)
        
        print(f"\n📦 Total de productos: {product_count}")
        
        if product_count < 1000:
            print("⚠️ Hay muy pocos productos, parece ser una BD de prueba")
            print("   La tienda real tiene 4,677+ productos")
        
        # Ver marcas disponibles
        print("\n🏷️ Marcas disponibles (muestra):")
        brands = await conn.fetch("""
            SELECT 
                SUBSTRING(title FROM '^([^ ]+)') as brand,
                COUNT(*) as count
            FROM knowledge_base
            WHERE content_type = 'product'
            GROUP BY SUBSTRING(title FROM '^([^ ]+)')
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for brand in brands:
            if brand['brand']:
                print(f"   {brand['brand']}: {brand['count']} productos")

if __name__ == "__main__":
    asyncio.run(check_products())