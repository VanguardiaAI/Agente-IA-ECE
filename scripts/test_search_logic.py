#!/usr/bin/env python3
"""
Script para probar la lógica de búsqueda mejorada sin base de datos
Simula los datos y prueba las funciones de clasificación y boost
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import HYBRID_SEARCH_CONFIG

# Simulación de la clase de base de datos para probar lógica
class MockHybridDatabaseService:
    def __init__(self):
        self._technical_terms_cache = {}
        self._search_cache = {}
        self._cache_max_size = 500

    def _classify_search_query(self, query_text: str) -> str:
        """Clasificar el tipo de consulta para optimizar la búsqueda"""
        query_lower = query_text.lower().strip()
        
        # Detectar búsquedas exactas/técnicas
        if any(pattern in query_lower for pattern in [
            'c10', 'c16', 'c20', 'c25', 'c32', 'c40', 'c50', 'c63',  # Curvas
            'dpn', 'pia', 'magnetotermico', 'diferencial',  # Automáticos
            'led', 'ip65', 'ip44', 'ip20',  # Códigos técnicos
            '220v', '12v', '24v', '230v',  # Voltajes
            '10a', '16a', '20a', '25a', '32a',  # Amperajes
            '30ma', '300ma',  # Sensibilidades
            '1.5mm', '2.5mm', '4mm', '6mm'  # Secciones
        ]):
            return 'technical'
        
        # Detectar búsquedas de códigos/modelos específicos
        import re
        if re.search(r'\b[A-Z]{2,}[0-9]*\b|\b\d+[WAV]?\b|\b[A-Z0-9]+-[A-Z0-9]+\b', query_text):
            return 'exact'
        
        # Detectar búsquedas semánticas (preguntas o descripciones)
        semantic_indicators = [
            'necesito', 'busco', 'quiero', 'para', 'como', 'que', 'donde',
            'cuanto', 'cual', 'ayuda', 'recomienda', 'mejor', 'sirve'
        ]
        if any(word in query_lower for word in semantic_indicators):
            return 'semantic'
        
        # Por defecto, búsqueda mixta
        return 'mixed'

    def _apply_commercial_boost(self, result: dict) -> dict:
        """Aplicar boost comercial basado en stock, precio, etc."""
        try:
            metadata = result.get('metadata', {})
            current_score = float(result.get('rrf_score', 0))
            
            # Boost por stock disponible
            if metadata.get('stock_status') == 'instock':
                current_score *= HYBRID_SEARCH_CONFIG["stock_boost_factor"]
            
            # Boost por producto destacado
            if metadata.get('featured', False):
                current_score *= HYBRID_SEARCH_CONFIG["popularity_boost_factor"]
            
            # Penalización leve por productos sin precio
            if not metadata.get('price', 0):
                current_score *= 0.9
            
            result['rrf_score'] = current_score
            return result
            
        except Exception as e:
            print(f"❌ Error aplicando boost comercial: {e}")
            return result

def test_query_classification():
    """Probar clasificación de consultas"""
    print("🔍 PRUEBA DE CLASIFICACIÓN DE CONSULTAS")
    print("=" * 50)
    
    mock_db = MockHybridDatabaseService()
    
    test_queries = [
        # Técnicas
        ("automatico C16", "technical"),
        ("diferencial 25A 30mA", "technical"),
        ("LED E27 9W", "technical"),
        ("cable 2.5mm", "technical"),
        
        # Exactas
        ("DPN123", "exact"),
        ("IP65", "exact"),
        ("220V", "exact"),
        
        # Semánticas
        ("necesito bombillas para sala", "semantic"),
        ("busco proteccion para casa", "semantic"),
        ("que iluminacion recomiendas", "semantic"),
        
        # Mixtas
        ("interruptor automatico", "mixed"),
        ("lampara led", "mixed"),
        ("enchufes", "mixed")
    ]
    
    for query, expected in test_queries:
        result = mock_db._classify_search_query(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{query}' → {result} (esperado: {expected})")

def test_commercial_boost():
    """Probar boost comercial"""
    print("\n💰 PRUEBA DE BOOST COMERCIAL")
    print("=" * 50)
    
    mock_db = MockHybridDatabaseService()
    
    # Productos de prueba
    test_products = [
        {
            'title': 'Producto sin stock',
            'rrf_score': 10.0,
            'metadata': {'stock_status': 'outofstock', 'price': 25.0}
        },
        {
            'title': 'Producto con stock',
            'rrf_score': 10.0,
            'metadata': {'stock_status': 'instock', 'price': 25.0}
        },
        {
            'title': 'Producto destacado',
            'rrf_score': 10.0,
            'metadata': {'stock_status': 'instock', 'price': 25.0, 'featured': True}
        },
        {
            'title': 'Producto sin precio',
            'rrf_score': 10.0,
            'metadata': {'stock_status': 'instock', 'price': 0}
        }
    ]
    
    for product in test_products:
        original_score = product['rrf_score']
        boosted = mock_db._apply_commercial_boost(product.copy())
        new_score = boosted['rrf_score']
        boost_factor = new_score / original_score
        
        print(f"{product['title']:<20} | Score: {original_score:.1f} → {new_score:.1f} (x{boost_factor:.2f})")

def test_search_simulation():
    """Simular búsqueda completa"""
    print("\n🎯 SIMULACIÓN DE BÚSQUEDA COMPLETA")
    print("=" * 50)
    
    mock_db = MockHybridDatabaseService()
    
    # Productos simulados de WooCommerce
    wc_products = [
        {
            'title': 'Automático DPN C16 25A Schneider',
            'rrf_score': 80.0,
            'source': 'woocommerce',
            'metadata': {'stock_status': 'instock', 'price': 45.0}
        },
        {
            'title': 'Automático C16 20A ABB',
            'rrf_score': 75.0,
            'source': 'woocommerce',
            'metadata': {'stock_status': 'instock', 'price': 38.0}
        }
    ]
    
    # Productos simulados de búsqueda híbrida
    hybrid_products = [
        {
            'title': 'Magnetotérmico C16 Legrand',
            'rrf_score': 12.0,
            'source': 'hybrid',
            'metadata': {'stock_status': 'instock', 'price': 42.0, 'featured': True}
        },
        {
            'title': 'Disyuntor automático 16A',
            'rrf_score': 8.0,
            'source': 'hybrid',
            'metadata': {'stock_status': 'outofstock', 'price': 35.0}
        }
    ]
    
    query = "automatico C16"
    query_type = mock_db._classify_search_query(query)
    
    print(f"Consulta: '{query}' (Tipo: {query_type})")
    print()
    
    # Aplicar boost según tipo de consulta
    boost_factor = (HYBRID_SEARCH_CONFIG["exact_match_weight"] 
                    if query_type in ['exact', 'technical'] 
                    else HYBRID_SEARCH_CONFIG["semantic_match_weight"])
    
    print(f"WooCommerce (boost x{boost_factor}):")
    for product in wc_products:
        original_score = product['rrf_score']
        product['rrf_score'] = original_score * boost_factor
        boosted = mock_db._apply_commercial_boost(product)
        print(f"  • {product['title']:<30} | Score: {original_score:.1f} → {boosted['rrf_score']:.1f}")
    
    print(f"\nBúsqueda Híbrida:")
    for product in hybrid_products:
        boosted = mock_db._apply_commercial_boost(product)
        print(f"  • {product['title']:<30} | Score: {product['rrf_score']:.1f} → {boosted['rrf_score']:.1f}")
    
    # Combinar y ordenar resultados
    all_products = wc_products + hybrid_products
    all_products.sort(key=lambda x: x['rrf_score'], reverse=True)
    
    print(f"\nResultados finales ordenados:")
    for i, product in enumerate(all_products, 1):
        source_icon = "🎯" if product['source'] == "woocommerce" else "🔍"
        print(f"  {i}. {source_icon} {product['title']:<30} | Score: {product['rrf_score']:.1f}")

def test_configuration():
    """Mostrar configuración actual"""
    print("\n⚙️ CONFIGURACIÓN ACTUAL")
    print("=" * 50)
    
    for key, value in HYBRID_SEARCH_CONFIG.items():
        print(f"{key:<25} = {value}")

def main():
    """Función principal"""
    print("🚀 PRUEBAS DE LÓGICA DE BÚSQUEDA MEJORADA")
    print("=" * 60)
    
    test_configuration()
    test_query_classification()
    test_commercial_boost()
    test_search_simulation()
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("=" * 60)

if __name__ == "__main__":
    main()