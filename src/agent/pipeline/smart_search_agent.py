"""
🔍 Smart Search Agent
Agente especializado en ejecutar búsquedas optimizadas en la base de datos
usando diferentes estrategias según el tipo de búsqueda
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from .agent_interfaces import (
    ISmartSearchAgent,
    SearchResults,
    ProductUnderstanding,
    SearchError
)
from .shared_context import shared_context

# Importar servicios de búsqueda existentes
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.database import db_service
from services.embedding_service import embedding_service as embeddings_service

logger = logging.getLogger(__name__)

class SearchStrategy(Enum):
    """Estrategias de búsqueda disponibles"""
    HYBRID = "hybrid"          # Búsqueda híbrida (vector + texto)
    VECTOR = "vector"          # Solo búsqueda vectorial
    TEXT = "text"              # Solo búsqueda de texto
    EXACT = "exact"            # Búsqueda exacta
    CATEGORY = "category"      # Búsqueda por categoría
    BRAND = "brand"            # Búsqueda por marca
    FALLBACK = "fallback"      # Búsqueda amplia de respaldo

class SmartSearchAgent(ISmartSearchAgent):
    """
    Agente que ejecuta búsquedas inteligentes en la base de datos
    aplicando diferentes estrategias según el contexto
    """
    
    def __init__(self):
        super().__init__(name="SmartSearch")
        
        # Inicializar servicios de forma asíncrona al primer uso
        self._db_initialized = False
        self._embeddings_initialized = False
        
        # Configuración de estrategias
        self.strategy_config = {
            SearchStrategy.HYBRID: {
                "vector_weight": 0.6,
                "text_weight": 0.4,
                "min_score": 0.5,
                "limit": 20
            },
            SearchStrategy.VECTOR: {
                "min_score": 0.6,
                "limit": 15
            },
            SearchStrategy.TEXT: {
                "min_score": 0.4,
                "limit": 25
            },
            SearchStrategy.EXACT: {
                "min_score": 0.8,
                "limit": 10
            },
            SearchStrategy.CATEGORY: {
                "limit": 30
            },
            SearchStrategy.BRAND: {
                "limit": 30
            },
            SearchStrategy.FALLBACK: {
                "min_score": 0.3,
                "limit": 50
            }
        }
        
        # Cache de búsquedas recientes
        self.search_cache = {}
        self.cache_ttl = 300  # 5 minutos
        
        self.logger.info("✅ Smart Search Agent inicializado")
    
    async def process(self, input_data: Any, context: Dict[str, Any]) -> SearchResults:
        """Procesa la comprensión del producto y ejecuta búsqueda"""
        if isinstance(input_data, ProductUnderstanding):
            understanding = input_data
        else:
            # Crear ProductUnderstanding desde dict
            understanding = ProductUnderstanding(
                search_query=input_data.get("search_query", ""),
                product_type=input_data.get("product_type"),
                brand=input_data.get("brand"),
                specifications=input_data.get("specifications", {}),
                synonyms_applied=input_data.get("synonyms_applied", []),
                confidence=input_data.get("confidence", 0.5)
            )
        
        return await self.search_products(understanding)
    
    async def search_products(
        self,
        understanding: ProductUnderstanding,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Ejecuta búsqueda inteligente de productos
        
        Args:
            understanding: Comprensión del producto del agente anterior
            filters: Filtros adicionales opcionales
            
        Returns:
            Resultados de búsqueda con estrategia aplicada
        """
        # Asegurar que los servicios estén inicializados
        await self._ensure_services_initialized()
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🔍 Iniciando búsqueda para: '{understanding.search_query}'")
            
            # Verificar cache
            cache_key = self._get_cache_key(understanding, filters)
            if cache_key in self.search_cache:
                cached = self.search_cache[cache_key]
                if (datetime.now() - cached["timestamp"]).seconds < self.cache_ttl:
                    self.logger.info("📦 Retornando resultados desde cache")
                    return cached["results"]
            
            # Determinar estrategia de búsqueda
            strategy = self._determine_strategy(understanding, filters)
            self.logger.info(f"📊 Estrategia seleccionada: {strategy.value}")
            
            # Ejecutar búsqueda según estrategia
            results = await self._execute_search(strategy, understanding, filters)
            
            # Si no hay resultados, intentar estrategias de respaldo
            if not results.products or results.total_count == 0:
                self.logger.warning("⚠️ Sin resultados, intentando estrategias de respaldo")
                results = await self._fallback_search(understanding, filters)
            
            # Aplicar post-procesamiento
            results = self._post_process_results(results, understanding)
            
            # Guardar en cache
            self.search_cache[cache_key] = {
                "results": results,
                "timestamp": datetime.now()
            }
            
            # Registrar métricas
            time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_metrics(time_ms, True)
            
            self.logger.info(f"✅ Búsqueda completada: {results.total_count} productos encontrados")
            self.logger.info(f"   Estrategia: {results.search_strategy}")
            self.logger.info(f"   Tiempo: {time_ms}ms")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {e}")
            self.log_metrics(0, False)
            
            # Retornar resultado vacío en caso de error
            return SearchResults(
                products=[],
                total_count=0,
                search_strategy="error",
                query_used="",
                filters_applied={}
            )
    
    def _determine_strategy(
        self,
        understanding: ProductUnderstanding,
        filters: Optional[Dict[str, Any]]
    ) -> SearchStrategy:
        """Determina la mejor estrategia de búsqueda"""
        
        # Si hay marca específica, usar estrategia de marca
        if understanding.brand:
            return SearchStrategy.BRAND
        
        # Si hay categoría específica en filtros
        if filters and filters.get("category"):
            return SearchStrategy.CATEGORY
        
        # Si la confianza es muy alta, búsqueda exacta
        if understanding.confidence > 0.9:
            return SearchStrategy.EXACT
        
        # Si hay muchos sinónimos aplicados, búsqueda vectorial
        if len(understanding.synonyms_applied) > 3:
            return SearchStrategy.VECTOR
        
        # Por defecto, búsqueda híbrida
        return SearchStrategy.HYBRID
    
    async def _execute_search(
        self,
        strategy: SearchStrategy,
        understanding: ProductUnderstanding,
        filters: Optional[Dict[str, Any]]
    ) -> SearchResults:
        """Ejecuta la búsqueda según la estrategia"""
        
        config = self.strategy_config[strategy]
        
        if strategy == SearchStrategy.HYBRID:
            return await self._hybrid_search(understanding, config, filters)
        
        elif strategy == SearchStrategy.VECTOR:
            return await self._vector_search(understanding, config, filters)
        
        elif strategy == SearchStrategy.TEXT:
            return await self._text_search(understanding, config, filters)
        
        elif strategy == SearchStrategy.EXACT:
            return await self._exact_search(understanding, config, filters)
        
        elif strategy == SearchStrategy.CATEGORY:
            return await self._category_search(understanding, config, filters)
        
        elif strategy == SearchStrategy.BRAND:
            return await self._brand_search(understanding, config, filters)
        
        else:  # FALLBACK
            return await self._fallback_search_strategy(understanding, config, filters)
    
    async def _hybrid_search(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Búsqueda híbrida (vector + texto)"""
        
        try:
            # Generar embedding para búsqueda híbrida
            embedding = await self._get_embedding(understanding.search_query)
            if not embedding:
                # Fallback a búsqueda de texto si no hay embeddings
                return await self._text_search(understanding, config, filters)
            
            # Usar el servicio existente de búsqueda híbrida
            results = await db_service.hybrid_search(
                query_text=understanding.search_query,
                query_embedding=embedding,
                limit=config["limit"]
            )
            
            products = []
            for r in results:
                product = {
                    "product_id": r.get("product_id"),
                    "sku": r.get("sku"),
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "price": r.get("price"),
                    "stock": r.get("stock_quantity", 0),
                    "category": r.get("category"),
                    "brand": r.get("brand"),
                    "score": r.get("score", 0),
                    "image_url": r.get("image_url")
                }
                products.append(product)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="hybrid",
                query_used=understanding.search_query,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda híbrida: {e}")
            return SearchResults(
                products=[],
                total_count=0,
                search_strategy="hybrid_error",
                query_used=understanding.search_query,
                filters_applied={}
            )
    
    async def _vector_search(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Búsqueda solo vectorial"""
        
        try:
            # Generar embedding para la query
            embedding = await embeddings_service.generate_embedding(understanding.search_query)
            
            # Buscar por similitud vectorial
            results = await db_service.vector_search(
                query_embedding=embedding,
                limit=config["limit"],
                min_similarity=config.get("min_score", 0.6)
            )
            
            products = self._format_products(results)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="vector",
                query_used=understanding.search_query,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda vectorial: {e}")
            return SearchResults(products=[], total_count=0, search_strategy="vector_error", query_used=understanding.search_query, filters_applied={})
    
    async def _text_search(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Búsqueda solo de texto"""
        
        try:
            # Construir query de texto con sinónimos
            text_query = understanding.search_query
            if understanding.synonyms_applied:
                text_query = f"{text_query} {' '.join(understanding.synonyms_applied[:3])}"
            
            results = await db_service.text_search(
                query_text=text_query,
                limit=config["limit"]
            )
            
            products = self._format_products(results)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="text",
                query_used=text_query,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda de texto: {e}")
            return SearchResults(products=[], total_count=0, search_strategy="text_error", query_used=understanding.search_query, filters_applied={})
    
    async def _exact_search(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Búsqueda exacta de alta precisión usando búsqueda de texto"""
        
        try:
            # Usar búsqueda de texto con la query exacta
            results = await db_service.text_search(
                query_text=understanding.search_query,
                limit=config["limit"]
            )
            
            # Filtrar solo coincidencias exactas
            exact_products = []
            for r in results:
                name = r.get("name", "").lower()
                sku = r.get("sku", "").lower()
                query_lower = understanding.search_query.lower()
                
                # Verificar coincidencia exacta en nombre o SKU
                if query_lower in name or query_lower in sku or sku == query_lower:
                    exact_products.append(r)
            
            products = self._format_products(exact_products)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="exact",
                query_used=understanding.search_query,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda exacta: {e}")
            return SearchResults(products=[], total_count=0, search_strategy="exact_error", query_used=understanding.search_query, filters_applied={})
    
    async def _category_search(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Búsqueda por categoría usando búsqueda de texto"""
        
        try:
            category = filters.get("category") if filters else None
            if not category and understanding.product_type:
                # Mapear tipo de producto a categoría
                category = self._map_product_type_to_category(understanding.product_type)
            
            if category:
                # Usar búsqueda de texto con la categoría
                results = await db_service.text_search(
                    query_text=category,
                    limit=config["limit"]
                )
            else:
                results = []
            
            products = self._format_products(results)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="category",
                query_used=category or understanding.search_query,
                filters_applied={"category": category} if category else {}
            )
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda por categoría: {e}")
            return SearchResults(products=[], total_count=0, search_strategy="category_error", query_used=understanding.search_query, filters_applied={})
    
    async def _brand_search(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Búsqueda por marca usando búsqueda de texto"""
        
        try:
            if understanding.brand:
                # Combinar marca con tipo de producto si existe
                search_query = understanding.brand
                if understanding.product_type:
                    search_query = f"{understanding.brand} {understanding.product_type}"
                
                # Buscar productos usando búsqueda de texto
                results = await db_service.text_search(
                    query_text=search_query,
                    limit=config["limit"]
                )
                
                products = self._format_products(results)
                
                return SearchResults(
                    products=products,
                    total_count=len(products),
                    search_strategy="brand",
                    query_used=search_query,
                    filters_applied={"brand": understanding.brand}
                )
            
            return SearchResults(products=[], total_count=0, search_strategy="brand", query_used=understanding.search_query, filters_applied={})
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda por marca: {e}")
            return SearchResults(products=[], total_count=0, search_strategy="brand_error", query_used=understanding.search_query, filters_applied={})
    
    async def _fallback_search_strategy(
        self,
        understanding: ProductUnderstanding,
        config: Dict,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Estrategia de respaldo con búsqueda amplia"""
        
        try:
            # Simplificar query para búsqueda más amplia
            simplified_query = understanding.product_type or understanding.search_query.split()[0]
            
            # Generar embedding para búsqueda híbrida
            embedding = await self._get_embedding(simplified_query)
            if embedding:
                results = await db_service.hybrid_search(
                    query_text=simplified_query,
                    query_embedding=embedding,
                    limit=config["limit"]
                )
            else:
                # Fallback a búsqueda de texto
                results = await db_service.text_search(
                    query_text=simplified_query,
                    limit=config["limit"]
                )
            
            products = self._format_products(results)
            
            return SearchResults(
                products=products,
                total_count=len(products),
                search_strategy="fallback",
                query_used=simplified_query,
                filters_applied=filters or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda de respaldo: {e}")
            return SearchResults(products=[], total_count=0, search_strategy="fallback_error", query_used=understanding.search_query, filters_applied={})
    
    async def _ensure_services_initialized(self):
        """Asegura que los servicios estén inicializados"""
        global db_service, embeddings_service
        
        if not self._db_initialized:
            try:
                if not db_service.initialized:
                    await db_service.initialize()
                self._db_initialized = True
                self.logger.info("✅ Base de datos inicializada")
            except Exception as e:
                self.logger.warning(f"No se pudo inicializar la base de datos: {e}")
        
        if not self._embeddings_initialized:
            try:
                if not embeddings_service.initialized:
                    await embeddings_service.initialize()
                self._embeddings_initialized = True
                self.logger.info("✅ Servicio de embeddings inicializado")
            except Exception as e:
                self.logger.warning(f"No se pudo inicializar embeddings: {e}")
    
    async def _fallback_search(
        self,
        understanding: ProductUnderstanding,
        filters: Optional[Dict]
    ) -> SearchResults:
        """Intenta múltiples estrategias de respaldo cuando no hay resultados"""
        
        strategies_to_try = [
            SearchStrategy.TEXT,
            SearchStrategy.VECTOR,
            SearchStrategy.CATEGORY,
            SearchStrategy.FALLBACK
        ]
        
        for strategy in strategies_to_try:
            self.logger.info(f"🔄 Intentando estrategia de respaldo: {strategy.value}")
            results = await self._execute_search(strategy, understanding, filters)
            
            if results.products and results.total_count > 0:
                results.search_strategy = f"{results.search_strategy}_fallback"
                return results
        
        # Si todo falla, retornar vacío
        return SearchResults(
            products=[],
            total_count=0,
            search_strategy="no_results",
            query_used=understanding.search_query,
            filters_applied=filters or {}
        )
    
    def _post_process_results(
        self,
        results: SearchResults,
        understanding: ProductUnderstanding
    ) -> SearchResults:
        """Post-procesa los resultados para mejorar relevancia"""
        
        if not results.products:
            return results
        
        # Aplicar boost por marca coincidente
        if understanding.brand:
            for product in results.products:
                product_brand = product.get("brand", "")
                if product_brand and understanding.brand:
                    if product_brand.lower() == understanding.brand.lower():
                        product["score"] = product.get("score", 0) * 1.2
        
        # Aplicar boost por especificaciones coincidentes
        for spec_key, spec_value in understanding.specifications.items():
            for product in results.products:
                if self._matches_specification(product, spec_key, spec_value):
                    product["score"] = product.get("score", 0) * 1.1
        
        # Re-ordenar por score
        results.products.sort(key=lambda p: p.get("score", 0), reverse=True)
        
        return results
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Genera embedding para un texto"""
        try:
            if embeddings_service:
                return await embeddings_service.generate_embedding(text)
            return None
        except Exception as e:
            self.logger.warning(f"No se pudo generar embedding: {e}")
            return None
    
    def _format_products(self, raw_results: List[Dict]) -> List[Dict]:
        """Formatea los productos del resultado de la BD"""
        products = []
        for r in raw_results:
            product = {
                "product_id": r.get("product_id") or r.get("id"),
                "sku": r.get("sku"),
                "name": r.get("name"),
                "description": r.get("description"),
                "price": r.get("price"),
                "stock": r.get("stock_quantity", 0),
                "category": r.get("category"),
                "brand": r.get("brand") or r.get("attributes", {}).get("brand"),
                "score": r.get("score", 0),
                "image_url": r.get("image_url") or r.get("images", [{}])[0].get("src") if r.get("images") else None
            }
            products.append(product)
        return products
    
    def _get_cache_key(
        self,
        understanding: ProductUnderstanding,
        filters: Optional[Dict]
    ) -> str:
        """Genera clave de cache para la búsqueda"""
        key_parts = [
            understanding.search_query,
            understanding.brand or "",
            str(filters) if filters else ""
        ]
        return "|".join(key_parts)
    
    def _map_product_type_to_category(self, product_type: str) -> Optional[str]:
        """Mapea tipo de producto a categoría de la BD"""
        category_mapping = {
            "diferencial": "Protecciones eléctricas",
            "magnetotérmico": "Protecciones eléctricas",
            "automático": "Protecciones eléctricas",
            "lámpara": "Iluminación",
            "led": "Iluminación",
            "panel": "Iluminación",
            "cable": "Cables y conductores",
            "manguera": "Cables y conductores",
            "ventilador": "Climatización y ventilación",
            "extractor": "Climatización y ventilación",
            "contactor": "Automatización y control",
            "variador": "Automatización y control",
            "caja": "Material de instalación",
            "tubo": "Material de instalación",
            "enrollacables": "Herramientas y accesorios"
        }
        
        product_type_lower = product_type.lower()
        for key, category in category_mapping.items():
            if key in product_type_lower:
                return category
        
        return None
    
    def _matches_specification(
        self,
        product: Dict,
        spec_key: str,
        spec_value: Any
    ) -> bool:
        """Verifica si un producto coincide con una especificación"""
        
        # Buscar en atributos del producto
        attributes = product.get("attributes", {})
        
        # Mapeo de claves de especificación a atributos
        spec_mapping = {
            "amperaje": ["amperaje", "corriente", "intensidad"],
            "voltaje": ["voltaje", "tension", "voltage"],
            "potencia": ["potencia", "power", "watts"],
            "sensibilidad": ["sensibilidad", "sensitivity"],
            "seccion_cable": ["seccion", "section", "diametro"],
            "proteccion_ip": ["ip", "proteccion", "grado_ip"]
        }
        
        # Buscar coincidencias
        possible_keys = spec_mapping.get(spec_key, [spec_key])
        
        for key in possible_keys:
            if key in attributes and spec_value is not None and attributes[key] is not None:
                if str(spec_value).lower() in str(attributes[key]).lower():
                    return True
        
        # Buscar en descripción
        description = product.get("description", "")
        if description and spec_value is not None:
            if str(spec_value).lower() in description.lower():
                return True
        
        return False
    
    def get_search_strategies(self) -> List[str]:
        """Retorna las estrategias de búsqueda disponibles"""
        return [s.value for s in SearchStrategy]
    
    async def search_by_category(self, category: str) -> SearchResults:
        """Implementación de búsqueda por categoría de la interfaz"""
        understanding = ProductUnderstanding(
            search_query=category,
            product_type=None,
            brand=None,
            specifications={},
            synonyms_applied=[],
            confidence=0.7
        )
        filters = {"category": category}
        return await self.search_products(understanding, filters)
    
    async def search_similar(self, product_id: str) -> SearchResults:
        """Implementación de búsqueda de productos similares"""
        # Por ahora, retornar resultado vacío
        # TODO: Implementar búsqueda de similares cuando tengamos el producto
        return SearchResults(
            products=[],
            total_count=0,
            search_strategy="similar",
            query_used=product_id,
            filters_applied={"product_id": product_id}
        )

# Instancia singleton
smart_search = SmartSearchAgent()