"""
Analizador de búsqueda simplificado
Prioriza mostrar productos sobre pedir clarificaciones
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
from .synonym_manager import SynonymManager

logger = logging.getLogger(__name__)


@dataclass
class SimpleSearchAnalysis:
    """Resultado simplificado del análisis"""
    product_type: str
    search_terms: List[str]
    needs_clarification: bool = False
    clarification_message: Optional[str] = None


class SimpleSearchAnalyzer:
    """Analizador simplificado que prioriza resultados"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.synonym_manager = SynonymManager()
        
    async def analyze_search(
        self,
        query: str,
        context: List[Dict[str, Any]] = None
    ) -> SimpleSearchAnalysis:
        """
        Analiza búsqueda de forma simple y práctica
        """
        query_lower = query.lower()
        
        # Detección rápida de productos comunes
        product_mappings = {
            "ventilador": "ventilador",
            "cable": "cable eléctrico",
            "lámpara": "lámpara",
            "led": "lámpara LED",
            "diferencial": "interruptor diferencial",
            "magnetotérmico": "interruptor magnetotérmico",
            "automático": "interruptor magnetotérmico",
            "enchufe": "enchufe",
            "regleta": "regleta",
            "tubo": "tubo corrugado"
        }
        
        # Buscar producto principal
        product_type = "producto eléctrico"
        search_terms = []
        
        for key, value in product_mappings.items():
            if key in query_lower:
                product_type = value
                search_terms.append(key)
                break
                
        # Agregar términos adicionales relevantes
        if "industrial" in query_lower or "almacén" in query_lower or "nave" in query_lower:
            search_terms.append("industrial")
            if "ventilador" in product_type:
                product_type = "ventilador industrial"
                
        if "grande" in query_lower:
            search_terms.append("grande")
            
        # Extraer especificaciones numéricas
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?(?:mm²?|m|A|mA|W|V)?', query)
        search_terms.extend(numbers)
        
        # Solo pedir clarificación en casos MUY específicos
        needs_clarification = False
        clarification_message = None
        
        # Casos donde SÍ necesitamos clarificación
        if product_type == "cable eléctrico" and not any(term for term in search_terms if 'mm' in str(term)):
            needs_clarification = True
            clarification_message = "¿Qué sección de cable necesitas? Tenemos 1.5mm², 2.5mm², 4mm², 6mm² y más."
            
        elif product_type == "interruptor diferencial" and not any(term for term in search_terms if 'mA' in str(term)):
            needs_clarification = True
            clarification_message = "¿Necesitas un diferencial de 30mA (uso doméstico) o 300mA (industrial)?"
            
        # En todos los demás casos, intentar buscar con lo que tenemos
        return SimpleSearchAnalysis(
            product_type=product_type,
            search_terms=search_terms if search_terms else [query],
            needs_clarification=needs_clarification,
            clarification_message=clarification_message
        )