#!/usr/bin/env python3
"""
Query Optimizer Agent
Optimiza las consultas de búsqueda usando sinónimos y conocimiento del sector
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity

logger = logging.getLogger(__name__)


@dataclass
class OptimizedQuery:
    """Resultado de optimización de query"""
    primary_query: str  # Query principal optimizada
    alternative_queries: List[str] = field(default_factory=list)  # Queries alternativas
    search_terms: List[str] = field(default_factory=list)  # Términos individuales
    filters: Dict[str, Any] = field(default_factory=dict)  # Filtros extraídos
    synonyms_used: List[str] = field(default_factory=list)  # Sinónimos aplicados
    search_strategy: str = "hybrid"  # hybrid, exact, fuzzy, semantic
    confidence: float = 0.8


class QueryOptimizerAgent:
    """Agente para optimizar queries de búsqueda"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Cargar sinónimos
        self.synonyms = self._load_synonyms()
    
    def _load_synonyms(self) -> Dict:
        """Carga el diccionario de sinónimos"""
        try:
            with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/knowledge/sinonimos_electricos.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error cargando sinónimos: {e}")
            return {}
    
    async def optimize_query(
        self, 
        refined_query: str, 
        extracted_specs: Dict[str, Any],
        search_strategy: str = "standard",
        previous_attempts: List[str] = None
    ) -> OptimizedQuery:
        """
        Optimiza una query de búsqueda
        
        Args:
            refined_query: Query refinada del agente anterior
            extracted_specs: Especificaciones extraídas
            search_strategy: Estrategia de búsqueda (specific, standard, broad)
            previous_attempts: Queries anteriores que no dieron buenos resultados
            
        Returns:
            OptimizedQuery con múltiples variantes
        """
        
        # Contexto de intentos previos
        previous_context = ""
        if previous_attempts:
            previous_context = "\n\nQUERIES ANTERIORES QUE NO FUNCIONARON:\n"
            for attempt in previous_attempts:
                previous_context += f"- {attempt}\n"
            previous_context += "\nEvita repetir estos términos exactos, usa sinónimos o variantes."
        
        # Incluir conocimiento de sinónimos
        synonyms_context = self._get_relevant_synonyms(refined_query, extracted_specs)
        
        optimization_prompt = f"""Optimiza esta búsqueda de productos eléctricos generando múltiples variantes usando sinónimos del sector.

BÚSQUEDA REFINADA: "{refined_query}"
ESPECIFICACIONES: {json.dumps(extracted_specs, ensure_ascii=False)}
ESTRATEGIA: {search_strategy}
{previous_context}

{synonyms_context}

REGLAS DE OPTIMIZACIÓN:

1. Para búsqueda ESPECÍFICA:
   - Usa términos técnicos exactos
   - Incluye todas las especificaciones
   - Ordena: [tipo_producto] [especificaciones] [marca opcional]

2. Para búsqueda ESTÁNDAR:
   - Combina términos técnicos y coloquiales
   - Incluye especificaciones principales
   - Genera 2-3 variantes con sinónimos

3. Para búsqueda AMPLIA:
   - Usa múltiples sinónimos del producto
   - Omite especificaciones muy específicas
   - Genera 3-4 variantes diferentes

OPTIMIZACIONES ESPECIALES:
- Si busca "automático" → incluir "magnetotérmico", "PIA", "disyuntor"
- Si busca "diferencial superinmunizado" → incluir "HPI", "SI", "alta inmunidad"
- Si busca "lámpara industrial" → incluir "campana industrial", "proyector", "alto bay"
- Si busca números, mantenerlos exactos (40A, 2.5mm², etc.)

Responde con JSON:
{{
    "primary_query": "query principal optimizada",
    "alternative_queries": [
        "variante 1 con sinónimos",
        "variante 2 diferente",
        "variante 3 si aplica"
    ],
    "search_terms": ["término1", "término2", "sinónimo1"],
    "filters": {{
        "amperaje": "40A",
        "tipo": "superinmunizado"
    }},
    "synonyms_used": ["sinónimos aplicados"],
    "search_strategy": "hybrid/exact/fuzzy",
    "reasoning": "breve explicación"
}}

EJEMPLOS:

Entrada: "diferencial 40A superinmunizado"
Salida: {{
    "primary_query": "diferencial 40A superinmunizado HPI SI",
    "alternative_queries": [
        "interruptor diferencial 40A alta inmunidad",
        "ID 40A superinmunizado HPI FSI",
        "diferencial 40 amperios SI B-SI"
    ],
    "search_terms": ["diferencial", "40A", "superinmunizado", "HPI", "SI", "alta inmunidad"],
    "filters": {{"amperaje": "40A", "tipo": "superinmunizado"}},
    "synonyms_used": ["HPI", "SI", "alta inmunidad", "ID"],
    "search_strategy": "hybrid"
}}"""

        try:
            response = await self.gpt5.create_response(
                input_text=optimization_prompt,
                model="gpt-5-mini",  # Modelo económico para optimización
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW
            )
            
            # Parsear respuesta
            try:
                result = json.loads(response.content)
                
                optimized = OptimizedQuery(
                    primary_query=result.get("primary_query", refined_query),
                    alternative_queries=result.get("alternative_queries", []),
                    search_terms=result.get("search_terms", []),
                    filters=result.get("filters", {}),
                    synonyms_used=result.get("synonyms_used", []),
                    search_strategy=result.get("search_strategy", "hybrid"),
                    confidence=0.9 if result.get("synonyms_used") else 0.7
                )
                
                self.logger.info(f"Query optimizada: {optimized.primary_query} "
                               f"({len(optimized.alternative_queries)} alternativas)")
                
                return optimized
                
            except json.JSONDecodeError:
                self.logger.error("Error parseando respuesta JSON")
                return self._fallback_optimization(refined_query, extracted_specs)
                
        except Exception as e:
            self.logger.error(f"Error en optimización: {e}")
            return self._fallback_optimization(refined_query, extracted_specs)
    
    def _get_relevant_synonyms(self, query: str, specs: Dict) -> str:
        """Obtiene sinónimos relevantes del diccionario"""
        
        if not self.synonyms:
            return ""
        
        relevant_synonyms = []
        query_lower = query.lower()
        
        # Buscar en cada categoría
        for category, items in self.synonyms.items():
            if isinstance(items, dict):
                for key, data in items.items():
                    if key in query_lower:
                        if isinstance(data, dict) and "sinonimos" in data:
                            relevant_synonyms.append(f"{key}: {', '.join(data['sinonimos'][:5])}")
        
        if not relevant_synonyms:
            return ""
        
        synonyms_text = "SINÓNIMOS RELEVANTES DEL SECTOR:\n"
        for syn in relevant_synonyms[:5]:  # Máximo 5 grupos
            synonyms_text += f"- {syn}\n"
        
        return synonyms_text
    
    def _fallback_optimization(self, query: str, specs: Dict) -> OptimizedQuery:
        """Optimización básica como fallback"""
        
        query_lower = query.lower()
        terms = query.split()
        alternatives = []
        synonyms_used = []
        
        # Aplicar sinónimos básicos manualmente
        synonym_map = {
            "automatico": ["magnetotérmico", "PIA"],
            "diferencial": ["interruptor diferencial", "ID"],
            "lampara": ["bombilla", "luminaria"],
            "cable": ["conductor", "manguera"],
            "enrollacables": ["recogecables", "carrete cable"]
        }
        
        # Generar alternativas
        for original, syns in synonym_map.items():
            if original in query_lower:
                for syn in syns[:2]:
                    alt_query = query_lower.replace(original, syn)
                    if alt_query != query_lower:
                        alternatives.append(alt_query)
                        synonyms_used.append(syn)
        
        # Si no hay alternativas, agregar variaciones simples
        if not alternatives and len(terms) > 1:
            alternatives.append(" ".join(reversed(terms)))  # Invertir orden
        
        return OptimizedQuery(
            primary_query=query,
            alternative_queries=alternatives[:3],
            search_terms=terms,
            filters=specs,
            synonyms_used=synonyms_used,
            search_strategy="fuzzy",
            confidence=0.6
        )
    
    def combine_with_feedback(
        self, 
        original_query: OptimizedQuery, 
        feedback: str
    ) -> OptimizedQuery:
        """
        Ajusta la query basándose en feedback del validador
        
        Args:
            original_query: Query original
            feedback: Feedback del validador
            
        Returns:
            Nueva query optimizada
        """
        
        # Si el feedback sugiere ser más específico
        if "especifico" in feedback.lower() or "preciso" in feedback.lower():
            # Usar solo la query principal con todos los filtros
            new_query = f"{original_query.primary_query} {' '.join(f'{k}:{v}' for k, v in original_query.filters.items())}"
            return OptimizedQuery(
                primary_query=new_query,
                alternative_queries=[],
                search_terms=original_query.search_terms,
                filters=original_query.filters,
                search_strategy="exact",
                confidence=0.8
            )
        
        # Si sugiere ser más amplio
        elif "amplio" in feedback.lower() or "general" in feedback.lower():
            # Usar términos más generales
            general_terms = []
            for term in original_query.search_terms:
                if not any(char.isdigit() for char in term):  # Omitir números
                    general_terms.append(term)
            
            return OptimizedQuery(
                primary_query=" ".join(general_terms[:3]),
                alternative_queries=original_query.alternative_queries,
                search_terms=general_terms,
                filters={},  # Sin filtros para búsqueda amplia
                search_strategy="semantic",
                confidence=0.7
            )
        
        # Por defecto, intentar con más sinónimos
        return original_query


# Instancia singleton
query_optimizer = QueryOptimizerAgent()