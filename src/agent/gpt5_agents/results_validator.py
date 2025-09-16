"""
Validador de resultados de búsqueda usando GPT-5-mini
Evalúa la calidad y relevancia de los resultados
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Resultado de la validación de búsqueda"""
    is_valid: bool
    relevance_score: float
    result_quality: str  # excellent, good, acceptable, poor
    issues: List[str]
    suggestions: List[str]
    best_matches: List[int]  # índices de mejores resultados
    needs_refinement: bool
    refinement_reason: Optional[str]


class ResultsValidator:
    """Valida la calidad de los resultados de búsqueda"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.model = "gpt-5-mini"  # USAR GPT-5-MINI PARA VALIDACIÓN
        
    async def validate_results(
        self,
        original_query: str,
        search_results: List[Dict[str, Any]],
        search_context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Valida si los resultados son buenos para la consulta del usuario
        
        Args:
            original_query: Consulta original del usuario
            search_results: Lista de productos encontrados
            search_context: Contexto de la búsqueda (tipo producto, specs, etc.)
            
        Returns:
            ValidationResult con el análisis
        """
        
        if not search_results:
            return ValidationResult(
                is_valid=False,
                relevance_score=0.0,
                result_quality="poor",
                issues=["No se encontraron resultados"],
                suggestions=["Ampliar búsqueda", "Usar términos más generales"],
                best_matches=[],
                needs_refinement=True,
                refinement_reason="Sin resultados"
            )
        
        # Preparar info de productos para análisis
        products_info = []
        for i, product in enumerate(search_results[:10]):  # Analizar máx 10
            products_info.append({
                "index": i,
                "title": product.get('title', ''),
                "description": product.get('content', '')[:200],  # Primeros 200 chars
                "price": product.get('metadata', {}).get('price', 0),
                "in_stock": product.get('metadata', {}).get('stock_status') == 'instock'
            })
        
        # Formatear la información para el prompt
        product_type = search_context.get('product_type', 'no especificado')
        specs = search_context.get('specs', {})
        total_results = len(search_results)
        products_formatted = self._format_products_for_prompt(products_info)
        
        prompt = f"""Analiza ESTRICTAMENTE si estos resultados coinciden con la búsqueda.

BÚSQUEDA DEL USUARIO: "{original_query}"
TIPO ESPERADO: {product_type}
ESPECIFICACIONES: {specs}

PRODUCTOS ENCONTRADOS ({total_results} total):
{products_formatted}

ANÁLISIS ESTRICTO:

1. RELEVANCIA EXACTA:
   - Si busca "ventilador industrial" → ¿Son REALMENTE ventiladores industriales?
   - Si busca "cable 2.5mm" → ¿Son EXACTAMENTE cables de 2.5mm?
   - NO aceptes productos "parecidos" o "relacionados"

2. CALIDAD DE COINCIDENCIA:
   - Cuenta cuántas palabras de la búsqueda aparecen en el título
   - Prioriza productos que contengan TODAS las palabras clave
   - Penaliza productos que no coincidan exactamente

3. CRITERIOS DE CALIDAD:
   - EXCELLENT: Título contiene TODAS las palabras clave, producto EXACTO
   - GOOD: Producto correcto, falta algún detalle menor
   - ACCEPTABLE: Producto relacionado pero no exacto
   - POOR: Producto diferente o sin relación clara

4. REFINAMIENTO NECESARIO SI:
   - Menos de 3 productos son EXACTAMENTE lo buscado
   - Los mejores resultados no contienen las palabras clave principales
   - Hay muchos productos pero ninguno es lo que se busca

Responde SOLO con JSON válido, sin texto adicional:
""" + """
{
    "is_valid": true/false,
    "relevance_score": 0.0-1.0,
    "result_quality": "excellent/good/acceptable/poor",
    "issues": ["lista de problemas encontrados"],
    "suggestions": ["sugerencias de mejora"],
    "best_matches": [0, 1, 2, 3, 4],
    "needs_refinement": true/false,
    "refinement_reason": "razón si necesita refinamiento"
}"""

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=500
            )
            
            import json
            result = json.loads(response.content)
            
            return ValidationResult(
                is_valid=result.get("is_valid", False),
                relevance_score=float(result.get("relevance_score", 0.5)),
                result_quality=result.get("result_quality", "acceptable"),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                best_matches=result.get("best_matches", [0, 1, 2, 3, 4])[:8],  # Permitir hasta 8 mejores matches
                needs_refinement=result.get("needs_refinement", False),
                refinement_reason=result.get("refinement_reason")
            )
            
        except Exception as e:
            logger.error(f"Error validando resultados: {e}")
            
            # Validación básica como fallback
            return self._basic_validation(
                original_query,
                search_results,
                search_context
            )
            
    def _format_products_for_prompt(self, products: List[Dict]) -> str:
        """Formatea productos para el prompt"""
        lines = []
        for p in products:
            stock = "✓ En stock" if p['in_stock'] else "✗ Sin stock"
            price = f"€{p['price']:.2f}" if p['price'] else "Precio no disponible"
            lines.append(
                f"{p['index']}. {p['title'][:80]}... | {price} | {stock}"
            )
        return "\n".join(lines)
        
    def _basic_validation(
        self,
        query: str,
        results: List[Dict],
        context: Dict
    ) -> ValidationResult:
        """Validación básica como fallback"""
        
        # Contar resultados
        total = len(results)
        in_stock = sum(1 for r in results if r.get('metadata', {}).get('stock_status') == 'instock')
        
        # Validación simple
        issues = []
        suggestions = []
        
        if total == 0:
            issues.append("Sin resultados")
            suggestions.append("Ampliar búsqueda")
            quality = "poor"
            valid = False
        elif total < 3:
            issues.append("Muy pocos resultados")
            suggestions.append("Buscar términos relacionados")
            quality = "acceptable"
            valid = True
        elif total > 20:
            issues.append("Demasiados resultados")
            suggestions.append("Ser más específico")
            quality = "acceptable"
            valid = True
        else:
            quality = "good"
            valid = True
            
        if in_stock == 0 and total > 0:
            issues.append("Ningún producto en stock")
            
        return ValidationResult(
            is_valid=valid,
            relevance_score=0.5 if valid else 0.0,
            result_quality=quality,
            issues=issues,
            suggestions=suggestions,
            best_matches=list(range(min(5, total))),  # Devolver hasta 5 mejores
            needs_refinement=not valid or quality == "poor",
            refinement_reason=issues[0] if issues else None
        )
        
    async def analyze_refinement_needs(
        self,
        validation_result: ValidationResult,
        search_attempts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analiza qué tipo de refinamiento necesita la búsqueda
        
        Returns:
            Diccionario con estrategia de refinamiento
        """
        
        if not validation_result.needs_refinement:
            return {"needs_refinement": False}
            
        # Analizar patrones en intentos anteriores
        attempts_summary = []
        for attempt in search_attempts:
            attempts_summary.append({
                "query": attempt.get("query", ""),
                "results": attempt.get("results_count", 0),
                "valid": attempt.get("valid", False)
            })
            
        # Formatear la información para el prompt
        refinement_reason = validation_result.refinement_reason
        issues_list = validation_result.issues
        
        prompt = f"""Analiza qué refinamiento necesita esta búsqueda.

PROBLEMA ACTUAL: {refinement_reason}
ISSUES: {issues_list}

INTENTOS ANTERIORES:
{attempts_summary}

Determina la mejor estrategia:
1. BROADEN: Ampliar búsqueda (menos específico)
2. NARROW: Reducir búsqueda (más específico)
3. SYNONYMS: Usar sinónimos diferentes
4. RETHINK: Repensar completamente el enfoque

Responde SOLO con JSON válido, sin texto adicional:
""" + """
{
    "strategy": "BROADEN/NARROW/SYNONYMS/RETHINK",
    "specific_action": "acción específica a tomar",
    "avoid": ["términos a evitar"],
    "include": ["términos a incluir"]
}"""

        try:
            response = await self.gpt5.create_response(
                input_text=prompt,
                model=self.model,
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW,
                max_completion_tokens=300
            )
            
            import json
            result = json.loads(response.content)
            result["needs_refinement"] = True
            return result
            
        except:
            # Estrategia simple de fallback
            if "pocos resultados" in str(validation_result.issues):
                strategy = "BROADEN"
            elif "demasiados" in str(validation_result.issues):
                strategy = "NARROW"
            else:
                strategy = "SYNONYMS"
                
            return {
                "needs_refinement": True,
                "strategy": strategy,
                "specific_action": f"Aplicar estrategia {strategy}",
                "avoid": [],
                "include": []
            }


# Instancia global
results_validator = ResultsValidator()