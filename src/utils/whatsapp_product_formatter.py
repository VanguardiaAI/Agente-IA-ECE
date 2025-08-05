"""
Formateador especializado de productos para WhatsApp
"""

from typing import List, Dict, Any, Optional
import re


def format_products_for_whatsapp(products: List[Dict[str, Any]], query: str) -> str:
    """
    Formatea productos para una visualización óptima en WhatsApp
    
    Args:
        products: Lista de productos encontrados
        query: Consulta original del usuario
        
    Returns:
        Mensaje formateado para WhatsApp
    """
    if not products:
        return "🔍 No encontré productos que coincidan con tu búsqueda.\n\n¿Podrías darme más detalles o buscar con otras palabras?"
    
    # Encabezado más conversacional según cantidad de productos
    num_products = len(products)
    
    if num_products == 1:
        header = "✨ Encontré exactamente lo que creo que buscas:\n"
    elif num_products <= 3:
        header = f"🛍️ Mira, tengo {num_products} opciones que podrían interesarte:\n"
    else:
        header = f"📦 He encontrado varios productos. Te muestro los {min(num_products, 5)} más relevantes:\n"
    
    # Construir respuesta
    response = header
    response += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Formatear cada producto
    for i, product in enumerate(products[:5], 1):
        response += format_single_product(product, i)
        
        # Separador entre productos (excepto el último)
        if i < min(len(products), 5):
            response += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
    
    # Pie del mensaje más natural
    response += "\n━━━━━━━━━━━━━━━━━━━━\n"
    
    if num_products > 5:
        response += f"\n📋 Tengo {num_products - 5} productos más que también podrían interesarte.\n"
    
    # Mensaje conversacional según el contexto
    if num_products == 1:
        response += "\n¿Este es el producto que buscabas? "
        response += "Puedo darte más información sobre sus características, "
        response += "verificar el stock en tu zona o buscar alternativas similares. "
    elif num_products <= 3:
        response += "\n¿Alguno de estos productos es lo que necesitas? "
        response += "Puedo contarte más sobre cualquiera de ellos, "
        response += "comparar sus características o seguir buscando si prefieres otras opciones. "
    else:
        response += "\n¿Te interesa alguno en particular? "
        response += "Puedo darte información más detallada, "
        response += "ayudarte a elegir el más adecuado para ti o buscar algo diferente. "
    
    response += "\n\n💬 Solo dime qué necesitas saber."
    
    return response


def format_single_product(product: Dict[str, Any], index: int) -> str:
    """
    Formatea un producto individual para WhatsApp
    
    Args:
        product: Diccionario con datos del producto
        index: Número del producto en la lista
        
    Returns:
        Producto formateado
    """
    # Extraer datos con valores por defecto
    title = product.get('title', product.get('name', 'Producto'))
    metadata = product.get('metadata', {})
    price = float(metadata.get('price', 0))
    regular_price = float(metadata.get('regular_price', price))
    sale_price = float(metadata.get('sale_price', 0))
    stock_status = metadata.get('stock_status', 'unknown')
    permalink = metadata.get('permalink', '')
    sku = metadata.get('sku', '')
    
    # Limpiar título si es muy largo
    if len(title) > 60:
        title = title[:57] + "..."
    
    # Construir mensaje del producto de forma más limpia
    msg = f"▫️ *{title}*\n"
    
    # Precio con formato mejorado
    if sale_price and sale_price > 0 and sale_price < regular_price:
        discount = int(((regular_price - sale_price) / regular_price) * 100)
        msg += f"   💰 ~{regular_price:.2f}€~ → *{sale_price:.2f}€*\n"
        msg += f"   🏷️ ¡{discount}% de descuento!\n"
    else:
        msg += f"   💰 *{price:.2f}€* (IVA incluido)\n"
    
    # Estado del stock simplificado
    if stock_status == 'instock':
        msg += "   ✅ Disponible\n"
    elif stock_status == 'outofstock':
        msg += "   ⏳ Agotado\n"
    
    # Código de producto (solo si existe)
    if sku:
        msg += f"   📌 Ref: {sku}\n"
    
    # Link completo para que funcione correctamente
    if permalink:
        msg += f"   🔗 {permalink}\n"
    
    return msg


def format_product_comparison(products: List[Dict[str, Any]]) -> str:
    """
    Formatea una comparación de productos para WhatsApp
    
    Args:
        products: Lista de productos a comparar
        
    Returns:
        Comparación formateada
    """
    if len(products) < 2:
        return "Necesito al menos 2 productos para hacer una comparación."
    
    response = "📊 *COMPARACIÓN DE PRODUCTOS*\n"
    response += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Comparar hasta 3 productos
    for i, product in enumerate(products[:3], 1):
        metadata = product.get('metadata', {})
        title = product.get('title', 'Producto')[:40]
        price = float(metadata.get('price', 0))
        
        response += f"*{i}. {title}*\n"
        response += f"   💰 {price:.2f}€\n"
        
        # Características destacadas (si las hay)
        features = metadata.get('short_description', '').split(',')[:3]
        if features and features[0]:
            response += "   ✓ " + "\n   ✓ ".join(f.strip() for f in features) + "\n"
        
        response += "\n"
    
    response += "¿Te gustaría una comparación más detallada?"
    
    return response


def format_cart_summary(items: List[Dict[str, Any]], total: float) -> str:
    """
    Formatea un resumen del carrito para WhatsApp
    
    Args:
        items: Lista de items en el carrito
        total: Total del carrito
        
    Returns:
        Resumen formateado
    """
    response = "🛒 *RESUMEN DE TU CARRITO*\n"
    response += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, item in enumerate(items, 1):
        name = item.get('name', 'Producto')[:40]
        quantity = item.get('quantity', 1)
        price = float(item.get('price', 0))
        subtotal = quantity * price
        
        response += f"{i}. {name}\n"
        response += f"   {quantity} x {price:.2f}€ = *{subtotal:.2f}€*\n\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━\n"
    response += f"💳 *TOTAL: {total:.2f}€*\n"
    response += "_IVA incluido_\n\n"
    
    response += "✅ *¿Listo para finalizar tu compra?*\n"
    response += "Puedo ayudarte con el proceso de pago."
    
    return response