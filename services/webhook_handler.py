"""
Manejador de Webhooks de WooCommerce
Procesa actualizaciones automáticas de productos, pedidos y categorías
"""

import asyncio
import logging
import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import HTTPException
from services.woocommerce_sync import wc_sync_service
from services.database import db_service
from services.embedding_service import embedding_service
from config.settings import settings

logger = logging.getLogger(__name__)

class WooCommerceWebhookHandler:
    """Manejador de webhooks de WooCommerce"""
    
    def __init__(self):
        self.webhook_secret = getattr(settings, 'WOOCOMMERCE_WEBHOOK_SECRET', '')
        self.supported_events = {
            'product.created',
            'product.updated', 
            'product.deleted',
            'product.restored',
            'order.created',
            'order.updated',
            'order.deleted'
        }
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verificar la firma del webhook de WooCommerce"""
        if not self.webhook_secret:
            logger.warning("⚠️ WOOCOMMERCE_WEBHOOK_SECRET no configurado - saltando verificación")
            return True
        
        try:
            # WooCommerce usa HMAC-SHA256
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
            
            # Convertir a base64 como lo hace WooCommerce
            import base64
            expected_signature_b64 = base64.b64encode(expected_signature).decode('utf-8')
            
            # Comparar de forma segura
            return hmac.compare_digest(signature, expected_signature_b64)
            
        except Exception as e:
            logger.error(f"❌ Error verificando firma webhook: {e}")
            return False
    
    async def handle_webhook(self, event: str, payload: Dict[str, Any], 
                           signature: str = None, raw_payload: bytes = None) -> Dict[str, Any]:
        """
        Manejar webhook de WooCommerce
        Args:
            event: Tipo de evento (ej: 'product.updated')
            payload: Datos del webhook
            signature: Firma del webhook para verificación
            raw_payload: Payload crudo para verificación de firma
        Returns:
            Resultado del procesamiento
        """
        try:
            # Verificar firma si se proporciona
            if signature and raw_payload:
                if not self.verify_webhook_signature(raw_payload, signature):
                    raise HTTPException(status_code=401, detail="Firma de webhook inválida")
            
            # Verificar que el evento sea soportado
            if event not in self.supported_events:
                logger.warning(f"⚠️ Evento no soportado: {event}")
                return {"status": "ignored", "reason": "evento no soportado"}
            
            logger.info(f"📨 Procesando webhook: {event}")
            
            # Procesar según el tipo de evento
            if event.startswith('product.'):
                return await self._handle_product_webhook(event, payload)
            elif event.startswith('order.'):
                return await self._handle_order_webhook(event, payload)
            else:
                return {"status": "ignored", "reason": "tipo de evento no implementado"}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error procesando webhook {event}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_product_webhook(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar webhooks relacionados con productos"""
        try:
            product_id = payload.get('id')
            if not product_id:
                return {"status": "error", "error": "ID de producto no encontrado"}
            
            if event == 'product.created':
                return await self._handle_product_created(product_id, payload)
            elif event == 'product.updated':
                return await self._handle_product_updated(product_id, payload)
            elif event == 'product.deleted':
                return await self._handle_product_deleted(product_id, payload)
            elif event == 'product.restored':
                return await self._handle_product_restored(product_id, payload)
            
            return {"status": "ignored"}
            
        except Exception as e:
            logger.error(f"❌ Error en webhook de producto: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_product_created(self, product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar creación de producto"""
        logger.info(f"🆕 Producto creado: {product_id}")
        
        try:
            # Sincronizar el nuevo producto
            success = await wc_sync_service.sync_single_product(product_id)
            
            if success:
                return {
                    "status": "success",
                    "action": "product_created",
                    "product_id": product_id,
                    "message": "Producto sincronizado correctamente"
                }
            else:
                return {
                    "status": "error", 
                    "action": "product_created",
                    "product_id": product_id,
                    "error": "Error sincronizando producto"
                }
                
        except Exception as e:
            logger.error(f"❌ Error creando producto {product_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_product_updated(self, product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar actualización de producto"""
        logger.info(f"🔄 Producto actualizado: {product_id}")
        
        try:
            # Sincronizar el producto actualizado
            success = await wc_sync_service.sync_single_product(product_id)
            
            if success:
                return {
                    "status": "success",
                    "action": "product_updated", 
                    "product_id": product_id,
                    "message": "Producto actualizado correctamente"
                }
            else:
                return {
                    "status": "error",
                    "action": "product_updated",
                    "product_id": product_id, 
                    "error": "Error actualizando producto"
                }
                
        except Exception as e:
            logger.error(f"❌ Error actualizando producto {product_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_product_deleted(self, product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar eliminación de producto"""
        logger.info(f"🗑️ Producto eliminado: {product_id}")
        
        try:
            # Marcar producto como inactivo en la base de conocimiento
            external_id = f"product_{product_id}"
            existing = await db_service.get_knowledge_by_external_id(external_id)
            
            if existing:
                success = await db_service.delete_knowledge(existing['id'])
                
                if success:
                    return {
                        "status": "success",
                        "action": "product_deleted",
                        "product_id": product_id,
                        "message": "Producto marcado como inactivo"
                    }
                else:
                    return {
                        "status": "error",
                        "action": "product_deleted", 
                        "product_id": product_id,
                        "error": "Error marcando producto como inactivo"
                    }
            else:
                return {
                    "status": "ignored",
                    "action": "product_deleted",
                    "product_id": product_id,
                    "message": "Producto no encontrado en base de conocimiento"
                }
                
        except Exception as e:
            logger.error(f"❌ Error eliminando producto {product_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_product_restored(self, product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar restauración de producto"""
        logger.info(f"♻️ Producto restaurado: {product_id}")
        
        try:
            # Re-sincronizar el producto restaurado
            success = await wc_sync_service.sync_single_product(product_id)
            
            if success:
                return {
                    "status": "success",
                    "action": "product_restored",
                    "product_id": product_id,
                    "message": "Producto restaurado y sincronizado"
                }
            else:
                return {
                    "status": "error",
                    "action": "product_restored",
                    "product_id": product_id,
                    "error": "Error restaurando producto"
                }
                
        except Exception as e:
            logger.error(f"❌ Error restaurando producto {product_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _handle_order_webhook(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar webhooks relacionados con pedidos"""
        try:
            order_id = payload.get('id')
            if not order_id:
                return {"status": "error", "error": "ID de pedido no encontrado"}
            
            logger.info(f"📦 Webhook de pedido {event}: {order_id}")
            
            # Por ahora solo registramos los eventos de pedidos
            # En el futuro se puede implementar análisis de tendencias, etc.
            
            return {
                "status": "success",
                "action": event,
                "order_id": order_id,
                "message": "Evento de pedido registrado"
            }
            
        except Exception as e:
            logger.error(f"❌ Error en webhook de pedido: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_webhook_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de webhooks procesados"""
        try:
            # Aquí se podría implementar un sistema de métricas más avanzado
            # Por ahora retornamos información básica
            
            return {
                "supported_events": list(self.supported_events),
                "webhook_secret_configured": bool(self.webhook_secret),
                "last_processed": datetime.now().isoformat(),
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de webhooks: {e}")
            return {"error": str(e)}

# Instancia global del manejador de webhooks
webhook_handler = WooCommerceWebhookHandler() 