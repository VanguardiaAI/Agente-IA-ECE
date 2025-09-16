"""
Refinador de búsqueda usando GPT-5
Mejora las búsquedas basándose en el feedback del validador
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
from .synonym_manager import synonym_manager

logger = logging.getLogger(__name__)


@dataclass
class RefinementStrategy:
    """Estrategia de refinamiento de búsqueda"""
    new_approach: str
    refined_queries: List[str]
    avoid_terms: List[str]
    focus_terms: List[str]
    reasoning: str
    confidence: float


class SearchRefiner:
    """Refina búsquedas basándose en resultados anteriores"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.model = "gpt-5"  # USAR GPT-5 PARA REFINAMIENTO
        self.synonym_manager = synonym_manager
        
    async def refine_search(
        self,
        original_query: str,
        search_context: Dict[str, Any],
        validation_result: Dict[str, Any],
        search_history: List[Dict[str, Any]]
    ) -> RefinementStrategy:
        """
        Refina la búsqueda basándose en resultados anteriores
        
        Args:
            original_query: Consulta original del usuario
            search_context: Contexto de búsqueda (tipo producto, specs)
            validation_result: Resultado de la validación
            search_history: Historial de intentos anteriores
            
        Returns:
            RefinementStrategy con nuevo enfoque
        """
        
        # Analizar qué ha fallado
        failed_queries = []
        successful_patterns = []
        
        for attempt in search_history:
            if not attempt.get('valid', False):
                failed_queries.append(attempt.get('query', ''))
            else:
                successful_patterns.append(attempt.get('query', ''))
        
        # Obtener sinónimos adicionales
        product_type = search_context.get('product_type', '')
        additional_synonyms = self.synonym_manager.get_category_terms(
            self._map_to_category(product_type)
        )
        
        # Extraer valores para evitar problemas con f-strings
        refinement_reason = validation_result.get('refinement_reason', 'resultados no satisfactorios')
        issues = validation_result.get('issues', [])
        strategy = validation_result.get('strategy', 'SYNONYMS')
        synonyms_slice = additional_synonyms[:10]
        
        prompt = f"""Eres un experto refinando búsquedas de productos eléctricos.

SITUACIÓN:
- Consulta original: "{original_query}"
- Tipo de producto: {product_type}
- Problema encontrado: {refinement_reason}
- Issues: {issues}
- Estrategia sugerida: {strategy}

HISTORIAL DE BÚSQUEDAS:
Fallidas: {failed_queries}
Exitosas: {successful_patterns}

SINÓNIMOS DISPONIBLES: {synonyms_slice}

ANALIZA el problema y genera una NUEVA ESTRATEGIA completamente diferente.

ESTRATEGIAS POSIBLES:
1. Si había pocos/ningún resultado → simplificar, usar términos más generales
2. Si había demasiados → añadir especificaciones, ser más preciso
3. Si no eran relevantes → cambiar enfoque, usar sinónimos diferentes
4. Si falta info → sugerir preguntar al usuario

IMPORTANTE:
- NO repitas queries que ya fallaron
- Piensa creativamente en cómo un vendedor experto buscaría
- Considera errores de escritura comunes
- Usa conocimiento de nomenclatura regional

Responde SOLO con JSON válido, sin texto adicional:
""" + """
{
    "new_approach": "descripción del nuevo enfoque",
    "refined_queries": ["query1", "query2", "query3", "query4"],
    "avoid_terms": ["términos que no funcionaron"],
    "focus_terms": ["términos clave a enfatizar"],
    "reasoning": "explicación del razonamiento",
    "confidence": 0.0-1.0
}

EJEMPLO:
Si buscaba "diferencial 30ma" sin resultados, probar:
- "interruptor diferencial"
- "ID 30mA"
- "protección diferencial"
- "diferencial monofásico"
No solo añadir/quitar palabras, sino repensar la búsqueda."""

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
            
            return RefinementStrategy(
                new_approach=result.get("new_approach", ""),
                refined_queries=result.get("refined_queries", []),
                avoid_terms=result.get("avoid_terms", []),
                focus_terms=result.get("focus_terms", []),
                reasoning=result.get("reasoning", ""),
                confidence=float(result.get("confidence", 0.7))
            )
            
        except Exception as e:
            logger.error(f"Error refinando búsqueda: {e}")
            
            # Estrategia de fallback
            return self._fallback_refinement(
                original_query,
                product_type,
                validation_result
            )
            
    def _map_to_category(self, product_type: str) -> str:
        """Mapea tipo de producto a categoría de sinónimos"""
        category_map = {
            "magnetotérmico": "protecciones_electricas",
            "diferencial": "protecciones_electricas",
            "cable": "cables_conexiones",
            "lámpara": "iluminacion",
            "iluminación": "iluminacion",
            "enchufe": "industrial",
            "cuadro": "industrial"
        }
        
        for key, category in category_map.items():
            if key in product_type.lower():
                return category
                
        return "industrial"  # default
        
    def _fallback_refinement(
        self,
        query: str,
        product_type: str,
        validation_result: Dict
    ) -> RefinementStrategy:
        """Estrategia de refinamiento básica como fallback"""
        
        strategy = validation_result.get('strategy', 'SYNONYMS')
        
        refined_queries = []
        
        if strategy == 'BROADEN':
            # Simplificar - quitar especificaciones
            words = query.split()
            if len(words) > 2:
                refined_queries.append(' '.join(words[:2]))
            refined_queries.append(product_type)
            
        elif strategy == 'NARROW':
            # Añadir especificaciones comunes
            refined_queries.append(f"{query} Schneider")
            refined_queries.append(f"{query} Legrand")
            refined_queries.append(f"{query} 16A")
            
        else:  # SYNONYMS
            # Usar sinónimos del manager
            synonyms = self.synonym_manager.expand_query(query, 4)
            refined_queries = synonyms
            
        return RefinementStrategy(
            new_approach=f"Estrategia {strategy} aplicada",
            refined_queries=refined_queries[:4],
            avoid_terms=[],
            focus_terms=[product_type],
            reasoning="Refinamiento automático por fallback",
            confidence=0.5
        )
        
    async def generate_user_clarification(
        self,
        search_context: Dict[str, Any],
        validation_issues: List[str]
    ) -> str:
        """
        Genera una pregunta de clarificación para el usuario
        
        Args:
            search_context: Contexto de la búsqueda
            validation_issues: Problemas encontrados
            
        Returns:
            Pregunta amigable para el usuario
        """
        
        prompt = f"""Genera una pregunta amigable para clarificar qué busca el usuario.

Contexto:
- Busca: {search_context.get('product_type', 'producto')}
- Problemas: {validation_issues}
- Info faltante: {search_context.get('missing_info', [])}

La pregunta debe ser:
- Clara y específica
- Amigable y profesional
- Ofrecer opciones si es posible
- Máximo 2 líneas

Ejemplos buenos:
- "¿Qué amperaje necesitas para el automático? Tenemos de 10A, 16A, 20A y 25A disponibles."
- "¿Buscas un diferencial de 30mA o 300mA? ¿Para uso doméstico o industrial?"

Responde SOLO con la pregunta, sin comillas ni formato JSON."""

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model="gpt-5-mini",  # OK usar mini para clarificación
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=100
            )
            
            return response.content.strip()
            
        except:
            # Pregunta genérica
            missing = search_context.get('missing_info', [])
            if missing:
                return f"¿Podrías especificar {', '.join(missing[:2])}?"
            else:
                return "¿Podrías darme más detalles sobre lo que buscas?"


# Instancia global
search_refiner = SearchRefiner()