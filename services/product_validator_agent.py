"""
Agente Validador de Productos
Este agente verifica que los productos encontrados realmente coincidan
con lo que el usuario está buscando, filtrando resultados irrelevantes.
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple
import aiohttp
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("env.agent")

logger = logging.getLogger(__name__)

class ProductValidatorAgent:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY no configurada en env.agent")
        else:
            logger.info(f"✅ API Key cargada correctamente (longitud: {len(self.api_key)})")
        
    async def validate_products(
        self, 
        user_request: str,
        products: List[Dict[str, Any]],
        max_products: int = 10
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Valida que los productos encontrados sean relevantes para la petición del usuario.
        
        Returns:
            - Lista de productos relevantes (máximo max_products)
            - Mensaje explicativo si no hay productos relevantes
        """
        
        if not products:
            return [], "No se encontraron productos."
            
        logger.info(f"🔍 Validando {len(products)} productos para: '{user_request}'")
        
        # Formatear productos para el análisis
        products_text = self._format_products_for_validation(products[:30])  # Analizar máximo 30
        
        prompt = f'''
Eres un experto en productos eléctricos validando resultados de búsqueda.

EL CLIENTE BUSCA: "{user_request}"

PRODUCTOS ENCONTRADOS:
{products_text}

TAREA CRÍTICA:
Identifica qué productos SÍ coinciden con lo que busca el cliente.

REGLAS ESTRICTAS:
1. Si busca "lámpara" o "iluminación":
   - SÍ incluir: lámparas, campanas, luminarias, bombillas, focos, proyectores
   - NO incluir: reguladores, minuteros, interruptores, accesorios PARA lámparas
2. Si busca "cable":
   - SÍ incluir: cables, mangueras, hilos conductores
   - NO incluir: herramientas para cables, canaletas, organizadores
3. Si busca "diferencial":
   - SÍ incluir: interruptores diferenciales, ID, llave diferencial
   - NO incluir: magnetotérmicos, PIAs, automáticos (a menos que sean diferenciales)
4. REGLA CRÍTICA: El producto debe SER lo que busca, no algo PARA lo que busca
   - "lámpara" != "regulador para lámpara"
   - "cable" != "cortador de cable"
5. Para uso industrial/fábrica/almacén:
   - Priorizar productos de alta potencia, industriales, profesionales

Responde con JSON:
{{
    "relevant_products": [1, 3, 5],  // IDs de productos que SÍ coinciden (máximo 10)
    "irrelevant_count": 25,  // Cuántos NO coinciden
    "explanation": "Encontré X lámparas industriales. Los demás eran reguladores y accesorios.",
    "search_quality": "good/poor",  // Calidad de los resultados
    "suggestion": "buscar 'campana industrial' para mejores resultados"  // Si hay mala calidad
}}
'''

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Eres un validador experto de productos. SIEMPRE respondes con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Muy baja para ser consistente
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"Error en validación: {error}")
                        return products[:max_products], ""
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    validation = json.loads(content)
                    
                    # Filtrar solo productos relevantes
                    relevant_ids = validation.get('relevant_products', [])
                    relevant_products = []
                    
                    for pid in relevant_ids[:max_products]:
                        if 0 <= pid < len(products):
                            relevant_products.append(products[pid])
                    
                    logger.info(f"✅ Validación completada:")
                    logger.info(f"   Relevantes: {len(relevant_products)}/{len(products)}")
                    logger.info(f"   Calidad: {validation.get('search_quality', 'unknown')}")
                    
                    # Si no hay productos relevantes, devolver mensaje explicativo
                    if not relevant_products:
                        if validation.get('suggestion'):
                            return [], f"No encontré exactamente lo que buscas. {validation.get('suggestion', '')}"
                        else:
                            return [], validation.get('explanation', 'No se encontraron productos relevantes.')
                    
                    # Si hay pocos resultados relevantes y muchos irrelevantes, avisar
                    if len(relevant_products) < 3 and validation.get('irrelevant_count', 0) > 20:
                        explanation = validation.get('explanation', '')
                        if explanation:
                            # Añadir explicación al primer producto como contexto
                            if relevant_products:
                                relevant_products[0]['_validation_note'] = explanation
                    
                    return relevant_products, validation.get('explanation', '')
                    
        except Exception as e:
            logger.error(f"Error validando productos: {e}")
            # En caso de error, devolver los primeros productos sin filtrar
            return products[:max_products], ""
    
    def _format_products_for_validation(self, products: List[Dict]) -> str:
        """Formatea productos para el análisis de la IA"""
        formatted = []
        for i, product in enumerate(products):
            title = product.get('title', 'Sin título')
            content_type = product.get('content_type', '')
            metadata = product.get('metadata', {})
            
            # Incluir información relevante
            desc = f"{i}. {title}"
            if metadata.get('category'):
                desc += f" | Categoría: {metadata['category']}"
            if metadata.get('brand'):
                desc += f" | Marca: {metadata['brand']}"
            if metadata.get('price'):
                desc += f" | €{metadata['price']}"
                
            formatted.append(desc)
            
        return "\n".join(formatted)

# Instancia singleton
product_validator = ProductValidatorAgent()