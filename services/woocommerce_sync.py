"""
Servicio de sincronización WooCommerce → PostgreSQL + Embeddings
Sincroniza productos, categorías y información de la tienda con la base de conocimiento
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone
import json

from services.woocommerce import WooCommerceService
from services.database import db_service
from services.embedding_service import embedding_service
from config.settings import settings

logger = logging.getLogger(__name__)

class WooCommerceSyncService:
    """Servicio para sincronizar datos de WooCommerce con PostgreSQL"""
    
    def __init__(self):
        self.wc_service = WooCommerceService()
        self.batch_size = 50  # Productos por lote
        self.max_retries = 3
        
    async def sync_all_products(self, force_update: bool = False) -> Dict[str, int]:
        """
        Sincronizar todos los productos de WooCommerce
        Args:
            force_update: Si True, actualiza todos los productos independientemente de la fecha
        Returns:
            Dict con estadísticas de sincronización
        """
        logger.info("🔄 Iniciando sincronización completa de productos...")
        
        stats = {
            "total_fetched": 0,
            "new_products": 0,
            "updated_products": 0,
            "errors": 0,
            "categories_synced": 0
        }
        
        try:
            # 1. Sincronizar categorías primero
            await self._sync_categories(stats)
            
            # 2. Obtener todos los productos de WooCommerce
            page = 1
            per_page = self.batch_size
            all_products = []
            
            while True:
                logger.info(f"📥 Obteniendo página {page} de productos...")
                
                products = await self.wc_service.get_products(
                    page=page,
                    per_page=per_page,
                    status='publish'  # Solo productos publicados
                )
                
                if not products or len(products) == 0:
                    break
                    
                all_products.extend(products)
                stats["total_fetched"] += len(products)
                
                # Si obtenemos menos productos que per_page, es la última página
                if len(products) < per_page:
                    break
                    
                page += 1
                
                # Pequeña pausa para no sobrecargar la API
                await asyncio.sleep(0.5)
            
            logger.info(f"📊 Total productos obtenidos: {len(all_products)}")
            
            # 3. Procesar productos en lotes
            for i in range(0, len(all_products), self.batch_size):
                batch = all_products[i:i + self.batch_size]
                batch_stats = await self._process_product_batch(batch, force_update)
                
                stats["new_products"] += batch_stats["new"]
                stats["updated_products"] += batch_stats["updated"]
                stats["errors"] += batch_stats["errors"]
                
                logger.info(f"✅ Procesado lote {i//self.batch_size + 1}: "
                          f"{batch_stats['new']} nuevos, {batch_stats['updated']} actualizados")
                
                # Pausa entre lotes
                await asyncio.sleep(1)
            
            # 4. Limpiar productos inactivos (que ya no existen en WooCommerce)
            await self._cleanup_inactive_products(all_products)
            
            logger.info(f"🎉 Sincronización completada: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}")
            stats["errors"] += 1
            return stats
    
    async def sync_single_product(self, product_id: int) -> bool:
        """
        Sincronizar un producto específico
        Args:
            product_id: ID del producto en WooCommerce
        Returns:
            True si se sincronizó correctamente
        """
        try:
            logger.info(f"🔄 Sincronizando producto {product_id}...")
            
            # Obtener producto de WooCommerce
            product = await self.wc_service.get_product(product_id)
            if not product:
                logger.warning(f"⚠️ Producto {product_id} no encontrado en WooCommerce")
                return False
            
            # Procesar producto
            success = await self._process_single_product(product)
            
            if success:
                logger.info(f"✅ Producto {product_id} sincronizado correctamente")
            else:
                logger.error(f"❌ Error sincronizando producto {product_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error sincronizando producto {product_id}: {e}")
            return False
    
    async def _sync_categories(self, stats: Dict[str, int]):
        """Sincronizar categorías de productos"""
        try:
            logger.info("🏷️ Sincronizando categorías...")
            
            categories = await self.wc_service.get_product_categories(per_page=100)
            if not categories:
                return
            
            for category in categories:
                category_content = self._format_category_for_knowledge(category)
                
                # Generar embedding
                embedding = await embedding_service.generate_embedding(category_content["content"])
                
                # Insertar o actualizar en base de conocimiento
                await db_service.upsert_knowledge(
                    content_type="category",
                    title=category_content["title"],
                    content=category_content["content"],
                    embedding=embedding,
                    external_id=f"category_{category['id']}",
                    metadata=category_content["metadata"]
                )
                
                stats["categories_synced"] += 1
                
            logger.info(f"✅ {stats['categories_synced']} categorías sincronizadas")
            
        except Exception as e:
            logger.error(f"❌ Error sincronizando categorías: {e}")
    
    async def _process_product_batch(self, products: List[Dict], force_update: bool = False) -> Dict[str, int]:
        """Procesar un lote de productos"""
        batch_stats = {"new": 0, "updated": 0, "errors": 0}
        
        # Procesar productos en paralelo (pero limitado)
        semaphore = asyncio.Semaphore(5)  # Máximo 5 productos en paralelo
        
        async def process_with_semaphore(product):
            async with semaphore:
                return await self._process_single_product(product, force_update)
        
        tasks = [process_with_semaphore(product) for product in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                batch_stats["errors"] += 1
            elif result == "new":
                batch_stats["new"] += 1
            elif result == "updated":
                batch_stats["updated"] += 1
            elif result == "error":
                batch_stats["errors"] += 1
        
        return batch_stats
    
    async def _process_single_product(self, product: Dict, force_update: bool = False) -> str:
        """
        Procesar un producto individual
        Returns: 'new', 'updated', 'skipped', or 'error'
        """
        try:
            # Validación defensiva - verificar que product es un diccionario
            if not isinstance(product, dict):
                logger.error(f"❌ Producto no es diccionario: {type(product)} - {product}")
                return "error"
            
            product_id = product.get('id')
            if not product_id:
                logger.error(f"❌ Producto sin ID: {product}")
                return "error"
                
            external_id = f"product_{product_id}"
            
            # Verificar si ya existe
            existing = await db_service.get_knowledge_by_external_id(external_id)
            
            # Decidir si actualizar
            should_update = force_update
            if existing and not force_update:
                # Comparar fecha de modificación
                date_modified = product.get('date_modified', '')
                if date_modified:
                    try:
                        # Convertir fecha de WooCommerce a datetime con zona horaria
                        wc_modified = datetime.fromisoformat(date_modified.replace('Z', '+00:00'))
                        db_modified = existing.get('updated_at')
                        
                        if db_modified:
                            # Si db_modified es naive (sin timezone), hacerlo aware en UTC
                            if db_modified.tzinfo is None:
                                db_modified = db_modified.replace(tzinfo=timezone.utc)
                            
                            # Si wc_modified es naive, hacerlo aware en UTC
                            if wc_modified.tzinfo is None:
                                wc_modified = wc_modified.replace(tzinfo=timezone.utc)
                                
                            should_update = wc_modified > db_modified
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"⚠️ Error procesando fecha {date_modified}: {e}")
                        should_update = True  # Si hay error en fecha, actualizar
            
            if existing and not should_update:
                return "skipped"
            
            # Formatear producto para base de conocimiento
            product_content = self._format_product_for_knowledge(product)
            
            # Generar embedding
            embedding = await embedding_service.generate_embedding(product_content["content"])
            
            # Insertar o actualizar
            result_id = await db_service.upsert_knowledge(
                content_type="product",
                title=product_content["title"],
                content=product_content["content"],
                embedding=embedding,
                external_id=external_id,
                metadata=product_content["metadata"]
            )
            
            # Log detallado para debugging
            if existing and should_update:
                logger.debug(f"Actualizando producto {product_id}: Precio={product_content['metadata'].get('price')}")
            
            return "new" if not existing else "updated"
            
        except Exception as e:
            # Manejo de error más defensivo
            product_id = "unknown"
            if isinstance(product, dict):
                product_id = product.get('id', 'unknown')
            logger.error(f"❌ Error procesando producto {product_id}: {e}")
            return "error"
    
    def _format_product_for_knowledge(self, product: Dict) -> Dict[str, Any]:
        """Formatear producto de WooCommerce para base de conocimiento"""
        
        # Información básica
        name = product.get('name', '')
        description = product.get('description', '')
        short_description = product.get('short_description', '')
        sku = product.get('sku', '')
        price = product.get('price', '')
        regular_price = product.get('regular_price', '')
        sale_price = product.get('sale_price', '')
        stock_status = product.get('stock_status', '')
        stock_quantity = product.get('stock_quantity', 0)
        
        # Categorías (con validación defensiva)
        categories = []
        for cat in product.get('categories', []):
            if isinstance(cat, dict):
                categories.append(cat.get('name', ''))
            else:
                logger.warning(f"⚠️ Categoría no es diccionario: {type(cat)} - {cat}")
        category_text = ', '.join(categories) if categories else ''
        
        # Atributos (con validación defensiva)
        attributes = []
        for attr in product.get('attributes', []):
            if isinstance(attr, dict):
                attr_name = attr.get('name', '')
                attr_options = attr.get('options', [])
                if isinstance(attr_options, list):
                    attr_options_text = ', '.join(str(opt) for opt in attr_options)
                else:
                    attr_options_text = str(attr_options) if attr_options else ''
                if attr_name and attr_options_text:
                    attributes.append(f"{attr_name}: {attr_options_text}")
            else:
                logger.warning(f"⚠️ Atributo no es diccionario: {type(attr)} - {attr}")
        
        attributes_text = ' | '.join(attributes) if attributes else ''
        
        # Limpiar HTML de descripciones
        clean_description = self._clean_html(description)
        clean_short_description = self._clean_html(short_description)
        
        # Construir contenido optimizado para búsqueda
        # Aplicar IVA del 21% a los precios para el contenido
        VAT_RATE = 1.21
        price_with_vat = round(self._safe_float_conversion(price) * VAT_RATE, 2) if price else 0
        regular_price_with_vat = round(self._safe_float_conversion(regular_price) * VAT_RATE, 2) if regular_price else 0
        sale_price_with_vat = round(self._safe_float_conversion(sale_price) * VAT_RATE, 2) if sale_price else 0
        
        content_parts = [
            f"Producto: {name}",
            f"SKU: {sku}" if sku else "",
            f"Precio: {price_with_vat}€ (IVA incluido)" if price else "",
            f"Precio regular: {regular_price_with_vat}€ (IVA incluido)" if regular_price and regular_price != price else "",
            f"Precio oferta: {sale_price_with_vat}€ (IVA incluido)" if sale_price else "",
            f"Stock: {stock_status}",
            f"Cantidad disponible: {stock_quantity}" if stock_quantity else "",
            f"Categorías: {category_text}" if category_text else "",
            f"Características: {attributes_text}" if attributes_text else "",
            f"Descripción: {clean_short_description}" if clean_short_description else "",
            clean_description if clean_description else ""
        ]
        
        content = '\n'.join([part for part in content_parts if part])
        
        # Metadatos estructurados (con validación defensiva)
        # Atributos para metadatos
        metadata_attributes = {}
        for attr in product.get('attributes', []):
            if isinstance(attr, dict):
                attr_name = attr.get('name', '')
                attr_options = attr.get('options', [])
                if attr_name:
                    metadata_attributes[attr_name] = attr_options if isinstance(attr_options, list) else []
        
        # Imágenes para metadatos
        metadata_images = []
        for img in product.get('images', [])[:3]:  # Máximo 3 imágenes
            if isinstance(img, dict):
                img_src = img.get('src', '')
                if img_src:
                    metadata_images.append(img_src)
        
        # Aplicar IVA del 21% a los precios
        VAT_RATE = 1.21
        
        metadata = {
            "wc_id": product.get('id'),
            "sku": sku,
            "price": round(self._safe_float_conversion(price) * VAT_RATE, 2),
            "regular_price": round(self._safe_float_conversion(regular_price) * VAT_RATE, 2),
            "sale_price": round(self._safe_float_conversion(sale_price) * VAT_RATE, 2) if sale_price else 0,
            "stock_status": stock_status,
            "stock_quantity": stock_quantity if isinstance(stock_quantity, (int, float)) else 0,
            "categories": categories,
            "attributes": metadata_attributes,
            "permalink": product.get('permalink', ''),
            "date_created": product.get('date_created', ''),
            "date_modified": product.get('date_modified', ''),
            "images": metadata_images
        }
        
        return {
            "title": name,
            "content": content,
            "metadata": metadata
        }
    
    def _format_category_for_knowledge(self, category: Dict) -> Dict[str, Any]:
        """Formatear categoría para base de conocimiento"""
        
        name = category.get('name', '')
        description = category.get('description', '')
        count = category.get('count', 0)
        
        clean_description = self._clean_html(description)
        
        content = f"Categoría: {name}\n"
        if clean_description:
            content += f"Descripción: {clean_description}\n"
        content += f"Número de productos: {count}"
        
        metadata = {
            "wc_id": category.get('id'),
            "slug": category.get('slug', ''),
            "parent": category.get('parent', 0),
            "count": count,
            "permalink": category.get('link', '')
        }
        
        return {
            "title": f"Categoría: {name}",
            "content": content,
            "metadata": metadata
        }
    
    def _clean_html(self, html_text: str) -> str:
        """Limpiar HTML básico de texto"""
        if not html_text:
            return ""
        
        # Reemplazos básicos de HTML
        replacements = {
            '<p>': '\n',
            '</p>': '',
            '<br>': '\n',
            '<br/>': '\n',
            '<br />': '\n',
            '<strong>': '',
            '</strong>': '',
            '<b>': '',
            '</b>': '',
            '<em>': '',
            '</em>': '',
            '<i>': '',
            '</i>': '',
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"'
        }
        
        text = html_text
        for html_tag, replacement in replacements.items():
            text = text.replace(html_tag, replacement)
        
        # Limpiar espacios múltiples y saltos de línea
        lines = [line.strip() for line in text.split('\n')]
        clean_lines = [line for line in lines if line]
        
        return '\n'.join(clean_lines)
    
    def _safe_float_conversion(self, value: Any) -> float:
        """Convertir de forma segura un valor a float"""
        if not value:
            return 0.0
        
        try:
            # Si ya es un número, devolverlo
            if isinstance(value, (int, float)):
                return float(value)
            
            # Si es string, limpiar y convertir
            if isinstance(value, str):
                # Remover espacios y símbolos de moneda comunes
                cleaned = value.strip().replace('€', '').replace('$', '').replace(',', '.')
                # Intentar convertir
                return float(cleaned)
        except (ValueError, TypeError) as e:
            logger.warning(f"No se pudo convertir '{value}' a float: {e}")
            
        return 0.0
    
    async def _cleanup_inactive_products(self, active_products: List[Dict]):
        """Marcar como inactivos los productos que ya no existen en WooCommerce"""
        try:
            # Obtener IDs de productos activos
            active_ids = {f"product_{p['id']}" for p in active_products}
            
            # Marcar como inactivos los productos que no están en la lista
            deactivated = await db_service.deactivate_missing_products(active_ids)
            
            if deactivated > 0:
                logger.info(f"🗑️ {deactivated} productos marcados como inactivos")
                
        except Exception as e:
            logger.error(f"❌ Error en limpieza de productos inactivos: {e}")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Obtener estado de la sincronización"""
        try:
            stats = await db_service.get_statistics()
            
            # Obtener última sincronización
            last_sync = await db_service.get_last_sync_time()
            
            return {
                "total_products": stats.get("products", 0),
                "total_categories": stats.get("categories", 0),
                "active_products": stats.get("active_products", 0),
                "last_sync": last_sync.isoformat() if last_sync else None,
                "sync_needed": self._is_sync_needed(last_sync)
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de sincronización: {e}")
            return {"error": str(e)}
    
    def _is_sync_needed(self, last_sync: Optional[datetime]) -> bool:
        """Determinar si se necesita sincronización"""
        if not last_sync:
            return True
        
        # Sincronizar cada 6 horas
        sync_interval = timedelta(hours=6)
        
        # Manejar timezones correctamente
        now = datetime.now(timezone.utc) if last_sync.tzinfo else datetime.now()
        
        # Si last_sync tiene timezone, convertir now a UTC
        if last_sync.tzinfo:
            if not now.tzinfo:
                now = datetime.now(timezone.utc)
        
        try:
            return now - last_sync > sync_interval
        except TypeError:
            # Si aún hay problemas con timezone, asumir que necesita sync
            logger.warning("Problema comparando fechas con timezone, asumiendo que necesita sincronización")
            return True

# Instancia global del servicio
wc_sync_service = WooCommerceSyncService() 