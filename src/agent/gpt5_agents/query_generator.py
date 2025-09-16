"""
Generador de queries de búsqueda usando GPT-5-mini
Genera múltiples variantes de búsqueda optimizadas
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
from .synonym_manager import synonym_manager

logger = logging.getLogger(__name__)


@dataclass
class SearchQueries:
    """Queries de búsqueda generados"""
    primary_query: str
    alternative_queries: List[str]
    synonym_queries: List[str]
    broad_query: str
    narrow_queries: List[str]
    strategy: str


class QueryGenerator:
    """Genera queries de búsqueda inteligentes"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.model = "gpt-5-mini"  # USAR GPT-5-MINI PARA QUERIES
        self.synonym_manager = synonym_manager
        
    async def generate_queries(
        self,
        original_query: str,
        extracted_info: Dict[str, Any],
        product_type: str,
        refinement_feedback: Optional[str] = None
    ) -> SearchQueries:
        """
        Genera múltiples queries de búsqueda optimizados
        
        Args:
            original_query: Consulta original del usuario
            extracted_info: Información extraída por el analizador
            product_type: Tipo de producto identificado
            refinement_feedback: Feedback de intentos anteriores
            
        Returns:
            SearchQueries con múltiples variantes
        """
        
        # PRIMERO: Extraer palabras relevantes del mensaje original
        # Eliminar palabras comunes que no son productos
        stop_words = {
            'hola', 'quiero', 'necesito', 'busco', 'dame', 'muestra', 'un', 'una', 
            'unos', 'unas', 'el', 'la', 'los', 'las', 'de', 'por', 'favor', 'gracias',
            'me', 'mi', 'tu', 'su', 'que', 'con', 'para', 'en', 'a', 'y', 'o'
        }
        
        words = original_query.lower().split()
        product_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Query simple y directo
        simple_query = ' '.join(product_words) if product_words else original_query
        
        # Si la query simple es muy corta o no tiene palabras de producto, usar el tipo de producto
        if len(simple_query) < 4 or not product_words:
            simple_query = product_type if product_type else original_query
        
        # Expandir con sinónimos
        synonym_expansions = self.synonym_manager.expand_query(simple_query, max_expansions=3)
        
        # Información técnica del producto
        tech_info = self.synonym_manager.get_technical_info(product_type)
        
        # Construir contexto
        context = f"""
Query simplificada: "{simple_query}"
Consulta original: "{original_query}"
Tipo de producto: {product_type}
Especificaciones extraídas: {extracted_info}
Expansiones con sinónimos: {synonym_expansions}
"""

        if refinement_feedback:
            context += f"\nFeedback de búsqueda anterior: {refinement_feedback}"
            
        if tech_info:
            context += f"\nInformación técnica: {tech_info}"

        base_prompt = f"""Eres un experto en búsquedas para El Corte Eléctrico, tienda de MATERIAL ELÉCTRICO.

CONTEXTO DE LA TIENDA:
- Miles de productos eléctricos: protección, cableado, iluminación, mecanismos, etc.
- Los productos tienen nombres técnicos y comerciales
- Terminología común del sector:
  * "Automático" = magnetotérmico, PIA, interruptor automático
  * "Diferencial" = ID, interruptor diferencial
  * Los clientes usan términos coloquiales y técnicos indistintamente

{context}

GENERA queries de búsqueda optimizados considerando:

1. La base de datos busca en título y descripción de productos
2. Los productos tienen nombres técnicos y comerciales
3. Importante incluir sinónimos y variaciones regionales
4. La query simplificada YA tiene las palabras clave extraídas - úsala como base
5. CRÍTICO: No agregar términos técnicos que el usuario no mencionó (como "high-bay" si solo dijo "lámpara")

CRÍTICO - CORRECCIÓN ORTOGRÁFICA INTELIGENTE:
El usuario frecuentemente comete errores al escribir. Tu trabajo es:

1. ANALIZAR cada palabra buscando posibles errores:
   - "autpmátic" → claramente quiso decir "automático"
   - "diferencal" → claramente quiso decir "diferencial"
   - "cabel" → claramente quiso decir "cable"
   - Usa tu conocimiento de productos eléctricos para identificar la intención

2. SIEMPRE CORREGIR en el query principal:
   - Si detectas UN error ortográfico, la query principal DEBE tener la versión corregida
   - La query original con error va en alternative_queries

3. ESTRATEGIA DE CORRECCIÓN:
   - Query principal: SIEMPRE la versión corregida
   - Primera alternativa: la versión original (con error)
   - Otras alternativas: sinónimos de la versión corregida

REGLAS CRÍTICAS:
- Si detectas un error ortográfico, corrige en la query principal
- Incluye la versión original en alternativas
- NO inventes especificaciones que el usuario no pidió

ESTRATEGIAS DE BÚSQUEDA:
- Extrae las palabras clave del producto mencionado
- NO cambies términos que el usuario usó (si dice "lámpara", busca "lámpara", no "campana")
- NUNCA añadas especificaciones inventadas
- Genera variaciones simples basadas en sinónimos comunes del sector eléctrico

La base de datos contiene miles de productos eléctricos con nombres técnicos y comerciales variados.

Responde SOLO con JSON válido, sin texto adicional:
"""
        
        json_example = """
{
    "primary_query": "query principal optimizado",
    "alternative_queries": ["variante 1", "variante 2", "variante 3"],
    "synonym_queries": ["con sinónimo 1", "con sinónimo 2"],
    "broad_query": "query más general",
    "narrow_queries": ["muy específico 1", "muy específico 2"],
    "strategy": "explicación breve de la estrategia usada"
}"""
        
        prompt = base_prompt + json_example

        # SIEMPRE usar GPT-5 para manejar posibles errores ortográficos
        # La IA es quien debe detectar y corregir, no código mecánico
        logger.info(f"🤖 Procesando query con GPT-5: '{simple_query}'")
        
        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=600
            )
            
            import json
            result = json.loads(response.content)
            
            # IMPORTANTE: Si GPT-5 devuelve algo diferente a la query simple, usar la simple
            primary = result.get("primary_query", simple_query)
            if len(primary.split()) > len(simple_query.split()) + 2:
                # GPT-5 añadió demasiadas cosas, usar la versión simple
                primary = simple_query
            
            return SearchQueries(
                primary_query=primary,
                alternative_queries=result.get("alternative_queries", []),
                synonym_queries=result.get("synonym_queries", synonym_expansions),
                broad_query=result.get("broad_query", product_type),
                narrow_queries=result.get("narrow_queries", []),
                strategy=result.get("strategy", "búsqueda estándar")
            )
            
        except Exception as e:
            logger.error(f"Error generando queries: {e}")
            
            # Fallback: generar queries básicos
            return self._generate_fallback_queries(
                simple_query if simple_query else original_query, 
                product_type, 
                synonym_expansions
            )
            
    def _generate_fallback_queries(
        self, 
        query: str, 
        product_type: str,
        synonyms: List[str]
    ) -> SearchQueries:
        """Genera queries básicos como fallback"""
        
        # Query principal limpio
        primary = query.strip()
        
        # Alternativas con sinónimos
        alternatives = synonyms[:3] if synonyms else [query]
        
        # Query amplio (solo tipo de producto)
        broad = product_type
        
        # Queries específicos (añadir palabras clave)
        narrow = []
        
        # Detectar especificaciones en el query
        specs = []
        words = query.lower().split()
        
        # Buscar amperajes
        for word in words:
            if word.endswith('a') and any(c.isdigit() for c in word):
                specs.append(word)
                
        # Buscar polos
        for word in words:
            if word in ['1p', '2p', '3p', '4p']:
                specs.append(word)
                
        # Crear query específico si hay specs
        if specs:
            narrow.append(f"{product_type} {' '.join(specs)}")
            
        return SearchQueries(
            primary_query=primary,
            alternative_queries=alternatives,
            synonym_queries=synonyms,
            broad_query=broad,
            narrow_queries=narrow,
            strategy="fallback básico"
        )
        
    async def optimize_for_retry(
        self,
        previous_queries: List[str],
        feedback: str,
        original_info: Dict[str, Any]
    ) -> SearchQueries:
        """
        Optimiza queries basándose en intentos anteriores fallidos
        
        Args:
            previous_queries: Queries que ya se intentaron
            feedback: Razón del fallo
            original_info: Información original de la búsqueda
            
        Returns:
            Nuevos queries optimizados
        """
        
        prompt = f"""Búsquedas anteriores no dieron buenos resultados.

Queries intentados: {previous_queries}
Problema: {feedback}
Información original: {original_info}

Genera NUEVOS queries diferentes que:
1. NO repitan los anteriores
2. Aborden el problema identificado
3. Usen estrategias alternativas

Si había muy pocos resultados → queries más generales
Si había demasiados → queries más específicos
Si no eran relevantes → usar sinónimos o términos diferentes

Responde en JSON con el mismo formato anterior."""

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=600
            )
            
            import json
            result = json.loads(response.content)
            
            return SearchQueries(
                primary_query=result.get("primary_query", ""),
                alternative_queries=result.get("alternative_queries", []),
                synonym_queries=result.get("synonym_queries", []),
                broad_query=result.get("broad_query", ""),
                narrow_queries=result.get("narrow_queries", []),
                strategy=result.get("strategy", "refinamiento")
            )
            
        except Exception as e:
            logger.error(f"Error optimizando queries: {e}")
            
            # Generar algo diferente como fallback
            return SearchQueries(
                primary_query=original_info.get('product_type', 'producto'),
                alternative_queries=[],
                synonym_queries=[],
                broad_query="material eléctrico",
                narrow_queries=[],
                strategy="fallback de refinamiento"
            )


# Instancia global
query_generator = QueryGenerator()