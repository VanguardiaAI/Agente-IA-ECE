"""
Servicio de optimización de búsqueda usando IA
Analiza la consulta del usuario y genera los mejores términos de búsqueda
"""

import os
from typing import List, Dict, Any, Tuple
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class SearchOptimizer:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-5-mini"  # Modelo económico para análisis rápido
        
    async def analyze_product_query(self, user_query: str) -> Dict[str, Any]:
        """
        Analiza la consulta del usuario y extrae:
        - Términos de búsqueda optimizados
        - Tipo de producto
        - Características específicas
        - Intención real del usuario
        """
        
        prompt = f"""
Eres un experto en productos eléctricos. Un cliente dice: "{user_query}"

Tu tarea es entender QUÉ producto está buscando realmente y generar la MEJOR consulta de búsqueda para encontrarlo en una base de datos de productos.

PROCESO DE ANÁLISIS:
1. Identifica el producto real que busca (no te quedes con las palabras literales)
2. Piensa en cómo ese producto aparecería en un catálogo de tienda
3. Genera términos de búsqueda que coincidan con nombres reales de productos

EJEMPLOS DE ANÁLISIS:
- "quiero un termo eléctrico" → El cliente busca un CALENTADOR DE AGUA ELÉCTRICO o TERMO ELÉCTRICO (aparato para calentar agua)
- "necesito un ventilador de pared" → Busca un VENTILADOR DE PARED (no un ventilador de techo ni portátil)
- "busco un diferencial" → Busca un INTERRUPTOR DIFERENCIAL o DIFERENCIAL (protección eléctrica)

Para la consulta actual, genera:
{{
    "search_terms": [lista de palabras clave que aparecerían en el nombre del producto],
    "product_type": "categoría específica del producto",
    "specific_features": [características mencionadas como marca, capacidad, etc],
    "search_query": "la consulta optimizada que buscarías en el catálogo",
    "intent": "qué producto busca realmente el cliente"
}}

REGLAS:
- NO incluyas verbos como quiero/busco/necesito
- SÍ incluye el nombre real del producto como aparecería en una tienda
- Si el cliente usa términos coloquiales, tradúcelos al nombre técnico/comercial
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de consultas de productos eléctricos. Entiendes sinónimos y variaciones de productos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_completion_tokens=200,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ Análisis de búsqueda: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error en análisis de búsqueda: {e}")
            # Fallback básico
            return {
                "search_terms": user_query.lower().split(),
                "product_type": "producto",
                "specific_features": [],
                "search_query": user_query,
                "intent": "buscar producto"
            }
    
    async def optimize_search_results(self, user_query: str, products: List[Dict], limit: int = 5) -> List[Dict]:
        """
        Re-ordena y filtra los resultados según la relevancia real para el usuario
        """
        if not products:
            return products
            
        # Si hay pocos productos, no es necesario optimizar
        if len(products) <= limit:
            return products
            
        prompt = f"""
El cliente busca: "{user_query}"

Aquí están los productos encontrados:
{self._format_products_for_analysis(products[:20])}  # Analizar máximo 20

Selecciona los {limit} productos MÁS RELEVANTES para lo que busca el cliente.
Considera:
- Coincidencia exacta con lo que pide
- Características mencionadas (capacidad, marca, etc)
- Relevancia real vs coincidencias parciales de palabras

Responde SOLO con los IDs de los productos más relevantes en orden de relevancia.
Formato JSON: {{"product_ids": ["id1", "id2", "id3", ...]}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en productos eléctricos que ayuda a encontrar exactamente lo que el cliente necesita."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_completion_tokens=100,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            selected_ids = result.get("product_ids", [])
            
            # Reordenar productos según la selección de la IA
            ordered_products = []
            for product_id in selected_ids:
                for product in products:
                    if str(product.get('id')) == str(product_id) or str(product.get('external_id')) == str(product_id):
                        ordered_products.append(product)
                        break
            
            # Si no se encontraron todos, agregar los primeros como fallback
            if len(ordered_products) < limit:
                for product in products:
                    if product not in ordered_products:
                        ordered_products.append(product)
                        if len(ordered_products) >= limit:
                            break
            
            return ordered_products[:limit]
            
        except Exception as e:
            logger.error(f"Error optimizando resultados: {e}")
            return products[:limit]
    
    def _format_products_for_analysis(self, products: List[Dict]) -> str:
        """Formatea productos para el análisis de la IA"""
        formatted = []
        for p in products:
            # Usar external_id si está disponible, sino usar id
            product_id = p.get('external_id', p.get('id', 'unknown'))
            title = p.get('title', 'Sin título')
            metadata = p.get('metadata', {})
            price = metadata.get('price', 'N/A')
            
            formatted.append(f"ID: {product_id} | {title} | Precio: {price}")
        
        return "\n".join(formatted)

# Instancia singleton
search_optimizer = SearchOptimizer()