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
from services.woocommerce import WooCommerceService
from services.database import db_service
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
        self.wc_service = WooCommerceService()
        self.template_manager = template_manager
        self.recovery_window_hours = 24  # Tiempo después del cual considerar abandonado
        self.cooldown_hours = 48  # No enviar otro mensaje antes de este tiempo
        
    async def initialize(self):
        """Inicializa el servicio"""
        await self.db_service.initialize()
        logger.info("Cart Recovery Service initialized")
    
    async def get_abandoned_carts(self) -> List[Dict[str, Any]]:
        """
        Obtiene carritos abandonados de WooCommerce
        
        Returns:
            Lista de carritos abandonados con información del cliente
        """
        try:
            # Aquí deberías implementar la lógica real para obtener carritos abandonados
            # Esto puede venir de:
            # 1. Plugin de carritos abandonados de WooCommerce
            # 2. Sesiones guardadas en tu base de datos
            # 3. Webhooks de WooCommerce
            
            # Por ahora, simulamos algunos carritos de ejemplo
            mock_carts = [
                {
                    "cart_id": "cart_123",
                    "customer_name": "María García",
                    "customer_email": "maria@example.com",
                    "customer_phone": "34612345678",
                    "whatsapp_optin": True,
                    "abandoned_at": datetime.now() - timedelta(hours=25),
                    "items": [
                        {
                            "name": "Vela de Lavanda Premium",
                            "quantity": 2,
                            "price": 15.99
                        },
                        {
                            "name": "Difusor de Aromas",
                            "quantity": 1,
                            "price": 24.99
                        }
                    ],
                    "total": 56.97,
                    "cart_url": f"{settings.WOOCOMMERCE_API_URL}/cart?recover=cart_123"
                }
            ]
            
            # Filtrar carritos que cumplan condiciones
            abandoned_carts = []
            for cart in mock_carts:
                # Verificar que el carrito esté abandonado hace más del tiempo configurado
                time_abandoned = datetime.now() - cart["abandoned_at"]
                if time_abandoned.total_seconds() / 3600 >= self.recovery_window_hours:
                    # Verificar que no se haya enviado un mensaje recientemente
                    if not await self._check_recent_message(cart["customer_phone"]):
                        abandoned_carts.append(cart)
            
            logger.info(f"Found {len(abandoned_carts)} abandoned carts eligible for recovery")
            return abandoned_carts
            
        except Exception as e:
            logger.error(f"Error getting abandoned carts: {e}")
            return []
    
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
                        # Enviar mensaje real
                        result = await self.template_manager.send_cart_recovery(
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