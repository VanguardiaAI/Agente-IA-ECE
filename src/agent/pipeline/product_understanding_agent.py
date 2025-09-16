"""
🧠 Product Understanding Agent
Agente especializado en entender qué producto busca el usuario
aplicando conocimiento del dominio eléctrico
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import aiohttp
from dotenv import load_dotenv

from .agent_interfaces import (
    IProductUnderstandingAgent,
    ProductUnderstanding,
    ProductUnderstandingError
)
from .shared_context import shared_context

# Cargar variables de entorno
load_dotenv("env.agent")

logger = logging.getLogger(__name__)

class ProductUnderstandingAgent(IProductUnderstandingAgent):
    """
    Agente que entiende profundamente qué producto busca el usuario
    usando IA y conocimiento del dominio eléctrico
    """
    
    def __init__(self):
        super().__init__(name="ProductUnderstanding")
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY no configurada")
        
        # Conocimiento del dominio eléctrico
        self.domain_knowledge = {
            # Protecciones eléctricas
            "automático": ["magnetotérmico", "PIA", "disyuntor", "breaker", "interruptor automático", "térmico"],
            "diferencial": ["ID", "llave diferencial", "protección diferencial", "interruptor diferencial", "RCD"],
            "magnetotérmico": ["automático", "PIA", "breaker", "térmico", "disyuntor"],
            
            # Iluminación
            "lámpara": ["luminaria", "foco", "bombilla", "iluminación", "luz", "reflector"],
            "led": ["LED", "luz LED", "iluminación LED", "bombilla LED", "lámpara LED"],
            "panel": ["panel LED", "panel luminoso", "plafón", "luminaria panel"],
            "foco": ["lámpara", "bombilla", "spot", "reflector", "luz"],
            "downlight": ["empotrable", "spot empotrado", "ojo de buey", "foco empotrado"],
            
            # Cables y conductores
            "cable": ["conductor", "manguera", "hilo", "alambre", "cableado"],
            "manguera": ["cable flexible", "cable multipolar", "conductor flexible"],
            
            # Material de instalación
            "caja": ["caja de registro", "caja de empalme", "caja de derivación", "caja estanca"],
            "tubo": ["tubo corrugado", "tubo rígido", "canalización", "conducto"],
            "canaleta": ["canal", "moldura", "ducto", "canalización"],
            
            # Mecanismos
            "interruptor": ["llave", "switch", "conmutador", "pulsador"],
            "enchufe": ["tomacorriente", "toma", "base", "schuko"],
            "dimmer": ["regulador", "atenuador", "variador de luz", "regulador de intensidad"],
            
            # Industrial
            "contactor": ["contactora", "relé de potencia", "arrancador"],
            "variador": ["variador de frecuencia", "VFD", "inverter", "convertidor de frecuencia"],
            "ventilador": ["extractor", "ventilador industrial", "ventilación", "aireador"],
            
            # Herramientas y accesorios
            "enrollacables": ["enrollador", "carrete", "extensión enrollable", "alargador enrollable"],
            "regleta": ["base múltiple", "zapatilla", "multicontacto", "ladrón"],
            
            # Términos técnicos
            "trifásico": ["3F", "tres fases", "380V", "trifásica"],
            "monofásico": ["1F", "una fase", "220V", "monofásica"],
            "amperio": ["A", "amp", "amperios", "ampere"],
            "voltio": ["V", "volt", "voltaje", "tensión"],
            "vatio": ["W", "watt", "potencia", "watts"]
        }
        
        # Marcas principales del sector
        self.known_brands = [
            "schneider", "abb", "legrand", "simon", "hager", 
            "siemens", "chint", "gewiss", "bticino", "merlin gerin",
            "philips", "osram", "sylvania", "ge", "3m",
            "prysmian", "general cable", "top cable", "miguélez"
        ]
        
        # Especificaciones comunes
        self.common_specs = {
            "corriente": ["10A", "16A", "20A", "25A", "32A", "40A", "50A", "63A"],
            "voltaje": ["12V", "24V", "110V", "220V", "380V", "400V"],
            "potencia": ["10W", "20W", "30W", "50W", "100W", "150W", "200W"],
            "sección_cable": ["1.5mm", "2.5mm", "4mm", "6mm", "10mm", "16mm", "25mm"],
            "sensibilidad_diferencial": ["30mA", "300mA", "10mA"],
            "temperatura_color": ["3000K", "4000K", "6000K", "6500K"],
            "tipo_curva": ["curva B", "curva C", "curva D"],
            "grado_protección": ["IP20", "IP44", "IP54", "IP65", "IP67", "IP68"]
        }
        
        self.logger.info("✅ Product Understanding Agent inicializado")
    
    async def process(self, input_data: Any, context: Dict[str, Any]) -> ProductUnderstanding:
        """Procesa el mensaje y comprende el producto buscado"""
        if isinstance(input_data, str):
            message = input_data
        else:
            message = input_data.get("cleaned_message", "")
        
        intent = context.get("intent", "product_search")
        return await self.understand_product(message, intent, context)
    
    async def understand_product_request(
        self,
        cleaned_message: str,
        intent_details: Dict[str, Any]
    ) -> ProductUnderstanding:
        """
        Implementación de la interfaz IProductUnderstandingAgent
        """
        intent = intent_details.get("intent", "product_search")
        session_context = intent_details.get("session_context", {})
        return await self.understand_product(cleaned_message, intent, session_context)
    
    async def understand_product(
        self,
        cleaned_message: str,
        intent: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> ProductUnderstanding:
        """
        Comprende profundamente qué producto busca el usuario
        
        Args:
            cleaned_message: Mensaje limpio sin palabras de transición
            intent: Intención clasificada
            session_context: Contexto de la sesión
            
        Returns:
            Comprensión profunda del producto con query optimizada
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🧠 Analizando producto para: '{cleaned_message}'")
            
            # Si no es búsqueda de producto, retornar básico
            if intent != "product_search":
                return ProductUnderstanding(
                    search_query=cleaned_message,
                    product_type=None,
                    brand=None,
                    specifications={},
                    expanded_terms=[],
                    confidence=0.5
                )
            
            # Análisis con IA
            understanding = await self._analyze_with_ai(cleaned_message, session_context)
            
            # Expandir con sinónimos del dominio
            expanded_terms = self._expand_with_synonyms(understanding)
            understanding["expanded_terms"] = expanded_terms
            
            # Detectar marcas
            brand = self._detect_brand(cleaned_message)
            if brand and not understanding.get("brand"):
                understanding["brand"] = brand
            
            # Detectar especificaciones
            specs = self._extract_specifications(cleaned_message)
            understanding["specifications"].update(specs)
            
            # Construir query optimizada
            optimized_query = self._build_optimized_query(understanding)
            understanding["search_query"] = optimized_query
            
            # Crear objeto de respuesta
            result = ProductUnderstanding(
                search_query=optimized_query,
                product_type=understanding.get("product_type"),
                brand=understanding.get("brand"),
                specifications=understanding.get("specifications", {}),
                synonyms_applied=expanded_terms,
                confidence=understanding.get("confidence", 0.9)
            )
            
            # Registrar métricas
            time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_metrics(time_ms, True)
            
            self.logger.info(f"✅ Producto comprendido: {result.product_type}")
            self.logger.info(f"   Query optimizada: '{result.search_query}'")
            self.logger.info(f"   Términos expandidos: {len(result.synonyms_applied)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error comprendiendo producto: {e}")
            self.log_metrics(0, False)
            
            # Fallback básico
            return self._fallback_understanding(cleaned_message)
    
    async def _analyze_with_ai(self, message: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analiza el producto usando IA"""
        
        # Preparar información de contexto
        context_info = ""
        if context and context.get("refinement_history"):
            context_info = "CONTEXTO: Usuario está refinando búsqueda anterior\n"
            context_info += f"Búsquedas previas: {context.get('refinement_history')}\n"
        
        prompt = f'''
Eres un experto en material eléctrico analizando qué producto busca un cliente.

MENSAJE DEL CLIENTE: "{message}"

{context_info}

CONOCIMIENTO DEL DOMINIO:
- Automatismos: magnetotérmicos, diferenciales, contactores, PLCs
- Iluminación: LED, halógenos, fluorescentes, industriales, emergencia
- Cables: unipolar, multipolar, mangueras, libre halógenos
- Instalación: cajas, tubos, canaletas, bandejas
- Marcas principales: Schneider, ABB, Legrand, Simon, Hager

ANALIZA y responde con JSON:
{{
    "product_type": "tipo específico de producto",
    "category": "categoría general",
    "brand": "marca si la menciona o null",
    "specifications": {{
        "amperaje": "16A",
        "voltaje": "230V",
        "otras_specs": "valor"
    }},
    "search_terms": ["término1", "término2", "término3"],
    "is_industrial": true/false,
    "confidence": 0.95,
    "reasoning": "explicación breve"
}}

IMPORTANTE:
- Identifica el producto principal
- Extrae TODAS las especificaciones
- Sugiere términos de búsqueda relevantes
- Detecta si es uso industrial o doméstico
'''

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Eres un experto en material eléctrico. SIEMPRE respondes con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 400,
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
                        raise ProductUnderstandingError(f"API error: {response.status}")
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    understanding = json.loads(content)
                    self.logger.debug(f"Análisis IA: {understanding}")
                    
                    return understanding
                    
        except Exception as e:
            logger.error(f"Error llamando a OpenAI: {e}")
            raise ProductUnderstandingError(str(e))
    
    def _expand_with_synonyms(self, understanding: Dict[str, Any]) -> List[str]:
        """Expande términos con sinónimos del dominio"""
        expanded = set()
        
        # Añadir términos de búsqueda sugeridos por IA
        if "search_terms" in understanding:
            for term in understanding["search_terms"]:
                expanded.add(term.lower())
        
        # Buscar sinónimos para el tipo de producto
        product_type = understanding.get("product_type", "").lower()
        for key, synonyms in self.domain_knowledge.items():
            if key in product_type or product_type in key:
                expanded.update(synonyms)
                break
        
        # Buscar sinónimos en los términos de búsqueda
        for term in understanding.get("search_terms", []):
            term_lower = term.lower()
            for key, synonyms in self.domain_knowledge.items():
                if key in term_lower or term_lower in key:
                    expanded.update(synonyms[:3])  # Limitar a 3 sinónimos
        
        return list(expanded)
    
    def _detect_brand(self, message: str) -> Optional[str]:
        """Detecta marcas conocidas en el mensaje"""
        message_lower = message.lower()
        
        for brand in self.known_brands:
            if brand in message_lower:
                return brand.title()
        
        return None
    
    def _extract_specifications(self, message: str) -> Dict[str, Any]:
        """Extrae especificaciones técnicas del mensaje"""
        specs = {}
        
        # Detectar amperaje
        amp_pattern = r'(\d+)\s*[Aa](?:mp)?(?:erios?)?'
        amp_match = re.search(amp_pattern, message)
        if amp_match:
            specs["amperaje"] = f"{amp_match.group(1)}A"
        
        # Detectar voltaje
        volt_pattern = r'(\d+)\s*[Vv](?:olt)?(?:ios?)?'
        volt_match = re.search(volt_pattern, message)
        if volt_match:
            specs["voltaje"] = f"{volt_match.group(1)}V"
        
        # Detectar potencia
        watt_pattern = r'(\d+)\s*[Ww](?:att)?s?'
        watt_match = re.search(watt_pattern, message)
        if watt_match:
            specs["potencia"] = f"{watt_match.group(1)}W"
        
        # Detectar sección de cable
        cable_pattern = r'(\d+(?:\.\d+)?)\s*mm2?'
        cable_match = re.search(cable_pattern, message)
        if cable_match:
            specs["seccion_cable"] = f"{cable_match.group(1)}mm"
        
        # Detectar sensibilidad diferencial
        ma_pattern = r'(\d+)\s*m[Aa]'
        ma_match = re.search(ma_pattern, message)
        if ma_match and "diferencial" in message.lower():
            specs["sensibilidad"] = f"{ma_match.group(1)}mA"
        
        # Detectar número de polos
        poles_pattern = r'(\d)[Pp]\+?[Nn]?|(\d)\s*polos?'
        poles_match = re.search(poles_pattern, message)
        if poles_match:
            num_poles = poles_match.group(1) or poles_match.group(2)
            specs["polos"] = f"{num_poles}P"
        
        # Detectar trifásico/monofásico
        if any(term in message.lower() for term in ["trifásico", "trifasico", "3f", "tres fases"]):
            specs["tipo_conexion"] = "trifásico"
        elif any(term in message.lower() for term in ["monofásico", "monofasico", "1f", "una fase"]):
            specs["tipo_conexion"] = "monofásico"
        
        # Detectar grado de protección IP
        ip_pattern = r'[Ii][Pp]\s*(\d{2})'
        ip_match = re.search(ip_pattern, message)
        if ip_match:
            specs["proteccion_ip"] = f"IP{ip_match.group(1)}"
        
        return specs
    
    def _build_optimized_query(self, understanding: Dict[str, Any]) -> str:
        """Construye una query optimizada para búsqueda"""
        parts = []
        
        # Tipo de producto principal
        if understanding.get("product_type"):
            parts.append(understanding["product_type"])
        
        # Marca si existe
        if understanding.get("brand"):
            parts.append(understanding["brand"])
        
        # Especificaciones principales (máximo 2)
        specs = understanding.get("specifications", {})
        important_specs = []
        
        if "amperaje" in specs:
            important_specs.append(specs["amperaje"])
        if "voltaje" in specs and len(important_specs) < 2:
            important_specs.append(specs["voltaje"])
        if "sensibilidad" in specs and len(important_specs) < 2:
            important_specs.append(specs["sensibilidad"])
        
        parts.extend(important_specs)
        
        # Si es industrial, añadir indicador
        if understanding.get("is_industrial"):
            parts.append("industrial")
        
        # Construir query final
        query = " ".join(parts)
        
        # Si la query es muy corta, añadir términos expandidos
        if len(query) < 20 and understanding.get("expanded_terms"):
            additional = understanding["expanded_terms"][:2]
            query = f"{query} {' '.join(additional)}".strip()
        
        return query
    
    def _fallback_understanding(self, message: str) -> ProductUnderstanding:
        """Comprensión de fallback sin IA"""
        
        # Buscar tipo de producto básico
        product_type = None
        for key in self.domain_knowledge.keys():
            if key in message.lower():
                product_type = key
                break
        
        # Detectar marca
        brand = self._detect_brand(message)
        
        # Extraer especificaciones
        specs = self._extract_specifications(message)
        
        return ProductUnderstanding(
            search_query=message,
            product_type=product_type,
            brand=brand,
            specifications=specs,
            synonyms_applied=[],
            confidence=0.6
        )
    
    def get_domain_knowledge(self) -> Dict[str, List[str]]:
        """Retorna el conocimiento del dominio"""
        return self.domain_knowledge.copy()
    
    def get_known_brands(self) -> List[str]:
        """Retorna las marcas conocidas"""
        return self.known_brands.copy()

# Instancia singleton
product_understander = ProductUnderstandingAgent()