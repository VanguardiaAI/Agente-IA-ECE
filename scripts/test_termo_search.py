#!/usr/bin/env python3
"""
Script para probar específicamente la búsqueda de termos eléctricos
"""

import asyncio
import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv("env.agent")

import logging
logging.basicConfig(level=logging.INFO)

async def test_termo_search():
    from services.search_optimizer import SearchOptimizer
    from services.database import db_service
    from services.embedding_service import embedding_service
    
    # Inicializar servicios
    if not db_service.initialized:
        await db_service.initialize()
    if not embedding_service.initialized:
        await embedding_service.initialize()
    
    optimizer = SearchOptimizer()
    
    test_queries = [
        "quiero un termo eléctrico",
        "busco termos electricos",
        "necesito un calentador de agua",
        "quiero una caldera eléctrica"
    ]
    
    print("\n=== PRUEBA DE BÚSQUEDA DE TERMOS ===\n")
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"📝 Query: '{query}'")
        print(f"{'='*60}\n")
        
        try:
            # 1. Optimizar la consulta
            result = await optimizer.analyze_product_query(query)
            print(f"✅ Consulta optimizada: {result['search_query']}")
            print(f"   Términos: {result['search_terms']}")
            
            # 2. Generar embedding
            embedding = await embedding_service.generate_embedding(result['search_query'])
            
            # 3. Buscar productos
            products = await db_service.hybrid_search(
                query_text=result['search_query'],
                query_embedding=embedding,
                content_types=["product"],
                limit=5
            )
            
            # 4. Mostrar resultados
            print(f"\n📦 Productos encontrados ({len(products)}):")
            for i, product in enumerate(products[:5], 1):
                title = product.get('title', 'Sin título')
                score = product.get('rrf_score', 0)
                match_type = product.get('match_type', 'unknown')
                
                # Detectar tipo de producto
                title_lower = title.lower()
                if 'termo' in title_lower:
                    product_type = "✅ TERMO"
                elif 'caldera' in title_lower:
                    product_type = "⚠️ CALDERA"
                elif 'calentador' in title_lower:
                    product_type = "✅ CALENTADOR"
                else:
                    product_type = "❓ OTRO"
                
                print(f"   {i}. {product_type} - {title}")
                print(f"      Score: {score:.1f}, Tipo: {match_type}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(test_termo_search())