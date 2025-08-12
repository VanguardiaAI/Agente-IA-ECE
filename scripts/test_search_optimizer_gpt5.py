#!/usr/bin/env python3
"""
Script para probar el optimizador de búsqueda con GPT-5
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

from services.search_optimizer import SearchOptimizer

async def test_search_optimizer():
    optimizer = SearchOptimizer()
    
    test_queries = [
        "quiero un termo eléctrico",
        "necesito un ventilador industrial",
        "busco un diferencial",
        "calentador de agua 50 litros",
        "ventilador de pared potente",
        "termo eléctrico fleck"
    ]
    
    print("\n=== PRUEBA DE OPTIMIZADOR DE BÚSQUEDA CON GPT-5 ===\n")
    
    for query in test_queries:
        print(f"\n📝 Query original: '{query}'")
        print("-" * 60)
        
        try:
            # Analizar la consulta
            result = await optimizer.analyze_product_query(query)
            
            print(f"✅ Análisis completado:")
            print(f"   🔍 Términos de búsqueda: {result['search_terms']}")
            print(f"   📦 Tipo de producto: {result['product_type']}")
            print(f"   🎯 Consulta optimizada: {result['search_query']}")
            print(f"   💡 Intención: {result['intent']}")
            
            if result.get('specific_features'):
                print(f"   ⚙️  Características: {result['specific_features']}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(test_search_optimizer())