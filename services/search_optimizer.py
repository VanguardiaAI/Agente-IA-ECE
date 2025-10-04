"""
Servicio de optimización de búsqueda usando IA
Analiza la consulta del usuario y genera los mejores términos de búsqueda
"""

import os
from typing import List, Dict, Any, Tuple
import logging
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
import aiohttp
import json

logger = logging.getLogger(__name__)

class SearchOptimizer:
    def __init__(self):
        self.gpt5 = GPT5Client()
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
Un cliente de una tienda eléctrica dice: "{user_query}"

ANALIZA qué producto busca y genera términos de búsqueda optimizados.

DETECCIÓN DE REFERENCIAS SKU:
- Los electricistas profesionales a menudo buscan por referencia/SKU
- Ejemplos de búsquedas con SKU:
  - "Quiero el producto con referencia 10004922"
  - "Busco la ref 1232234234"
  - "Necesito el SKU A58K004"
  - "10004922" (solo el número)
- Si detectas números largos (6+ dígitos) o códigos alfanuméricos que parecen referencias, inclúyelos en detected_sku
- Las referencias pueden aparecer después de palabras como: referencia, ref, sku, código, modelo

IMPORTANTE - Equivalencias y sinónimos del sector eléctrico (proporcionados por el cliente):

PROTECCIONES ELÉCTRICAS:
- "automático/automáticos" → "magnetotérmico", "PIA", "disyuntor", "interruptor automático"
- "diferencial" → "llave diferencial", "protección de personas", "interruptor diferencial"
- "fusibles" → "plomos", "cortacircuitos"
- "superinmunizado" → "diferencial HPI", "diferencial FSI", "diferencial SI", "diferencial B-SI", "diferencial A-SI"

CABLES Y CONEXIONES:
- "cable" → "hilo", "manguera", "conductor", "cable eléctrico"
- "clema" → "regleta", "borna", "conector cable", "regleta borne"
- "bridas" → "fleje", "cintillo", "chincho", "abrazadera", "precinto", "cintillos"
- "regleta" → "ladrón", "prolongador", "base múltiple"
- "recoge cables" → "enrollacables", "organizador cables", "portacables", "recogecables"
- "enrollacables" → "recoge cables", "bobina cable", "carrete cable"

ILUMINACIÓN:
- "lámpara" → "bombilla", "foco", "luz", "bombillo", "luminaria"
- "portalámparas" → "casquillo", "socket"
- "lámpara para fábrica/industrial/nave" → "campana industrial", "luminaria industrial", "proyector", "alto bay"

CALEFACCIÓN Y AGUA:
- "termo/termos" → "calentador de agua", "termo eléctrico"
- "caldera/calderas" → "calentador"
- "calefactor" → "radiador eléctrico", "estufa", "calentador de baño"
- "emisores térmicos" → "radiador eléctrico", "radiador de inercia térmica"
- "convector" → "radiador de aire", "radiador por convección"
- "termoventilador" → "estufa con ventilador", "calentador con ventilador"
- "toallero/toalleros" → "secatoallas", "radiador toallero"

COMUNICACIÓN:
- "portero" → "telefonillo", "auricular", "intercomunicador"
- "videoportero" → "telefonillo con cámara", "visor de puerta"

INDUSTRIAL:
- "cetac" → "conector industrial", "enchufe industrial", "base industrial"
- "control de nivel" → "boya", "flotador"
- "transformador" → "trafo"
- "estabilizador" → "regulador de voltaje", "controlador de voltaje", "afianzador"
- "estanco" → "hermético", "impermeable"
- "estanqueidad" → "IP", "grado de protección"
- "arco eléctrico" → "apaga chispas", "ARC"

CONFIGURACIONES:
- "unipolar" → "1P"
- "bipolar" → "2P", "1+N"
- "tripolar" → "3P"
- "tetrapolar" → "4P", "3+N"
- "miliamperios" → "mA"

Devuelve JSON con términos de búsqueda ampliados:
{{
    "search_terms": ["término principal", "sinónimos relevantes"],
    "product_type": "tipo de producto",
    "search_query": "consulta optimizada para búsqueda",
    "detected_sku": "referencia SKU si se detecta, o null si no hay"
}}

Ejemplos:
- Usuario: "necesito un automático de 16A"
- Respuesta: {{"search_terms": ["automático", "magnetotérmico", "PIA", "disyuntor", "16A"], "product_type": "protección eléctrica", "search_query": "magnetotérmico PIA 16A automático", "detected_sku": null}}

- Usuario: "Quiero el producto con referencia 10004922"
- Respuesta: {{"search_terms": ["10004922"], "product_type": "producto específico", "search_query": "10004922", "detected_sku": "10004922"}}

- Usuario: "busco la ref A58K004 que es un diferencial"
- Respuesta: {{"search_terms": ["A58K004", "diferencial"], "product_type": "protección eléctrica", "search_query": "A58K004 diferencial", "detected_sku": "A58K004"}}

REGLAS:
- EXPANDE la búsqueda con sinónimos técnicos del sector
- INCLUYE términos alternativos que se usan para el mismo producto
- CORRIGE typos evidentes
- NO incluir saludos ni verbos (hola/quiero/busco)
"""

        try:
            # Usar GPT5Client con Responses API
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.MINIMAL,
                verbosity=Verbosity.LOW
            )
            
            content = response.content
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
            # Usar GPT5Client con Responses API
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.MINIMAL,
                verbosity=Verbosity.LOW
            )
            
            content = response.content
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