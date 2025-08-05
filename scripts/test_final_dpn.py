#!/usr/bin/env python3
"""
Script de prueba final para verificar búsqueda de DPN
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service

async def test_dpn_search():
    """Probar búsqueda de DPN con el sistema mejorado"""
    try:
        # Inicializar base de datos
        await db_service.initialize()
        print("✅ Base de datos inicializada\n")
        
        # Simulación de búsqueda "diferencial DPN"
        query_text = "diferencial DPN"
        
        # Detectar términos técnicos
        technical_terms = db_service._extract_technical_terms(query_text)
        print(f"🔍 Query: '{query_text}'")
        print(f"🔧 Términos técnicos detectados: {technical_terms}")
        print("="*70)
        
        # Simular búsqueda directa de términos técnicos
        async with db_service.pool.acquire() as conn:
            all_results = {}
            
            # Buscar productos con términos técnicos
            if technical_terms:
                for term in technical_terms:
                    # Ignorar palabras comunes
                    if term.lower() in ['busco', 'quiero', 'necesito', 'un', 'una', 'el', 'la']:
                        continue
                    
                    print(f"\n📌 Buscando productos con término '{term}'...")
                    
                    # Búsqueda en título
                    query = """
                        SELECT id, title, metadata
                        FROM knowledge_base 
                        WHERE is_active = true 
                        AND content_type = 'product'
                        AND UPPER(title) LIKE '%' || UPPER($1) || '%'
                        ORDER BY title
                        LIMIT 20
                    """
                    
                    rows = await conn.fetch(query, term)
                    print(f"   ✅ Encontrados {len(rows)} productos con '{term}' en título")
                    
                    if rows:
                        print("   Primeros 5:")
                        for i, row in enumerate(rows[:5], 1):
                            print(f"      {i}. {row['title']}")
                    
                    for row in rows:
                        if row['id'] not in all_results:
                            all_results[row['id']] = {
                                'title': row['title'],
                                'score': 1000.0,  # Score alto para coincidencias exactas
                                'match_type': 'exact_title',
                                'term': term
                            }
            
            # Mostrar resumen
            print("\n" + "="*70)
            print("📊 RESUMEN DE RESULTADOS")
            print("="*70)
            
            if all_results:
                print(f"\n✅ Total de productos con términos técnicos: {len(all_results)}")
                print("\nTop 10 productos (ordenados por score):")
                
                # Ordenar por score
                sorted_results = sorted(all_results.values(), key=lambda x: x['score'], reverse=True)
                
                for i, result in enumerate(sorted_results[:10], 1):
                    has_dpn = 'DPN' in result['title'].upper()
                    dpn_indicator = "✅ [DPN]" if has_dpn else "❌ [NO DPN]"
                    print(f"{i:2}. {dpn_indicator} {result['title']}")
                    print(f"     Score: {result['score']:.0f} | Tipo: {result['match_type']} | Término: {result['term']}")
            else:
                print("❌ No se encontraron productos con los términos técnicos")
        
        # Verificar específicamente productos con DPN
        print("\n" + "="*70)
        print("🔍 VERIFICACIÓN ESPECÍFICA DE PRODUCTOS CON DPN")
        print("="*70)
        
        async with db_service.pool.acquire() as conn:
            query = """
                SELECT COUNT(*) as total
                FROM knowledge_base 
                WHERE is_active = true 
                AND content_type = 'product'
                AND UPPER(title) LIKE '%DPN%'
            """
            
            result = await conn.fetchrow(query)
            total_dpn = result['total']
            
            print(f"\n📈 Estadísticas:")
            print(f"   - Total de productos con 'DPN' en título: {total_dpn}")
            print(f"   - Productos encontrados por búsqueda: {len([r for r in all_results.values() if 'DPN' in r['title'].upper()])}")
            
            if total_dpn > 0 and len(all_results) > 0:
                dpn_found = len([r for r in all_results.values() if 'DPN' in r['title'].upper()])
                percentage = (dpn_found / total_dpn) * 100
                print(f"   - Efectividad: {percentage:.1f}% de productos DPN encontrados")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_dpn_search())