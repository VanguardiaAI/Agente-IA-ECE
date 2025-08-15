#!/usr/bin/env python3
"""
Script para probar el sistema de búsqueda mejorado
Compara resultados de búsqueda tradicional vs inteligente
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import db_service
from services.woocommerce import WooCommerceService
from services.embedding_service import embedding_service
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search_comparison():
    """Comparar búsqueda tradicional vs inteligente"""
    
    # Casos de prueba variados
    test_queries = [
        # Búsquedas exactas/técnicas
        "automatico C16",
        "diferencial 25A 30mA",
        "LED E27 9W",
        "cable 2.5mm",
        
        # Búsquedas semánticas
        "bombillas para sala",
        "proteccion para casa",
        "iluminacion exterior",
        "cable para cocina",
        
        # Búsquedas mixtas
        "interruptor automatico",
        "lampara led barata",
        "enchufes industriales",
        "fusibles 10A"
    ]
    
    print("=" * 60)
    print("PRUEBA DE BÚSQUEDA MEJORADA")
    print("=" * 60)
    
    # Inicializar servicios
    await db_service.initialize()
    await embedding_service.initialize()
    wc_service = WooCommerceService()
    
    for query in test_queries:
        print(f"\n🔍 CONSULTA: '{query}'")
        print("-" * 50)
        
        try:
            # Generar embedding
            embedding = await embedding_service.generate_embedding(query)
            
            # Búsqueda inteligente (nueva)
            print("📊 BÚSQUEDA INTELIGENTE:")
            smart_results = await db_service.intelligent_product_search(
                query_text=query,
                query_embedding=embedding,
                content_types=["product"],
                limit=5,
                wc_service=wc_service
            )
            
            if smart_results:
                for i, result in enumerate(smart_results[:3], 1):
                    title = result.get('title', 'Sin título')[:50]
                    score = result.get('rrf_score', 0)
                    source = result.get('source', 'unknown')
                    match_type = result.get('match_type', 'unknown')
                    stock = result.get('metadata', {}).get('stock_status', 'unknown')
                    
                    print(f"  {i}. {title}... (Score: {score:.1f}, {source}/{match_type}, Stock: {stock})")
            else:
                print("  ❌ Sin resultados")
            
            # Búsqueda tradicional (comparación)
            print("\n📊 BÚSQUEDA TRADICIONAL:")
            traditional_results = await db_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                content_types=["product"],
                limit=5
            )
            
            if traditional_results:
                for i, result in enumerate(traditional_results[:3], 1):
                    title = result.get('title', 'Sin título')[:50]
                    score = result.get('rrf_score', 0)
                    match_type = result.get('match_type', 'hybrid')
                    stock = result.get('metadata', {}).get('stock_status', 'unknown')
                    
                    print(f"  {i}. {title}... (Score: {score:.1f}, {match_type}, Stock: {stock})")
            else:
                print("  ❌ Sin resultados")
            
            # Comparación de rendimiento
            smart_count = len(smart_results) if smart_results else 0
            traditional_count = len(traditional_results) if traditional_results else 0
            wc_count = len([r for r in smart_results if r.get('source') == 'woocommerce']) if smart_results else 0
            
            print(f"\n📈 COMPARACIÓN:")
            print(f"  • Inteligente: {smart_count} resultados ({wc_count} de WooCommerce)")
            print(f"  • Tradicional: {traditional_count} resultados")
            
        except Exception as e:
            print(f"❌ Error en consulta '{query}': {e}")
    
    print("\n" + "=" * 60)
    print("PRUEBA COMPLETADA")
    print("=" * 60)

async def test_cache_performance():
    """Probar rendimiento del cache"""
    print("\n🚀 PRUEBA DE CACHE")
    print("-" * 30)
    
    test_query = "automatico C16"
    embedding = await embedding_service.generate_embedding(test_query)
    wc_service = WooCommerceService()
    
    import time
    
    # Primera búsqueda (sin cache)
    start = time.time()
    results1 = await db_service.intelligent_product_search(
        query_text=test_query,
        query_embedding=embedding,
        content_types=["product"],
        limit=5,
        wc_service=wc_service
    )
    time1 = time.time() - start
    
    # Segunda búsqueda (con cache)
    start = time.time()
    results2 = await db_service.intelligent_product_search(
        query_text=test_query,
        query_embedding=embedding,
        content_types=["product"],
        limit=5,
        wc_service=wc_service
    )
    time2 = time.time() - start
    
    print(f"⏱️ Primera búsqueda: {time1:.3f}s ({len(results1)} resultados)")
    print(f"⏱️ Segunda búsqueda: {time2:.3f}s ({len(results2)} resultados)")
    print(f"🚀 Mejora de rendimiento: {((time1 - time2) / time1 * 100):.1f}%")

async def main():
    """Función principal"""
    try:
        await test_search_comparison()
        await test_cache_performance()
    except Exception as e:
        logger.error(f"Error en pruebas: {e}")
        raise
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(main())