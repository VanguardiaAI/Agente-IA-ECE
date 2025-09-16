#!/usr/bin/env python3
"""
Debug búsqueda de automático
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
load_dotenv("env.agent")

from services.database import HybridDatabaseService
from services.embedding_service import EmbeddingService
from src.agent.gpt5_agents import SearchAnalyzer

async def test():
    # Primero, ver qué encuentra la búsqueda directa
    print("1. BÚSQUEDA DIRECTA EN DB")
    print("="*60)
    
    db = HybridDatabaseService()
    embedding_service = EmbeddingService()
    await db.initialize()
    await embedding_service.initialize()
    
    # Buscar solo "automático"
    results = await db.text_search(
        query_text="automático",
        content_types=['product'],
        limit=10
    )
    
    print(f"Resultados para 'automático': {len(results)}")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r['title']}")
    
    # También con embeddings
    print("\n2. BÚSQUEDA HÍBRIDA")
    print("="*60)
    
    embedding = await embedding_service.generate_embedding("automático")
    hybrid_results = await db.hybrid_search(
        query_text="automático",
        query_embedding=embedding,
        content_types=['product'],
        limit=10
    )
    
    print(f"Resultados híbridos: {len(hybrid_results)}")
    for i, r in enumerate(hybrid_results[:5], 1):
        print(f"{i}. {r['title']} (Score: {r.get('rrf_score', 0)})")
    
    # Ver qué analiza el SearchAnalyzer
    print("\n3. ANÁLISIS DE BÚSQUEDA")
    print("="*60)
    
    analyzer = SearchAnalyzer()
    analysis = await analyzer.analyze_search(
        "quiero un automático",
        []  # Sin mensajes previos
    )
    
    print(f"Tipo de producto: {analysis.product_type}")
    print(f"Tiene suficiente info: {analysis.has_enough_info}")
    print(f"Necesita clarificación: {analysis.clarification_needed}")
    print(f"Info faltante: {analysis.missing_info}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(test())