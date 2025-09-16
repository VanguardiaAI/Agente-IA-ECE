"""
✅ Results Validator Agent
Agente especializado en validar la relevancia de los resultados
y generar preguntas de refinamiento inteligentes
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import aiohttp
from dotenv import load_dotenv

from .agent_interfaces import (
    IResultsValidatorAgent,
    ValidationResult,
    SearchResults,
    ProductUnderstanding,
    ValidationError
)
from .shared_context import shared_context

# Cargar variables de entorno
load_dotenv("env.agent")

logger = logging.getLogger(__name__)

class ResultsValidatorAgent(IResultsValidatorAgent):
    """
    Agente que valida la relevancia de los resultados de búsqueda
    y decide si se necesita refinamiento
    """
    
    def __init__(self):
        super().__init__(name="ResultsValidator")
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY no configurada")
        
        # Umbrales de validación
        self.thresholds = {
            "min_relevance_score": 0.7,      # Score mínimo para considerar relevante
            "min_products_needed": 1,         # Mínimo de productos válidos necesarios
            "max_products_to_show": 10,       # Máximo de productos a mostrar
            "refinement_threshold": 0.5,      # Score por debajo del cual sugerir refinamiento
            "confidence_for_no_refinement": 0.85  # Confianza para no pedir refinamiento
        }
        
        # Preguntas de refinamiento predefinidas por contexto
        self.refinement_templates = {
            "too_many_results": [
                "Encontré muchos productos. ¿Podrías ser más específico?",
                "Hay varias opciones. ¿Qué características son más importantes para ti?",
                "Tengo {count} productos. ¿Prefieres alguna marca o especificación en particular?"
            ],
            "low_relevance": [
                "Los resultados no parecen exactamente lo que buscas. ¿Podrías darme más detalles?",
                "No estoy seguro de haber entendido bien. ¿Qué tipo de {product} necesitas exactamente?",
                "Los productos encontrados pueden no ser ideales. ¿Para qué lo vas a usar?"
            ],
            "missing_specs": [
                "¿Qué potencia necesitas?",
                "¿Necesitas algún amperaje específico?",
                "¿Prefieres alguna marca en particular?",
                "¿Es para uso doméstico o industrial?",
                "¿Qué medidas o tamaño necesitas?"
            ],
            "no_results": [
                "No encontré exactamente lo que buscas. ¿Podrías describir el producto de otra forma?",
                "No tengo productos que coincidan. ¿Buscas algo similar a {product}?",
                "No encontré resultados. ¿Podrías verificar el nombre del producto?"
            ],
            "ambiguous": [
                "Tu búsqueda es un poco general. ¿Qué tipo específico necesitas?",
                "Hay diferentes tipos de {product}. ¿Cuál te interesa?",
                "¿Podrías especificar más sobre qué modelo o tipo buscas?"
            ]
        }
        
        self.logger.info("✅ Results Validator Agent inicializado")
    
    async def process(self, input_data: Any, context: Dict[str, Any]) -> ValidationResult:
        """Procesa los resultados de búsqueda y valida relevancia"""
        
        # Extraer datos necesarios
        if isinstance(input_data, dict):
            search_results = SearchResults(**input_data.get("search_results", {}))
            understanding = ProductUnderstanding(**input_data.get("understanding", {}))
        else:
            # Asumir que es SearchResults directamente
            search_results = input_data
            understanding = context.get("understanding", ProductUnderstanding(
                search_query="",
                product_type=None,
                brand=None,
                specifications={},
                synonyms_applied=[],
                confidence=0.5
            ))
        
        original_query = context.get("original_query", understanding.search_query)
        
        return await self.validate_results(search_results, original_query, understanding)
    
    async def validate_results(
        self,
        search_results: SearchResults,
        original_request: str,
        understanding: ProductUnderstanding
    ) -> ValidationResult:
        """
        Valida la relevancia de los resultados de búsqueda
        
        Args:
            search_results: Resultados de la búsqueda
            understanding: Comprensión del producto
            original_query: Query original del usuario
            
        Returns:
            Validación con productos filtrados y sugerencias
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"✅ Validando {search_results.total_count} resultados para: '{original_request}'")
            
            # Caso especial: Sin resultados
            if not search_results.products or search_results.total_count == 0:
                return await self._handle_no_results(understanding, original_request)
            
            # Validar relevancia con IA
            validation = await self._validate_with_ai(
                search_results.products[:20],  # Validar máximo 20 productos
                understanding,
                original_request
            )
            
            # Filtrar productos válidos
            valid_products = []
            invalid_products = []
            
            for i, product in enumerate(search_results.products[:20]):
                product_validation = validation.get("products", [])[i] if i < len(validation.get("products", [])) else {}
                relevance_score = product_validation.get("relevance_score", 0.5)
                
                if relevance_score >= self.thresholds["min_relevance_score"]:
                    product["relevance_score"] = relevance_score
                    product["relevance_reason"] = product_validation.get("reason", "")
                    valid_products.append(product)
                else:
                    product["relevance_score"] = relevance_score
                    product["rejection_reason"] = product_validation.get("reason", "Baja relevancia")
                    invalid_products.append(product)
            
            # Ordenar productos válidos por relevancia
            valid_products.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
            
            # Limitar cantidad de productos a mostrar
            valid_products = valid_products[:self.thresholds["max_products_to_show"]]
            
            # Determinar si necesita refinamiento
            needs_refinement = self._needs_refinement(
                valid_products,
                invalid_products,
                validation.get("overall_confidence", 0.5)
            )
            
            # Generar pregunta de refinamiento si es necesario
            refinement_question = None
            if needs_refinement:
                refinement_question = await self._generate_refinement_question(
                    valid_products,
                    invalid_products,
                    understanding,
                    validation
                )
            
            # Calcular score de validación
            validation_score = self._calculate_validation_score(
                valid_products,
                search_results.total_count
            )
            
            # Crear resultado de validación
            result = ValidationResult(
                valid_products=valid_products,
                invalid_products=invalid_products,
                needs_refinement=needs_refinement,
                refinement_question=refinement_question,
                validation_score=validation_score,
                rejection_reasons=[p.get("rejection_reason", "") for p in invalid_products]
            )
            
            # Registrar métricas
            time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_metrics(time_ms, True)
            
            self.logger.info(f"✅ Validación completada: {len(valid_products)} productos válidos")
            self.logger.info(f"   Score de validación: {validation_score:.2f}")
            self.logger.info(f"   Necesita refinamiento: {needs_refinement}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validando resultados: {e}")
            self.log_metrics(0, False)
            
            # Fallback: Aceptar todos los productos
            return self._fallback_validation(search_results)
    
    async def _validate_with_ai(
        self,
        products: List[Dict],
        understanding: ProductUnderstanding,
        original_query: str
    ) -> Dict[str, Any]:
        """Valida relevancia usando IA"""
        
        # Preparar información de productos para IA
        products_info = []
        for i, product in enumerate(products[:10]):  # Limitar a 10 para el prompt
            products_info.append({
                "index": i,
                "name": product.get("name", ""),
                "description": (product.get("description", "") or "")[:200],
                "brand": product.get("brand", ""),
                "price": product.get("price", 0),
                "category": product.get("category", "")
            })
        
        prompt = f'''
Eres un experto validador de productos eléctricos evaluando relevancia.

PETICIÓN ORIGINAL DEL USUARIO: "{original_query}"

COMPRENSIÓN DEL PRODUCTO:
- Tipo: {understanding.product_type}
- Marca deseada: {understanding.brand or "No especificada"}
- Especificaciones: {json.dumps(understanding.specifications, ensure_ascii=False)}
- Query de búsqueda: "{understanding.search_query}"

PRODUCTOS A VALIDAR:
{json.dumps(products_info, indent=2, ensure_ascii=False)}

EVALÚA cada producto y responde con JSON:
{{
    "overall_confidence": 0.85,  // Confianza general en los resultados
    "main_issue": "ninguno|too_many|low_relevance|missing_specs|ambiguous",
    "products": [
        {{
            "index": 0,
            "relevance_score": 0.95,  // 0.0 a 1.0
            "reason": "Coincide exactamente con lo solicitado",
            "matches_intent": true,
            "has_required_specs": true
        }},
        // ... más productos
    ],
    "missing_information": ["amperaje", "voltaje"],  // Info que falta
    "suggested_filters": {{"brand": "Schneider", "min_amperage": "16A"}},
    "refinement_needed": false,
    "refinement_focus": "specifications|brand|type|usage"
}}

CRITERIOS DE RELEVANCIA:
1. Coincidencia con el tipo de producto (40%)
2. Especificaciones correctas (30%)
3. Marca solicitada (20%)
4. Uso apropiado (10%)

IMPORTANTE:
- Score > 0.8: Muy relevante
- Score 0.6-0.8: Relevante
- Score 0.4-0.6: Posiblemente relevante
- Score < 0.4: No relevante
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
                "temperature": 0.3,
                "max_tokens": 800,
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
                        logger.error(f"Error en API: {error}")
                        raise ValidationError(f"API error: {response.status}")
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    validation = json.loads(content)
                    self.logger.debug(f"Validación IA: {validation}")
                    
                    return validation
                    
        except Exception as e:
            logger.error(f"Error llamando a OpenAI: {e}")
            # Fallback: validación básica
            return {
                "overall_confidence": 0.5,
                "products": [{"index": i, "relevance_score": 0.6} for i in range(len(products))],
                "refinement_needed": True
            }
    
    async def _handle_no_results(
        self,
        understanding: ProductUnderstanding,
        original_query: str
    ) -> ValidationResult:
        """Maneja el caso de no tener resultados"""
        
        # Generar pregunta de refinamiento para sin resultados
        refinement_question = self.refinement_templates["no_results"][0].format(
            product=understanding.product_type or "producto"
        )
        
        return ValidationResult(
            valid_products=[],
            invalid_products=[],
            needs_refinement=True,
            refinement_question=refinement_question,
            validation_score=0.0,
            rejection_reasons=["No se encontraron productos"]
        )
    
    def _needs_refinement(
        self,
        valid_products: List[Dict],
        invalid_products: List[Dict],
        overall_confidence: float
    ) -> bool:
        """Determina si se necesita refinamiento"""
        
        # No hay productos válidos
        if len(valid_products) < self.thresholds["min_products_needed"]:
            return True
        
        # Confianza muy baja
        if overall_confidence < self.thresholds["refinement_threshold"]:
            return True
        
        # Demasiados productos (más de 20 válidos)
        if len(valid_products) > 20:
            return True
        
        # Mayoría de productos son inválidos
        if len(invalid_products) > len(valid_products) * 2:
            return True
        
        # Alta confianza y buenos resultados
        if overall_confidence >= self.thresholds["confidence_for_no_refinement"] and len(valid_products) >= 3:
            return False
        
        # Por defecto, no refinamiento si hay algunos productos válidos
        return len(valid_products) < 3
    
    async def _generate_refinement_question(
        self,
        valid_products: List[Dict],
        invalid_products: List[Dict],
        understanding: ProductUnderstanding,
        validation: Dict[str, Any]
    ) -> str:
        """Genera una pregunta de refinamiento inteligente"""
        
        # Determinar el tipo de problema principal
        main_issue = validation.get("main_issue", "low_relevance")
        
        # Si la IA sugiere información faltante específica
        missing_info = validation.get("missing_information", [])
        if missing_info:
            if "amperaje" in missing_info:
                return "¿Qué amperaje necesitas para el " + (understanding.product_type or "producto") + "?"
            elif "voltaje" in missing_info:
                return "¿Para qué voltaje lo necesitas? ¿230V o 400V?"
            elif "potencia" in missing_info:
                return "¿Qué potencia necesitas?"
            elif "uso" in missing_info:
                return "¿Es para uso doméstico o industrial?"
        
        # Seleccionar template según el problema
        if main_issue == "too_many_results" or len(valid_products) > 15:
            template = self.refinement_templates["too_many_results"][0]
            return template.format(count=len(valid_products))
        
        elif main_issue == "low_relevance":
            template = self.refinement_templates["low_relevance"][1]
            return template.format(product=understanding.product_type or "producto")
        
        elif main_issue == "ambiguous":
            template = self.refinement_templates["ambiguous"][1]
            return template.format(product=understanding.product_type or "producto")
        
        # Si no hay especificaciones
        if not understanding.specifications:
            return self.refinement_templates["missing_specs"][0]
        
        # Por defecto
        return "Los resultados no son perfectos. ¿Podrías darme más detalles sobre lo que necesitas?"
    
    def _calculate_validation_score(
        self,
        valid_products: List[Dict],
        total_found: int
    ) -> float:
        """Calcula el score general de validación"""
        
        if not valid_products:
            return 0.0
        
        # Promedio de scores de productos válidos
        avg_score = sum(p.get("relevance_score", 0) for p in valid_products) / len(valid_products)
        
        # Penalización si hay muy pocos productos válidos
        ratio_penalty = min(1.0, len(valid_products) / 5)  # Ideal: 5+ productos
        
        # Score final
        return avg_score * ratio_penalty
    
    def _fallback_validation(self, search_results: SearchResults) -> ValidationResult:
        """Validación de fallback cuando falla la IA"""
        
        # Aceptar los primeros 10 productos con score medio
        valid_products = []
        for product in search_results.products[:10]:
            product["relevance_score"] = 0.6
            product["relevance_reason"] = "Validación automática"
            valid_products.append(product)
        
        return ValidationResult(
            valid_products=valid_products,
            invalid_products=[],
            needs_refinement=len(valid_products) < 3,
            refinement_question="¿Estos productos son lo que buscabas?" if len(valid_products) > 0 else None,
            validation_score=0.6,
            rejection_reasons=[]
        )
    
    def generate_refinement_question(
        self,
        products: List[Dict[str, Any]],
        understanding: ProductUnderstanding
    ) -> str:
        """
        Implementación síncrona de la interfaz para compatibilidad
        """
        # Usar la implementación asíncrona interna de forma síncrona
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            validation = {"main_issue": "general", "missing_information": []}
            return loop.run_until_complete(
                self._generate_refinement_question(
                    products,
                    [],
                    understanding,
                    validation
                )
            )
        finally:
            loop.close()
    
    async def generate_refinement_suggestions(
        self,
        current_results: List[Dict[str, Any]],
        user_feedback: Optional[str] = None
    ) -> List[str]:
        """
        Genera sugerencias de refinamiento basadas en resultados actuales
        Implementación de la interfaz
        """
        suggestions = []
        
        # Analizar marcas disponibles
        brands = list(set(p.get("brand", "") for p in current_results if p.get("brand")))
        if len(brands) > 3:
            suggestions.append(f"Filtrar por marca: {', '.join(brands[:3])}")
        
        # Analizar rangos de precio
        prices = [p.get("price", 0) for p in current_results if p.get("price")]
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            if max_price > min_price * 2:
                suggestions.append(f"Especificar rango de precio")
        
        # Sugerir especificaciones
        suggestions.append("Indicar especificaciones técnicas necesarias")
        suggestions.append("Aclarar si es para uso doméstico o industrial")
        
        return suggestions[:4]  # Máximo 4 sugerencias

# Instancia singleton
results_validator = ResultsValidatorAgent()