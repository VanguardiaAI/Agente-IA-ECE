"""
Gestor de sinónimos para productos eléctricos
Carga y gestiona el archivo de sinónimos para búsquedas inteligentes
"""

import json
import logging
from typing import List, Dict, Any, Set, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SynonymManager:
    """Gestiona sinónimos y variaciones de términos eléctricos"""
    
    def __init__(self):
        self.synonyms_data: Dict[str, Any] = {}
        self.synonym_map: Dict[str, List[str]] = {}
        self.loaded = False
        
    def load_synonyms(self, file_path: Optional[str] = None) -> bool:
        """Carga el archivo de sinónimos"""
        if file_path is None:
            # Use relative path from the project root
            file_path = "knowledge/sinonimos_electricos.json"
            
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Archivo de sinónimos no encontrado: {file_path}")
                return False
                
            with open(path, 'r', encoding='utf-8') as f:
                self.synonyms_data = json.load(f)
                
            self._build_synonym_map()
            self.loaded = True
            logger.info(f"✅ Sinónimos cargados: {len(self.synonym_map)} términos mapeados")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando sinónimos: {e}")
            return False
            
    def _build_synonym_map(self):
        """Construye un mapa plano de sinónimos para búsqueda rápida"""
        self.synonym_map = {}
        
        # Procesar cada categoría
        for category, items in self.synonyms_data.items():
            if isinstance(items, dict):
                for key, value in items.items():
                    if isinstance(value, dict) and 'sinonimos' in value:
                        # Término principal y sus sinónimos
                        term = key.lower()
                        synonyms = [s.lower() for s in value['sinonimos']]
                        
                        # Mapear término principal a todos sus sinónimos
                        self.synonym_map[term] = synonyms
                        
                        # Mapear cada sinónimo al término principal y otros sinónimos
                        for syn in synonyms:
                            other_syns = [term] + [s for s in synonyms if s != syn]
                            if syn in self.synonym_map:
                                self.synonym_map[syn].extend(other_syns)
                            else:
                                self.synonym_map[syn] = other_syns
                                
                        # Procesar tipos técnicos si existen
                        if 'tipos_tecnicos' in value:
                            for tipo, variantes in value['tipos_tecnicos'].items():
                                tipo_lower = tipo.lower()
                                variantes_lower = [v.lower() for v in variantes]
                                
                                # Añadir variantes técnicas
                                for var in variantes_lower:
                                    if var in self.synonym_map:
                                        self.synonym_map[var].append(tipo_lower)
                                    else:
                                        self.synonym_map[var] = [tipo_lower]
                                        
    def get_synonyms(self, term: str) -> List[str]:
        """Obtiene sinónimos para un término"""
        if not self.loaded:
            self.load_synonyms()
            
        term_lower = term.lower()
        synonyms = self.synonym_map.get(term_lower, [])
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_synonyms = []
        for syn in synonyms:
            if syn not in seen and syn != term_lower:
                seen.add(syn)
                unique_synonyms.append(syn)
                
        return unique_synonyms
        
    def expand_query(self, query: str, max_expansions: int = 5) -> List[str]:
        """
        Expande una consulta con sinónimos relevantes
        
        Args:
            query: Consulta original
            max_expansions: Número máximo de expansiones
            
        Returns:
            Lista de variaciones de la consulta
        """
        if not self.loaded:
            self.load_synonyms()
            
        query_lower = query.lower()
        words = query_lower.split()
        expansions = [query]  # Incluir original
        
        # Buscar sinónimos para cada palabra
        for i, word in enumerate(words):
            synonyms = self.get_synonyms(word)
            
            if synonyms:
                # Crear variaciones reemplazando la palabra por sus sinónimos
                for syn in synonyms[:3]:  # Limitar a 3 sinónimos por palabra
                    new_words = words.copy()
                    new_words[i] = syn
                    new_query = ' '.join(new_words)
                    
                    if new_query not in expansions:
                        expansions.append(new_query)
                        
                    if len(expansions) >= max_expansions:
                        return expansions
                        
        return expansions
        
    def get_technical_info(self, term: str) -> Dict[str, Any]:
        """Obtiene información técnica sobre un término si existe"""
        if not self.loaded:
            self.load_synonyms()
            
        term_lower = term.lower()
        
        # Buscar en todas las categorías
        for category, items in self.synonyms_data.items():
            if isinstance(items, dict):
                for key, value in items.items():
                    if key.lower() == term_lower or (
                        isinstance(value, dict) and 
                        'sinonimos' in value and 
                        term_lower in [s.lower() for s in value['sinonimos']]
                    ):
                        return {
                            "category": category,
                            "main_term": key,
                            "info": value
                        }
                        
        return {}
        
    def get_category_terms(self, category: str) -> List[str]:
        """Obtiene todos los términos de una categoría"""
        if not self.loaded:
            self.load_synonyms()
            
        terms = []
        
        if category in self.synonyms_data:
            category_data = self.synonyms_data[category]
            if isinstance(category_data, dict):
                for key, value in category_data.items():
                    terms.append(key)
                    if isinstance(value, dict) and 'sinonimos' in value:
                        terms.extend(value['sinonimos'])
                        
        return list(set(terms))  # Eliminar duplicados
        
    def find_brand_variations(self, query: str) -> List[str]:
        """Encuentra variaciones de marca en la consulta"""
        if not self.loaded:
            self.load_synonyms()
            
        brands = []
        query_lower = query.lower()
        
        # Obtener marcas principales y equivalencias
        marcas_data = self.synonyms_data.get('marcas_equivalencias', {})
        
        if 'principales' in marcas_data:
            for marca in marcas_data['principales']:
                if marca.lower() in query_lower:
                    brands.append(marca)
                    
        if 'equivalencias' in marcas_data:
            for old_brand, new_brand in marcas_data['equivalencias'].items():
                if old_brand.lower() in query_lower:
                    brands.append(new_brand)
                    
        return brands


# Instancia global
synonym_manager = SynonymManager()