"""
Analizador de búsqueda de productos usando GPT-5
Analiza qué busca el usuario y determina si necesita más información
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
from .synonym_manager import synonym_manager

logger = logging.getLogger(__name__)


@dataclass
class SearchAnalysis:
    """Resultado del análisis de búsqueda"""
    has_enough_info: bool
    missing_info: List[str]
    extracted_specs: Dict[str, Any]
    product_type: str
    brand: Optional[str]
    technical_specs: Dict[str, Any]
    clarification_needed: Optional[str]
    confidence: float
    synonyms_found: List[str]


class SearchAnalyzer:
    """Analiza búsquedas de productos con inteligencia contextual"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.model = "gpt-5"  # USAR GPT-5 PARA ANÁLISIS COMPLEJO
        self.synonym_manager = synonym_manager
        
    async def analyze_search(
        self, 
        query: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> SearchAnalysis:
        """
        Analiza una búsqueda de productos determinando si tiene información suficiente
        
        Args:
            query: Consulta del usuario
            context: Historial de conversación
            
        Returns:
            SearchAnalysis con el análisis completo
        """
        
        # Cargar sinónimos si no están cargados
        if not self.synonym_manager.loaded:
            self.synonym_manager.load_synonyms()
        
        # Buscar sinónimos en la consulta
        found_synonyms = []
        query_words = query.lower().split()
        for word in query_words:
            syns = self.synonym_manager.get_synonyms(word)
            if syns:
                found_synonyms.extend(syns[:2])  # Primeros 2 sinónimos
        
        # Contexto para el prompt
        context_str = ""
        if context:
            context_str = "\nHistorial reciente:\n"
            for msg in context[-3:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                context_str += f"{role}: {content}\n"
        
        # Construir prompt
        base_prompt = """Eres un experto vendedor en una tienda de MATERIAL ELÉCTRICO (El Corte Eléctrico).

CONTEXTO: Esta es una tienda especializada en productos eléctricos para instalaciones:
- Protección eléctrica (automáticos, diferenciales, fusibles)
- Cableado e instalación (cables, canalizaciones, cajas)
- Iluminación (lámparas, luminarias, proyectores)
- Mecanismos (enchufes, interruptores, bases)
- Climatización y ventilación
- Herramientas y equipos de medición
- Material industrial y doméstico

CONSULTA DEL CLIENTE: "{query}"{context}

SINÓNIMOS DETECTADOS: {synonyms}

IMPORTANTE: 
- Los clientes pueden usar términos coloquiales o tener errores de escritura
- "Automático" = interruptor magnetotérmico/PIA
- "Diferencial" = interruptor diferencial/ID
- Detecta la intención real basándote en el contexto de material eléctrico

CRÍTICO - SI EL ASISTENTE PIDIÓ CLARIFICACIÓN:
- Si el último mensaje del asistente pregunta por detalles específicos, el mensaje actual ES la respuesta
- SIEMPRE marca has_enough_info = true cuando el usuario está respondiendo a una clarificación
- Combina la información: query anterior + respuesta actual

ANALIZA la consulta y determina:

1. ¿Qué tipo de producto busca? (sé específico, corrigiendo errores ortográficos si los hay)
2. ¿Tiene información suficiente para una búsqueda precisa?
3. ¿Qué información crítica falta?

INFORMACIÓN CRÍTICA para productos eléctricos:
- Automáticos/Magnetotérmicos: amperaje (10A, 16A, etc.), curva (B, C, D), polos (1P, 2P, 3P, 4P)
- Diferenciales: sensibilidad (30mA, 300mA), amperaje, polos, tipo (AC, A, B)
- Cables: sección (1.5mm², 2.5mm², etc.), tipo (unipolar, manguera), color
- Lámparas: tipo (LED, halógena), potencia (W), casquillo (E27, GU10), uso (industrial, doméstico)
- Enchufes/Bases: tipo (schuko, industrial), amperaje, empotrar/superficie
- Ventiladores: tipo (industrial/doméstico) y ubicación suelen ser suficientes

IMPORTANTE - Sé FLEXIBLE:
- "ventilador para almacén" → SUFICIENTE (es ventilador industrial)
- "ventilador grande" → SUFICIENTE (buscar ventiladores de mayor tamaño)
- "cable para casa" → SUFICIENTE (cable doméstico estándar)
- "lámpara para fábrica" → SUFICIENTE (es lámpara industrial)
- Solo pide más info si realmente es CRÍTICA para la seguridad eléctrica

SI EL HISTORIAL MUESTRA QUE YA SE PIDIÓ INFO Y EL USUARIO RESPONDE:
- Combina la información del historial con la respuesta actual
- Ej: Si preguntaste por automático y ahora dice "de 16A", es un automático de 16A
- SIEMPRE considera el contexto completo de la conversación

Responde SOLO con JSON válido, sin texto adicional:
"""
        
        json_example = """{
    "has_enough_info": true,
    "missing_info": [],
    "extracted_specs": {
        "raw_specs": ["especificaciones mencionadas tal cual"],
        "normalized_specs": {
            "amperaje": "16A",
            "polos": "2P",
            "curva": "C"
        }
    },
    "product_type": "tipo de producto identificado",
    "brand": "marca si la menciona",
    "technical_specs": {
        "spec1": "valor1"
    },
    "clarification_needed": null,
    "confidence": 0.8
}

EJEMPLOS:
- "necesito un automático" → falta amperaje, curva, polos
- "busco diferencial 2P 40A 30mA" → tiene toda la info
- "cable de 2.5" → asumimos mm², pero falta tipo (unipolar/manguera)
- "lámpara industrial" → suficiente, es campana industrial/alto bay"""

        prompt = base_prompt.format(
            query=query,
            context=context_str,
            synonyms=', '.join(found_synonyms) if found_synonyms else 'ninguno'
        ) + json_example

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.MEDIUM,
                max_completion_tokens=800
            )
            
            import json
            result = json.loads(response.content)
            
            return SearchAnalysis(
                has_enough_info=result.get("has_enough_info", False),
                missing_info=result.get("missing_info", []),
                extracted_specs=result.get("extracted_specs", {}),
                product_type=result.get("product_type", ""),
                brand=result.get("brand"),
                technical_specs=result.get("technical_specs", {}),
                clarification_needed=result.get("clarification_needed"),
                confidence=float(result.get("confidence", 0.7)),
                synonyms_found=found_synonyms
            )
            
        except Exception as e:
            logger.error(f"Error analizando búsqueda: {e}")
            
            # Fallback genérico sin lógica mecánica
            # Si la IA falla, asumimos que la búsqueda puede proceder
            return SearchAnalysis(
                has_enough_info=True,  # En caso de fallo, proceder con la búsqueda
                missing_info=[],
                extracted_specs={},
                product_type="producto",
                brand=None,
                technical_specs={},
                clarification_needed=None,
                confidence=0.3,  # Baja confianza porque es fallback
                synonyms_found=found_synonyms
            )
            
    def _detect_product_type(self, query: str) -> str:
        """DEPRECATED: Este método usa lógica mecánica. La IA debe detectar el tipo."""
        # La IA en analyze_search ya detecta el tipo de producto
        return "producto eléctrico"
        
    async def suggest_specifications(self, product_type: str) -> List[str]:
        """DEPRECATED: Este método usa lógica mecánica. La IA debe sugerir basándose en contexto."""
        # No usar mapas hardcodeados - la IA debe generar sugerencias contextualmente
        return []


# Instancia global
search_analyzer = SearchAnalyzer()