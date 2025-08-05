#!/usr/bin/env python3
"""
Script para verificar búsqueda de productos con DPN
"""

import asyncio
import sys
from pathlib import Path
import json

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service

async def search_dpn_products():
    """Buscar productos con DPN directamente en la base de datos"""
    try:
        # Inicializar servicios
        await db_service.initialize()
        print("✅ Base de datos inicializada")
        
        # BÚSQUEDA 1: Buscar directamente productos con DPN en el título
        print("\n" + "="*70)
        print("BÚSQUEDA DIRECTA DE PRODUCTOS CON 'DPN' EN EL TÍTULO")
        print("="*70)
        
        async with db_service.pool.acquire() as conn:
            # Buscar productos que contengan DPN en el título
            query = """
                SELECT id, title, content, metadata
                FROM knowledge_base 
                WHERE is_active = true 
                AND content_type = 'product'
                AND (
                    UPPER(title) LIKE '%DPN%' 
                    OR UPPER(title) LIKE '%(DPN)%'
                    OR UPPER(title) LIKE '%D.P.N%'
                )
                ORDER BY title
                LIMIT 20
            """
            
            rows = await conn.fetch(query)
            
            if rows:
                print(f"\n✅ Encontrados {len(rows)} productos con DPN en el título:")
                for i, row in enumerate(rows, 1):
                    title = row['title']
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    price = metadata.get('price', 'N/A')
                    print(f"{i}. {title} - Precio: {price}€")
            else:
                print("❌ NO se encontraron productos con DPN en el título")
        
        # BÚSQUEDA 2: Buscar en el contenido/descripción
        print("\n" + "="*70)
        print("BÚSQUEDA DE PRODUCTOS CON 'DPN' EN LA DESCRIPCIÓN")
        print("="*70)
        
        async with db_service.pool.acquire() as conn:
            query = """
                SELECT id, title, content, metadata
                FROM knowledge_base 
                WHERE is_active = true 
                AND content_type = 'product'
                AND UPPER(content) LIKE '%DPN%'
                ORDER BY title
                LIMIT 20
            """
            
            rows = await conn.fetch(query)
            
            if rows:
                print(f"\n✅ Encontrados {len(rows)} productos con DPN en la descripción:")
                for i, row in enumerate(rows, 1):
                    title = row['title']
                    # Buscar dónde aparece DPN en el contenido
                    content = row['content']
                    dpn_index = content.upper().find('DPN')
                    context = content[max(0, dpn_index-30):min(len(content), dpn_index+30)]
                    print(f"{i}. {title}")
                    print(f"   Contexto: ...{context}...")
            else:
                print("❌ NO se encontraron productos con DPN en la descripción")
        
        # BÚSQUEDA 3: Búsqueda híbrida actual
        print("\n" + "="*70)
        print("BÚSQUEDA HÍBRIDA (como la hace el sistema)")
        print("="*70)
        
        await embedding_service.initialize()
        
        # Detectar términos técnicos
        query_text = "diferencial DPN"
        technical_terms = db_service._extract_technical_terms(query_text)
        print(f"\n📝 Query: '{query_text}'")
        print(f"🔧 Términos técnicos detectados: {technical_terms}")
        
        # Generar embedding
        embedding = await embedding_service.generate_embedding(query_text)
        
        # Búsqueda híbrida
        results = await db_service.hybrid_search(
            query_text=query_text,
            query_embedding=embedding,
            content_types=["product"],
            limit=10
        )
        
        print(f"\n📊 Resultados de búsqueda híbrida: {len(results)} productos")
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Sin título')
            score = result.get('rrf_score', 0)
            has_dpn = 'DPN' in title.upper()
            print(f"{i}. {title}")
            print(f"   Score: {score:.4f}")
            print(f"   Contiene DPN: {'✅ SÍ' if has_dpn else '❌ NO'}")
        
        # BÚSQUEDA 4: Ver algunos productos aleatorios para contexto
        print("\n" + "="*70)
        print("MUESTRA DE PRODUCTOS EN LA BASE DE DATOS")
        print("="*70)
        
        async with db_service.pool.acquire() as conn:
            query = """
                SELECT title 
                FROM knowledge_base 
                WHERE is_active = true 
                AND content_type = 'product'
                AND (title LIKE '%diferencial%' OR title LIKE '%Diferencial%')
                ORDER BY RANDOM()
                LIMIT 10
            """
            
            rows = await conn.fetch(query)
            
            if rows:
                print(f"\nMuestra de 10 diferenciales aleatorios:")
                for i, row in enumerate(rows, 1):
                    print(f"{i}. {row['title']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(search_dpn_products())