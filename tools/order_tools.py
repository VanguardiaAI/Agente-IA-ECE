"""
Herramientas MCP para gestión de pedidos de WooCommerce
"""

from typing import List, Dict, Any
from services.woocommerce import WooCommerceService

def register_order_tools(mcp):
    """Registrar herramientas relacionadas con pedidos"""
    
    @mcp.tool()
    async def get_order_status(order_id: int) -> str:
        """Consultar el estado de un pedido específico"""
        try:
            wc_service = WooCommerceService()
            order = await wc_service.get_order(order_id)
            
            if not order:
                return f"❌ No se encontró el pedido #{order_id}"
            
            return wc_service.format_order(order)
            
        except Exception as e:
            return f"❌ Error al consultar pedido: {str(e)}"
    
    @mcp.tool()
    async def get_order_with_validation(order_id: int, customer_email: str) -> str:
        """
        Consultar un pedido validando la identidad del cliente.
        Requiere el número de pedido y el email del cliente para verificación.
        """
        try:
            wc_service = WooCommerceService()
            order = await wc_service.get_order(order_id)
            
            if not order:
                return f"❌ No se encontró el pedido #{order_id}"
            
            # Validar email del cliente
            billing_email = order.get('billing', {}).get('email', '').lower()
            if billing_email != customer_email.lower():
                # Por seguridad, no revelamos si el pedido existe pero no coincide
                return f"❌ No se encontró el pedido #{order_id} asociado al email proporcionado"
            
            # Si la validación es exitosa, devolver información completa
            return await create_order_summary(order_id)
            
        except Exception as e:
            return f"❌ Error al consultar pedido: {str(e)}"
    
    @mcp.tool()
    async def track_order(order_id: int) -> str:
        """Rastrear un pedido y obtener información detallada"""
        try:
            wc_service = WooCommerceService()
            order = await wc_service.get_order(order_id)
            
            if not order:
                return f"❌ No se encontró el pedido #{order_id}"
            
            # Información básica
            result = wc_service.format_order(order)
            
            # Información adicional de envío
            shipping = order.get('shipping', {})
            if shipping:
                result += f"\n📍 **Dirección de envío:**\n"
                result += f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}\n"
                result += f"{shipping.get('address_1', '')}\n"
                if shipping.get('address_2'):
                    result += f"{shipping.get('address_2')}\n"
                result += f"{shipping.get('city', '')}, {shipping.get('state', '')}\n"
                result += f"{shipping.get('postcode', '')} {shipping.get('country', '')}\n"
            
            # Productos del pedido
            line_items = order.get('line_items', [])
            if line_items:
                result += f"\n🛍️ **Productos ({len(line_items)}):**\n"
                for item in line_items:
                    name = item.get('name', 'Producto')
                    quantity = item.get('quantity', 1)
                    total = item.get('total', '0')
                    result += f"• {name} x{quantity} - ${total}\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error al rastrear pedido: {str(e)}"
    
    @mcp.tool()
    async def get_recent_orders(limit: int = 10) -> str:
        """Obtener los pedidos más recientes"""
        try:
            wc_service = WooCommerceService()
            orders = await wc_service.get_orders(per_page=limit, orderby='date', order='desc')
            
            if not orders:
                return "❌ No se encontraron pedidos recientes"
            
            return wc_service.format_order_list(orders, "Pedidos Recientes")
            
        except Exception as e:
            return f"❌ Error al obtener pedidos recientes: {str(e)}"
    
    @mcp.tool()
    async def get_orders_by_status(status: str, limit: int = 10) -> str:
        """Obtener pedidos filtrados por estado"""
        try:
            # Validar estados válidos
            valid_statuses = ['pending', 'processing', 'on-hold', 'completed', 'cancelled', 'refunded', 'failed']
            if status not in valid_statuses:
                return f"❌ Estado inválido. Estados válidos: {', '.join(valid_statuses)}"
            
            wc_service = WooCommerceService()
            orders = await wc_service.get_orders_by_status(status, per_page=limit)
            
            if not orders:
                return f"❌ No se encontraron pedidos con estado: {status}"
            
            # Traducir estado para el título
            status_names = {
                'pending': 'Pendientes',
                'processing': 'En Proceso',
                'on-hold': 'En Espera',
                'completed': 'Completados',
                'cancelled': 'Cancelados',
                'refunded': 'Reembolsados',
                'failed': 'Fallidos'
            }
            
            title = f"Pedidos {status_names.get(status, status.title())}"
            return wc_service.format_order_list(orders, title)
            
        except Exception as e:
            return f"❌ Error al obtener pedidos por estado: {str(e)}"
    
    @mcp.tool()
    async def search_orders_by_customer(customer_email: str) -> str:
        """Buscar pedidos de un cliente específico por email"""
        try:
            wc_service = WooCommerceService()
            orders = await wc_service.search_orders_by_customer(customer_email)
            
            if not orders:
                return f"❌ No se encontraron pedidos para: {customer_email}"
            
            # Filtrar solo información básica por privacidad
            safe_orders = []
            for order in orders:
                safe_orders.append({
                    'id': order.get('id'),
                    'date_created': order.get('date_created'),
                    'status': order.get('status'),
                    'total': order.get('total')
                })
            
            # Formatear lista segura
            result = f"📦 **Pedidos encontrados para {customer_email}:**\n\n"
            for order in safe_orders:
                status_map = {
                    'pending': '⏳ Pendiente',
                    'processing': '🔄 Procesando',
                    'completed': '✅ Completado',
                    'cancelled': '❌ Cancelado'
                }
                status = status_map.get(order['status'], order['status'])
                date = order['date_created'][:10] if order['date_created'] else 'N/A'
                
                result += f"• Pedido #{order['id']} - {date} - {status} - ${order['total']}\n"
            
            result += f"\n💡 Para ver detalles de un pedido específico, proporciona el número de pedido y tu email."
            return result
            
        except Exception as e:
            return f"❌ Error al buscar pedidos del cliente: {str(e)}"
    
    @mcp.tool()
    async def create_order_summary(order_id: int) -> str:
        """Crear un resumen completo de un pedido"""
        try:
            wc_service = WooCommerceService()
            order = await wc_service.get_order(order_id)
            
            if not order:
                return f"❌ No se encontró el pedido #{order_id}"
            
            # Información básica
            order_id = order.get('id', 'N/A')
            status = order.get('status', 'unknown')
            total = order.get('total', '0')
            subtotal = order.get('subtotal', '0')
            tax_total = order.get('tax_total', '0')
            shipping_total = order.get('shipping_total', '0')
            date_created = order.get('date_created', 'N/A')
            
            # Cliente
            billing = order.get('billing', {})
            customer_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}"
            customer_email = billing.get('email', 'N/A')
            customer_phone = billing.get('phone', 'N/A')
            
            # Estado traducido
            status_map = {
                'pending': '⏳ Pendiente',
                'processing': '🔄 Procesando',
                'on-hold': '⏸️ En espera',
                'completed': '✅ Completado',
                'cancelled': '❌ Cancelado',
                'refunded': '💸 Reembolsado',
                'failed': '❌ Fallido'
            }
            status_display = status_map.get(status, f"❓ {status}")
            
            result = f"""
📦 **RESUMEN DEL PEDIDO #{order_id}**

📊 **Estado:** {status_display}
📅 **Fecha:** {date_created[:10] if date_created != 'N/A' else 'N/A'}

👤 **Cliente:**
• Nombre: {customer_name.strip() or 'N/A'}
• Email: {customer_email}
• Teléfono: {customer_phone}

💰 **Totales:**
• Subtotal: ${subtotal}
• Envío: ${shipping_total}
• Impuestos: ${tax_total}
• **Total: ${total}**
"""
            
            # Productos
            line_items = order.get('line_items', [])
            if line_items:
                result += f"\n🛍️ **Productos ({len(line_items)}):**\n"
                for item in line_items:
                    name = item.get('name', 'Producto')
                    quantity = item.get('quantity', 1)
                    price = item.get('price', '0')
                    total_item = item.get('total', '0')
                    result += f"• {name}\n"
                    result += f"  Cantidad: {quantity} | Precio: ${price} | Total: ${total_item}\n"
            
            return result.strip()
            
        except Exception as e:
            return f"❌ Error al crear resumen del pedido: {str(e)}" 