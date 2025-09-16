#!/usr/bin/env python3
"""
Servicio de Extracción y Gestión de Atributos de Productos
Analiza productos de WooCommerce para extraer atributos únicos y sugerir filtros
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
import json
import re

logger = logging.getLogger(__name__)

class ProductAttributesService:
    """Servicio para gestionar y analizar atributos de productos"""
    
    def __init__(self):
        self.attributes_cache = {}
        self.brands_cache = set()
        self.common_attributes = defaultdict(set)
        self.last_update = None
        
        # Patrones regex para extraer atributos del título/descripción
        self.patterns = {
            'amperaje': re.compile(r'(\d+(?:\.\d+)?)\s*[Aa](?:mp)?(?:perios?)?'),
            'voltaje': re.compile(r'(\d+)\s*[Vv](?:oltios?)?'),
            'potencia': re.compile(r'(\d+(?:\.\d+)?)\s*[KkWw][Ww]?'),
            'seccion': re.compile(r'(\d+(?:\.\d+)?)\s*mm2?'),
            'sensibilidad': re.compile(r'(\d+)\s*m[Aa]'),
            'curva': re.compile(r'[Cc]urva\s*([A-Z])'),
            'polos': re.compile(r'(\d)[Pp](?:\+[Nn])?'),
            'fase': re.compile(r'(monof[aá]sico|trif[aá]sico|bif[aá]sico)'),
            'ip': re.compile(r'IP\s*(\d{2})'),
            'temperatura': re.compile(r'(\d+)\s*°[CcFf]'),
            'frecuencia': re.compile(r'(\d+)\s*[Hh]z'),
            'longitud': re.compile(r'(\d+(?:\.\d+)?)\s*(?:m|metros?|cm|mm)')
        }
        
        # Marcas conocidas de material eléctrico
        self.known_brands = {
            'Schneider', 'Schneider Electric', 'ABB', 'Legrand', 'Hager', 
            'Siemens', 'Gewiss', 'Chint', 'Simon', 'BJC', 'Niessen',
            'Merlin Gerin', 'Bticino', 'BTicino', 'Circutor', 'Phoenix Contact',
            'Finder', 'Omron', 'Carlo Gavazzi', 'Lovato', 'Eaton',
            'General Electric', 'GE', 'Mitsubishi', 'Fuji', 'Allen Bradley',
            'Telemecanique', 'Crabtree', 'MK Electric', 'Clipsal', 'Vimar',
            'Jung', 'Gira', 'Busch-Jaeger', 'Berker', 'Merten'
        }
        
        # Tipos de productos y sus atributos típicos
        self.product_type_attributes = {
            'automático': ['amperaje', 'curva', 'polos', 'poder_corte', 'marca'],
            'diferencial': ['sensibilidad', 'amperaje', 'polos', 'clase', 'marca'],
            'contactor': ['amperaje', 'polos', 'bobina', 'contactos_aux', 'marca'],
            'cable': ['seccion', 'tipo', 'aislamiento', 'tension', 'longitud'],
            'motor': ['potencia', 'velocidad', 'tension', 'polos', 'marca'],
            'lámpara': ['potencia', 'casquillo', 'temperatura_color', 'lumenes', 'marca'],
            'transformador': ['potencia', 'tension_primaria', 'tension_secundaria', 'marca'],
            'enchufe': ['amperaje', 'tipo', 'ip', 'marca'],
            'interruptor': ['amperaje', 'polos', 'tipo', 'marca'],
            'fusible': ['amperaje', 'tipo', 'tamaño', 'curva', 'marca']
        }
    
    async def extract_attributes_from_products(self, products: List[Dict]) -> Dict[str, Any]:
        """
        Extrae todos los atributos únicos de una lista de productos
        """
        attributes = {
            'brands': set(),
            'technical': defaultdict(set),
            'categories': set(),
            'product_types': set(),
            'price_range': {'min': float('inf'), 'max': 0},
            'total_products': len(products)
        }
        
        for product in products:
            # Extraer de metadata de WooCommerce
            metadata = product.get('metadata', {})
            title = product.get('title', '')
            content = product.get('content', '')
            
            # Extraer marca
            brand = self._extract_brand(title, metadata)
            if brand:
                attributes['brands'].add(brand)
            
            # Extraer atributos técnicos del título
            technical_attrs = self._extract_technical_attributes(title)
            for attr_type, values in technical_attrs.items():
                attributes['technical'][attr_type].update(values)
            
            # Extraer categorías
            categories = metadata.get('categories', [])
            if isinstance(categories, list):
                attributes['categories'].update(categories)
            
            # Extraer tipo de producto
            product_type = self._identify_product_type(title, categories)
            if product_type:
                attributes['product_types'].add(product_type)
            
            # Actualizar rango de precios
            price = metadata.get('price', 0)
            if isinstance(price, (int, float)) and price > 0:
                attributes['price_range']['min'] = min(attributes['price_range']['min'], price)
                attributes['price_range']['max'] = max(attributes['price_range']['max'], price)
            
            # Extraer atributos de WooCommerce
            wc_attributes = metadata.get('attributes', {})
            if isinstance(wc_attributes, dict):
                for attr_name, attr_values in wc_attributes.items():
                    if isinstance(attr_values, list):
                        attributes['technical'][attr_name].update(attr_values)
        
        # Convertir sets a listas ordenadas
        attributes['brands'] = sorted(list(attributes['brands']))
        attributes['categories'] = sorted(list(attributes['categories']))
        attributes['product_types'] = sorted(list(attributes['product_types']))
        
        for key in attributes['technical']:
            attributes['technical'][key] = sorted(list(attributes['technical'][key]))
        
        # Si no hay precios válidos, ajustar
        if attributes['price_range']['min'] == float('inf'):
            attributes['price_range']['min'] = 0
        
        return attributes
    
    def _extract_brand(self, title: str, metadata: Dict) -> Optional[str]:
        """Extrae la marca del título o metadata"""
        title_lower = title.lower()
        
        # Buscar en marcas conocidas
        for brand in self.known_brands:
            if brand.lower() in title_lower:
                return brand
        
        # Buscar en metadata
        wc_attributes = metadata.get('attributes', {})
        if isinstance(wc_attributes, dict):
            for attr_name, attr_values in wc_attributes.items():
                if 'marca' in attr_name.lower() or 'brand' in attr_name.lower():
                    if isinstance(attr_values, list) and attr_values:
                        return attr_values[0]
                    elif isinstance(attr_values, str):
                        return attr_values
        
        return None
    
    def _extract_technical_attributes(self, text: str) -> Dict[str, Set[str]]:
        """Extrae atributos técnicos del texto usando regex"""
        attributes = defaultdict(set)
        
        for attr_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Formatear según el tipo
                if attr_type == 'amperaje':
                    attributes[attr_type].update([f"{m}A" for m in matches])
                elif attr_type == 'voltaje':
                    attributes[attr_type].update([f"{m}V" for m in matches])
                elif attr_type == 'potencia':
                    attributes[attr_type].update([f"{m}W" if 'w' in m.lower() else f"{m}kW" for m in matches])
                elif attr_type == 'seccion':
                    attributes[attr_type].update([f"{m}mm²" for m in matches])
                elif attr_type == 'sensibilidad':
                    attributes[attr_type].update([f"{m}mA" for m in matches])
                elif attr_type == 'polos':
                    attributes[attr_type].update([f"{m}P" for m in matches])
                else:
                    attributes[attr_type].update(matches)
        
        return attributes
    
    def _identify_product_type(self, title: str, categories: List[str]) -> Optional[str]:
        """Identifica el tipo de producto basándose en el título y categorías"""
        title_lower = title.lower()
        
        # Lista de tipos de productos ordenados por prioridad
        product_types = [
            ('automático', ['automático', 'magnetotérmico', 'pia']),
            ('diferencial', ['diferencial', 'rcd', 'id']),
            ('contactor', ['contactor']),
            ('cable', ['cable', 'manguera', 'conductor']),
            ('motor', ['motor']),
            ('lámpara', ['lámpara', 'bombilla', 'led', 'foco', 'luminaria']),
            ('transformador', ['transformador', 'trafo']),
            ('fusible', ['fusible']),
            ('interruptor', ['interruptor', 'conmutador', 'pulsador']),
            ('enchufe', ['enchufe', 'base', 'schuko', 'toma'])
        ]
        
        for product_type, keywords in product_types:
            if any(keyword in title_lower for keyword in keywords):
                return product_type
        
        # Buscar en categorías
        for category in categories:
            category_lower = category.lower() if isinstance(category, str) else ''
            for product_type, keywords in product_types:
                if any(keyword in category_lower for keyword in keywords):
                    return product_type
        
        return None
    
    def suggest_next_filter(
        self, 
        current_attributes: Dict[str, Any],
        available_attributes: Dict[str, List[str]],
        product_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sugiere el siguiente filtro más útil basándose en los atributos actuales
        Returns: {'attribute': 'amperaje', 'options': ['10A', '16A', '20A'], 'question': '...'}
        """
        # Si no hay marca y hay varias disponibles, sugerir marca primero
        if not current_attributes.get('brand') and len(available_attributes.get('brands', [])) >= 3:
            brands = available_attributes['brands'][:10]  # Limitar a 10 marcas
            return {
                'attribute': 'brand',
                'options': brands,
                'question': f"¿De qué marca lo prefieres? Disponibles: {', '.join(brands)}"
            }
        
        # Si conocemos el tipo de producto, sugerir atributos específicos
        if product_type and product_type in self.product_type_attributes:
            priority_attrs = self.product_type_attributes[product_type]
            
            for attr in priority_attrs:
                # Mapear nombre de atributo a clave en available_attributes
                attr_key = attr
                if attr == 'amperaje':
                    attr_key = 'amperajes'
                elif attr == 'curva':
                    attr_key = 'curvas'
                elif attr == 'polos':
                    attr_key = 'polos'
                elif attr == 'sensibilidad':
                    attr_key = 'sensibilidades'
                
                # Si no tenemos este atributo y hay opciones disponibles
                technical_attrs = available_attributes.get('technical', {})
                if attr not in current_attributes and attr_key in technical_attrs:
                    options = technical_attrs[attr_key]
                    if len(options) >= 2:
                        return self._format_attribute_question(attr, options[:10])
        
        # Si no hay sugerencia específica, buscar cualquier atributo técnico con múltiples opciones
        technical_attrs = available_attributes.get('technical', {})
        for attr_name, attr_values in technical_attrs.items():
            if len(attr_values) >= 3 and attr_name not in current_attributes:
                return self._format_attribute_question(attr_name, attr_values[:10])
        
        return None
    
    def _format_attribute_question(self, attribute: str, options: List[str]) -> Dict[str, Any]:
        """Formatea la pregunta para un atributo específico"""
        questions = {
            'amperaje': "¿Qué amperaje necesitas?",
            'amperajes': "¿Qué amperaje necesitas?",
            'curva': "¿Qué curva de disparo prefieres?",
            'curvas': "¿Qué curva de disparo prefieres?",
            'polos': "¿De cuántos polos lo necesitas?",
            'sensibilidad': "¿Qué sensibilidad necesitas?",
            'sensibilidades': "¿Qué sensibilidad necesitas?",
            'voltaje': "¿Qué voltaje requieres?",
            'potencia': "¿Qué potencia necesitas?",
            'seccion': "¿Qué sección de cable buscas?",
            'tipo': "¿Qué tipo prefieres?",
            'clase': "¿Qué clase necesitas?"
        }
        
        question = questions.get(attribute, f"¿Qué {attribute} prefieres?")
        
        return {
            'attribute': attribute,
            'options': options,
            'question': f"{question} Opciones: {', '.join(options)}"
        }
    
    async def update_cache_from_database(self, db_service):
        """Actualiza la caché de atributos desde la base de datos"""
        try:
            async with db_service.pool.acquire() as conn:
                # Obtener muestra de productos para análisis
                products = await conn.fetch("""
                    SELECT title, metadata, content_type
                    FROM knowledge_base
                    WHERE content_type = 'product'
                    AND is_active = true
                    LIMIT 1000
                """)
                
                # Procesar productos
                products_list = []
                for row in products:
                    metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                    products_list.append({
                        'title': row['title'],
                        'metadata': metadata or {}
                    })
                
                # Extraer atributos
                attributes = await self.extract_attributes_from_products(products_list)
                
                # Actualizar caché
                self.attributes_cache = attributes
                self.brands_cache = set(attributes.get('brands', []))
                
                logger.info(f"✅ Caché de atributos actualizada: {len(self.brands_cache)} marcas, {len(attributes.get('technical', {}))} tipos de atributos")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error actualizando caché de atributos: {e}")
            return False
    
    def get_brand_suggestions(self, partial_brand: str = None) -> List[str]:
        """Obtiene sugerencias de marcas basadas en entrada parcial"""
        if not partial_brand:
            return sorted(list(self.brands_cache))[:10]
        
        partial_lower = partial_brand.lower()
        matches = [
            brand for brand in self.brands_cache 
            if partial_lower in brand.lower()
        ]
        
        return sorted(matches)[:10]

# Instancia global del servicio
product_attributes_service = ProductAttributesService()