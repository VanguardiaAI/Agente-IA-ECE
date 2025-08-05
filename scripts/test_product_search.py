#!/usr/bin/env python3
"""
Script para probar la búsqueda de productos como lo hace el chat
"""

import asyncio
import sys
from pathlib import Path
import json

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service

async def test_product_search(search_query: str):
    """Probar búsqueda híbrida como lo hace el agente"""
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        print(f"\n🔍 Probando búsqueda híbrida para: '{search_query}'")
        
        # Generar embedding para la consulta
        embedding = await embedding_service.generate_embedding(search_query)
        
        # Realizar búsqueda híbrida
        results = await db_service.hybrid_search(
            query_text=search_query,
            query_embedding=embedding,
            content_types=["product"],
            limit=5
        )
        
        print(f"\n📊 Resultados de búsqueda híbrida:")
        print(f"   Encontrados: {len(results)} productos\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', 'Producto')}")
            print(f"   Score RRF: {result.get('rrf_score', 0):.4f}")
            
            metadata = result.get('metadata', {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            print(f"   💰 Precio: {metadata.get('price', 'N/A')}€")
            print(f"   💰 Regular: {metadata.get('regular_price', 'N/A')}€")
            print(f"   💰 Oferta: {metadata.get('sale_price', 'N/A')}€")
            print(f"   Stock: {metadata.get('stock_status', 'N/A')}")
            print(f"   SKU: {metadata.get('sku', 'N/A')}")
            print(f"   ID: {result.get('external_id', 'N/A')}")
            print("-" * 60)
        
        # También probar búsqueda solo por texto
        print(f"\n📊 Resultados de búsqueda solo texto:")
        text_results = await db_service.text_search(
            query_text=search_query,
            content_types=["product"],
            limit=3
        )
        
        for i, result in enumerate(text_results, 1):
            print(f"{i}. {result.get('title', 'Producto')}")
            metadata = result.get('metadata', {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            print(f"   💰 Precio: {metadata.get('price', 'N/A')}€")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    # Probar con diferentes búsquedas
    queries = [
        "Gabarron ventilador de techo industrial v-25 dc",
        "ventilador gabarron v-25",
        "gabarron v-25 dc"
    ]
    
    for query in queries:
        asyncio.run(test_product_search(query))
        print("\n" + "="*80 + "\n")