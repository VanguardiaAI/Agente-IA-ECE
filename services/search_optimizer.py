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
Analiza esta consulta de un cliente buscando productos eléctricos y extrae información para optimizar la búsqueda en base de datos.

CONSULTA DEL CLIENTE: "{user_query}"

Debes extraer:
1. search_terms: Lista de términos clave para buscar en la base de datos (sin palabras comunes)
2. product_type: Tipo principal de producto que busca
3. specific_features: Características específicas mencionadas (marca, modelo, capacidad, etc)
4. search_query: La mejor consulta de búsqueda optimizada para encontrar el producto
5. intent: La intención real del usuario en pocas palabras

IMPORTANTE:
- Para "termo eléctrico" debes entender que busca un calentador de agua eléctrico
- Para "ventilador industrial" debes mantener ambas palabras juntas
- Si menciona características como "multifix", "80 litros", etc, inclúyelas
- NO incluyas palabras como "quiero", "busco", "necesito", etc en search_terms

Responde SOLO en formato JSON:
{{
    "search_terms": ["término1", "término2"],
    "product_type": "tipo de producto",
    "specific_features": ["característica1", "característica2"],
    "search_query": "consulta optimizada completa",
    "intent": "descripción corta de lo que busca"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de consultas de productos eléctricos. Entiendes sinónimos y variaciones de productos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
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
                temperature=0.1,
                max_tokens=100,
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