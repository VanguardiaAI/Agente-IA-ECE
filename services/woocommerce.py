"""
Cliente API de WooCommerce para el servidor MCP de El Corte Eléctrico
"""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class WooCommerceService:
    """Servicio para interactuar con la API de WooCommerce"""
    
    def __init__(self):
        self.base_url = settings.woocommerce_api_url
        self.auth = (settings.WOOCOMMERCE_CONSUMER_KEY, settings.WOOCOMMERCE_CONSUMER_SECRET)
        self.timeout = 30.0
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Realizar petición HTTP a WooCommerce"""
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    auth=self.auth,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error HTTP: {e}")
                return None
            except Exception as e:
                print(f"Error: {e}")
                return None
    
    # Métodos de productos
    async def get_products(self, **params) -> Optional[List[Dict]]:
        """Obtener lista de productos"""
        return await self._make_request("GET", "products", params=params)
    
    async def get_product(self, product_id: int) -> Optional[Dict]:
        """Obtener producto específico"""
        return await self._make_request("GET", f"products/{product_id}")
    
    async def search_products(self, search: str, per_page: int = 10) -> Optional[List[Dict]]:
        """Buscar productos por término"""
        params = {"search": search, "per_page": per_page}
        return await self._make_request("GET", "products", params=params)
    
    async def get_product_categories(self, **params) -> Optional[List[Dict]]:
        """Obtener categorías de productos"""
        return await self._make_request("GET", "products/categories", params=params)
    
    # Métodos de pedidos
    async def get_orders(self, **params) -> Optional[List[Dict]]:
        """Obtener lista de pedidos"""
        return await self._make_request("GET", "orders", params=params)
    
    async def get_order(self, order_id: int) -> Optional[Dict]:
        """Obtener pedido específico"""
        return await self._make_request("GET", f"orders/{order_id}")
    
    async def get_orders_by_status(self, status: str, per_page: int = 10) -> Optional[List[Dict]]:
        """Obtener pedidos por estado"""
        params = {"status": status, "per_page": per_page}
        return await self._make_request("GET", "orders", params=params)
    
    async def search_orders_by_customer(self, customer_email: str) -> Optional[List[Dict]]:
        """Buscar pedidos por email del cliente (registrado o invitado)"""
        try:
            matching_orders = []
            
            # Primero intentar buscar cliente registrado
            customers = await self._make_request("GET", "customers", params={"email": customer_email})
            
            if customers and len(customers) > 0:
                # Si hay cliente registrado, buscar sus pedidos
                customer_id = customers[0].get('id')
                customer_orders = await self._make_request("GET", "orders", params={"customer": customer_id, "per_page": 100})
                if customer_orders:
                    matching_orders.extend(customer_orders)
            
            # También buscar pedidos de invitados (guest checkout)
            # WooCommerce no permite buscar directamente por billing email, 
            # así que obtenemos pedidos recientes y filtramos
            # Intentar obtener más pedidos si es necesario
            page = 1
            max_pages = 3  # Buscar hasta 300 pedidos
            
            while page <= max_pages:
                recent_orders = await self._make_request(
                    "GET", 
                    "orders", 
                    params={
                        "per_page": 100, 
                        "page": page,
                        "orderby": "date", 
                        "order": "desc"
                    }
                )
                
                if recent_orders:
                    # Filtrar pedidos por email de facturación
                    found_in_page = False
                    for order in recent_orders:
                        billing = order.get('billing', {})
                        if billing.get('email', '').lower() == customer_email.lower():
                            # Evitar duplicados si ya se agregó desde cliente registrado
                            if not any(o.get('id') == order.get('id') for o in matching_orders):
                                matching_orders.append(order)
                                found_in_page = True
                    
                    # Si encontramos al menos uno, podemos parar
                    if found_in_page and len(matching_orders) >= 5:
                        break
                    
                    # Si no hay más pedidos, salir
                    if len(recent_orders) < 100:
                        break
                else:
                    break
                
                page += 1
            
            # Ordenar por fecha más reciente
            matching_orders.sort(key=lambda x: x.get('date_created', ''), reverse=True)
            
            return matching_orders
            
        except Exception as e:
            self.logger.error(f"Error buscando pedidos del cliente: {e}")
            return []
    
    # Métodos de clientes
    async def get_customers(self, **params) -> Optional[List[Dict]]:
        """Obtener lista de clientes"""
        return await self._make_request("GET", "customers", params=params)
    
    async def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Obtener cliente específico"""
        return await self._make_request("GET", f"customers/{customer_id}")
    
    # Métodos de formateo
    def format_product(self, product: Dict) -> str:
        """Formatear información de producto para mostrar (optimizado para WhatsApp)"""
        if not product:
            return "❌ Producto no encontrado"
        
        name = product.get('name', 'Sin nombre')
        price = product.get('price', '0')
        regular_price = product.get('regular_price', '0')
        sale_price = product.get('sale_price', '')
        stock_status = product.get('stock_status', 'outofstock')
        stock_quantity = product.get('stock_quantity', 0)
        description = product.get('short_description', '').strip()
        permalink = product.get('permalink', '')
        sku = product.get('sku', '')
        categories = product.get('categories', [])
        
        # Aplicar IVA del 21% a los precios
        VAT_RATE = 1.21
        price_with_vat = round(float(price) * VAT_RATE, 2) if price else 0
        regular_price_with_vat = round(float(regular_price) * VAT_RATE, 2) if regular_price else 0
        sale_price_with_vat = round(float(sale_price) * VAT_RATE, 2) if sale_price else 0
        
        result = f"📦 **{name}**\n\n"
        
        # Precio con formato de oferta
        if sale_price and sale_price_with_vat > 0 and sale_price_with_vat < regular_price_with_vat:
            result += f"💰 ~{regular_price_with_vat}€~ **{sale_price_with_vat}€** ¡OFERTA!\n"
        else:
            result += f"💰 **{price_with_vat}€** (IVA incluido)\n"
        
        # Estado del stock
        if stock_status == 'instock':
            if stock_quantity > 0:
                result += f"✅ Disponible ({stock_quantity} unidades)\n"
            else:
                result += "✅ Disponible\n"
        else:
            result += "❌ Sin stock\n"
        
        # Categorías
        if categories:
            cat_names = [cat.get('name', '') for cat in categories[:2]]  # Máximo 2
            if cat_names:
                result += f"🏷️ {', '.join(cat_names)}\n"
        
        # SKU
        if sku:
            result += f"📋 Ref: {sku}\n"
        
        # Descripción (limpia y breve)
        if description:
            # Limpiar HTML básico
            clean_desc = description.replace('<p>', '').replace('</p>', '').replace('<br>', '\n')
            clean_desc = clean_desc.strip()[:150]  # Máximo 150 caracteres
            if clean_desc:
                result += f"\n📝 {clean_desc}...\n"
        
        # Link del producto
        if permalink:
            result += f"\n🔗 Ver producto:\n{permalink}"
        
        return result.strip()
    
    def format_order(self, order: Dict) -> str:
        """Formatear información de pedido para mostrar"""
        if not order:
            return "❌ Pedido no encontrado"
        
        order_id = order.get('id', 'N/A')
        status = order.get('status', 'unknown')
        total = order.get('total', '0')
        date_created = order.get('date_created', 'N/A')
        customer_email = order.get('billing', {}).get('email', 'N/A')
        
        # Traducir estados
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
📦 **Pedido #{order_id}**
📊 Estado: {status_display}
💰 Total: ${total}
📅 Fecha: {date_created[:10] if date_created != 'N/A' else 'N/A'}
👤 Cliente: {customer_email}
"""
        
        return result.strip()
    
    def format_product_list(self, products: List[Dict], title: str = "Productos") -> str:
        """Formatear lista de productos"""
        if not products:
            return f"❌ No se encontraron {title.lower()}"
        
        result = f"🛍️ **{title}** ({len(products)} encontrados)\n\n"
        
        for product in products[:10]:  # Limitar a 10 productos
            name = product.get('name', 'Sin nombre')
            price = product.get('price', '0')
            stock_status = product.get('stock_status', 'outofstock')
            
            stock_icon = "✅" if stock_status == 'instock' else "❌"
            result += f"{stock_icon} **{name}** - ${price}\n"
        
        if len(products) > 10:
            result += f"\n... y {len(products) - 10} productos más"
        
        return result
    
    def format_order_list(self, orders: List[Dict], title: str = "Pedidos") -> str:
        """Formatear lista de pedidos"""
        if not orders:
            return f"❌ No se encontraron {title.lower()}"
        
        result = f"📦 **{title}** ({len(orders)} encontrados)\n\n"
        
        status_map = {
            'pending': '⏳',
            'processing': '🔄',
            'completed': '✅',
            'cancelled': '❌',
            'on-hold': '⏸️'
        }
        
        for order in orders[:10]:  # Limitar a 10 pedidos
            order_id = order.get('id', 'N/A')
            status = order.get('status', 'unknown')
            total = order.get('total', '0')
            date = order.get('date_created', 'N/A')[:10] if order.get('date_created') else 'N/A'
            
            status_icon = status_map.get(status, '❓')
            result += f"{status_icon} **Pedido #{order_id}** - ${total} ({date})\n"
        
        if len(orders) > 10:
            result += f"\n... y {len(orders) - 10} pedidos más"
        
        return result

# Instancia global del servicio
wc_service = WooCommerceService()

# Funciones de utilidad para usar en herramientas MCP
async def search_products(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Buscar productos - función de utilidad"""
    return await wc_service.search_products(query, limit)

async def get_product_details(product_id: int) -> Dict[str, Any]:
    """Obtener detalles de producto - función de utilidad"""
    return await wc_service.get_product(product_id)

async def get_order_details(order_id: int) -> Dict[str, Any]:
    """Obtener detalles de pedido - función de utilidad"""
    return await wc_service.get_order(order_id)

async def get_categories() -> List[Dict[str, Any]]:
    """Obtener categorías - función de utilidad"""
    return await wc_service.get_product_categories() 