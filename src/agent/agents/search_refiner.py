#!/usr/bin/env python3
"""
Search Refiner Agent
Analiza las búsquedas de productos y determina si necesita más información
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity

logger = logging.getLogger(__name__)


@dataclass
class SearchRefinement:
    """Resultado del refinamiento de búsqueda"""
    is_complete: bool  # Si tiene suficiente información
    refined_query: str  # Query refinada/mejorada
    missing_info: List[str] = field(default_factory=list)  # Info que falta
    clarification_questions: List[str] = field(default_factory=list)  # Preguntas al usuario
    extracted_specs: Dict[str, Any] = field(default_factory=dict)  # Especificaciones extraídas
    search_strategy: str = "standard"  # standard, specific, broad
    confidence: float = 0.8


class SearchRefinerAgent:
    """Agente para refinar búsquedas de productos"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Especificaciones importantes por tipo de producto
        self.important_specs = {
            "diferencial": ["amperaje", "sensibilidad", "polos", "tipo", "marca"],
            "magnetotermico": ["amperaje", "curva", "polos", "poder_corte", "marca"],
            "cable": ["seccion", "tipo", "metros", "color", "uso"],
            "lampara": ["tipo", "potencia", "casquillo", "temperatura_color", "uso"],
            "termo": ["capacidad", "potencia", "instalacion", "marca"],
            "enrollacables": ["metros", "seccion", "uso", "con_termico"],
            "transformador": ["potencia", "entrada", "salida", "tipo"]
        }
    
    async def refine_search(self, user_message: str, context: Optional[Dict] = None) -> SearchRefinement:
        """
        Refina una búsqueda de productos
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (historial, productos previos, etc.)
            
        Returns:
            SearchRefinement con el análisis
        """
        
        # Contexto de productos previos si existe
        context_str = ""
        if context:
            if context.get("previous_products"):
                context_str += "\nProductos mostrados previamente:\n"
                for prod in context["previous_products"][:3]:
                    context_str += f"- {prod.get('name', 'Sin nombre')}\n"
            
            if context.get("conversation_history"):
                context_str += "\nHistorial reciente:\n"
                for msg in context["conversation_history"][-2:]:
                    context_str += f"- {msg}\n"
        
        refinement_prompt = f"""Analiza esta búsqueda de productos eléctricos y determina si tiene suficiente información para encontrar productos específicos.

BÚSQUEDA DEL CLIENTE: "{user_message}"
{context_str}

PRODUCTOS ELÉCTRICOS COMUNES Y SUS ESPECIFICACIONES IMPORTANTES:

1. DIFERENCIALES:
   - Amperaje (25A, 40A, 63A, etc.)
   - Sensibilidad (30mA doméstico, 300mA industrial)
   - Polos (2P, 4P)
   - Tipo (AC, A, B, F)
   - Superinmunizado o normal

2. MAGNETOTÉRMICOS/AUTOMÁTICOS:
   - Amperaje (6A, 10A, 16A, 20A, 25A, 32A, etc.)
   - Curva (B, C, D)
   - Polos (1P, 2P, 3P, 4P)
   - Poder de corte (6kA, 10kA)

3. CABLES:
   - Sección (1.5mm², 2.5mm², 4mm², 6mm², etc.)
   - Tipo (unipolar, manguera, paralelo)
   - Metros necesarios
   - Color (si es relevante)
   - Uso (doméstico, industrial)

4. LÁMPARAS/ILUMINACIÓN:
   - Tipo (LED, halógena, incandescente)
   - Potencia (W)
   - Casquillo (E27, E14, GU10, etc.)
   - Temperatura color (cálida, neutra, fría)
   - Uso (interior, exterior, industrial)

5. TERMOS/CALENTADORES:
   - Capacidad (30L, 50L, 80L, 100L, etc.)
   - Instalación (vertical, horizontal)
   - Potencia

ANALIZA:
1. ¿Qué tipo de producto busca?
2. ¿Qué especificaciones menciona?
3. ¿Qué información CRÍTICA falta para una búsqueda precisa?
4. ¿Necesita clarificación o tiene suficiente info?

ESTRATEGIAS DE BÚSQUEDA:
- "specific": Búsqueda muy específica (tiene todas las specs)
- "standard": Búsqueda normal (tiene info básica)
- "broad": Búsqueda amplia (poca información)

Responde con JSON:
{{
    "is_complete": true/false,
    "refined_query": "consulta mejorada para búsqueda",
    "missing_info": ["spec1", "spec2"],
    "clarification_questions": ["pregunta1", "pregunta2"],
    "extracted_specs": {{
        "tipo_producto": "diferencial",
        "amperaje": "40A",
        "sensibilidad": "30mA",
        "otros": "valor"
    }},
    "search_strategy": "specific/standard/broad",
    "reasoning": "explicación breve"
}}

EJEMPLOS:

Usuario: "necesito un diferencial"
Respuesta: {{
    "is_complete": false,
    "refined_query": "diferencial interruptor",
    "missing_info": ["amperaje", "sensibilidad", "polos"],
    "clarification_questions": [
        "¿De cuántos amperios necesitas el diferencial? (25A, 40A, 63A)",
        "¿Para uso doméstico (30mA) o industrial (300mA)?",
        "¿Bipolar (2P) o tetrapolar (4P)?"
    ],
    "extracted_specs": {{"tipo_producto": "diferencial"}},
    "search_strategy": "broad"
}}

Usuario: "busco un diferencial de 40A 30mA bipolar"
Respuesta: {{
    "is_complete": true,
    "refined_query": "diferencial 40A 30mA 2P bipolar",
    "missing_info": [],
    "clarification_questions": [],
    "extracted_specs": {{
        "tipo_producto": "diferencial",
        "amperaje": "40A",
        "sensibilidad": "30mA",
        "polos": "2P"
    }},
    "search_strategy": "specific"
}}"""

        try:
            response = await self.gpt5.create_response(
                input_text=refinement_prompt,
                model="gpt-5",
                reasoning_effort=ReasoningEffort.HIGH,
                verbosity=Verbosity.MEDIUM
            )
            
            # Parsear respuesta
            import json
            try:
                result = json.loads(response.content)
                
                refinement = SearchRefinement(
                    is_complete=result.get("is_complete", False),
                    refined_query=result.get("refined_query", user_message),
                    missing_info=result.get("missing_info", []),
                    clarification_questions=result.get("clarification_questions", []),
                    extracted_specs=result.get("extracted_specs", {}),
                    search_strategy=result.get("search_strategy", "standard"),
                    confidence=0.9 if result.get("is_complete") else 0.6
                )
                
                self.logger.info(f"Búsqueda refinada: completa={refinement.is_complete}, "
                               f"estrategia={refinement.search_strategy}")
                
                return refinement
                
            except json.JSONDecodeError:
                self.logger.error("Error parseando respuesta JSON")
                return self._fallback_refinement(user_message)
                
        except Exception as e:
            self.logger.error(f"Error en refinamiento: {e}")
            return self._fallback_refinement(user_message)
    
    def _fallback_refinement(self, user_message: str) -> SearchRefinement:
        """Refinamiento básico como fallback"""
        
        message_lower = user_message.lower()
        
        # Detectar tipo de producto
        product_type = None
        for prod_type in self.important_specs.keys():
            if prod_type in message_lower:
                product_type = prod_type
                break
        
        # Si no detecta producto, búsqueda amplia
        if not product_type:
            return SearchRefinement(
                is_complete=False,
                refined_query=user_message,
                missing_info=["tipo_producto"],
                clarification_questions=["¿Qué tipo de producto estás buscando?"],
                search_strategy="broad",
                confidence=0.5
            )
        
        # Verificar especificaciones mencionadas
        specs_needed = self.important_specs.get(product_type, [])
        missing = []
        
        # Verificación simple de especificaciones
        if product_type in ["diferencial", "magnetotermico"]:
            # Buscar amperaje
            import re
            amperaje_match = re.search(r'\d+\s*[aA]', message_lower)
            if not amperaje_match:
                missing.append("amperaje")
        
        # Si faltan muchas specs, no está completo
        if len(missing) >= 2:
            questions = []
            if "amperaje" in missing:
                questions.append("¿De cuántos amperios lo necesitas?")
            
            return SearchRefinement(
                is_complete=False,
                refined_query=user_message,
                missing_info=missing,
                clarification_questions=questions,
                extracted_specs={"tipo_producto": product_type},
                search_strategy="standard",
                confidence=0.7
            )
        
        # Si tiene info básica, está completo
        return SearchRefinement(
            is_complete=True,
            refined_query=user_message,
            missing_info=[],
            clarification_questions=[],
            extracted_specs={"tipo_producto": product_type},
            search_strategy="standard",
            confidence=0.8
        )
    
    def generate_clarification_message(self, refinement: SearchRefinement) -> str:
        """
        Genera un mensaje amigable de clarificación para el usuario
        
        Args:
            refinement: Resultado del refinamiento
            
        Returns:
            Mensaje formateado para el usuario
        """
        
        if refinement.is_complete:
            return ""
        
        message = "Para encontrar exactamente lo que buscas, "
        
        if len(refinement.clarification_questions) == 1:
            message += f"me ayudaría saber:\n\n{refinement.clarification_questions[0]}"
        elif len(refinement.clarification_questions) > 1:
            message += "necesitaría algunos detalles:\n\n"
            for i, question in enumerate(refinement.clarification_questions, 1):
                message += f"{i}. {question}\n"
        else:
            message += "¿podrías darme más detalles sobre el producto que buscas?"
        
        return message


# Instancia singleton
search_refiner = SearchRefinerAgent()