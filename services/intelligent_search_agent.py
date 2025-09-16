"""
Agente Inteligente de Búsqueda
Este agente usa IA para entender CUALQUIER petición del usuario y convertirla
en la búsqueda óptima para encontrar productos en la base de datos.

FILOSOFÍA: La IA hace el trabajo pesado de entender al usuario,
no necesitamos lógica rígida ni casos especiales.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("env.agent")

logger = logging.getLogger(__name__)

class IntelligentSearchAgent:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"  # Modelo rápido y eficiente
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY no configurada en env.agent")
        
    async def understand_user_request(self, user_message: str) -> Dict[str, Any]:
        """
        Entiende CUALQUIER petición del usuario y la convierte en una búsqueda estructurada.
        No hay casos especiales, no hay lógica rígida, solo IA entendiendo al usuario.
        """
        
        logger.info("=" * 60)
        logger.info("🤖 AGENTE INTELIGENTE ACTIVADO")
        logger.info(f"📝 Analizando: '{user_message}'")
        logger.info("=" * 60)
        
        prompt = f'''
Eres un experto en productos eléctricos de la tienda El Corte Eléctrico.
Tu trabajo es entender lo que el cliente quiere y convertirlo en la búsqueda perfecta.

PETICIÓN DEL CLIENTE: "{user_message}"

CONOCIMIENTO DE LA TIENDA:
Vendemos productos eléctricos como:
- Protecciones: diferenciales, magnetotérmicos (automáticos/PIA), fusibles
- Cables: mangueras, hilos, enrollacables  
- Iluminación: lámparas, bombillas, campanas industriales, proyectores
- Calefacción: termos, calentadores, radiadores, toalleros
- Comunicación: porteros, videoporteros, telefonillos
- Industrial: transformadores, contactores, variadores
- Accesorios: bridas, canaletas, cajas, tubos

SINÓNIMOS IMPORTANTES (el cliente puede usar cualquiera):
- "automático" = magnetotérmico, PIA, disyuntor
- "diferencial" = llave diferencial, protección de personas
- "fusibles" = plomos, cortacircuitos
- "lámpara para fábrica/nave" = campana industrial, luminaria industrial
- "termo" = calentador de agua
- "recoge cables" = enrollacables, organizador cables
- "cintillos" = bridas, abrazaderas
- "ladrón" = regleta, prolongador
- "casquillo" = portalámparas
- "telefonillo" = portero, intercomunicador

MARCAS QUE VENDEMOS:
Schneider, Legrand, Simon, Jung, ABB, Siemens, Hager, Chint, Gave, Orbis, Toscano

ANALIZA la petición y devuelve:
{{
    "search_query": "la mejor query para buscar en la BD (incluye sinónimos)",
    "product_type": "tipo de producto que busca",
    "brand": "marca si la menciona o null",
    "specifications": {{
        "amperaje": "16A" (si lo menciona),
        "voltaje": "230V" (si lo menciona),
        "sensibilidad": "30mA" (para diferenciales),
        "polos": "2P" (si lo menciona),
        "potencia": "2000W" (si lo menciona),
        "otros": "cualquier otra especificación"
    }},
    "intent": "comprar/consultar_precio/verificar_stock/comparar",
    "context": "uso doméstico/industrial/comercial (si lo menciona)",
    "original_request": "lo que pidió el cliente limpio de saludos"
}}

REGLAS CRÍTICAS:
1. IGNORA COMPLETAMENTE estas palabras de transición/confirmación:
   - "bien", "ok", "vale", "perfecto", "genial", "ahora", "también", "además"
   - "hola", "por favor", "gracias", "buenos días", "buenas tardes"
2. Si el mensaje empieza con "bien, ahora quiero..." → IGNORA "bien, ahora" y enfócate en lo que quiere
3. NUNCA uses palabras de transición como término de búsqueda
4. EXTRAE solo el PRODUCTO REAL que busca el usuario
5. Si no hay un producto claro, devuelve search_query vacía
6. EXPANDE con sinónimos relevantes del sector
7. Para uso industrial/fábrica/almacén: priorizar productos industriales

EJEMPLOS:

Cliente: "hola quiero un diferencial para un local comercial"
Respuesta: {{
    "search_query": "diferencial interruptor diferencial llave diferencial 30mA 300mA comercial",
    "product_type": "diferencial",
    "brand": null,
    "specifications": {{}},
    "intent": "comprar",
    "context": "comercial",
    "original_request": "diferencial para local comercial"
}}

Cliente: "necesito un automático de 16A schneider"
Respuesta: {{
    "search_query": "magnetotérmico automático PIA 16A schneider",
    "product_type": "magnetotérmico",
    "brand": "schneider",
    "specifications": {{"amperaje": "16A"}},
    "intent": "comprar",
    "context": null,
    "original_request": "automático 16A schneider"
}}

Cliente: "lámpara para una nave industrial"
Respuesta: {{
    "search_query": "campana industrial luminaria industrial proyector industrial alto bay LED nave",
    "product_type": "iluminación industrial",
    "brand": null,
    "specifications": {{}},
    "intent": "comprar",
    "context": "industrial",
    "original_request": "lámpara para nave industrial"
}}

Cliente: "bien, ahora quiero un ventilador también para fábrica"
Respuesta: {{
    "search_query": "ventilador industrial extractor aire fábrica nave",
    "product_type": "ventilador industrial",
    "brand": null,
    "specifications": {{}},
    "intent": "comprar",
    "context": "industrial",
    "original_request": "ventilador para fábrica"
}}

Cliente: "ok perfecto"
Respuesta: {{
    "search_query": "",
    "product_type": null,
    "brand": null,
    "specifications": {{}},
    "intent": "confirmación",
    "context": null,
    "original_request": "confirmación"
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
                    {"role": "system", "content": "Eres un experto analizador de peticiones de productos eléctricos. SIEMPRE respondes con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Baja temperatura para respuestas consistentes
                "max_tokens": 500,
                "response_format": {"type": "json_object"}  # Forzar respuesta JSON
            }
            
            logger.info(f"🚀 Llamando a OpenAI API con modelo: {self.model}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"Error en OpenAI API: {error}")
                        return self._fallback_analysis(user_message)
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    try:
                        analysis = json.loads(content)
                        logger.info(f"✨ Análisis inteligente completado:")
                        logger.info(f"   Query: {analysis.get('search_query')}")
                        logger.info(f"   Tipo: {analysis.get('product_type')}")
                        logger.info(f"   Marca: {analysis.get('brand')}")
                        return analysis
                    except json.JSONDecodeError:
                        logger.error(f"Error parseando JSON: {content}")
                        return self._fallback_analysis(user_message)
                        
        except Exception as e:
            logger.error(f"Error en análisis inteligente: {e}")
            return self._fallback_analysis(user_message)
    
    def _fallback_analysis(self, user_message: str) -> Dict[str, Any]:
        """
        Análisis básico de fallback si falla la IA
        """
        # Eliminar saludos comunes
        message = user_message.lower()
        for greeting in ['hola', 'buenos días', 'buenas tardes', 'por favor', 'gracias']:
            message = message.replace(greeting, '').strip()
        
        return {
            "search_query": message,
            "product_type": "producto",
            "brand": None,
            "specifications": {},
            "intent": "comprar",
            "context": None,
            "original_request": message
        }
    
    async def should_refine_results(
        self, 
        results: List[Dict],
        user_analysis: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Decide si los resultados necesitan refinamiento.
        Usa IA para tomar decisiones inteligentes, no reglas rígidas.
        """
        
        if not results:
            return False, None
            
        if len(results) <= 5:
            # Pocos resultados, no necesita refinamiento
            return False, None
            
        if len(results) <= 10 and user_analysis.get('brand'):
            # Si especificó marca y hay pocos resultados, mostrar todos
            return False, None
            
        # Para muchos resultados, preguntar a la IA qué hacer
        prompt = f'''
El cliente busca: {user_analysis.get('original_request')}
Encontramos {len(results)} productos.

Los primeros 5 son:
{self._format_results_for_ai(results[:5])}

¿Debemos refinar la búsqueda o mostrar estos resultados?

Si hay que refinar, sugiere UNA pregunta corta y clara para el cliente.
Por ejemplo:
- "¿De qué marca lo prefieres? Tenemos: Schneider, Legrand, Simon"
- "¿Qué amperaje necesitas? Disponibles: 10A, 16A, 25A"
- "¿Para uso doméstico o industrial?"

Responde con JSON:
{{
    "needs_refinement": true/false,
    "refinement_message": "pregunta al cliente" o null
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
                    {"role": "system", "content": "Eres un asistente de ventas experto. Decides si mostrar productos o hacer una pregunta para refinar."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 200,
                "response_format": {"type": "json_object"}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        decision = json.loads(content)
                        
                        return (
                            decision.get('needs_refinement', False),
                            decision.get('refinement_message')
                        )
                        
        except Exception as e:
            logger.error(f"Error decidiendo refinamiento: {e}")
            
        # Fallback: si hay muchos resultados, sugerir refinamiento básico
        if len(results) > 15:
            return True, f"Encontré {len(results)} opciones. ¿Podrías ser más específico sobre lo que necesitas?"
        
        return False, None
    
    def _format_results_for_ai(self, results: List[Dict]) -> str:
        """Formatea resultados para el análisis de la IA"""
        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get('title', 'Sin título')
            price = r.get('metadata', {}).get('price', 'Sin precio')
            formatted.append(f"{i}. {title} - {price}")
        return "\n".join(formatted)

# Instancia singleton
intelligent_search = IntelligentSearchAgent()