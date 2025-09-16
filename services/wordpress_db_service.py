"""
Servicio para conectar con la base de datos de WordPress/WooCommerce
y obtener información de carritos abandonados
"""

import asyncio
import aiomysql
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class WordPressDBService:
    """
    Servicio para interactuar con la base de datos de WordPress
    """
    
    def __init__(self):
        self.pool = None
        self.table_prefix = getattr(settings, 'WORDPRESS_TABLE_PREFIX', 'wp_')
        
    async def initialize(self):
        """Inicializa el pool de conexiones"""
        try:
            # Solo inicializar si hay configuración de WordPress
            if not hasattr(settings, 'WORDPRESS_DB_HOST'):
                logger.warning("No WordPress DB configuration found, skipping initialization")
                return
                
            self.pool = await aiomysql.create_pool(
                host=settings.WORDPRESS_DB_HOST,
                port=int(getattr(settings, 'WORDPRESS_DB_PORT', 3306)),
                user=settings.WORDPRESS_DB_USER,
                password=settings.WORDPRESS_DB_PASSWORD,
                db=settings.WORDPRESS_DB_NAME,
                charset='utf8mb4',
                autocommit=True,
                minsize=1,
                maxsize=10
            )
            logger.info("WordPress DB connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing WordPress DB: {e}")
            self.pool = None
    
    async def close(self):
        """Cierra el pool de conexiones"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
    
    async def get_abandoned_carts_from_woocommerce(self, hours_ago: int = 24) -> List[Dict[str, Any]]:
        """
        Obtiene carritos abandonados de las sesiones de WooCommerce
        
        Args:
            hours_ago: Horas hacia atrás para buscar carritos abandonados
            
        Returns:
            Lista de carritos abandonados
        """
        if not self.pool:
            logger.warning("WordPress DB not initialized")
            return []
            
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Query para obtener sesiones con carritos no vacíos
                    query = f"""
                    SELECT 
                        session_key,
                        session_value,
                        session_expiry
                    FROM {self.table_prefix}woocommerce_sessions
                    WHERE session_expiry > UNIX_TIMESTAMP()
                    AND session_expiry < UNIX_TIMESTAMP(DATE_ADD(NOW(), INTERVAL %s HOUR))
                    AND session_value LIKE '%cart_contents%'
                    AND session_value NOT LIKE '%cart_contents";a:0:%'
                    """
                    
                    await cursor.execute(query, (hours_ago,))
                    sessions = await cursor.fetchall()
                    
                    abandoned_carts = []
                    for session in sessions:
                        try:
                            # Parsear los datos de la sesión (PHP serialized)
                            cart_data = self._parse_session_data(session['session_value'])
                            if cart_data:
                                abandoned_carts.append({
                                    'session_key': session['session_key'],
                                    'cart_data': cart_data,
                                    'expiry': datetime.fromtimestamp(session['session_expiry'])
                                })
                        except Exception as e:
                            logger.error(f"Error parsing session {session['session_key']}: {e}")
                            
                    return abandoned_carts
                    
        except Exception as e:
            logger.error(f"Error getting abandoned carts from WooCommerce: {e}")
            return []
    
    async def get_abandoned_carts_from_cartflows(self, hours_ago: int = 24) -> List[Dict[str, Any]]:
        """
        Obtiene carritos abandonados de CartFlows si está instalado
        
        Args:
            hours_ago: Horas hacia atrás para buscar carritos abandonados
            
        Returns:
            Lista de carritos abandonados
        """
        if not self.pool:
            logger.warning("WordPress DB not initialized")
            return []
            
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Verificar si existe la tabla de CartFlows
                    table_name = f"{self.table_prefix}cartflows_ca_cart_abandonment"
                    check_query = """
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = %s 
                    AND table_name = %s
                    """
                    
                    await cursor.execute(check_query, (settings.WORDPRESS_DB_NAME, table_name))
                    result = await cursor.fetchone()
                    
                    if result['count'] == 0:
                        logger.info("CartFlows table not found")
                        return []
                    
                    # Query para obtener carritos abandonados de CartFlows
                    query = f"""
                    SELECT 
                        session_id,
                        email,
                        cart_contents,
                        cart_total,
                        time as abandoned_time,
                        other_fields,
                        checkout_id
                    FROM {table_name}
                    WHERE order_status IN ('abandoned', 'processing')
                    AND time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                    AND unsubscribed = 0
                    ORDER BY time DESC
                    """
                    
                    await cursor.execute(query, (hours_ago,))
                    carts = await cursor.fetchall()
                    
                    abandoned_carts = []
                    for cart in carts:
                        try:
                            # Parsear cart_contents (PHP serialized o JSON)
                            cart_items = self._parse_cart_contents(cart['cart_contents'])
                            
                            # Parsear other_fields para obtener teléfono
                            other_fields = self._parse_other_fields(cart['other_fields'])
                            
                            if cart_items and cart['email']:
                                abandoned_carts.append({
                                    'cart_id': cart['session_id'],
                                    'email': cart['email'],
                                    'phone': other_fields.get('phone', ''),
                                    'customer_name': other_fields.get('name', ''),
                                    'items': cart_items,
                                    'total': float(cart['cart_total']) if cart['cart_total'] else 0,
                                    'abandoned_at': cart['abandoned_time'],
                                    'checkout_id': cart['checkout_id']
                                })
                        except Exception as e:
                            logger.error(f"Error parsing cart {cart['session_id']}: {e}")
                            
                    return abandoned_carts
                    
        except Exception as e:
            logger.error(f"Error getting abandoned carts from CartFlows: {e}")
            return []
    
    def _parse_session_data(self, session_value: str) -> Optional[Dict[str, Any]]:
        """
        Parsea los datos de sesión de WooCommerce (PHP serialized)
        
        Args:
            session_value: Valor serializado de la sesión
            
        Returns:
            Datos parseados o None
        """
        # Esto es una simplificación - en producción necesitarías
        # una librería para parsear PHP serialized data
        try:
            # Por ahora retornamos None para indicar que necesita implementación
            logger.debug("PHP serialized parsing not implemented")
            return None
        except Exception as e:
            logger.error(f"Error parsing session data: {e}")
            return None
    
    def _parse_cart_contents(self, cart_contents: str) -> List[Dict[str, Any]]:
        """
        Parsea el contenido del carrito
        
        Args:
            cart_contents: Contenido serializado del carrito
            
        Returns:
            Lista de items del carrito
        """
        try:
            # Intenta parsear como JSON primero
            import json
            if cart_contents.startswith('{') or cart_contents.startswith('['):
                return json.loads(cart_contents)
            
            # Si no es JSON, probablemente es PHP serialized
            # Por ahora retornamos lista vacía
            return []
        except Exception as e:
            logger.error(f"Error parsing cart contents: {e}")
            return []
    
    def _parse_other_fields(self, other_fields: str) -> Dict[str, str]:
        """
        Parsea campos adicionales
        
        Args:
            other_fields: Campos serializados
            
        Returns:
            Diccionario con los campos
        """
        try:
            import json
            if other_fields and (other_fields.startswith('{') or other_fields.startswith('[')):
                return json.loads(other_fields)
            return {}
        except Exception as e:
            logger.error(f"Error parsing other fields: {e}")
            return {}


# Instancia global del servicio
wordpress_db_service = WordPressDBService()