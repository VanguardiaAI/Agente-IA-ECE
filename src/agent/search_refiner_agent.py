#!/usr/bin/env python3
"""
Agente de Refinamiento de Búsqueda
Intercepta búsquedas de productos y las refina mediante interacción con el usuario
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class RefinementState(Enum):
    """Estados del proceso de refinamiento"""
    INITIAL = "initial"
    ASKING_BRAND = "asking_brand"
    ASKING_ATTRIBUTE = "asking_attribute"
    REFINED = "refined"
    COMPLETED = "completed"

@dataclass
class SearchContext:
    """Contexto de búsqueda para mantener estado entre iteraciones"""
    original_query: str
    refined_query: str = ""
    current_state: RefinementState = RefinementState.INITIAL
    iterations: int = 0
    max_iterations: int = 3
    
    # Información recolectada
    selected_brand: Optional[str] = None
    selected_attributes: Dict[str, str] = field(default_factory=dict)
    excluded_terms: List[str] = field(default_factory=list)
    
    # Resultados de búsqueda
    last_search_count: int = 0
    last_search_results: List[Dict] = field(default_factory=list)
    available_brands: List[str] = field(default_factory=list)
    available_attributes: Dict[str, List[str]] = field(default_factory=dict)
    
    # Umbrales
    too_many_threshold: int = 10  # Más de 10 resultados es demasiado
    acceptable_threshold: int = 8  # 8 o menos es aceptable
    ideal_threshold: int = 5  # 5 o menos es ideal

class SearchRefinerAgent:
    """Agente que refina búsquedas de productos mediante interacción iterativa"""
    
    def __init__(self):
        self.contexts: Dict[str, SearchContext] = {}  # Contextos por sesión
        
        # Marcas comunes de material eléctrico (mantenemos para detección de marcas)
        self.common_brands = [
            'Schneider', 'ABB', 'Legrand', 'Hager', 'Siemens',
            'Gewiss', 'Chint', 'Simon', 'BJC', 'Niessen',
            'Merlin Gerin', 'Bticino', 'Circutor', 'Phoenix Contact',
            'Finder', 'Omron', 'Carlo Gavazzi', 'Lovato'
        ]
        
        # Grupos de sinónimos para búsqueda expandida
        self.synonym_groups = [
            ['interruptor', 'switch', 'conmutador', 'pulsador'],
            ['automático', 'magnetotérmico', 'PIA', 'breaker', 'interruptor automático'],
            ['diferencial', 'RCD', 'ID', 'interruptor diferencial'],
            ['cable', 'manguera', 'conductor', 'hilo', 'cableado'],
            ['lámpara', 'bombilla', 'foco', 'luminaria', 'luz', 'iluminación'],
            ['enchufe', 'toma', 'base', 'schuko', 'toma corriente'],
            ['motor', 'motor eléctrico', 'motorreductor'],
            ['transformador', 'trafo', 'fuente alimentación'],
            ['cuadro', 'cuadro eléctrico', 'caja distribución', 'armario eléctrico'],
            ['enrollacables', 'recoge cables', 'organizador cables', 'recogecables']
        ]
    
    def get_or_create_context(self, session_id: str, query: str) -> SearchContext:
        """Obtiene o crea un contexto de búsqueda para la sesión"""
        if session_id not in self.contexts:
            self.contexts[session_id] = SearchContext(original_query=query)
        return self.contexts[session_id]
    
    def expand_query_with_synonyms(self, query: str) -> List[str]:
        """
        Expande una consulta con sinónimos relevantes
        Returns: Lista de términos expandidos (incluyendo el original)
        """
        query_lower = query.lower()
        expanded_terms = [query]
        
        # Buscar sinónimos para cada palabra en la consulta
        for synonym_group in self.synonym_groups:
            for synonym in synonym_group:
                if synonym in query_lower:
                    # Añadir todos los sinónimos del grupo (excepto el ya presente)
                    for alt_synonym in synonym_group:
                        if alt_synonym != synonym and alt_synonym not in expanded_terms:
                            # Reemplazar el término original con el sinónimo
                            expanded_query = query_lower.replace(synonym, alt_synonym)
                            if expanded_query not in [eq.lower() for eq in expanded_terms]:
                                expanded_terms.append(expanded_query)
                    break  # Solo procesar el primer match en cada grupo
        
        return expanded_terms[:5]  # Limitar a 5 variaciones para no sobrecargar
    
    def analyze_query_specificity(self, query: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Analiza si una consulta es suficientemente específica
        Returns: (es_especifica, detalles_extraidos)
        """
        query_lower = query.lower()
        details = {
            'product_type': None,
            'brand': None,
            'technical_specs': {},
            'is_specific': False,
            'specificity_score': 0  # Puntuación de especificidad
        }
        
        # Detectar tipo de producto de forma más inteligente
        # Extraer palabras significativas de la consulta
        import re
        words = re.findall(r'\b[a-záéíóúñ]+\b', query_lower)
        
        # Buscar sustantivos principales que podrían ser productos
        # Excluir palabras comunes que no son productos
        stop_words = {
            # Artículos y preposiciones
            'para', 'con', 'sin', 'de', 'la', 'el', 'los', 'las', 'un', 'una', 'del', 'al',
            # Verbos comunes
            'busco', 'necesito', 'quiero', 'tengo', 'comprar', 'adquirir', 'conseguir',
            # Saludos y cortesías
            'hola', 'buenos', 'buenas', 'dias', 'tardes', 'noches', 'gracias', 'por', 'favor',
            # Conectores
            'que', 'como', 'donde', 'cuando', 'porque', 'pero', 'aunque'
        }
        product_candidates = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Tomar el primer candidato como tipo de producto
        if product_candidates:
            details['product_type'] = product_candidates[0]
            details['specificity_score'] += 1
        else:
            # Si no encontramos nada específico, usar 'productos' como fallback
            details['product_type'] = 'productos'
        
        # Detectar marca
        for brand in self.common_brands:
            if brand.lower() in query_lower:
                details['brand'] = brand
                details['specificity_score'] += 2  # La marca añade mucha especificidad
                break
        
        # Detectar especificaciones técnicas (números con unidades)
        import re
        
        # Amperaje
        amp_match = re.search(r'(\d+)\s*[Aa](?:mp)?(?:perios?)?', query)
        if amp_match:
            details['technical_specs']['amperaje'] = amp_match.group(1) + 'A'
            details['specificity_score'] += 2
        
        # Voltaje
        volt_match = re.search(r'(\d+)\s*[Vv](?:oltios?)?', query)
        if volt_match:
            details['technical_specs']['voltaje'] = volt_match.group(1) + 'V'
            details['specificity_score'] += 2
        
        # Potencia
        power_match = re.search(r'(\d+)\s*[WwKk][Ww]?', query)
        if power_match:
            details['technical_specs']['potencia'] = power_match.group(0)
        
        # Milímetros (sección de cable)
        mm_match = re.search(r'(\d+(?:\.\d+)?)\s*mm2?', query)
        if mm_match:
            details['technical_specs']['seccion'] = mm_match.group(0)
            details['specificity_score'] += 2
        
        # Sensibilidad diferencial
        sens_match = re.search(r'(\d+)\s*m[Aa]', query)
        if sens_match:
            details['technical_specs']['sensibilidad'] = sens_match.group(0)
            details['specificity_score'] += 2
        
        # Detectar curva de disparo
        curve_match = re.search(r'\b[Cc]urva\s*([A-Z])\b|^([A-Z])$', query)
        if curve_match:
            curve = (curve_match.group(1) or curve_match.group(2))
            if curve in ['A', 'B', 'C', 'D', 'K', 'Z']:
                details['technical_specs']['curva'] = curve
                details['specificity_score'] += 1
        
        # Detectar número de polos
        pole_match = re.search(r'(\d)[Pp](?:\+[Nn])?', query)
        if pole_match:
            details['technical_specs']['polos'] = pole_match.group(0)
            details['specificity_score'] += 1
        
        # Analizar longitud de la query y número de términos técnicos
        query_words = len(words)
        technical_terms_count = len(details['technical_specs'])
        
        # Una query es muy específica si:
        # 1. Tiene una puntuación de especificidad >= 3
        # 2. Tiene múltiples especificaciones técnicas
        # 3. Tiene más de 3 palabras significativas (indica descripción detallada)
        # 4. Es un término compuesto que podría ser una categoría (enrollacables, portafusibles, etc.)
        
        # Detectar términos compuestos que podrían ser categorías
        is_compound_term = False
        if len(words) <= 2:  # Una o dos palabras
            # Verificar si es un término compuesto largo y específico
            for word in product_candidates:
                # Palabras muy largas (>12 chars) o que contienen "cables", "fusibles", etc.
                if len(word) >= 12 or ('cable' in word and len(word) >= 10):
                    is_compound_term = True
                    details['specificity_score'] += 2
                    break
        
        if details['specificity_score'] >= 3:
            details['is_specific'] = True
        elif technical_terms_count >= 2:
            details['is_specific'] = True
        elif details['brand'] and technical_terms_count >= 1:
            details['is_specific'] = True
        elif query_words >= 4 and technical_terms_count >= 1:
            details['is_specific'] = True
        elif is_compound_term:
            details['is_specific'] = True
        else:
            details['is_specific'] = False
        
        return details['is_specific'], details
    
    def extract_attributes_from_results(self, search_results: List[Dict]) -> Dict[str, List[str]]:
        """
        Extrae atributos únicos de los resultados de búsqueda
        para sugerir al usuario
        """
        attributes = {
            'brands': set(),
            'amperajes': set(),
            'voltajes': set(),
            'potencias': set(),
            'curvas': set(),
            'polos': set(),
            'sensibilidades': set()
        }
        
        for result in search_results:
            metadata = result.get('metadata', {})
            title = result.get('title', '')
            
            # Extraer marca del título o metadata
            for brand in self.common_brands:
                if brand.lower() in title.lower():
                    attributes['brands'].add(brand)
            
            # Extraer atributos de WooCommerce
            wc_attributes = metadata.get('attributes', {})
            for attr_name, attr_values in wc_attributes.items():
                attr_name_lower = attr_name.lower()
                
                if 'marca' in attr_name_lower and isinstance(attr_values, list):
                    attributes['brands'].update(attr_values)
                elif 'amper' in attr_name_lower or 'intensidad' in attr_name_lower:
                    if isinstance(attr_values, list):
                        attributes['amperajes'].update(attr_values)
                elif 'curva' in attr_name_lower:
                    if isinstance(attr_values, list):
                        attributes['curvas'].update(attr_values)
                elif 'polo' in attr_name_lower:
                    if isinstance(attr_values, list):
                        attributes['polos'].update(attr_values)
            
            # Extraer del título usando regex
            import re
            
            # Amperajes
            amp_matches = re.findall(r'(\d+)\s*[Aa](?:mp)?', title)
            attributes['amperajes'].update([f"{a}A" for a in amp_matches])
            
            # Voltajes
            volt_matches = re.findall(r'(\d+)\s*[Vv]', title)
            attributes['voltajes'].update([f"{v}V" for v in volt_matches])
            
            # Curvas (A, B, C, D, K, Z)
            curve_matches = re.findall(r'[Cc]urva\s*([A-Z])', title)
            attributes['curvas'].update(curve_matches)
            
            # Polos
            pole_matches = re.findall(r'(\d)[Pp](?:\+[Nn])?', title)
            attributes['polos'].update([f"{p}P" for p in pole_matches])
        
        # Convertir sets a listas ordenadas
        return {
            k: sorted(list(v)) for k, v in attributes.items() if v
        }
    
    async def should_refine_search(
        self, 
        session_id: str,
        query: str, 
        search_results: List[Dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determina si se debe refinar la búsqueda y qué preguntar al usuario
        Returns: (necesita_refinamiento, mensaje_para_usuario)
        """
        context = self.get_or_create_context(session_id, query)
        context.last_search_results = search_results
        context.last_search_count = len(search_results)
        
        # Si ya hemos iterado demasiado, no refinar más
        if context.iterations >= context.max_iterations:
            logger.info(f"Máximo de iteraciones alcanzado ({context.max_iterations})")
            return False, None
        
        # Extraer atributos disponibles de los resultados PRIMERO
        available_attrs = self.extract_attributes_from_results(search_results)
        
        # Calcular la diversidad de los resultados
        num_brands = len(available_attrs.get('brands', []))
        num_categories = len(available_attrs.get('categories', []))
        num_specs = sum(len(v) for k, v in available_attrs.items() 
                       if k not in ['brands', 'categories'])
        
        # Decidir si refinar basado en cantidad Y diversidad
        needs_refinement = False
        
        # Criterio 1: Demasiados resultados (>10)
        if len(search_results) > 10:
            needs_refinement = True
            logger.info(f"✅ Refinamiento necesario: {len(search_results)} resultados (>10)")
        
        # Criterio 2: Alta diversidad de marcas o categorías (>3)
        elif num_brands > 3 or num_categories > 3:
            needs_refinement = True
            logger.info(f"✅ Refinamiento necesario: Alta diversidad (marcas:{num_brands}, categorías:{num_categories})")
        
        # Criterio 3: Muchas especificaciones diferentes (>5)
        elif num_specs > 5:
            needs_refinement = True
            logger.info(f"✅ Refinamiento necesario: Muchas especificaciones ({num_specs})")
        
        # Si no necesita refinamiento, terminar
        if not needs_refinement:
            logger.info(f"Búsqueda óptima con {len(search_results)} resultados, diversidad baja")
            context.current_state = RefinementState.COMPLETED
            return False, None
        
        # Analizar especificidad de la consulta
        is_specific, details = self.analyze_query_specificity(query)
        
        # Logging mejorado para debugging
        logger.info(f"📊 Análisis de especificidad: score={details.get('specificity_score', 0)}, "
                   f"specs={len(details.get('technical_specs', {}))}, "
                   f"brand={details.get('brand', 'None')}")
        
        # Si la consulta ya es muy específica, ajustar el umbral de refinamiento
        if is_specific:
            # Con queries muy específicas, solo refinar si hay MUCHOS resultados
            if len(search_results) <= 20:
                logger.info(f"✅ Consulta específica con {len(search_results)} resultados, no requiere refinamiento")
                return False, None
            elif details.get('specificity_score', 0) >= 4 and len(search_results) <= 30:
                # Query súper específica, tolerar hasta 30 resultados
                logger.info(f"✅ Consulta muy específica (score={details.get('specificity_score', 0)}), "
                           f"mostrando {len(search_results)} resultados directamente")
                return False, None
        context.available_attributes = available_attrs
        
        # Decidir qué preguntar basado en el estado y los atributos disponibles
        message = self.generate_refinement_question(context, details, available_attrs)
        
        if message:
            context.iterations += 1
            return True, message
        
        return False, None
    
    def generate_refinement_question(
        self,
        context: SearchContext,
        query_details: Dict[str, Any],
        available_attrs: Dict[str, List[str]]
    ) -> Optional[str]:
        """Genera la pregunta de refinamiento apropiada para el usuario"""
        
        # Asegurar que siempre tengamos un tipo de producto válido
        product_type = query_details.get('product_type')
        if not product_type or product_type == 'None':
            product_type = 'productos'
        result_count = context.last_search_count
        
        # Primera iteración: preguntar por marca si hay muchas disponibles
        if context.iterations == 0 and not query_details.get('brand'):
            brands = available_attrs.get('brands', [])
            if len(brands) >= 3:
                context.current_state = RefinementState.ASKING_BRAND
                brand_list = ', '.join(brands[:8])  # Mostrar max 8 marcas
                if len(brands) > 8:
                    brand_list += f" y {len(brands) - 8} más"
                
                return (
                    f"He encontrado {result_count} {product_type} disponibles. "
                    f"Para mostrarte los más relevantes, ¿de qué marca lo prefieres? "
                    f"Tenemos: {brand_list}"
                )
        
        # Segunda iteración: preguntar por atributo técnico basado en lo disponible
        if context.iterations <= 1:
            # Preguntar por atributos disponibles en los resultados
            if available_attrs.get('amperajes') and len(available_attrs['amperajes']) >= 2:
                amps = available_attrs['amperajes']
                context.current_state = RefinementState.ASKING_ATTRIBUTE
                amp_list = ', '.join(amps[:10])
                return (
                    f"Perfecto. Ahora, ¿qué amperaje necesitas? "
                    f"Disponibles: {amp_list}"
                )
            
            elif available_attrs.get('curvas') and len(available_attrs['curvas']) >= 2:
                curves = available_attrs['curvas']
                context.current_state = RefinementState.ASKING_ATTRIBUTE
                return (
                    f"¿Qué curva de disparo necesitas? "
                    f"Disponibles: {', '.join(curves)}"
                )
            
            elif available_attrs.get('polos') and len(available_attrs['polos']) >= 2:
                poles = available_attrs['polos']
                context.current_state = RefinementState.ASKING_ATTRIBUTE
                return (
                    f"¿De cuántos polos lo necesitas? "
                    f"Opciones: {', '.join(poles)}"
                )
            
            elif 'diferencial' in query_details.get('product_type', '').lower():
                context.current_state = RefinementState.ASKING_ATTRIBUTE
                return (
                    f"¿Qué sensibilidad necesitas para el diferencial? "
                    f"Las más comunes son: 30mA (uso doméstico), 300mA (industrial)"
                )
        
        # Si aún hay muchos resultados, preguntar algo genérico
        if result_count > context.too_many_threshold:
            context.current_state = RefinementState.ASKING_ATTRIBUTE
            return (
                f"Encontré {result_count} opciones. "
                f"¿Podrías darme más detalles sobre lo que buscas? "
                f"Por ejemplo: marca, características técnicas, o uso específico."
            )
        
        return None
    
    def refine_query_with_response(
        self,
        session_id: str,
        user_response: str,
        original_query: str
    ) -> str:
        """
        Refina la consulta original con la respuesta del usuario
        Returns: consulta refinada
        """
        context = self.contexts.get(session_id)
        if not context:
            return original_query
        
        response_lower = user_response.lower()
        refined_parts = [original_query]
        
        # Si estábamos preguntando por marca
        if context.current_state == RefinementState.ASKING_BRAND:
            # Buscar marca mencionada en las marcas disponibles
            brands = context.available_attributes.get('brands', [])
            brand_found = False
            
            # Primero buscar en las marcas disponibles de los resultados
            for brand in brands:
                if brand.lower() in response_lower or response_lower in brand.lower():
                    context.selected_brand = brand
                    refined_parts.append(brand)
                    brand_found = True
                    break
            
            # Si no se encontró en las disponibles, buscar en las comunes
            if not brand_found:
                for brand in self.common_brands:
                    if brand.lower() in response_lower:
                        context.selected_brand = brand
                        refined_parts.append(brand)
                        brand_found = True
                        break
            
            # Si aún no se encontró, usar la respuesta tal cual (podría ser una marca nueva)
            if not brand_found and len(user_response.strip()) > 1:
                context.selected_brand = user_response.strip()
                refined_parts.append(context.selected_brand)
        
        # Si estábamos preguntando por atributo técnico
        elif context.current_state == RefinementState.ASKING_ATTRIBUTE:
            # IMPORTANTE: Detectar si el usuario mencionó una marca en su respuesta
            brand_in_response = None
            for brand in self.common_brands:
                if brand.lower() in response_lower:
                    brand_in_response = brand
                    logger.info(f"🏷️ Marca detectada en respuesta: {brand}")
                    break
            
            # Si se mencionó una marca, usarla
            if brand_in_response:
                context.selected_brand = brand_in_response
                refined_parts.append(brand_in_response)
            # Si ya se seleccionó una marca antes, agregarla (solo si no está ya en refined_parts)
            elif context.selected_brand and context.selected_brand not in refined_parts:
                refined_parts.append(context.selected_brand)
            
            # Extraer valores numéricos y unidades
            import re
            
            # Amperaje
            amp_match = re.search(r'(\d+)\s*[Aa]?', response_lower)
            if amp_match:
                amp_value = f"{amp_match.group(1)}A"
                context.selected_attributes['amperaje'] = amp_value
                if amp_value not in refined_parts:
                    refined_parts.append(amp_value)
            
            # Curva
            curve_match = re.search(r'[Cc]urva\s*([A-Za-z])|^([A-Za-z])$', user_response)
            if curve_match:
                curve = (curve_match.group(1) or curve_match.group(2)).upper()
                if curve in ['A', 'B', 'C', 'D', 'K', 'Z']:
                    curve_str = f"curva {curve}"
                    context.selected_attributes['curva'] = curve_str
                    if curve_str not in refined_parts:
                        refined_parts.append(curve_str)
            
            # Polos
            pole_match = re.search(r'(\d)\s*[Pp]?', response_lower)
            if pole_match and 'polo' in response_lower:
                poles = f"{pole_match.group(1)}P"
                context.selected_attributes['polos'] = poles
                if poles not in refined_parts:
                    refined_parts.append(poles)
            
            # Sensibilidad
            sens_match = re.search(r'(\d+)\s*m[Aa]', response_lower)
            if sens_match:
                sensitivity = f"{sens_match.group(1)}mA"
                context.selected_attributes['sensibilidad'] = sensitivity
                if sensitivity not in refined_parts:
                    refined_parts.append(sensitivity)
        
        # Construir consulta refinada
        context.refined_query = ' '.join(refined_parts)
        context.current_state = RefinementState.REFINED
        
        logger.info(f"Consulta refinada: '{context.refined_query}'")
        return context.refined_query
    
    def get_search_summary(self, session_id: str) -> str:
        """Obtiene un resumen del proceso de refinamiento"""
        context = self.contexts.get(session_id)
        if not context:
            return ""
        
        summary_parts = []
        
        if context.selected_brand:
            summary_parts.append(f"Marca: {context.selected_brand}")
        
        for attr_name, attr_value in context.selected_attributes.items():
            summary_parts.append(f"{attr_name.capitalize()}: {attr_value}")
        
        if summary_parts:
            return f"Filtros aplicados: {', '.join(summary_parts)}"
        
        return ""
    
    def clear_context(self, session_id: str):
        """Limpia el contexto de una sesión"""
        if session_id in self.contexts:
            del self.contexts[session_id]
            logger.info(f"Contexto de sesión {session_id} eliminado")

# Instancia global del agente refinador
search_refiner = SearchRefinerAgent()