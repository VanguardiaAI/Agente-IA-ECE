"""
Formateador de mensajes interactivos para WhatsApp Business API
"""

from typing import List, Dict, Any, Optional


def create_product_list_message(products: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """
    Crea un mensaje interactivo de lista para WhatsApp
    
    Args:
        products: Lista de productos
        query: Búsqueda del usuario
        
    Returns:
        Estructura de mensaje interactivo para 360Dialog
    """
    if not products:
        return None
    
    # WhatsApp permite máximo 10 items en una lista
    products = products[:10]
    
    # Crear las filas de la lista
    rows = []
    for i, product in enumerate(products, 1):
        metadata = product.get('metadata', {})
        title = product.get('title', 'Producto')[:24]  # Límite de 24 caracteres
        price = float(metadata.get('price', 0))
        sale_price = float(metadata.get('sale_price', 0))
        sku = metadata.get('sku', '')
        
        # Precio para la descripción
        if sale_price and sale_price > 0 and sale_price < price:
            price_text = f"OFERTA: {sale_price:.2f}€"
        else:
            price_text = f"{price:.2f}€"
        
        # Descripción (máximo 72 caracteres)
        description = f"{price_text}"
        if sku:
            description += f" • Ref: {sku}"
        
        rows.append({
            "id": f"product_{i}",
            "title": title,
            "description": description[:72]
        })
    
    # Crear el mensaje interactivo
    interactive_message = {
        "type": "list",
        "header": {
            "type": "text",
            "text": "🛍️ Productos encontrados"
        },
        "body": {
            "text": f"He encontrado {len(products)} productos que coinciden con '{query}'. Selecciona uno para ver más detalles:"
        },
        "footer": {
            "text": "Powered by Eva AI"
        },
        "action": {
            "button": "Ver productos",
            "sections": [
                {
                    "title": "Productos disponibles",
                    "rows": rows
                }
            ]
        }
    }
    
    return interactive_message


def create_product_buttons_message(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un mensaje con botones para un producto específico
    
    Args:
        product: Datos del producto
        
    Returns:
        Estructura de mensaje con botones
    """
    metadata = product.get('metadata', {})
    title = product.get('title', 'Producto')
    price = float(metadata.get('price', 0))
    sale_price = float(metadata.get('sale_price', 0))
    permalink = metadata.get('permalink', '')
    stock_status = metadata.get('stock_status', 'unknown')
    
    # Construir el cuerpo del mensaje
    body_text = f"*{title}*\n\n"
    
    if sale_price and sale_price > 0 and sale_price < price:
        discount = int(((price - sale_price) / price) * 100)
        body_text += f"💰 Precio: ~{price:.2f}€~\n"
        body_text += f"🏷️ OFERTA: *{sale_price:.2f}€* (-{discount}%)\n"
    else:
        body_text += f"💰 Precio: *{price:.2f}€*\n"
    
    if stock_status == 'instock':
        body_text += "✅ Disponible para envío inmediato"
    else:
        body_text += "⏳ Temporalmente agotado"
    
    # Crear mensaje con botones
    button_message = {
        "type": "button",
        "body": {
            "text": body_text
        },
        "action": {
            "buttons": [
                {
                    "type": "url",
                    "title": "Ver producto",
                    "url": permalink
                },
                {
                    "type": "reply",
                    "title": "Más información",
                    "id": f"info_{metadata.get('sku', 'product')}"
                }
            ]
        }
    }
    
    return button_message


def should_use_interactive_message(products_count: int) -> bool:
    """
    Determina si usar mensaje interactivo o texto plano
    
    Args:
        products_count: Número de productos
        
    Returns:
        True si se debe usar mensaje interactivo
    """
    # Usar mensajes interactivos cuando hay entre 2 y 10 productos
    # Para 1 producto, mejor usar botones
    # Para más de 10, usar texto porque es el límite de WhatsApp
    return 2 <= products_count <= 10