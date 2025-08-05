"""
WordPress formatting utilities for Eva chatbot responses
"""
import json
from typing import List, Dict, Any, Optional
from html import escape


def format_product_card(product: Dict[str, Any]) -> str:
    """
    Format a single product as an HTML card for WordPress display.
    
    Args:
        product: Product dictionary with fields like name, price, images, permalink
        
    Returns:
        HTML string for the product card
    """
    name = escape(product.get('name', 'Producto'))
    price = product.get('price', '0')
    permalink = product.get('permalink', '#')
    
    # Extract first image if available
    images = product.get('images', [])
    image_url = ''
    image_alt = name
    
    if images and len(images) > 0:
        # Handle both string URLs and dict format
        if isinstance(images[0], str):
            image_url = images[0]
        elif isinstance(images[0], dict):
            image_url = images[0].get('src', '')
            image_alt = images[0].get('alt', name)
    
    # Extract price information
    regular_price = product.get('regular_price', '0')
    sale_price = product.get('sale_price', '0')
    
    # Determine if product is on sale
    is_on_sale = False
    if sale_price and regular_price:
        try:
            if float(sale_price) > 0 and float(sale_price) < float(regular_price):
                is_on_sale = True
                display_price = sale_price
            else:
                display_price = price
        except:
            display_price = price
    else:
        display_price = price
    
    # Build compact HTML card with white background
    html = f'''<div class="eva-product-card" style="border: 1px solid #e0e0e0; border-radius: 6px; padding: 10px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); display: flex; gap: 10px;">
    '''
    
    # Add image if available (smaller, on the left)
    if image_url:
        html += f'''<div class="eva-product-image" style="width: 80px; height: 80px; flex-shrink: 0; overflow: hidden; border-radius: 4px;">
        <img src="{escape(image_url)}" alt="{escape(image_alt)}" style="width: 100%; height: 100%; object-fit: cover;" />
    </div>'''
    
    # Product details container
    html += '''<div style="flex: 1; min-width: 0;">'''
    
    # Product name
    html += f'''<h3 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #000000; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{name}</h3>'''
    
    # Price section
    html += '''<div style="margin: 0 0 6px 0;">'''
    if is_on_sale:
        html += f'''<span style="text-decoration: line-through; color: #999; font-size: 13px; margin-right: 6px;">€{regular_price}</span>'''
        html += f'''<span style="font-size: 16px; font-weight: 600; color: #d32f2f;">€{display_price}</span>'''
    else:
        html += f'''<span style="font-size: 16px; font-weight: 600; color: #000000;">€{display_price}</span>'''
    html += '''</div>'''
    
    # Compact button
    html += f'''<a href="{escape(permalink)}" class="eva-product-link" style="display: inline-block; background: #54841e; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: 500; transition: all 0.2s;">Ver producto →</a>'''
    
    html += '''</div>'''  # Close product details container
    html += '''</div>'''  # Close product card
    
    return html


def format_product_search_response(products: List[Dict[str, Any]], search_query: str) -> str:
    """
    Format a list of products for WordPress display with rich previews.
    
    Args:
        products: List of product dictionaries
        search_query: Original search query
        
    Returns:
        Formatted HTML response
    """
    if not products:
        return '''<p style="margin: 0;">Hmm, no he encontrado productos que coincidan exactamente con lo que buscas.</p>
        <p style="margin: 8px 0 0 0;">¿Podrías darme más detalles sobre lo que necesitas? Por ejemplo, ¿para qué lo vas a usar o qué características son importantes para ti?</p>'''
    
    # Limit to first 5 products for chat display
    products = products[:5]
    
    # Crear una respuesta más natural y conversacional
    if len(products) == 1:
        response = '<p style="margin: 0 0 12px 0;">He encontrado este producto que podría interesarte:</p>'
    elif len(products) <= 3:
        response = '<p style="margin: 0 0 12px 0;">Te muestro algunas opciones que podrían ser lo que buscas:</p>'
    else:
        response = '<p style="margin: 0 0 12px 0;">Aquí tienes varias opciones que coinciden con lo que necesitas:</p>'
    
    response += '<div class="eva-products-list" style="max-height: 400px; overflow-y: auto; padding-right: 4px;">'
    
    for product in products:
        response += format_product_card(product)
    
    response += '</div>'
    
    # Mensaje de cierre más natural sin estilos especiales
    if len(products) >= 3:
        response += '<p style="margin: 12px 0 0 0;">¿Te gustaría más información sobre alguno de estos productos? Puedo explicarte las diferencias entre ellos o buscar otras opciones si no es exactamente lo que necesitas.</p>'
    elif len(products) == 2:
        response += '<p style="margin: 12px 0 0 0;">¿Alguno de estos dos productos es lo que buscabas? Si necesitas comparar características o ver más opciones, solo dímelo.</p>'
    else:
        response += '<p style="margin: 12px 0 0 0;">¿Es esto lo que estabas buscando? Si necesitas algo diferente, puedo seguir buscando.</p>'
    
    return response


def format_order_info_response(order: Dict[str, Any]) -> str:
    """
    Format order information for WordPress display.
    
    Args:
        order: Order dictionary with order details
        
    Returns:
        Formatted HTML response
    """
    order_id = order.get('id', 'N/A')
    status = order.get('status', 'unknown')
    total = order.get('total', '0')
    date_created = order.get('date_created', '')
    
    # Format status in Spanish
    status_map = {
        'pending': 'Pendiente',
        'processing': 'Procesando',
        'on-hold': 'En espera',
        'completed': 'Completado',
        'cancelled': 'Cancelado',
        'refunded': 'Reembolsado',
        'failed': 'Fallido'
    }
    status_text = status_map.get(status, status.title())
    
    # Status color
    status_colors = {
        'pending': '#ff9800',
        'processing': '#2196f3',
        'completed': '#4caf50',
        'cancelled': '#f44336',
        'on-hold': '#9e9e9e'
    }
    status_color = status_colors.get(status, '#666')
    
    html = f'''<div class="eva-order-info" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; background: #f9f9f9;">
    <h3 style="margin: 0 0 12px 0; color: #333;">Pedido #{order_id}</h3>
    <div style="display: flex; flex-wrap: wrap; gap: 20px;">
        <div>
            <span style="color: #666;">Estado:</span>
            <span style="color: {status_color}; font-weight: bold; margin-left: 8px;">{status_text}</span>
        </div>
        <div>
            <span style="color: #666;">Total:</span>
            <span style="font-weight: bold; margin-left: 8px;">€{total}</span>
        </div>
        <div>
            <span style="color: #666;">Fecha:</span>
            <span style="margin-left: 8px;">{date_created[:10] if date_created else 'N/A'}</span>
        </div>
    </div>
    '''
    
    # Add line items if available
    line_items = order.get('line_items', [])
    if line_items:
        html += '''
    <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e0e0e0;">
        <h4 style="margin: 0 0 10px 0; color: #333;">Productos:</h4>
        <ul style="margin: 0; padding-left: 20px;">'''
        
        for item in line_items:
            name = escape(item.get('name', 'Producto'))
            quantity = item.get('quantity', 1)
            total = item.get('total', '0')
            html += f'\n            <li>{name} x{quantity} - €{total}</li>'
        
        html += '\n        </ul>\n    </div>'
    
    html += '\n</div>'
    
    return html


def format_text_response(text: str, preserve_breaks: bool = True) -> str:
    """
    Format plain text response for WordPress display.
    
    Args:
        text: Plain text to format
        preserve_breaks: Whether to convert line breaks to <br> tags
        
    Returns:
        HTML formatted text
    """
    # First handle any special formatting markers in the text
    import re
    
    # Convert markdown-style bold to HTML (but subtle)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<span style="font-weight: 600;">\1</span>', text)
    text = re.sub(r'\*([^*]+)\*', r'<span style="font-weight: 600;">\1</span>', text)
    
    # Convert markdown-style italic to HTML (but subtle)
    text = re.sub(r'__([^_]+)__', r'<span style="font-style: italic;">\1</span>', text)
    text = re.sub(r'_([^_]+)_', r'<span style="font-style: italic;">\1</span>', text)
    
    # Now escape any remaining HTML characters
    # But preserve the spans we just added
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('&lt;span', '<span').replace('&lt;/span>', '</span>')
    text = text.replace('>', '&gt;').replace('style="font-weight: 600;"&gt;', 'style="font-weight: 600;">').replace('style="font-style: italic;"&gt;', 'style="font-style: italic;">')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#039;')
    
    # Remove emoji markers for WordPress (keep it clean)
    text = re.sub(r'[📦📅💰✅❌📋🔗]', '', text)
    
    # Format lists properly
    lines = text.split('\n')
    formatted_lines = []
    in_list = False
    list_html = []
    
    for line in lines:
        stripped = line.strip()
        
        # Check if it's a list item (starts with -, *, or number.)
        if re.match(r'^[-*•]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
            if not in_list:
                in_list = True
                list_html = ['<ul style="margin: 0 0 12px 0; padding-left: 20px;">']
            # Remove the list marker and add as list item
            item_text = re.sub(r'^[-*•]\s+', '', stripped)
            item_text = re.sub(r'^\d+\.\s+', '', item_text)
            list_html.append(f'<li style="margin: 0 0 4px 0; line-height: 1.5;">{item_text}</li>')
        else:
            # If we were in a list, close it
            if in_list:
                list_html.append('</ul>')
                formatted_lines.append('\n'.join(list_html))
                in_list = False
                list_html = []
            
            # Add the line if it's not empty
            if stripped:
                formatted_lines.append(stripped)
    
    # Close any open list
    if in_list:
        list_html.append('</ul>')
        formatted_lines.append('\n'.join(list_html))
    
    # Convert line breaks if requested
    if preserve_breaks:
        # Join lines and split by double line breaks for paragraphs
        text = '\n'.join(formatted_lines)
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                # Skip if it's already HTML (like lists)
                if paragraph.strip().startswith('<'):
                    formatted_paragraphs.append(paragraph)
                else:
                    # Convert single line breaks within paragraphs to <br>
                    paragraph_with_breaks = paragraph.replace('\n', '<br>')
                    formatted_paragraphs.append(f'<p style="margin: 0 0 12px 0; line-height: 1.5;">{paragraph_with_breaks}</p>')
        
        # Remove last paragraph margin
        if formatted_paragraphs:
            last_paragraph = formatted_paragraphs[-1]
            if '<p style="margin: 0 0 12px 0;' in last_paragraph:
                formatted_paragraphs[-1] = last_paragraph.replace('margin: 0 0 12px 0;', 'margin: 0;')
        
        formatted = '\n'.join(formatted_paragraphs)
    else:
        # Just wrap in a single paragraph
        formatted = f'<p style="margin: 0; line-height: 1.5;">{text}</p>'
    
    return formatted


def format_link_preview(url: str, title: Optional[str] = None, description: Optional[str] = None, image: Optional[str] = None) -> str:
    """
    Format a link with preview card for WordPress.
    
    Args:
        url: The link URL
        title: Link title (optional)
        description: Link description (optional)
        image: Preview image URL (optional)
        
    Returns:
        HTML formatted link preview
    """
    if not title:
        title = url
    
    html = f'''<div class="eva-link-preview" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin: 10px 0; background: #fff;">
    '''
    
    if image:
        html += f'''<div style="width: 100%; height: 150px; overflow: hidden; border-radius: 6px; margin-bottom: 10px;">
        <img src="{escape(image)}" alt="{escape(title)}" style="width: 100%; height: 100%; object-fit: cover;" />
    </div>
    '''
    
    html += f'''<h4 style="margin: 0 0 6px 0; font-size: 16px;">
        <a href="{escape(url)}" style="color: #54841e; text-decoration: none;">{escape(title)}</a>
    </h4>'''
    
    if description:
        html += f'\n    <p style="margin: 0; color: #666; font-size: 14px;">{escape(description)}</p>'
    
    html += '\n</div>'
    
    return html


def convert_whatsapp_to_wordpress(text: str) -> str:
    """
    Convert WhatsApp formatted text to WordPress HTML format.
    
    Args:
        text: WhatsApp formatted text with emojis and basic formatting
        
    Returns:
        HTML formatted text suitable for WordPress
    """
    # Convert WhatsApp style bold (*text*) to HTML
    import re
    html = escape(text)
    
    # Convert *bold* to <strong>
    html = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', html)
    
    # Convert _italic_ to <em>
    html = re.sub(r'_([^_]+)_', r'<em>\1</em>', html)
    
    # Convert line breaks
    html = html.replace('\n', '<br>\n')
    
    # Wrap in paragraph
    html = f'<p>{html}</p>'
    
    return html