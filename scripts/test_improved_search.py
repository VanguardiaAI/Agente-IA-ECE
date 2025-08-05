#!/usr/bin/env python3
"""
Script para probar la búsqueda mejorada con priorización de coincidencias exactas
"""

import asyncio
import sys
from pathlib import Path
import json
from typing import List, Dict, Any

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from config.settings import HYBRID_SEARCH_CONFIG

class SearchTester:
    def __init__(self):
        self.test_results = []
        
    async def test_search(self, query: str, expected_terms: List[str] = None):
        """Probar una búsqueda específica"""
        print(f"\n🔍 Probando búsqueda: '{query}'")
        print("-" * 60)
        
        # Generar embedding para la consulta
        embedding = await embedding_service.generate_embedding(query)
        
        # Realizar búsqueda híbrida
        results = await db_service.hybrid_search(
            query_text=query,
            query_embedding=embedding,
            content_types=["product"],
            limit=5
        )
        
        print(f"📊 Encontrados: {len(results)} productos")
        
        # Verificar términos técnicos detectados
        technical_terms = db_service._extract_technical_terms(query)
        print(f"🔧 Términos técnicos detectados: {technical_terms}")
        
        # Análisis de resultados
        exact_matches = 0
        partial_matches = 0
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Producto')
            metadata = result.get('metadata', {})
            score = result.get('rrf_score', 0)
            exact_boost = result.get('exact_match_boost', 0)
            
            print(f"\n{i}. {title}")
            print(f"   Score total: {score:.4f}")
            print(f"   Boost exacto: {exact_boost:.1f}")
            
            # Verificar coincidencias esperadas
            if expected_terms:
                matches = []
                for term in expected_terms:
                    if term.upper() in title.upper():
                        matches.append(f"✅ '{term}' en título")
                        exact_matches += 1
                    elif result.get('content') and term.upper() in result['content'].upper():
                        matches.append(f"📝 '{term}' en descripción")
                        partial_matches += 1
                    else:
                        matches.append(f"❌ '{term}' no encontrado")
                
                if matches:
                    print(f"   Coincidencias: {', '.join(matches)}")
            
            print(f"   💰 Precio: {metadata.get('price', 'N/A')}€")
            print(f"   Stock: {'✅ Disponible' if metadata.get('stock_status') == 'instock' else '❌ Sin stock'}")
        
        # Resumen
        print(f"\n📈 Resumen:")
        print(f"   - Coincidencias exactas en título: {exact_matches}")
        print(f"   - Coincidencias en descripción: {partial_matches}")
        
        return {
            'query': query,
            'results_count': len(results),
            'technical_terms': technical_terms,
            'exact_matches': exact_matches,
            'partial_matches': partial_matches
        }
    
    async def run_all_tests(self):
        """Ejecutar todos los casos de prueba"""
        print("\n" + "="*70)
        print("🧪 PRUEBAS DE BÚSQUEDA MEJORADA CON COINCIDENCIAS EXACTAS")
        print("="*70)
        
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Casos de prueba para términos técnicos específicos
        test_cases = [
            {
                'query': 'diferencial DPN',
                'expected': ['DPN'],
                'description': 'Búsqueda de diferencial con código DPN específico'
            },
            {
                'query': 'magnetotérmico C60N',
                'expected': ['C60N'],
                'description': 'Búsqueda de magnetotérmico modelo C60N'
            },
            {
                'query': 'cable H07V-K 2.5mm',
                'expected': ['H07V-K', '2.5mm'],
                'description': 'Búsqueda de cable con especificación técnica'
            },
            {
                'query': 'luminaria LED IP65 50W',
                'expected': ['LED', 'IP65', '50W'],
                'description': 'Búsqueda con múltiples especificaciones técnicas'
            },
            {
                'query': 'contactor LC1D12',
                'expected': ['LC1D12'],
                'description': 'Búsqueda de contactor con modelo específico'
            },
            {
                'query': 'diferencial tipo A 30mA',
                'expected': ['30mA'],
                'description': 'Búsqueda con especificación de sensibilidad'
            }
        ]
        
        print(f"\n📋 Ejecutando {len(test_cases)} casos de prueba...")
        
        for test_case in test_cases:
            print(f"\n{'='*70}")
            print(f"📝 {test_case['description']}")
            
            result = await self.test_search(
                test_case['query'], 
                test_case.get('expected', [])
            )
            self.test_results.append(result)
        
        # Pruebas de búsquedas generales (sin términos técnicos específicos)
        print(f"\n{'='*70}")
        print("🔍 PRUEBAS DE BÚSQUEDAS GENERALES")
        print("="*70)
        
        general_queries = [
            "iluminación exterior",
            "material eléctrico industrial",
            "automatización vivienda",
            "protección sobretensiones"
        ]
        
        for query in general_queries:
            result = await self.test_search(query)
            self.test_results.append(result)
        
        # Mostrar resumen final
        self.show_summary()
    
    def show_summary(self):
        """Mostrar resumen de todas las pruebas"""
        print("\n" + "="*70)
        print("📊 RESUMEN DE PRUEBAS")
        print("="*70)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r['results_count'] > 0)
        
        print(f"\n✅ Pruebas ejecutadas: {total_tests}")
        print(f"✅ Pruebas con resultados: {successful_tests}")
        print(f"❌ Pruebas sin resultados: {total_tests - successful_tests}")
        
        # Mostrar configuración actual
        print(f"\n⚙️ Configuración de búsqueda:")
        print(f"   - Peso vectorial: {HYBRID_SEARCH_CONFIG['vector_weight']}")
        print(f"   - Peso texto: {HYBRID_SEARCH_CONFIG['text_weight']}")
        print(f"   - Boost título exacto: {HYBRID_SEARCH_CONFIG.get('exact_match_title_boost', 0)}")
        print(f"   - Boost descripción exacta: {HYBRID_SEARCH_CONFIG.get('exact_match_desc_boost', 0)}")
        print(f"   - Boost parcial: {HYBRID_SEARCH_CONFIG.get('partial_match_boost', 0)}")
        
        print("\n✨ Mejoras implementadas:")
        print("   ✅ Detección automática de términos técnicos")
        print("   ✅ Priorización de coincidencias exactas en título")
        print("   ✅ Boost secundario para coincidencias en descripción")
        print("   ✅ Mantiene capacidad de búsqueda semántica")

async def main():
    tester = SearchTester()
    try:
        await tester.run_all_tests()
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(main())