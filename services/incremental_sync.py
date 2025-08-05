"""
Servicio de Sincronización Incremental para WooCommerce
Optimizado para actualizaciones en tiempo real y cambios mínimos
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import json
import hashlib

from services.woocommerce import WooCommerceService
from services.database import db_service
from services.embedding_service import embedding_service
from services.woocommerce_sync import WooCommerceSyncService
from config.settings import settings

logger = logging.getLogger(__name__)

class IncrementalSyncService:
    """Servicio para sincronización incremental eficiente"""
    
    def __init__(self):
        self.wc_service = WooCommerceService()
        self.sync_service = WooCommerceSyncService()
        self.last_sync_time = None
        self.sync_interval = 300  # 5 minutos por defecto
        self.running = False
        
    async def initialize(self):
        """Inicializar el servicio de sincronización incremental"""
        try:
            # Crear tabla para tracking de sincronización
            await self._create_sync_tables()
            
            # Obtener última sincronización
            self.last_sync_time = await self._get_last_sync_time()
            
            logger.info("✅ Servicio de sincronización incremental inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando sincronización incremental: {e}")
    
    async def _create_sync_tables(self):
        """Crear tablas para gestión de sincronización"""
        pool = await db_service.get_pool()
        async with pool.acquire() as conn:
            # Tabla de control de sincronización
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_control (
                    id SERIAL PRIMARY KEY,
                    sync_type VARCHAR(50) NOT NULL,
                    last_sync_time TIMESTAMP WITH TIME ZONE,
                    items_synced INTEGER DEFAULT 0,
                    status VARCHAR(20),
                    details JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Tabla de cambios pendientes (para webhooks)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_changes (
                    id SERIAL PRIMARY KEY,
                    resource_type VARCHAR(50) NOT NULL,
                    resource_id INTEGER NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    webhook_data JSONB,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    processed_at TIMESTAMP,
                    UNIQUE(resource_type, resource_id, action)
                );
            """)
            
            # Índices
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_control_type 
                ON sync_control(sync_type, last_sync_time DESC);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_changes_unprocessed 
                ON pending_changes(processed, created_at) 
                WHERE processed = FALSE;
            """)
    
    async def _get_last_sync_time(self) -> Optional[datetime]:
        """Obtener timestamp de la última sincronización exitosa"""
        pool = await db_service.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT last_sync_time FROM sync_control 
                WHERE sync_type = 'products' AND status = 'success'
                ORDER BY last_sync_time DESC 
                LIMIT 1
            """)
            
            if row and row['last_sync_time']:
                return row['last_sync_time']
            return None
    
    async def sync_incremental(self) -> Dict[str, int]:
        """Sincronizar solo cambios desde la última sincronización"""
        if self.running:
            logger.warning("⚠️ Sincronización ya en progreso, omitiendo")
            return {"status": "skipped"}
        
        self.running = True
        stats = {
            "products_checked": 0,
            "products_updated": 0,
            "products_added": 0,
            "products_removed": 0,
            "errors": 0
        }
        
        try:
            logger.info("🔄 Iniciando sincronización incremental...")
            
            # Determinar fecha de corte
            if self.last_sync_time:
                # Restar 1 minuto por seguridad (overlapping)
                modified_after = self.last_sync_time - timedelta(minutes=1)
                logger.info(f"📅 Buscando cambios desde: {modified_after}")
            else:
                # Primera sincronización o sin fecha previa
                logger.info("📅 Primera sincronización, obteniendo todos los productos")
                return await self.sync_service.sync_all_products()
            
            # Obtener productos modificados
            modified_products = await self._get_modified_products(modified_after)
            stats["products_checked"] = len(modified_products)
            
            if modified_products:
                logger.info(f"📦 Encontrados {len(modified_products)} productos modificados")
                
                # Procesar productos modificados
                for product in modified_products:
                    try:
                        result = await self._process_single_product(product)
                        if result == "added":
                            stats["products_added"] += 1
                        elif result == "updated":
                            stats["products_updated"] += 1
                    except Exception as e:
                        logger.error(f"Error procesando producto {product.get('id')}: {e}")
                        stats["errors"] += 1
            
            # Procesar cambios pendientes de webhooks
            webhook_stats = await self._process_pending_webhook_changes()
            stats.update(webhook_stats)
            
            # Registrar sincronización exitosa
            await self._record_sync_completion(stats)
            
            # Actualizar tiempo de última sincronización
            self.last_sync_time = datetime.now(timezone.utc)
            
            logger.info(f"✅ Sincronización incremental completada: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización incremental: {e}")
            stats["errors"] += 1
            await self._record_sync_completion(stats, status="failed", error=str(e))
            return stats
            
        finally:
            self.running = False
    
    async def _get_modified_products(self, modified_after: datetime) -> List[Dict[str, Any]]:
        """Obtener productos modificados después de una fecha"""
        modified_products = []
        page = 1
        
        while True:
            # WooCommerce espera formato ISO 8601
            modified_after_str = modified_after.strftime("%Y-%m-%dT%H:%M:%S")
            
            products = await self.wc_service.get_products(
                page=page,
                per_page=50,
                modified_after=modified_after_str,
                orderby='modified',
                order='asc'
            )
            
            if not products:
                break
                
            modified_products.extend(products)
            
            if len(products) < 50:
                break
                
            page += 1
            await asyncio.sleep(0.5)  # Rate limiting
        
        return modified_products
    
    async def _process_single_product(self, product: Dict[str, Any]) -> str:
        """Procesar un único producto actualizado"""
        pool = await db_service.get_pool()
        
        # Calcular hash del producto para detectar cambios reales
        product_hash = self._calculate_product_hash(product)
        
        async with pool.acquire() as conn:
            # Verificar si el producto existe
            existing = await conn.fetchrow("""
                SELECT id, data_hash FROM products 
                WHERE woo_id = $1
            """, product['id'])
            
            if existing:
                # Comparar hash para ver si realmente cambió
                if existing['data_hash'] == product_hash:
                    logger.debug(f"Producto {product['id']} sin cambios reales")
                    return "unchanged"
                
                # Actualizar producto existente
                return await self._update_product(product, product_hash)
            else:
                # Nuevo producto
                return await self._insert_product(product, product_hash)
    
    def _calculate_product_hash(self, product: Dict[str, Any]) -> str:
        """Calcular hash de los datos importantes del producto"""
        # Campos relevantes para detectar cambios
        relevant_data = {
            'name': product.get('name'),
            'description': product.get('description'),
            'short_description': product.get('short_description'),
            'price': product.get('price'),
            'regular_price': product.get('regular_price'),
            'sale_price': product.get('sale_price'),
            'stock_status': product.get('stock_status'),
            'stock_quantity': product.get('stock_quantity'),
            'categories': [c['id'] for c in product.get('categories', [])],
            'images': [img['src'] for img in product.get('images', [])]
        }
        
        # Crear string determinístico y calcular hash
        data_string = json.dumps(relevant_data, sort_keys=True)
        return hashlib.md5(data_string.encode()).hexdigest()
    
    async def _update_product(self, product: Dict[str, Any], product_hash: str) -> str:
        """Actualizar producto existente"""
        # Usar el método existente del sync_service
        pool = await db_service.get_pool()
        
        # Preparar texto para embedding
        text_for_embedding = self.sync_service._prepare_product_text(product)
        
        # Generar nuevo embedding solo si el contenido cambió significativamente
        embedding = await embedding_service.generate_embedding(text_for_embedding)
        
        if embedding:
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE products SET
                        name = $2,
                        description = $3,
                        short_description = $4,
                        price = $5,
                        categories = $6,
                        embedding = $7,
                        metadata = $8,
                        data_hash = $9,
                        updated_at = NOW()
                    WHERE woo_id = $1
                """, 
                product['id'],
                product.get('name'),
                product.get('description'),
                product.get('short_description'),
                float(product.get('price', 0) or 0),
                [cat['name'] for cat in product.get('categories', [])],
                embedding,
                json.dumps(self.sync_service._extract_metadata(product)),
                product_hash
                )
                
            logger.info(f"✅ Actualizado producto: {product.get('name')}")
            return "updated"
        
        return "error"
    
    async def _insert_product(self, product: Dict[str, Any], product_hash: str) -> str:
        """Insertar nuevo producto"""
        # Reutilizar lógica del sync_service
        batch_stats = await self.sync_service._process_product_batch([product], force_update=False)
        
        if batch_stats["new"] > 0:
            # Actualizar hash
            pool = await db_service.get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE products SET data_hash = $2 
                    WHERE woo_id = $1
                """, product['id'], product_hash)
            
            return "added"
        
        return "error"
    
    async def register_webhook_change(
        self, 
        resource_type: str, 
        resource_id: int, 
        action: str, 
        webhook_data: Dict[str, Any]
    ) -> bool:
        """Registrar cambio recibido por webhook para procesamiento posterior"""
        try:
            pool = await db_service.get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pending_changes 
                    (resource_type, resource_id, action, webhook_data)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (resource_type, resource_id, action) 
                    DO UPDATE SET 
                        webhook_data = $4,
                        created_at = NOW()
                """, resource_type, resource_id, action, json.dumps(webhook_data))
                
            logger.info(f"📌 Registrado cambio webhook: {resource_type} {resource_id} - {action}")
            return True
            
        except Exception as e:
            logger.error(f"Error registrando cambio webhook: {e}")
            return False
    
    async def _process_pending_webhook_changes(self) -> Dict[str, int]:
        """Procesar cambios pendientes de webhooks"""
        stats = {"webhook_processed": 0, "webhook_errors": 0}
        
        pool = await db_service.get_pool()
        async with pool.acquire() as conn:
            # Obtener cambios pendientes
            pending = await conn.fetch("""
                SELECT * FROM pending_changes 
                WHERE processed = FALSE 
                ORDER BY created_at ASC 
                LIMIT 100
            """)
            
            for change in pending:
                try:
                    if change['resource_type'] == 'product':
                        if change['action'] in ['created', 'updated']:
                            # Obtener producto actualizado de WooCommerce
                            product = await self.wc_service.get_product(change['resource_id'])
                            if product:
                                await self._process_single_product(product)
                        elif change['action'] == 'deleted':
                            # Marcar como inactivo
                            await conn.execute("""
                                UPDATE products SET is_active = FALSE 
                                WHERE woo_id = $1
                            """, change['resource_id'])
                    
                    # Marcar como procesado
                    await conn.execute("""
                        UPDATE pending_changes 
                        SET processed = TRUE, processed_at = NOW() 
                        WHERE id = $1
                    """, change['id'])
                    
                    stats["webhook_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error procesando cambio webhook {change['id']}: {e}")
                    stats["webhook_errors"] += 1
        
        return stats
    
    async def _record_sync_completion(
        self, 
        stats: Dict[str, int], 
        status: str = "success", 
        error: Optional[str] = None
    ):
        """Registrar finalización de sincronización"""
        pool = await db_service.get_pool()
        async with pool.acquire() as conn:
            details = {
                "stats": stats,
                "duration_seconds": 0,  # TODO: Calcular duración real
                "error": error
            }
            
            await conn.execute("""
                INSERT INTO sync_control 
                (sync_type, last_sync_time, items_synced, status, details)
                VALUES ($1, $2, $3, $4, $5)
            """, 
            "products", 
            datetime.now(timezone.utc), 
            stats.get("products_updated", 0) + stats.get("products_added", 0),
            status,
            json.dumps(details)
            )
    
    async def start_continuous_sync(self, interval: int = 300):
        """Iniciar sincronización continua cada N segundos"""
        self.sync_interval = interval
        logger.info(f"🔄 Iniciando sincronización continua cada {interval} segundos")
        
        while True:
            try:
                await self.sync_incremental()
            except Exception as e:
                logger.error(f"Error en sincronización continua: {e}")
            
            await asyncio.sleep(self.sync_interval)

# Instancia global del servicio
incremental_sync_service = IncrementalSyncService()