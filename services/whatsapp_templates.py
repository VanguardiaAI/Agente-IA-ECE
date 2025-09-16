"""
Sistema de plantillas para mensajes de WhatsApp
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from services.whatsapp_360dialog_service import whatsapp_service
from services.woocommerce import WooCommerceService
from services.database import db_service
from config.settings import settings

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Tipos de plantillas disponibles"""
    CART_RECOVERY = "cart_recovery"
    ORDER_CONFIRMATION = "order_confirmation"
    WELCOME = "welcome_message"
    SHIPPING_UPDATE = "shipping_update"
    PAYMENT_REMINDER = "payment_reminder"
    PRODUCT_BACK_IN_STOCK = "product_back_in_stock"
    REVIEW_REQUEST = "review_request"
    PROMOTIONAL = "promotional"


class WhatsAppTemplateManager:
    """
    Gestiona las plantillas de WhatsApp para diferentes casos de uso
    """
    
    def __init__(self):
        self.db_service = db_service
        self.wc_service = WooCommerceService()
        self.templates = {
            TemplateType.CART_RECOVERY: getattr(settings, 'WHATSAPP_CART_RECOVERY_TEMPLATE', 'cart_recovery'),
            TemplateType.ORDER_CONFIRMATION: getattr(settings, 'WHATSAPP_ORDER_CONFIRMATION_TEMPLATE', 'order_confirmation'),
            TemplateType.WELCOME: getattr(settings, 'WHATSAPP_WELCOME_TEMPLATE', 'welcome_message')
        }
        logger.info("WhatsApp Template Manager initialized")
    
    async def send_cart_recovery_multimedia(self, phone_number: str, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía mensaje de recuperación de carrito con plantilla multimedia aprobada
        Requiere plantilla aprobada: carrito_abandono_multimedia
        
        Variables de la plantilla:
        {{1}}: Nombre del cliente
        {{2}}: Lista de productos formateada
        {{3}}: Total del carrito
        {{4}}: Código de descuento
        {{5}}: URL del carrito (para botón)
        """
        try:
            # Usar la nueva plantilla multimedia
            template_name = "carrito_abandono_multimedia"
            
            # Preparar componentes con el nuevo formato
            components = self._build_cart_recovery_multimedia_components(cart_data)
            
            # Enviar plantilla
            result = await whatsapp_service.send_template_message(
                to=phone_number,
                template_name=template_name,
                language_code="es",
                components=components
            )
            
            # Registrar envío
            await self._log_template_sent(
                phone_number,
                TemplateType.CART_RECOVERY,
                cart_data,
                result
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error sending multimedia cart recovery template: {str(e)}")
            # NO hacer fallback - propagar el error para ver qué pasa
            raise
    
    async def send_cart_recovery(self, phone_number: str, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía mensaje de recuperación de carrito abandonado con plantilla carrito_recuperacion_descuento
        
        Args:
            phone_number: Número de teléfono del cliente
            cart_data: Datos del carrito abandonado (debe incluir discount_code, items, total)
            
        Returns:
            Respuesta de la API con el ID del mensaje
        """
        try:
            # Usar la plantilla específica carrito_recuperacion_descuento
            template_name = "carrito_recuperacion_descuento"
            
            # Preparar componentes de la plantilla con el formato específico
            components = self._build_cart_recovery_components_v2(cart_data)
            
            # Enviar plantilla
            result = await whatsapp_service.send_template_message(
                to=phone_number,
                template_name=template_name,
                language_code="es",  # Cambiar a "es" que es el idioma aprobado
                components=components
            )
            
            # Registrar envío
            await self._log_template_sent(
                phone_number,
                TemplateType.CART_RECOVERY,
                cart_data,
                result
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error sending cart recovery template: {str(e)}")
            raise
    
    async def send_order_confirmation(self, phone_number: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía confirmación de pedido
        
        Args:
            phone_number: Número de teléfono del cliente
            order_data: Datos del pedido
            
        Returns:
            Respuesta de la API
        """
        try:
            # Preparar componentes
            components = self._build_order_confirmation_components(order_data)
            
            # Enviar plantilla
            result = await whatsapp_service.send_template_message(
                to=phone_number,
                template_name=self.templates[TemplateType.ORDER_CONFIRMATION],
                language_code="es",
                components=components
            )
            
            # Registrar envío
            await self._log_template_sent(
                phone_number,
                TemplateType.ORDER_CONFIRMATION,
                order_data,
                result
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error sending order confirmation template: {str(e)}")
            raise
    
    async def send_welcome_message(self, phone_number: str, customer_name: str = "") -> Dict[str, Any]:
        """
        Envía mensaje de bienvenida
        
        Args:
            phone_number: Número de teléfono del cliente
            customer_name: Nombre del cliente (opcional)
            
        Returns:
            Respuesta de la API
        """
        try:
            # Preparar componentes
            components = []
            if customer_name:
                components.append({
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": customer_name}
                    ]
                })
            
            # Enviar plantilla
            result = await whatsapp_service.send_template_message(
                to=phone_number,
                template_name=self.templates[TemplateType.WELCOME],
                language_code="es",
                components=components if components else None
            )
            
            # Registrar envío
            await self._log_template_sent(
                phone_number,
                TemplateType.WELCOME,
                {"customer_name": customer_name},
                result
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error sending welcome template: {str(e)}")
            raise
    
    def _build_cart_recovery_components(self, cart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye los componentes para la plantilla de recuperación de carrito
        
        Args:
            cart_data: Datos del carrito
            
        Returns:
            Lista de componentes
        """
        components = []
        
        # Componente del cuerpo con parámetros dinámicos
        body_params = []
        
        # Nombre del cliente
        if cart_data.get("customer_name"):
            body_params.append({
                "type": "text",
                "text": cart_data["customer_name"]
            })
        
        # Productos del carrito (máximo 3 para no sobrecargar)
        items = cart_data.get("items", [])[:3]
        product_list = []
        for item in items:
            product_list.append(f"• {item.get('name', 'Producto')} x{item.get('quantity', 1)}")
        
        if product_list:
            body_params.append({
                "type": "text",
                "text": "\n".join(product_list)
            })
        
        # Total del carrito
        if cart_data.get("total"):
            body_params.append({
                "type": "text",
                "text": f"{cart_data['total']}€"
            })
        
        if body_params:
            components.append({
                "type": "body",
                "parameters": body_params
            })
        
        # Botón con enlace al carrito
        if cart_data.get("cart_url"):
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {
                        "type": "text",
                        "text": cart_data["cart_url"]
                    }
                ]
            })
        
        return components
    
    def _build_cart_recovery_components_v2(self, cart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye los componentes para la plantilla carrito_recuperacion_descuento
        con el formato específico requerido por Meta
        
        Variables de la plantilla:
        {{1}}: Código de descuento (DESCUENTOEXPRESS)
        {{2}}: Lista formateada de productos con guión
        {{3}}: Total del carrito en formato "X,XX €"
        
        Args:
            cart_data: Datos del carrito con keys: discount_code, items, total
            
        Returns:
            Lista de componentes para la plantilla
        """
        components = []
        
        # Componente del cuerpo con 3 parámetros
        body_params = []
        
        # Variable {{1}}: Código de descuento (siempre DESCUENTOEXPRESS)
        discount_code = cart_data.get("discount_code", "DESCUENTOEXPRESS")
        body_params.append({
            "type": "text",
            "text": discount_code
        })
        
        # Variable {{2}}: Lista formateada de productos
        items = cart_data.get("items", [])
        product_list = []
        
        for item in items:
            # Formato como en el ejemplo de la plantilla:
            # - Nombre del Producto (SKU si existe)
            product_name = item.get('name', 'Producto')
            sku = item.get('sku', '')
            quantity = item.get('quantity', 1)
            
            # Si hay más de 1 unidad, incluir cantidad
            if quantity > 1:
                if sku:
                    formatted_item = f"- {product_name} ({sku}) x{quantity}"
                else:
                    formatted_item = f"- {product_name} x{quantity}"
            else:
                if sku:
                    formatted_item = f"- {product_name} ({sku})"
                else:
                    formatted_item = f"- {product_name}"
            
            product_list.append(formatted_item)
        
        # Unir todos los productos con punto y coma o coma
        # No podemos usar saltos de línea en los parámetros de plantilla
        products_text = "; ".join(product_list) if product_list else "- Productos del carrito"
        body_params.append({
            "type": "text",
            "text": products_text
        })
        
        # Variable {{3}}: Total del carrito en formato español (13,81 €)
        cart_total = cart_data.get("total", 0)
        # Formatear con coma decimal como en España
        total_formatted = f"{cart_total:.2f}".replace('.', ',') + " €"
        body_params.append({
            "type": "text",
            "text": total_formatted
        })
        
        # Añadir componente del cuerpo con los 3 parámetros
        components.append({
            "type": "body",
            "parameters": body_params
        })
        
        # NO agregar botón - la plantilla aprobada no tiene botón
        
        return components
    
    def _build_cart_recovery_multimedia_components(self, cart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye componentes para la nueva plantilla multimedia
        
        Variables del body:
        {{1}}: Nombre del cliente
        {{2}}: Lista de productos formateada  
        {{3}}: Total del carrito
        {{4}}: Código de descuento
        
        Nota: El botón tiene URL estática, no dinámica
        """
        components = []
        
        # Header con imagen - REQUERIDO para plantilla multimedia
        # Usar la imagen exacta de El Corte Eléctrico
        components.append({
            "type": "header",
            "parameters": [
                {
                    "type": "image",
                    "image": {
                        "link": cart_data.get("header_image_url", "https://i.imgur.com/HP7WXrY.png")
                    }
                }
            ]
        })
        
        # Body con 4 parámetros
        body_params = []
        
        # Variable {{1}}: Nombre del cliente
        customer_name = cart_data.get("customer_name", "Cliente")
        # Obtener solo el primer nombre
        first_name = customer_name.split()[0] if customer_name else "Cliente"
        body_params.append({
            "type": "text",
            "text": first_name
        })
        
        # Variable {{2}}: Lista de productos formateada
        items = cart_data.get("items", [])
        product_lines = []
        
        for item in items[:5]:  # Máximo 5 productos
            name = item.get('name', 'Producto')
            sku = item.get('sku', '')
            quantity = item.get('quantity', 1)
            
            # Formato como en la imagen: "- Nombre SKU"
            if sku:
                line = f"- {name} {sku}"
            else:
                line = f"- {name}"
            
            if quantity > 1:
                line += f" x{quantity}"
            
            product_lines.append(line)
        
        # NO podemos usar saltos de línea en parámetros de plantilla
        # Usar punto y coma o coma para separar
        products_text = "; ".join(product_lines) if product_lines else "- Tus productos seleccionados"
        body_params.append({
            "type": "text",
            "text": products_text
        })
        
        # Variable {{3}}: Total formateado
        cart_total = cart_data.get("total", 0)
        if isinstance(cart_total, str):
            total_formatted = cart_total
        else:
            total_formatted = f"{cart_total:.2f}".replace('.', ',') + " €"
        body_params.append({
            "type": "text",
            "text": total_formatted
        })
        
        # Variable {{4}}: Código de descuento
        discount_code = cart_data.get("discount_code", "DESCUENTOEXPRESS")
        body_params.append({
            "type": "text",
            "text": discount_code
        })
        
        # Añadir componente del cuerpo
        components.append({
            "type": "body",
            "parameters": body_params
        })
        
        # NO incluir botón - La plantilla tiene URL estática configurada en Meta
        
        return components
    
    def _build_order_confirmation_components(self, order_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye los componentes para la plantilla de confirmación de pedido
        
        Args:
            order_data: Datos del pedido
            
        Returns:
            Lista de componentes
        """
        components = []
        
        # Parámetros del cuerpo
        body_params = []
        
        # Número de pedido
        if order_data.get("order_number"):
            body_params.append({
                "type": "text",
                "text": f"#{order_data['order_number']}"
            })
        
        # Nombre del cliente
        if order_data.get("customer_name"):
            body_params.append({
                "type": "text",
                "text": order_data["customer_name"]
            })
        
        # Total del pedido
        if order_data.get("total"):
            body_params.append({
                "type": "text",
                "text": f"{order_data['total']}€"
            })
        
        # Fecha estimada de entrega
        if order_data.get("estimated_delivery"):
            body_params.append({
                "type": "text",
                "text": order_data["estimated_delivery"]
            })
        
        if body_params:
            components.append({
                "type": "body",
                "parameters": body_params
            })
        
        # Botón para ver el pedido
        if order_data.get("order_url"):
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {
                        "type": "text",
                        "text": order_data["order_url"]
                    }
                ]
            })
        
        return components
    
    async def _log_template_sent(self, phone_number: str, template_type: TemplateType,
                                data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Registra el envío de una plantilla
        
        Args:
            phone_number: Número de teléfono
            template_type: Tipo de plantilla
            data: Datos utilizados
            result: Resultado del envío
        """
        try:
            log_entry = {
                "timestamp": datetime.now(),
                "phone_number": phone_number,
                "template_type": template_type.value,
                "template_data": data,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "status": "sent",
                "response": result
            }
            
            # Aquí deberías guardar en la base de datos
            logger.info(f"Template sent: {template_type.value} to {phone_number}")
            
        except Exception as e:
            logger.error(f"Error logging template: {str(e)}")
    
    async def get_abandoned_carts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtiene carritos abandonados para recuperación
        
        Args:
            hours: Horas de abandono para considerar
            
        Returns:
            Lista de carritos abandonados
        """
        try:
            # Aquí deberías implementar la lógica para obtener carritos abandonados
            # desde WooCommerce o tu sistema de tracking
            
            # Por ahora, retornamos un ejemplo
            abandoned_carts = []
            
            # Esta es una implementación de ejemplo
            # En producción, deberías consultar tu base de datos o WooCommerce
            
            return abandoned_carts
        
        except Exception as e:
            logger.error(f"Error getting abandoned carts: {str(e)}")
            return []
    
    async def process_cart_recovery_batch(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Procesa un lote de carritos abandonados para recuperación
        
        Args:
            dry_run: Si es True, no envía mensajes, solo simula
            
        Returns:
            Resumen del procesamiento
        """
        try:
            # Obtener carritos abandonados
            abandoned_carts = await self.get_abandoned_carts()
            
            results = {
                "total_carts": len(abandoned_carts),
                "messages_sent": 0,
                "errors": 0,
                "skipped": 0
            }
            
            for cart in abandoned_carts:
                try:
                    # Verificar si el cliente tiene opt-in para WhatsApp
                    if not cart.get("whatsapp_optin", False):
                        results["skipped"] += 1
                        continue
                    
                    # Verificar si ya se envió un mensaje recientemente
                    if await self._already_sent_recently(cart["phone_number"], TemplateType.CART_RECOVERY):
                        results["skipped"] += 1
                        continue
                    
                    if not dry_run:
                        # Enviar mensaje de recuperación
                        await self.send_cart_recovery(cart["phone_number"], cart)
                        results["messages_sent"] += 1
                    else:
                        logger.info(f"[DRY RUN] Would send cart recovery to {cart['phone_number']}")
                        results["messages_sent"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing cart {cart.get('id')}: {str(e)}")
                    results["errors"] += 1
            
            logger.info(f"Cart recovery batch completed: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Error in cart recovery batch: {str(e)}")
            raise
    
    async def _already_sent_recently(self, phone_number: str, 
                                   template_type: TemplateType,
                                   hours: int = 48) -> bool:
        """
        Verifica si ya se envió una plantilla recientemente
        
        Args:
            phone_number: Número de teléfono
            template_type: Tipo de plantilla
            hours: Horas a considerar como "reciente"
            
        Returns:
            True si ya se envió recientemente
        """
        # Aquí deberías consultar tu base de datos
        # Por ahora retornamos False
        return False
    
    async def register_template(self, template_name: str, 
                              template_content: str,
                              language: str = "es") -> Dict[str, Any]:
        """
        Registra una nueva plantilla en 360Dialog
        
        Args:
            template_name: Nombre de la plantilla
            template_content: Contenido de la plantilla
            language: Código de idioma
            
        Returns:
            Respuesta de la API
        """
        # Esta función sería para registrar nuevas plantillas
        # El proceso real requiere aprobación de WhatsApp
        logger.info(f"Template registration requested: {template_name}")
        return {"status": "pending_approval"}


# Instancia singleton del gestor de plantillas
template_manager = WhatsAppTemplateManager()