"""
Acortador de URLs para WhatsApp
"""

import hashlib
import re
from typing import Dict, Optional

# Cache simple para URLs acortadas
url_cache: Dict[str, str] = {}


def shorten_url(url: str, base_domain: str = None) -> str:
    """
    Acorta una URL para hacerla más amigable en WhatsApp
    
    Args:
        url: URL completa del producto
        base_domain: Dominio base para extraer (opcional)
        
    Returns:
        URL acortada o la misma URL si no se puede acortar
    """
    if not url:
        return url
    
    # Si ya está en cache, devolverla
    if url in url_cache:
        return url_cache[url]
    
    try:
        # Extraer el slug del producto de la URL
        # Ejemplo: https://elcorteelectrico.com/producto/ventilador-techo-htb-3000/
        match = re.search(r'/producto/([^/]+)/?', url)
        if match:
            slug = match.group(1)
            # Crear una URL más corta
            if base_domain:
                short_url = f"{base_domain}/p/{slug}"
            else:
                # Extraer dominio de la URL original
                domain_match = re.match(r'(https?://[^/]+)', url)
                if domain_match:
                    domain = domain_match.group(1)
                    short_url = f"{domain}/p/{slug}"
                else:
                    short_url = url
            
            url_cache[url] = short_url
            return short_url
        else:
            return url
    except:
        return url


def create_product_id(url: str) -> str:
    """
    Crea un ID corto para el producto basado en la URL
    
    Args:
        url: URL del producto
        
    Returns:
        ID corto de 6 caracteres
    """
    # Crear hash de la URL
    hash_object = hashlib.md5(url.encode())
    hex_dig = hash_object.hexdigest()
    
    # Tomar los primeros 6 caracteres
    return hex_dig[:6].upper()


def format_whatsapp_link(url: str, product_name: str = None) -> str:
    """
    Formatea un enlace para WhatsApp de la mejor manera posible
    
    Args:
        url: URL completa
        product_name: Nombre del producto (opcional)
        
    Returns:
        Enlace formateado
    """
    if not url:
        return ""
    
    # Intentar acortar la URL
    short_url = shorten_url(url)
    
    # Si la URL es muy larga, usar un ID
    if len(short_url) > 50:
        product_id = create_product_id(url)
        return f"🔗 Ver producto [#{product_id}]"
    else:
        return f"🔗 {short_url}"