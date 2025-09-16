"""
Plantillas profesionales de WhatsApp para El Corte Eléctrico
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ProfessionalTemplates:
    """
    Gestiona las plantillas profesionales con header, body, footer y buttons
    """
    
    def build_cart_recovery_pro_components(self, cart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye los componentes para la plantilla profesional de recuperación
        
        Args:
            cart_data: Datos del carrito con keys:
                - customer_name: Nombre del cliente
                - items: Lista de productos
                - total: Total del carrito
                - cart_url: URL de recuperación
                - header_image_url: URL de la imagen del header (opcional)
                
        Returns:
            Lista de componentes para la plantilla
        """
        components = []
        
        # 1. HEADER - Imagen
        header_image = cart_data.get('header_image_url', 'https://elcorteelectrico.com/wp-content/uploads/banner-descuento.jpg')
        components.append({
            "type": "header",
            "parameters": [
                {
                    "type": "image",
                    "image": {
                        "link": header_image
                    }
                }
            ]
        })
        
        # 2. BODY - Preparar las 3 variables
        body_params = []
        
        # {{1}} - Nombre del cliente
        customer_name = cart_data.get('customer_name', 'Cliente')
        body_params.append({
            "type": "text",
            "text": customer_name
        })
        
        # {{2}} - Lista de productos formateada
        items = cart_data.get('items', [])
        product_list = []
        
        for item in items:
            name = item.get('name', 'Producto')
            quantity = item.get('quantity', 1)
            
            if quantity > 1:
                formatted_item = f"{name} x{quantity}"
            else:
                formatted_item = name
                
            product_list.append(formatted_item)
        
        # Unir con punto y coma (sin saltos de línea)
        products_text = "; ".join(product_list[:3])  # Limitar a 3 productos
        if len(product_list) > 3:
            products_text += f" y {len(product_list) - 3} más"
            
        body_params.append({
            "type": "text",
            "text": products_text
        })
        
        # {{3}} - Total formateado
        cart_total = cart_data.get('total', 0)
        total_formatted = f"{cart_total:.2f}".replace('.', ',') + " €"
        body_params.append({
            "type": "text",
            "text": total_formatted
        })
        
        # Agregar body con los 3 parámetros
        components.append({
            "type": "body",
            "parameters": body_params
        })
        
        # 3. BUTTON - URL dinámica
        # Extraer solo la parte después del dominio para el parámetro
        cart_url = cart_data.get('cart_url', '')
        if cart_url:
            # Si la URL es completa, extraer solo los parámetros
            if '?' in cart_url:
                url_suffix = '?' + cart_url.split('?', 1)[1]
            else:
                url_suffix = f"?recover={cart_data.get('cart_id', 'default')}"
                
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {
                        "type": "text",
                        "text": url_suffix
                    }
                ]
            })
        
        return components
    
    def build_order_confirmation_pro_components(self, order_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye componentes para confirmación de pedido profesional
        """
        components = []
        
        # Header con imagen
        components.append({
            "type": "header",
            "parameters": [
                {
                    "type": "image",
                    "image": {
                        "link": "https://elcorteelectrico.com/wp-content/uploads/pedido-confirmado.jpg"
                    }
                }
            ]
        })
        
        # Body con datos del pedido
        body_params = [
            {
                "type": "text",
                "text": order_data.get('customer_name', 'Cliente')
            },
            {
                "type": "text",
                "text": order_data.get('order_number', '0000')
            },
            {
                "type": "text",
                "text": f"{order_data.get('total', 0):.2f}".replace('.', ',') + " €"
            }
        ]
        
        components.append({
            "type": "body",
            "parameters": body_params
        })
        
        # Botón para ver pedido
        if order_data.get('order_url'):
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                    {
                        "type": "text",
                        "text": f"?order={order_data.get('order_id', '')}"
                    }
                ]
            })
        
        return components
    
    def build_welcome_pro_components(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Construye componentes para mensaje de bienvenida profesional
        """
        components = []
        
        # Header con imagen de bienvenida
        components.append({
            "type": "header",
            "parameters": [
                {
                    "type": "image",
                    "image": {
                        "link": "https://elcorteelectrico.com/wp-content/uploads/bienvenido.jpg"
                    }
                }
            ]
        })
        
        # Body con nombre
        components.append({
            "type": "body",
            "parameters": [
                {
                    "type": "text",
                    "text": user_data.get('name', 'Cliente')
                }
            ]
        })
        
        # Botón para ver catálogo
        components.append({
            "type": "button",
            "sub_type": "url",
            "index": "0",
            "parameters": [
                {
                    "type": "text",
                    "text": "/catalogo"
                }
            ]
        })
        
        return components


# Instancia global
professional_templates = ProfessionalTemplates()