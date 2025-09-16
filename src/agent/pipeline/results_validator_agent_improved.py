"""
✅ Results Validator Agent MEJORADO
Agente que valida inteligentemente la calidad de los resultados de búsqueda
y genera preguntas de refinamiento contextuales cuando es necesario
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from .agent_interfaces import (
    IResultsValidatorAgent,
    SearchResults,
    ValidationResult,
    ProductUnderstanding
)

# Cargar configuración
load_dotenv("env.agent")

from openai import OpenAI

# Configurar cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)

class ImprovedResultsValidatorAgent(IResultsValidatorAgent):
    """
    Agente validador de resultados con IA avanzada
    
    Características clave:
    - Evaluación inteligente de calidad de resultados
    - Detección de necesidad real de refinamiento
    - Generación de preguntas contextuales específicas
    - Sin respuestas mecánicas repetitivas
    """
    
    def __init__(self):
        self.logger = logger
        self.name = "ImprovedResultsValidator"
        
        # Umbrales adaptativos según contexto
        self.quality_thresholds = {
            "excellent": {
                "min_relevance": 0.85,
                "min_products": 1,
                "max_products": 10,
                "confidence": 0.9
            },
            "good": {
                "min_relevance": 0.7,
                "min_products": 2,
                "max_products": 20,
                "confidence": 0.75
            },
            "acceptable": {
                "min_relevance": 0.6,
                "min_products": 3,
                "max_products": 30,
                "confidence": 0.6
            },
            "needs_refinement": {
                "min_relevance": 0.4,
                "confidence": 0.4
            }
        }
    
    async def validate(self, *args, **kwargs):
        """Método principal de validación"""
        return await self.validate_results(*args, **kwargs)
    
    async def process(self, *args, **kwargs):
        """Método process requerido por la interfaz"""
        return await self.validate_results(*args, **kwargs)
    
    async def generate_refinement_question(self, understanding: ProductUnderstanding, search_results: SearchResults) -> str:
        """Genera pregunta de refinamiento - requerido por interfaz"""
        # Evaluar calidad primero
        quality = await self._assess_results_quality(search_results, understanding, "")
        needs_refine, reason = self._determine_refinement_need(quality, search_results.total_count)
        
        if needs_refine:
            return await self._generate_contextual_refinement_question(
                search_results.products[:5],
                understanding,
                "",
                reason,
                quality
            )
        return ""
    
    async def validate_results(
        self,
        search_results: SearchResults,
        original_request: str,
        understanding: ProductUnderstanding
    ) -> ValidationResult:
        """
        Valida inteligentemente los resultados de búsqueda
        
        Proceso:
        1. Evalúa calidad general de resultados
        2. Determina si realmente necesita refinamiento
        3. Genera pregunta contextual específica si es necesario
        """
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🔍 Validando {search_results.total_count} resultados")
            
            # Caso especial: Sin resultados
            if not search_results.products or search_results.total_count == 0:
                return await self._handle_no_results(understanding, original_request)
            
            # 1. Evaluar calidad general de los resultados
            quality_assessment = await self._assess_results_quality(
                search_results,
                understanding,
                original_request
            )
            
            # 2. Determinar si necesita refinamiento basado en calidad real
            needs_refinement, refinement_reason = self._determine_refinement_need(
                quality_assessment,
                search_results.total_count
            )
            
            # 3. Generar pregunta de refinamiento SOLO si es necesario
            refinement_question = None
            if needs_refinement:
                refinement_question = await self._generate_contextual_refinement_question(
                    search_results.products[:5],
                    understanding,
                    original_request,
                    refinement_reason,
                    quality_assessment
                )
            
            # 4. Filtrar productos válidos basado en scores
            valid_products = []
            invalid_products = []
            
            products_to_validate = search_results.products if search_results.products else []
            for product in products_to_validate[:30]:  # Máximo 30 productos
                if product:  # Verificar que el producto no sea None
                    relevance = self._calculate_product_relevance(
                        product,
                        understanding,
                        quality_assessment
                    )
                    
                    if relevance >= 0.6:  # Umbral más flexible
                        if "relevance_score" not in product or product.get("relevance_score") is None:
                            product["relevance_score"] = relevance
                        valid_products.append(product)
                    else:
                        invalid_products.append(product)
            
            # 5. Calcular score de validación final
            validation_score = self._calculate_final_score(
                quality_assessment,
                valid_products,
                search_results.total_count
            )
            
            # Log de decisión
            self.logger.info(f"📊 Calidad: {quality_assessment.get('quality_level', 'unknown')}")
            self.logger.info(f"✅ Productos válidos: {len(valid_products)}/{search_results.total_count}")
            self.logger.info(f"🎯 Score de validación: {validation_score:.2f}")
            self.logger.info(f"🔄 Necesita refinamiento: {needs_refinement}")
            if refinement_question:
                self.logger.info(f"❓ Pregunta: {refinement_question[:100]}...")
            
            return ValidationResult(
                valid_products=valid_products,
                invalid_products=invalid_products,
                needs_refinement=needs_refinement,
                refinement_question=refinement_question,
                validation_score=validation_score,
                rejection_reasons=[]
            )
            
        except Exception as e:
            self.logger.error(f"Error en validación: {e}")
            # Fallback inteligente
            return self._intelligent_fallback(search_results, understanding)
    
    async def _assess_results_quality(
        self,
        search_results: SearchResults,
        understanding: ProductUnderstanding,
        original_query: str
    ) -> Dict[str, Any]:
        """
        Evalúa la calidad general de los resultados con IA
        """
        
        # Preparar muestra de productos para análisis
        sample_products = []
        for product in search_results.products[:10] if search_results.products else []:
            name = product.get("name") if product else ""
            sample_products.append({
                "name": (name[:100] if name else "Sin nombre"),
                "brand": product.get("brand", "") if product else "",
                "price": product.get("price", 0) if product else 0,
                "category": product.get("category", "") if product else "",
                "key_specs": self._extract_key_specs(product) if product else []
            })
        
        prompt = f"""
Analiza la calidad de estos resultados de búsqueda para un usuario de tienda eléctrica.

SOLICITUD ORIGINAL: "{original_query}"

BÚSQUEDA REALIZADA:
- Tipo de producto: {understanding.product_type}
- Marca solicitada: {understanding.brand or "No especificada"}
- Especificaciones: {json.dumps(understanding.specifications, ensure_ascii=False)}

RESULTADOS OBTENIDOS:
- Total encontrados: {search_results.total_count}
- Muestra de productos:
{json.dumps(sample_products, indent=2, ensure_ascii=False)}

EVALÚA y responde en JSON:
{{
    "quality_level": "excellent|good|acceptable|poor",
    "confidence_score": 0.85,  // 0.0 a 1.0
    "main_issues": [],  // Lista de problemas encontrados
    "strengths": [],  // Aspectos positivos de los resultados
    "matches_intent": true,  // Si los resultados coinciden con la intención
    "specificity_level": "very_specific|specific|general|too_general",
    "recommendation": "show_results|ask_refinement|suggest_alternatives",
    "missing_information": [],  // Información que ayudaría a mejorar resultados
    "dominant_category": "",  // Categoría predominante en resultados
    "price_range_appropriate": true,
    "brand_consistency": true  // Si pidió marca, ¿los resultados la tienen?
}}

IMPORTANTE: Sé ESTRICTO pero JUSTO. Si hay 2-5 productos muy relevantes, es EXCELLENT.
Si hay 10-20 productos relevantes pero variados, es GOOD.
Si hay más de 30 productos poco específicos, considera pedir refinamiento.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en evaluación de calidad de búsquedas de productos eléctricos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parsear JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            self.logger.error(f"Error evaluando calidad: {e}")
            # Evaluación heurística de respaldo
            return self._heuristic_quality_assessment(search_results, understanding)
    
    def _determine_refinement_need(
        self,
        quality_assessment: Dict[str, Any],
        total_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Determina si REALMENTE necesita refinamiento
        
        Returns:
            (needs_refinement, reason)
        """
        
        quality_level = quality_assessment.get("quality_level", "acceptable")
        confidence = quality_assessment.get("confidence_score", 0.7)
        recommendation = quality_assessment.get("recommendation", "show_results")
        
        # Casos donde NO necesita refinamiento
        if quality_level in ["excellent", "good"]:
            return False, None
        
        # Si hay pocos productos pero muy relevantes, NO pedir refinamiento
        if total_count <= 5 and confidence >= 0.8:
            return False, None
        
        # Si la recomendación es mostrar resultados, confiar en eso
        if recommendation == "show_results":
            return False, None
        
        # Casos donde SÍ necesita refinamiento
        if quality_level == "poor":
            return True, "low_quality"
        
        if total_count > 30 and confidence < 0.7:
            return True, "too_many_results"
        
        if quality_assessment.get("specificity_level") == "too_general":
            return True, "too_general"
        
        if quality_assessment.get("missing_information"):
            return True, "missing_info"
        
        # Por defecto, NO pedir refinamiento innecesario
        return False, None
    
    async def _generate_contextual_refinement_question(
        self,
        products: List[Dict],
        understanding: ProductUnderstanding,
        original_query: str,
        refinement_reason: str,
        quality_assessment: Dict[str, Any]
    ) -> str:
        """
        Genera una pregunta de refinamiento CONTEXTUAL y ESPECÍFICA
        NO genérica ni mecánica
        """
        
        missing_info = quality_assessment.get("missing_information", [])
        main_issues = quality_assessment.get("main_issues", [])
        
        # Analizar qué información falta específicamente
        context = {
            "reason": refinement_reason,
            "missing": missing_info,
            "issues": main_issues,
            "current_results": len(products),
            "product_type": understanding.product_type,
            "has_brand": bool(understanding.brand),
            "has_specs": bool(understanding.specifications)
        }
        
        prompt = f"""
Eres un vendedor experto en material eléctrico. Genera una pregunta ESPECÍFICA para ayudar al cliente a encontrar exactamente lo que busca.

SITUACIÓN ACTUAL:
- Cliente busca: "{original_query}"
- Tipo de producto identificado: {understanding.product_type or "no especificado"}
- Encontré {len(products)} productos pero necesito más información
- Razón: {refinement_reason}

PRODUCTOS QUE TENGO (ejemplos):
{json.dumps([p.get("name", "")[:60] for p in products[:3]], ensure_ascii=False)}

INFORMACIÓN QUE AYUDARÍA:
{missing_info if missing_info else ["especificaciones técnicas", "uso previsto", "marca preferida"]}

BASÁNDOTE EN EL TIPO DE PRODUCTO, PREGUNTA POR:

Si es DIFERENCIAL → Amperaje (25A, 40A, 63A), Sensibilidad (30mA, 300mA), Número de polos
Si es MAGNETOTÉRMICO → Amperaje (10A, 16A, 20A, 25A), Curva (B, C, D), Número de polos  
Si es CABLE → Sección (1.5mm², 2.5mm², 4mm², 6mm²), Color, Longitud en metros
Si es ENCHUFE → Tipo (schuko, industrial), Montaje (empotrar, superficie), Color
Si es LÁMPARA → Potencia en W, Tipo (LED, halógena), Uso (interior, exterior)
Si es INTERRUPTOR → Tipo (simple, conmutador, cruzamiento), Serie/Marca, Color
Si es CONTADOR → Tipo (monofásico, trifásico), Conexión (directa, con transformador)

IMPORTANTE:
- SÉ ESPECÍFICO: Menciona valores concretos que tienes disponibles
- SÉ ÚTIL: Si hay pocas opciones, menciónalas todas
- SÉ NATURAL: Como si estuvieras en el mostrador de la tienda
- NO seas genérico ni uses frases vagas

Responde SOLO con la pregunta en español, directa y amigable."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un vendedor experto en material eléctrico ayudando a un cliente."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            question = response.choices[0].message.content.strip()
            
            # Limpiar respuesta
            question = question.replace('"', '').replace("'", '')
            
            # Asegurar que termina con signo de interrogación
            if not question.endswith('?'):
                question += '?'
            
            return question
            
        except Exception as e:
            self.logger.error(f"Error generando pregunta: {e}")
            # Pregunta de respaldo basada en contexto
            return self._generate_fallback_question(understanding, refinement_reason)
    
    def _calculate_product_relevance(
        self,
        product: Dict,
        understanding: ProductUnderstanding,
        quality_assessment: Dict[str, Any]
    ) -> float:
        """
        Calcula la relevancia de un producto individual
        """
        
        score = 0.5  # Base
        
        # Boost por coincidencia de tipo
        if understanding.product_type:
            product_name = (product.get("name") or "").lower()
            if understanding.product_type.lower() in product_name:
                score += 0.2
        
        # Boost por marca correcta
        if understanding.brand:
            product_brand = (product.get("brand") or "").lower()
            if understanding.brand.lower() == product_brand:
                score += 0.15
        
        # Boost por especificaciones coincidentes
        for spec_key, spec_value in understanding.specifications.items():
            if self._product_has_spec(product, spec_key, spec_value):
                score += 0.1
        
        # Ajuste por calidad general
        quality_level = quality_assessment.get("quality_level", "acceptable")
        if quality_level == "excellent":
            score *= 1.2
        elif quality_level == "poor":
            score *= 0.8
        
        return min(1.0, max(0.0, score))
    
    def _product_has_spec(self, product: Dict, spec_key: str, spec_value: Any) -> bool:
        """Verifica si un producto tiene una especificación"""
        
        # Buscar en nombre
        product_name = (product.get("name") or "").lower()
        if spec_value is not None and str(spec_value).lower() in product_name:
            return True
        
        # Buscar en descripción
        description = (product.get("description") or "").lower()
        if spec_value is not None and str(spec_value).lower() in description:
            return True
        
        # Buscar en atributos
        attributes = product.get("attributes") or {}
        if spec_key in attributes and attributes[spec_key] is not None and spec_value is not None:
            if str(spec_value).lower() in str(attributes[spec_key]).lower():
                return True
        
        return False
    
    def _calculate_final_score(
        self,
        quality_assessment: Dict[str, Any],
        valid_products: List[Dict],
        total_count: int
    ) -> float:
        """
        Calcula el score de validación final
        """
        
        base_score = quality_assessment.get("confidence_score", 0.7)
        
        # Ajustar por cantidad de productos válidos
        if len(valid_products) == 0:
            return 0.0
        elif len(valid_products) <= 5:
            # Pocos pero buenos es mejor que muchos mediocres
            if base_score >= 0.8:
                return base_score
        elif len(valid_products) > 30:
            # Demasiados productos reduce el score
            base_score *= 0.8
        
        return min(1.0, max(0.0, base_score))
    
    def _extract_key_specs(self, product: Dict) -> List[str]:
        """Extrae especificaciones clave de un producto"""
        
        specs = []
        
        # Extraer de nombre
        name = product.get("name") or ""
        if not isinstance(name, str):
            name = str(name) if name is not None else ""
        
        # Buscar patrones comunes
        import re
        
        # Amperaje
        amp_match = re.search(r'(\d+)\s*A\b', name)
        if amp_match:
            specs.append(f"{amp_match.group(1)}A")
        
        # Voltaje
        volt_match = re.search(r'(\d+)\s*V\b', name)
        if volt_match:
            specs.append(f"{volt_match.group(1)}V")
        
        # Potencia
        watt_match = re.search(r'(\d+)\s*W\b', name)
        if watt_match:
            specs.append(f"{watt_match.group(1)}W")
        
        # mA (miliamperios)
        ma_match = re.search(r'(\d+)\s*mA\b', name)
        if ma_match:
            specs.append(f"{ma_match.group(1)}mA")
        
        return specs
    
    def _heuristic_quality_assessment(
        self,
        search_results: SearchResults,
        understanding: ProductUnderstanding
    ) -> Dict[str, Any]:
        """
        Evaluación heurística de respaldo cuando falla la IA
        """
        
        total = search_results.total_count
        
        if total == 0:
            quality_level = "poor"
            confidence = 0.0
        elif total <= 5:
            quality_level = "excellent"
            confidence = 0.9
        elif total <= 15:
            quality_level = "good"
            confidence = 0.75
        elif total <= 30:
            quality_level = "acceptable"
            confidence = 0.6
        else:
            quality_level = "poor"
            confidence = 0.4
        
        return {
            "quality_level": quality_level,
            "confidence_score": confidence,
            "main_issues": ["too_many"] if total > 30 else [],
            "strengths": ["specific"] if total <= 10 else [],
            "matches_intent": total > 0,
            "specificity_level": "specific" if total <= 15 else "general",
            "recommendation": "show_results" if total <= 20 else "ask_refinement",
            "missing_information": [],
            "dominant_category": "",
            "price_range_appropriate": True,
            "brand_consistency": True
        }
    
    def _generate_fallback_question(
        self,
        understanding: ProductUnderstanding,
        reason: str
    ) -> str:
        """
        Genera pregunta de respaldo cuando falla la IA
        """
        
        if reason == "too_many_results":
            if not understanding.brand:
                return "Hay muchas opciones disponibles. ¿Prefieres alguna marca en particular?"
            elif not understanding.specifications.get("amperaje"):
                return f"¿Qué amperaje necesitas para el {understanding.product_type}?"
            else:
                return "¿Es para uso doméstico o industrial?"
        
        elif reason == "missing_info":
            if understanding.product_type == "diferencial":
                return "¿Necesitas el diferencial de 25A, 40A o 63A?"
            elif understanding.product_type == "cable":
                return "¿Qué sección de cable necesitas? ¿1.5mm², 2.5mm² o 4mm²?"
            elif understanding.product_type == "magnetotérmico":
                return "¿Qué curva prefieres? Tenemos curva C y curva D disponibles"
            else:
                return f"¿Podrías especificar las características técnicas del {understanding.product_type}?"
        
        elif reason == "low_quality":
            return "No encuentro exactamente lo que buscas. ¿Podrías describir el producto de otra manera?"
        
        else:
            return f"¿Qué características específicas necesitas para el {understanding.product_type}?"
    
    def _intelligent_fallback(
        self,
        search_results: SearchResults,
        understanding: ProductUnderstanding
    ) -> ValidationResult:
        """
        Fallback inteligente cuando falla la validación principal
        """
        
        # Si hay menos de 10 productos, probablemente sean buenos
        if search_results.total_count <= 10:
            return ValidationResult(
                valid_products=search_results.products[:10],
                invalid_products=[],
                needs_refinement=False,
                refinement_question=None,
                validation_score=0.75,
                rejection_reasons=[]
            )
        
        # Si hay entre 10-30, pedir refinamiento solo si no hay marca
        elif search_results.total_count <= 30:
            needs_refine = not understanding.brand
            question = None
            if needs_refine:
                question = self._generate_fallback_question(understanding, "missing_info")
            
            return ValidationResult(
                valid_products=search_results.products[:20],
                invalid_products=[],
                needs_refinement=needs_refine,
                refinement_question=question,
                validation_score=0.6,
                rejection_reasons=[]
            )
        
        # Si hay más de 30, definitivamente necesita refinamiento
        else:
            return ValidationResult(
                valid_products=search_results.products[:10],
                invalid_products=[],
                needs_refinement=True,
                refinement_question=self._generate_fallback_question(understanding, "too_many_results"),
                validation_score=0.4,
                rejection_reasons=[]
            )
    
    async def _handle_no_results(
        self,
        understanding: ProductUnderstanding,
        original_query: str
    ) -> ValidationResult:
        """
        Maneja el caso de no resultados de forma inteligente
        """
        
        # Generar sugerencia específica
        suggestion = f"No encontré {understanding.product_type or 'ese producto'}. "
        
        if understanding.brand:
            suggestion += f"¿Quizás buscas otra marca similar a {understanding.brand}?"
        else:
            suggestion += "¿Podrías describir el producto de otra forma o buscar algo similar?"
        
        return ValidationResult(
            valid_products=[],
            invalid_products=[],
            needs_refinement=True,
            refinement_question=suggestion,
            validation_score=0.0,
            rejection_reasons=["No se encontraron productos"]
        )