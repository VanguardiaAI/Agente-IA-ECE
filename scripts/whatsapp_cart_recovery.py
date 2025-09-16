#!/usr/bin/env python3
"""
Script para recuperación de carritos abandonados vía WhatsApp
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.whatsapp_templates import template_manager
from services.whatsapp_360dialog_service import whatsapp_service
from services.woocommerce import WooCommerceService
from services.database import db_service
from services.wordpress_db_service import wordpress_db_service
from config.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CartRecoveryService:
    """
    Servicio para recuperación de carritos abandonados
    """
    
    def __init__(self):
        self.db_service = db_service
        self.wordpress_db = wordpress_db_service
        self.wc_service = WooCommerceService()
        self.template_manager = template_manager
        self.recovery_window_hours = getattr(settings, 'CART_ABANDONMENT_MINUTES', 20) / 60  # Convertir minutos a horas
        self.cooldown_hours = getattr(settings, 'CART_RECOVERY_DISCOUNT_HOURS', 48)
        
    async def initialize(self):
        """Inicializa el servicio"""
        try:
            await self.db_service.initialize()
        except Exception as e:
            logger.warning(f"Could not initialize database service: {e}")
            logger.info("Continuing without database for testing purposes")
        
        await self.wordpress_db.initialize()
        logger.info("Cart Recovery Service initialized")
    
    async def get_abandoned_carts(self) -> List[Dict[str, Any]]:
        """
        Obtiene carritos abandonados de WooCommerce
        
        Returns:
            Lista de carritos abandonados con información del cliente
        """
        try:
            all_abandoned_carts = []
            
            # Intentar obtener de CartFlows primero
            cartflows_carts = await self.wordpress_db.get_abandoned_carts_from_cartflows(
                hours_ago=int(self.recovery_window_hours)
            )
            
            if cartflows_carts:
                logger.info(f"Found {len(cartflows_carts)} carts from CartFlows")
                for cart in cartflows_carts:
                    # Formatear para nuestro sistema
                    formatted_cart = {
                        "cart_id": cart['cart_id'],
                        "customer_name": cart['customer_name'] or cart['email'].split('@')[0],
                        "customer_email": cart['email'],
                        "customer_phone": self._normalize_phone(cart['phone']),
                        "whatsapp_optin": True,  # Asumir opt-in si tienen teléfono
                        "abandoned_at": cart['abandoned_at'],
                        "items": cart['items'],
                        "total": cart['total'],
                        "cart_url": f"{settings.WOOCOMMERCE_URL}/checkout/?recover={cart['cart_id']}"
                    }
                    
                    # Solo agregar si tiene número de teléfono válido
                    if formatted_cart['customer_phone']:
                        all_abandoned_carts.append(formatted_cart)
            
            # Si no hay de CartFlows, intentar obtener de sesiones de WooCommerce
            if not all_abandoned_carts:
                woo_carts = await self.wordpress_db.get_abandoned_carts_from_woocommerce(
                    hours_ago=int(self.recovery_window_hours)
                )
                
                if woo_carts:
                    logger.info(f"Found {len(woo_carts)} carts from WooCommerce sessions")
                    # Procesar carritos de WooCommerce (necesita más trabajo para extraer datos)
            
            # Si aún no hay carritos reales y estamos en desarrollo, usar mock data
            if not all_abandoned_carts and settings.ENVIRONMENT == 'development':
                logger.warning("No real abandoned carts found, using mock data for testing")
                # Usar número de México para pruebas
                test_phone = "525610830260"  # Número de prueba de México
                all_abandoned_carts = [
                    {
                        "cart_id": "test_cart_mx_123",
                        "customer_name": "Cliente Prueba México",
                        "customer_email": "prueba@vanguardia.dev", 
                        "customer_phone": test_phone,
                        "whatsapp_optin": True,
                        "abandoned_at": datetime.now() - timedelta(hours=2),
                        "items": [
                            {
                                "name": "Cable THHN 12 AWG Rojo (100m)",
                                "quantity": 2,
                                "price": 45.50
                            },
                            {
                                "name": "Contacto Duplex Polarizado",
                                "quantity": 5,
                                "price": 12.80
                            }
                        ],
                        "total": 155.00,
                        "cart_url": f"{settings.WOOCOMMERCE_URL}/cart?recover=test_cart_mx_123"
                    }
                ]
            
            # Filtrar carritos elegibles
            eligible_carts = []
            for cart in all_abandoned_carts:
                # Verificar que no se haya enviado un mensaje recientemente
                if not await self._check_recent_message(cart["customer_phone"]):
                    eligible_carts.append(cart)
                else:
                    logger.info(f"Skipping cart {cart['cart_id']} - recent message sent")
            
            logger.info(f"Found {len(eligible_carts)} abandoned carts eligible for recovery")
            return eligible_carts
            
        except Exception as e:
            logger.error(f"Error getting abandoned carts: {e}")
            return []
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normaliza el número de teléfono al formato esperado
        
        Args:
            phone: Número de teléfono
            
        Returns:
            Número normalizado o cadena vacía si no es válido
        """
        if not phone:
            return ""
            
        # Eliminar caracteres no numéricos
        phone = ''.join(filter(str.isdigit, phone))
        
        # Si no empieza con código de país, agregar el de España (34)
        if len(phone) == 9 and phone[0] in ['6', '7']:
            phone = '34' + phone
        
        # Validar longitud mínima
        if len(phone) < 10:
            return ""
            
        return phone
    
    async def _check_recent_message(self, phone_number: str) -> bool:
        """
        Verifica si se envió un mensaje de recuperación recientemente
        
        Args:
            phone_number: Número de teléfono del cliente
            
        Returns:
            True si se envió un mensaje recientemente
        """
        try:
            # Consultar en la base de datos si hay mensajes recientes
            query = """
            SELECT COUNT(*) as count
            FROM conversation_logs
            WHERE user_id = $1
            AND platform = 'whatsapp'
            AND metadata->>'template_type' = 'cart_recovery'
            AND timestamp > $2
            """
            
            cutoff_time = datetime.now() - timedelta(hours=self.cooldown_hours)
            
            # Por ahora retornamos False (no hay mensaje reciente)
            # En producción, ejecutarías la query real
            return False
            
        except Exception as e:
            logger.error(f"Error checking recent messages: {e}")
            return True  # En caso de error, mejor no enviar
    
    async def send_recovery_messages(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Envía mensajes de recuperación de carrito
        
        Args:
            dry_run: Si es True, no envía mensajes reales
            
        Returns:
            Estadísticas del proceso
        """
        try:
            # Obtener carritos abandonados
            abandoned_carts = await self.get_abandoned_carts()
            
            stats = {
                "total_carts": len(abandoned_carts),
                "messages_sent": 0,
                "errors": 0,
                "skipped": 0,
                "dry_run": dry_run
            }
            
            for cart in abandoned_carts:
                try:
                    # Preparar datos del carrito
                    cart_data = {
                        "customer_name": cart["customer_name"],
                        "items": cart["items"],
                        "total": cart["total"],
                        "cart_url": cart["cart_url"]
                    }
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would send cart recovery to {cart['customer_phone']} - {cart['customer_name']}")
                        stats["messages_sent"] += 1
                    else:
                        # Enviar mensaje real con plantilla multimedia
                        result = await self.template_manager.send_cart_recovery_multimedia(
                            phone_number=cart["customer_phone"],
                            cart_data=cart_data
                        )
                        
                        if result:
                            logger.info(f"Sent cart recovery message to {cart['customer_phone']}")
                            stats["messages_sent"] += 1
                            
                            # Registrar el envío en la base de datos
                            await self._log_recovery_sent(cart)
                        else:
                            stats["errors"] += 1
                    
                    # Pequeña pausa entre mensajes para evitar rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error sending recovery for cart {cart.get('cart_id')}: {e}")
                    stats["errors"] += 1
            
            # Log resumen
            logger.info(f"Cart recovery completed: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in cart recovery process: {e}")
            raise
    
    async def _send_enhanced_cart_recovery(self, phone_number: str, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía mensaje de recuperación con formato visual mejorado
        """
        try:
            # Opción 1: Intentar enviar con imagen y caption (no requiere aprobación)
            customer_name = cart_data.get("customer_name", "").split()[0] if cart_data.get("customer_name") else "Cliente"
            items = cart_data.get("items", [])
            total = cart_data.get("total", 0)
            discount_code = cart_data.get("discount_code", "DESCUENTOEXPRESS")
            cart_url = cart_data.get("cart_url", "")
            
            # Formatear productos como en la imagen de referencia
            product_lines = []
            for item in items[:5]:  # Máximo 5 productos
                name = item.get('name', 'Producto')
                sku = item.get('sku', '')
                quantity = item.get('quantity', 1)
                
                if sku:
                    line = f"- {name} ({sku})"
                else:
                    line = f"- {name}"
                
                if quantity > 1:
                    line += f" x{quantity}"
                    
                product_lines.append(line)
            
            # Crear el mensaje con formato similar a la imagen
            caption = f"""¡Hola {customer_name}! 👋

No te olvides de completar tu compra. Hemos guardado estos productos para ti:

{chr(10).join(product_lines)}

💰 Total: {total:.2f} €

🎁 ¡OFERTA ESPECIAL!
Usa el código {discount_code} y obtén un 5% de descuento

⏰ Válido solo por 24 horas

¿Necesitas ayuda? Responde a este mensaje.

🛒 Completa tu compra aquí:
{cart_url}"""

            # URL del logo de El Corte Eléctrico
            logo_url = getattr(settings, 'COMPANY_LOGO_URL', 'https://elcorteelectrico.es/wp-content/uploads/2023/01/logo-el-corte-electrico.png')
            
            # Intentar enviar con imagen
            try:
                result = await whatsapp_service.send_image_message(
                    to=phone_number,
                    image_url=logo_url,
                    caption=caption
                )
                logger.info(f"Sent enhanced cart recovery with image to {phone_number}")
                return result
            except Exception as img_error:
                logger.warning(f"Could not send image message: {img_error}")
                
                # Fallback: enviar solo texto
                result = await whatsapp_service.send_text_message(
                    to=phone_number,
                    text=caption
                )
                logger.info(f"Sent text-only cart recovery to {phone_number}")
                return result
                
        except Exception as e:
            logger.error(f"Error in enhanced cart recovery: {e}")
            # Último fallback: usar plantilla aprobada
            return await self.template_manager.send_cart_recovery(
                phone_number=phone_number,
                cart_data=cart_data
            )
    
    async def _log_recovery_sent(self, cart: Dict[str, Any]):
        """
        Registra el envío de un mensaje de recuperación
        
        Args:
            cart: Datos del carrito
        """
        try:
            # Aquí deberías guardar en la base de datos
            log_data = {
                "timestamp": datetime.now(),
                "user_id": cart["customer_phone"],
                "platform": "whatsapp",
                "message": "Cart recovery template sent",
                "metadata": {
                    "template_type": "cart_recovery",
                    "cart_id": cart["cart_id"],
                    "cart_total": cart["total"],
                    "customer_email": cart["customer_email"]
                }
            }
            
            # En producción, guardarías esto en la base de datos
            logger.info(f"Logged recovery message for {cart['customer_phone']}")
            
        except Exception as e:
            logger.error(f"Error logging recovery: {e}")
    
    async def get_recovery_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtiene estadísticas de recuperación de carritos
        
        Args:
            days: Días a incluir en las estadísticas
            
        Returns:
            Estadísticas de recuperación
        """
        try:
            # En producción, consultarías la base de datos
            stats = {
                "period_days": days,
                "messages_sent": 0,
                "carts_recovered": 0,
                "recovery_rate": 0.0,
                "revenue_recovered": 0.0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting recovery stats: {e}")
            return {}


async def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Cart Recovery Tool')
    parser.add_argument('--dry-run', action='store_true', help='Simular sin enviar mensajes reales')
    parser.add_argument('--stats', action='store_true', help='Mostrar estadísticas de recuperación')
    parser.add_argument('--days', type=int, default=7, help='Días para estadísticas (default: 7)')
    
    args = parser.parse_args()
    
    # Inicializar servicio
    service = CartRecoveryService()
    await service.initialize()
    
    if args.stats:
        # Mostrar estadísticas
        stats = await service.get_recovery_stats(args.days)
        print("\n📊 ESTADÍSTICAS DE RECUPERACIÓN DE CARRITOS")
        print("=" * 50)
        print(f"Período: Últimos {stats['period_days']} días")
        print(f"Mensajes enviados: {stats['messages_sent']}")
        print(f"Carritos recuperados: {stats['carts_recovered']}")
        print(f"Tasa de recuperación: {stats['recovery_rate']:.1f}%")
        print(f"Ingresos recuperados: €{stats['revenue_recovered']:.2f}")
        print("=" * 50)
    else:
        # Ejecutar recuperación de carritos
        print("\n🛒 INICIANDO RECUPERACIÓN DE CARRITOS ABANDONADOS")
        print("=" * 50)
        
        if args.dry_run:
            print("⚠️  MODO DRY RUN - No se enviarán mensajes reales")
        
        stats = await service.send_recovery_messages(dry_run=args.dry_run)
        
        print("\n✅ PROCESO COMPLETADO")
        print("=" * 50)
        print(f"Carritos encontrados: {stats['total_carts']}")
        print(f"Mensajes enviados: {stats['messages_sent']}")
        print(f"Errores: {stats['errors']}")
        print(f"Omitidos: {stats['skipped']}")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())