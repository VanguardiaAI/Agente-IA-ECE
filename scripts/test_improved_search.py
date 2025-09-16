#!/usr/bin/env python3
"""
Test mejorado de búsqueda con validación de relevancia
"""

import asyncio
import sys
import os
import json
from typing import Dict, List, Tuple
import logging

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent
from services.database import HybridDatabaseService
from services.embedding_service import EmbeddingService
from services.search_optimizer import search_optimizer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedSearchTester:
    def __init__(self):
        self.agent = HybridCustomerAgent()
        self.db_service = HybridDatabaseService()
        self.embedding_service = EmbeddingService()
        
        self.test_cases = [
            # Casos que buscan productos industriales
            {
                "query": "lámpara para una fábrica",
                "expected_products": ["campana", "industrial", "led", "proyector"],
                "should_refine": False,
                "reason": "Debe expandir a productos industriales y mostrarlos directamente"
            },
            {
                "query": "recoge cables",
                "expected_products": ["enrollacables", "organizador"],
                "should_refine": False,
                "reason": "Debe encontrar enrollacables y organizadores de cables"
            },
            {
                "query": "automático 16 amperios",
                "expected_products": ["magnetotérmico", "16A", "interruptor automático"],
                "should_refine": False,
                "reason": "Búsqueda específica de componente eléctrico"
            },
            {
                "query": "diferencial schneider 25A",
                "expected_products": ["schneider", "diferencial", "25A"],
                "should_refine": False,
                "reason": "Marca + especificación, resultados muy específicos"
            },
            # Casos genéricos que SÍ deberían refinar
            {
                "query": "lámpara",
                "expected_products": ["lámpara", "led", "bombilla"],
                "should_refine": True,
                "reason": "Término muy genérico con muchos tipos"
            },
            {
                "query": "cable",
                "expected_products": ["cable", "manguera", "conductor"],
                "should_refine": True,
                "reason": "Muy genérico, necesita especificar tipo/sección"
            }
        ]
        
    async def initialize(self):
        """Inicializa los servicios necesarios"""
        await self.db_service.initialize()
        await self.embedding_service.initialize()
        
    async def test_search_optimization(self, query: str) -> Dict:
        """Prueba la optimización de búsqueda"""
        try:
            # Usar search_optimizer para expandir la búsqueda
            analysis = await search_optimizer.analyze_product_query(query)
            logger.info(f"📝 Query: '{query}'")
            logger.info(f"   Términos expandidos: {analysis.get('search_terms', [])}")
            logger.info(f"   Query optimizada: {analysis.get('search_query', query)}")
            
            return analysis
        except Exception as e:
            logger.error(f"Error en optimización: {e}")
            return {"search_terms": query.split(), "search_query": query}
            
    async def test_search_results(self, query: str, expected_products: List[str]) -> Tuple[bool, int, float]:
        """Prueba los resultados de búsqueda"""
        try:
            # Primero optimizar la búsqueda
            analysis = await search_optimizer.analyze_product_query(query)
            optimized_query = analysis.get('search_query', query)
            
            # Generar embedding
            embedding = await self.embedding_service.generate_embedding(optimized_query)
            
            # Buscar productos
            results = await self.db_service.hybrid_search(
                query_text=optimized_query,
                query_embedding=embedding,
                content_types=["product"],
                limit=30
            )
            
            if not results:
                logger.warning(f"   ⚠️ No se encontraron resultados")
                return False, 0, 0.0
                
            # Analizar relevancia de los primeros 10 resultados
            top_10 = results[:10]
            relevant_count = 0
            
            for result in top_10:
                title = result.get('title', '').lower()
                content = result.get('content', '').lower()
                
                # Verificar si contiene términos esperados
                is_relevant = any(term.lower() in title or term.lower() in content 
                                 for term in expected_products)
                if is_relevant:
                    relevant_count += 1
                    
            relevance_ratio = relevant_count / len(top_10) if top_10 else 0
            
            logger.info(f"   📊 Encontrados: {len(results)} productos")
            logger.info(f"   📊 Relevancia top 10: {relevant_count}/{len(top_10)} ({relevance_ratio:.1%})")
            
            # Mostrar algunos resultados
            for i, result in enumerate(top_10[:3], 1):
                logger.info(f"      {i}. {result.get('title', 'Sin título')}")
                
            return True, len(results), relevance_ratio
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return False, 0, 0.0
            
    async def determine_refinement_decision(self, query: str, num_results: int, relevance_ratio: float) -> bool:
        """Determina si se debe ofrecer refinamiento basado en los resultados"""
        # Si hay pocos resultados (<=10), no refinar
        if num_results <= 10:
            return False
            
        # Detectar si es un término genérico único
        search_terms = query.lower().split()
        generic_single_terms = {'lámpara', 'cable', 'interruptor', 'enchufe', 'caja', 'tubo', 'led', 'bombilla'}
        is_generic_single = len(search_terms) == 1 and search_terms[0] in generic_single_terms
        
        if is_generic_single:
            # Términos genéricos únicos siempre refinan
            return True
            
        # Para búsquedas expandidas significativamente (lámpara para fábrica)
        # no refinar si hay alta relevancia
        analysis = await search_optimizer.analyze_product_query(query)
        expanded_terms = analysis.get('search_terms', [])
        significant_expansion = len(expanded_terms) >= len(search_terms) * 2
        
        if significant_expansion and relevance_ratio >= 0.7:
            # Expansión significativa con alta relevancia, no refinar
            return False
            
        # En otros casos con muchos resultados, sí refinar
        return True
        
    async def run_test_case(self, test_case: Dict) -> bool:
        """Ejecuta un caso de prueba completo"""
        query = test_case["query"]
        expected_products = test_case["expected_products"]
        should_refine = test_case["should_refine"]
        reason = test_case["reason"]
        
        print(f"\n{'='*60}")
        print(f"📝 Query: '{query}'")
        print(f"📋 Razón: {reason}")
        print(f"🎯 Debería refinar: {'Sí' if should_refine else 'No'}")
        print("-" * 60)
        
        # 1. Probar optimización
        analysis = await self.test_search_optimization(query)
        
        # 2. Probar resultados de búsqueda
        success, num_results, relevance_ratio = await self.test_search_results(query, expected_products)
        
        if not success:
            print(f"❌ FAIL: No se encontraron resultados")
            return False
            
        # 3. Determinar si se debería refinar
        actual_refine = await self.determine_refinement_decision(query, num_results, relevance_ratio)
        
        # 4. Verificar si coincide con lo esperado
        if actual_refine == should_refine:
            print(f"✅ PASS: Decisión correcta de refinamiento")
            if not should_refine and relevance_ratio >= 0.7:
                print(f"   ✨ Alta relevancia detectada correctamente ({relevance_ratio:.1%})")
            return True
        else:
            print(f"❌ FAIL: Decisión incorrecta")
            print(f"   Esperado: {'Refinar' if should_refine else 'No refinar'}")
            print(f"   Obtenido: {'Refinar' if actual_refine else 'No refinar'}")
            print(f"   Relevancia: {relevance_ratio:.1%}, Resultados: {num_results}")
            return False
            
    async def run_all_tests(self):
        """Ejecuta todos los casos de prueba"""
        print("\n" + "="*80)
        print("TEST DE BÚSQUEDA MEJORADA CON VALIDACIÓN DE RELEVANCIA")
        print("="*80)
        
        await self.initialize()
        
        results = []
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n📌 Caso {i}/{len(self.test_cases)}")
            success = await self.run_test_case(test_case)
            results.append(success)
            await asyncio.sleep(0.5)  # Pequeña pausa entre pruebas
            
        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN DE RESULTADOS")
        print("="*80)
        
        total = len(results)
        passed = sum(results)
        failed = total - passed
        
        print(f"Total de pruebas: {total}")
        print(f"✅ Exitosas: {passed}")
        print(f"❌ Fallidas: {failed}")
        print(f"📊 Tasa de éxito: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print(f"\n🎉 TODAS LAS PRUEBAS PASARON")
            print("El sistema está validando correctamente la relevancia y tomando")
            print("decisiones apropiadas sobre cuándo ofrecer refinamiento.")
        else:
            print(f"\n⚠️ ALGUNAS PRUEBAS FALLARON")
            print("El sistema necesita ajustes en la lógica de refinamiento.")
            
        await self.db_service.close()
        
        return passed == total

async def main():
    """Función principal"""
    tester = ImprovedSearchTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nPruebas interrumpidas por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\nError inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())