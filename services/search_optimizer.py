"""
Servicio de optimización de búsqueda usando IA
Analiza la consulta del usuario y genera los mejores términos de búsqueda
"""

import os
from typing import List, Dict, Any, Tuple
import logging
from openai import AsyncOpenAI
import aiohttp
import json

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
Un cliente dice: "{user_query}"

INSTRUCCIONES IMPORTANTES:
1. CORRIGE errores ortográficos (ej: "temro" → "termo", "electrico" → "eléctrico")
2. IDENTIFICA el producto real que busca
3. GENERA términos de búsqueda que coincidan con nombres de catálogo

TRADUCCIONES CLAVE:
- "termo eléctrico" = CALENTADOR DE AGUA ELÉCTRICO (aparato para calentar agua)
- "diferencial" = INTERRUPTOR DIFERENCIAL
- "ventilador" = VENTILADOR (NO confundir con otros productos eléctricos)

Devuelve JSON:
{{
    "search_terms": ["calentador", "agua", "termo"],
    "product_type": "calentador de agua",
    "search_query": "calentador agua termo"
}}

REGLAS:
- NO incluir saludos ni verbos (hola/quiero/busco/necesito)
- SOLO términos del producto
- Si dice "termo" SIEMPRE incluir "calentador agua"
"""

        try:
            # Usar la Responses API para GPT-5
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "input": prompt,
                "reasoning": {
                    "effort": "minimal"  # Usar mínimo esfuerzo para respuestas rápidas
                },
                "text": {
                    "verbosity": "low"  # Respuestas concisas
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error en API: {response.status} - {error_text}")
                        raise ValueError(f"API error: {response.status}")
                    
                    result = await response.json()
                    logger.info(f"🔍 Response object: {result}")
                    
                    # Extraer el contenido de la respuesta GPT-5
                    content = ''
                    output = result.get('output', [])
                    if output and len(output) > 1:
                        message = output[1]  # El mensaje es el segundo elemento
                        if message.get('type') == 'message' and message.get('content'):
                            content_array = message.get('content', [])
                            if content_array and isinstance(content_array, list):
                                # Extraer el texto del primer elemento de contenido
                                for content_item in content_array:
                                    if content_item.get('type') == 'output_text':
                                        content = content_item.get('text', '')
                                        break
                    
                    logger.info(f"📝 Respuesta de IA: '{content[:200]}...' (truncada)" if len(content) > 200 else f"📝 Respuesta de IA: '{content}'")
                    
                    if not content:
                        logger.warning("Respuesta vacía, usando fallback")
                        raise ValueError("Empty response")
                    
                    try:
                        # Intentar parsear como JSON
                        parsed = json.loads(content)
                        
                        # Asegurar que tiene la estructura esperada
                        return {
                            "search_terms": parsed.get("search_terms", user_query.lower().split()),
                            "product_type": parsed.get("product_type", "producto"),
                            "specific_features": parsed.get("specific_features", []),
                            "search_query": parsed.get("search_query", user_query),
                            "intent": parsed.get("intent", f"buscar {parsed.get('product_type', 'producto')}")
                        }
                    except json.JSONDecodeError:
                        # Si no es JSON, tratar como texto plano
                        logger.info("Respuesta no es JSON, procesando como texto")
                        terms = [term.strip() for term in content.split(',') if term.strip()]
                        
                        return {
                            "search_terms": terms if terms else user_query.lower().split(),
                            "product_type": "producto",
                            "specific_features": [],
                            "search_query": ' '.join(terms) if terms else user_query,
                            "intent": "buscar producto"
                        }
            
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

IMPORTANTE: Si busca "termo eléctrico" quiere CALENTADORES DE AGUA, NO otros productos eléctricos.

Productos encontrados:
{self._format_products_for_analysis(products[:20])}

Selecciona SOLO los {limit} productos que coincidan con lo que busca el cliente.
- Si busca "termo eléctrico": SOLO calentadores de agua/termos
- Si busca "ventilador": SOLO ventiladores
- NO incluir productos no relacionados aunque tengan "eléctrico"

Responde con JSON: {{"product_ids": ["id1", "id2", "id3"]}}
"""

        try:
            # Usar la Responses API para GPT-5
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "input": prompt,
                "reasoning": {
                    "effort": "minimal"
                },
                "text": {
                    "verbosity": "low"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error en API: {response.status} - {error_text}")
                        return products[:limit]
                    
                    result = await response.json()
                    
                    # Extraer el contenido de la respuesta GPT-5
                    content = ''
                    output = result.get('output', [])
                    if output and len(output) > 1:
                        message = output[1]
                        if message.get('type') == 'message' and message.get('content'):
                            content_array = message.get('content', [])
                            if content_array and isinstance(content_array, list):
                                for content_item in content_array:
                                    if content_item.get('type') == 'output_text':
                                        content = content_item.get('text', '')
                                        break
                    
                    logger.info(f"📝 Respuesta optimización: {content[:200]}...' (truncada)" if len(content) > 200 else f"📝 Respuesta optimización: {content}")
                    
                    if not content:
                        return products[:limit]
                    
                    try:
                        parsed = json.loads(content)
                        selected_ids = parsed.get("product_ids", [])
                        
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
                    except json.JSONDecodeError:
                        logger.error("Error parseando respuesta como JSON")
                        return products[:limit]
            
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