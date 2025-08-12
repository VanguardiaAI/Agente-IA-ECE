#!/usr/bin/env python3
"""
Script para probar el optimizador de búsqueda con errores ortográficos
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

async def test_typos():
    optimizer = SearchOptimizer()
    
    test_cases = [
        ("hola, quiero un temro eléctrico", "Typo: temro → termo"),
        ("busco un termo electrico", "Sin tildes"),
        ("necesito un diferencial", "Correcto"),
        ("quiero un ventilador industrial", "Correcto"),
        ("termo electrico 50 litros", "Sin tildes"),
        ("calentador de agua electrico", "Debería funcionar bien")
    ]
    
    print("\n=== PRUEBA DE OPTIMIZADOR CON ERRORES ORTOGRÁFICOS ===\n")
    
    for query, description in test_cases:
        print(f"\n📝 Query: '{query}' ({description})")
        print("-" * 60)
        
        try:
            # Analizar la consulta
            result = await optimizer.analyze_product_query(query)
            
            print(f"✅ Análisis completado:")
            print(f"   🔍 Términos de búsqueda: {result['search_terms']}")
            print(f"   📦 Tipo de producto: {result['product_type']}")
            print(f"   🎯 Consulta optimizada: {result['search_query']}")
            
            # Verificar si se corrigió el typo
            if "temro" in query.lower() and "termo" in str(result['search_terms']):
                print("   ✨ TYPO CORREGIDO: temro → termo")
            
            # Verificar si se identificó correctamente el producto
            if "termo" in query.lower() and "calentador" in str(result['search_terms']):
                print("   ✨ PRODUCTO IDENTIFICADO: termo → calentador de agua")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(test_typos())