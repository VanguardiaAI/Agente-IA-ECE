#!/usr/bin/env python3
"""
Results Validator Agent
Valida si los resultados de búsqueda son relevantes para el usuario
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Resultado de validación de productos"""
    are_results_good: bool  # Si los resultados son buenos
    relevance_score: float  # Puntuación de relevancia (0-1)
    relevant_products: List[Dict] = field(default_factory=list)  # Productos relevantes
    irrelevant_products: List[Dict] = field(default_factory=list)  # Productos no relevantes
    feedback: str = ""  # Feedback para el optimizador si no son buenos
    reasoning: str = ""  # Razonamiento de la decisión
    retry_suggestion: Optional[str] = None  # Sugerencia para reintentar


class ResultsValidatorAgent:
    """Agente para validar resultados de búsqueda"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_retries = 3
    
    async def validate_results(
        self,
        user_query: str,
        search_results: List[Dict],
        extracted_specs: Dict[str, Any],
        attempt_number: int = 1
    ) -> ValidationResult:
        """
        Valida si los resultados son relevantes para el usuario
        
        Args:
            user_query: Query original del usuario
            search_results: Resultados de la búsqueda
            extracted_specs: Especificaciones extraídas
            attempt_number: Número de intento actual
            
        Returns:
            ValidationResult con el análisis
        """
        
        if not search_results:
            return ValidationResult(
                are_results_good=False,
                relevance_score=0.0,
                feedback="No se encontraron productos. Intenta con términos más generales.",
                retry_suggestion="amplio"
            )
        
        # Formatear productos para análisis
        products_text = self._format_products_for_validation(search_results[:10])
        
        validation_prompt = f"""Analiza si estos productos encontrados corresponden a lo que el cliente busca.

BÚSQUEDA DEL CLIENTE: "{user_query}"
ESPECIFICACIONES SOLICITADAS: {extracted_specs}
INTENTO NÚMERO: {attempt_number} de {self.max_retries}

PRODUCTOS ENCONTRADOS:
{products_text}

CRITERIOS DE VALIDACIÓN:

1. RELEVANCIA ALTA (0.8-1.0):
   - El producto es EXACTAMENTE lo que busca el cliente
   - Coinciden tipo de producto Y especificaciones principales
   - Ejemplo: Busca "diferencial 40A" → Encuentra "Diferencial 40A 30mA"

2. RELEVANCIA MEDIA (0.5-0.7):
   - Es el tipo de producto correcto pero faltan algunas especificaciones
   - O tiene especificaciones diferentes pero podría servir
   - Ejemplo: Busca "diferencial 40A" → Encuentra "Diferencial 25A"

3. RELEVANCIA BAJA (0.0-0.4):
   - NO es el tipo de producto que busca
   - Producto completamente diferente
   - Ejemplo: Busca "diferencial" → Encuentra "Cable eléctrico"

REGLAS ESPECIALES:
- Si busca "automático" y encuentra "magnetotérmico" → RELEVANCIA ALTA (son sinónimos)
- Si busca marca específica y no la encuentra → RELEVANCIA MEDIA (puede considerar alternativas)
- Si no hay resultados del tipo correcto → Sugerir búsqueda más amplia
- Si hay muchos resultados irrelevantes → Sugerir búsqueda más específica

Responde con JSON:
{{
    "are_results_good": true/false,
    "relevance_score": 0.0-1.0,
    "relevant_count": número de productos relevantes,
    "total_count": total de productos analizados,
    "best_matches": ["id1", "id2"],
    "feedback": "explicación si no son buenos",
    "retry_suggestion": "especifico/amplio/diferente",
    "reasoning": "breve razonamiento"
}}

EJEMPLOS:

Cliente busca "diferencial 40A", encuentra diferenciales de 40A:
{{
    "are_results_good": true,
    "relevance_score": 0.95,
    "relevant_count": 8,
    "total_count": 10,
    "best_matches": ["DIFF-40A-30MA", "DIFF-40A-300MA"],
    "reasoning": "Encontrados múltiples diferenciales de 40A como solicitó"
}}

Cliente busca "automático 16A", encuentra solo cables:
{{
    "are_results_good": false,
    "relevance_score": 0.1,
    "relevant_count": 0,
    "total_count": 10,
    "feedback": "No se encontraron magnetotérmicos/automáticos. Los resultados muestran cables.",
    "retry_suggestion": "diferente",
    "reasoning": "Resultados no corresponden al tipo de producto buscado"
}}"""

        try:
            response = await self.gpt5.create_response(
                input_text=validation_prompt,
                model="gpt-5-mini",
                reasoning_effort=ReasoningEffort.MEDIUM,
                verbosity=Verbosity.LOW
            )
            
            # Parsear respuesta
            import json
            try:
                result = json.loads(response.content)
                
                # Identificar productos relevantes e irrelevantes
                relevant_products = []
                irrelevant_products = []
                best_matches = result.get("best_matches", [])
                
                for product in search_results:
                    product_id = str(product.get("id", ""))
                    if product_id in best_matches or result.get("relevance_score", 0) > 0.7:
                        relevant_products.append(product)
                    else:
                        irrelevant_products.append(product)
                
                # Ajustar decisión basada en intento
                are_good = result.get("are_results_good", False)
                if attempt_number >= self.max_retries and result.get("relevance_score", 0) > 0.5:
                    # En último intento, ser más permisivo
                    are_good = True
                
                validation = ValidationResult(
                    are_results_good=are_good,
                    relevance_score=float(result.get("relevance_score", 0.5)),
                    relevant_products=relevant_products[:10],  # Máximo 10
                    irrelevant_products=irrelevant_products[:5],  # Para análisis
                    feedback=result.get("feedback", ""),
                    reasoning=result.get("reasoning", ""),
                    retry_suggestion=result.get("retry_suggestion") if not are_good else None
                )
                
                self.logger.info(
                    f"Validación: relevancia={validation.relevance_score:.2f}, "
                    f"buenos={validation.are_results_good}, "
                    f"relevantes={len(validation.relevant_products)}/{len(search_results)}"
                )
                
                return validation
                
            except json.JSONDecodeError:
                self.logger.error("Error parseando respuesta JSON")
                return self._fallback_validation(user_query, search_results, attempt_number)
                
        except Exception as e:
            self.logger.error(f"Error en validación: {e}")
            return self._fallback_validation(user_query, search_results, attempt_number)
    
    def _format_products_for_validation(self, products: List[Dict]) -> str:
        """Formatea productos para el análisis"""
        
        if not products:
            return "Sin productos"
        
        formatted = []
        for i, product in enumerate(products, 1):
            # Extraer información clave
            name = product.get("title", product.get("name", "Sin nombre"))
            prod_id = product.get("id", "N/A")
            metadata = product.get("metadata", {})
            
            # Información relevante
            price = metadata.get("price", "N/A")
            brand = metadata.get("brand", "")
            category = metadata.get("categories", [""])[0] if metadata.get("categories") else ""
            
            # Especificaciones técnicas
            specs = []
            description = metadata.get("short_description", "")
            if description:
                # Buscar especificaciones en la descripción
                import re
                # Buscar amperajes
                amp_match = re.findall(r'\d+\s*[aA]', description)
                if amp_match:
                    specs.extend(amp_match)
                # Buscar sensibilidad
                ma_match = re.findall(r'\d+\s*m[aA]', description)
                if ma_match:
                    specs.extend(ma_match)
            
            formatted.append(
                f"{i}. [{prod_id}] {name}\n"
                f"   Precio: {price} | Marca: {brand} | Categoría: {category}\n"
                f"   Specs: {', '.join(specs) if specs else 'No especificadas'}"
            )
        
        return "\n".join(formatted)
    
    def _fallback_validation(
        self, 
        user_query: str, 
        results: List[Dict], 
        attempt: int
    ) -> ValidationResult:
        """Validación básica como fallback"""
        
        if not results:
            return ValidationResult(
                are_results_good=False,
                relevance_score=0.0,
                feedback="Sin resultados",
                retry_suggestion="amplio"
            )
        
        # Validación simple por coincidencia de palabras
        query_words = set(user_query.lower().split())
        relevant_count = 0
        
        for product in results:
            name = product.get("title", "").lower()
            name_words = set(name.split())
            
            # Si comparten palabras clave
            common_words = query_words.intersection(name_words)
            if len(common_words) >= 1:
                relevant_count += 1
        
        relevance_ratio = relevant_count / len(results)
        
        # Decisión simple
        if relevance_ratio > 0.6:
            return ValidationResult(
                are_results_good=True,
                relevance_score=relevance_ratio,
                relevant_products=results[:10],
                reasoning="Mayoría de productos parecen relevantes"
            )
        elif attempt >= self.max_retries:
            # Último intento, aceptar lo que hay
            return ValidationResult(
                are_results_good=True,
                relevance_score=0.5,
                relevant_products=results[:5],
                reasoning="Mejores resultados disponibles después de varios intentos"
            )
        else:
            return ValidationResult(
                are_results_good=False,
                relevance_score=relevance_ratio,
                feedback="Pocos productos relevantes encontrados",
                retry_suggestion="diferente"
            )
    
    def generate_retry_feedback(self, validation: ValidationResult) -> str:
        """
        Genera feedback específico para el optimizador de queries
        
        Args:
            validation: Resultado de la validación
            
        Returns:
            Feedback para mejorar la búsqueda
        """
        
        if validation.are_results_good:
            return ""
        
        if validation.retry_suggestion == "especifico":
            return "Ser más específico: agregar marca, modelo o especificaciones técnicas"
        elif validation.retry_suggestion == "amplio":
            return "Ser más amplio: usar términos más generales o sinónimos"
        elif validation.retry_suggestion == "diferente":
            return "Probar términos completamente diferentes o sinónimos del sector"
        else:
            return validation.feedback


# Instancia singleton
results_validator = ResultsValidatorAgent()