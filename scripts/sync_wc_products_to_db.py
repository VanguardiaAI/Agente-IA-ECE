#!/usr/bin/env python3
"""
Script para sincronizar productos de WooCommerce a PostgreSQL con pgvector
Este script carga todos los productos de WooCommerce en la base de datos local
para que el sistema de refinamiento pueda funcionar correctamente.
"""

import asyncio
import os
import sys
from datetime import datetime
import json

# Añadir el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import asyncpg
from services.woocommerce import WooCommerceService
from services.embedding_service import EmbeddingService

# Cargar variables de entorno
load_dotenv('.env')

async def create_tables_if_not_exist(conn):
    """Crear las tablas necesarias si no existen"""
    
    # Crear extensión pgvector si no existe
    await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Crear tabla de knowledge_base (productos)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id SERIAL PRIMARY KEY,
            content_type VARCHAR(50),
            title TEXT,
            content TEXT,
            metadata JSONB,
            embedding vector(1536),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear índices
    await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_knowledge_base_content_type 
        ON knowledge_base(content_type)
    ''')
    
    await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding 
        ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    ''')
    
    print("✅ Tablas e índices creados/verificados")

async def sync_products():
    """Sincronizar productos de WooCommerce a PostgreSQL"""
    
    # Conectar a PostgreSQL
    conn = await asyncpg.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'woocommerce'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )
    
    try:
        # Crear tablas si no existen
        await create_tables_if_not_exist(conn)
        
        # Inicializar servicios
        wc_service = WooCommerceService()
        embedding_service = EmbeddingService()
        
        # Inicializar el servicio de embeddings
        print("🔄 Inicializando servicio de embeddings...")
        await embedding_service.initialize()
        print("✅ Servicio de embeddings inicializado")
        
        print("\n🔄 Obteniendo productos de WooCommerce...")
        
        # Obtener todos los productos (paginado)
        all_products = []
        page = 1
        per_page = 100
        
        while True:
            products = await wc_service.get_products(page=page, per_page=per_page)
            if not products:
                break
            all_products.extend(products)
            print(f"   Página {page}: {len(products)} productos")
            page += 1
            
            # Limitar para pruebas (quitar en producción)
            if len(all_products) >= 50:
                print("   ⚠️ Limitado a 50 productos para prueba rápida")
                break
        
        print(f"\n📦 Total de productos obtenidos: {len(all_products)}")
        
        # Limpiar productos existentes
        await conn.execute("DELETE FROM knowledge_base WHERE content_type = 'product'")
        print("🗑️ Productos anteriores eliminados")
        
        # Insertar productos nuevos
        print("\n📝 Insertando productos en la base de datos...")
        
        for i, product in enumerate(all_products, 1):
            try:
                # Preparar contenido para embedding
                content = f"{product.get('name', '')} {product.get('description', '')} {product.get('short_description', '')}"
                
                # Generar embedding
                embedding = await embedding_service.generate_embedding(content)
                
                # Preparar metadata
                metadata = {
                    'product_id': product.get('id'),
                    'sku': product.get('sku', ''),
                    'price': float(product.get('price', 0) or 0),
                    'regular_price': float(product.get('regular_price', 0) or 0),
                    'sale_price': float(product.get('sale_price', 0) or 0),
                    'stock_status': product.get('stock_status', 'unknown'),
                    'stock_quantity': product.get('stock_quantity'),
                    'categories': [cat.get('name', '') for cat in product.get('categories', [])],
                    'tags': [tag.get('name', '') for tag in product.get('tags', [])],
                    'permalink': product.get('permalink', ''),
                    'images': [img.get('src', '') for img in product.get('images', [])][:1],  # Solo primera imagen
                    'attributes': {attr.get('name', ''): attr.get('options', []) for attr in product.get('attributes', [])}
                }
                
                # Convertir embedding a formato pgvector
                if isinstance(embedding, list):
                    # pgvector espera un string con formato '[x,y,z,...]'
                    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                else:
                    embedding_str = embedding
                
                # Insertar en la base de datos
                await conn.execute('''
                    INSERT INTO knowledge_base (content_type, title, content, metadata, embedding)
                    VALUES ($1, $2, $3, $4, $5::vector)
                ''', 'product', product.get('name', ''), content, json.dumps(metadata), embedding_str)
                
                if i % 10 == 0:
                    print(f"   Procesados: {i}/{len(all_products)}")
                    
            except Exception as e:
                print(f"   ⚠️ Error con producto {product.get('name', 'Unknown')}: {e}")
        
        # Contar productos insertados
        count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_base WHERE content_type = 'product'")
        print(f"\n✅ {count} productos sincronizados exitosamente")
        
        # Mostrar algunos ejemplos de búsqueda
        print("\n🔍 Verificando búsquedas de ejemplo:")
        
        # Buscar cables
        cable_count = await conn.fetchval("""
            SELECT COUNT(*) FROM knowledge_base 
            WHERE content_type = 'product' 
            AND (title ILIKE '%cable%' OR content ILIKE '%cable%')
        """)
        print(f"   - Productos con 'cable': {cable_count}")
        
        # Buscar diferenciales
        dif_count = await conn.fetchval("""
            SELECT COUNT(*) FROM knowledge_base 
            WHERE content_type = 'product' 
            AND (title ILIKE '%diferencial%' OR content ILIKE '%diferencial%')
        """)
        print(f"   - Productos con 'diferencial': {dif_count}")
        
        # Buscar automáticos
        auto_count = await conn.fetchval("""
            SELECT COUNT(*) FROM knowledge_base 
            WHERE content_type = 'product' 
            AND (title ILIKE '%automático%' OR content ILIKE '%magnetotérmico%')
        """)
        print(f"   - Productos con 'automático/magnetotérmico': {auto_count}")
        
        print("\n🎉 Sincronización completada exitosamente")
        print("📌 Ahora el sistema de refinamiento debería funcionar correctamente")
        
    finally:
        await conn.close()

async def main():
    """Función principal"""
    print("🚀 SINCRONIZACIÓN DE PRODUCTOS WOOCOMMERCE → POSTGRESQL")
    print("="*60)
    
    try:
        await sync_products()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())