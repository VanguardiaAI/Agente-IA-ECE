#!/usr/bin/env python3
"""
Script para consultar directamente la API de WooCommerce
"""

import asyncio
import aiohttp
import base64
import json
from datetime import datetime

# Configuración de WooCommerce
WC_URL = "https://staging.elcorteelectrico.com"
WC_KEY = "ck_7d08edfcdb4c80e03cf5ade6b6abc02c8772900d"
WC_SECRET = "cs_1fe210cfd63d5786ef73ef735412ee8bc41704df"

async def check_product_direct(product_id: int):
    """Consultar producto directamente vía API REST de WooCommerce"""
    
    # Crear autenticación básica
    credentials = f"{WC_KEY}:{WC_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    url = f"{WC_URL}/wp-json/wc/v3/products/{product_id}"
    
    print(f"\n🔍 Consultando directamente la API de WooCommerce")
    print(f"   URL: {url}")
    print(f"   Product ID: {product_id}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"\n📦 Respuesta de WooCommerce API:")
                    print(f"   Nombre: {data.get('name', 'N/A')}")
                    print(f"   SKU: {data.get('sku', 'N/A')}")
                    print(f"   Status: {data.get('status', 'N/A')}")
                    print(f"   Tipo: {data.get('type', 'N/A')}")
                    
                    print(f"\n💰 Precios:")
                    print(f"   price: {data.get('price', 'N/A')}")
                    print(f"   regular_price: {data.get('regular_price', 'N/A')}")
                    print(f"   sale_price: {data.get('sale_price', 'N/A')}")
                    
                    print(f"\n📅 Fechas:")
                    print(f"   date_created: {data.get('date_created', 'N/A')}")
                    print(f"   date_modified: {data.get('date_modified', 'N/A')}")
                    print(f"   date_on_sale_from: {data.get('date_on_sale_from', 'N/A')}")
                    print(f"   date_on_sale_to: {data.get('date_on_sale_to', 'N/A')}")
                    
                    print(f"\n📊 Metadatos y variaciones:")
                    print(f"   manage_stock: {data.get('manage_stock', 'N/A')}")
                    print(f"   stock_quantity: {data.get('stock_quantity', 'N/A')}")
                    print(f"   stock_status: {data.get('stock_status', 'N/A')}")
                    
                    # Si es un producto variable, mostrar variaciones
                    if data.get('type') == 'variable':
                        print(f"\n🔄 Producto variable - verificando variaciones...")
                        variations = data.get('variations', [])
                        print(f"   Número de variaciones: {len(variations)}")
                        
                        # Obtener precios de variaciones
                        if variations:
                            var_url = f"{WC_URL}/wp-json/wc/v3/products/{product_id}/variations"
                            async with session.get(var_url, headers=headers, ssl=False) as var_response:
                                if var_response.status == 200:
                                    var_data = await var_response.json()
                                    print(f"\n   Variaciones encontradas:")
                                    for idx, var in enumerate(var_data[:3], 1):  # Mostrar máx 3
                                        print(f"\n   Variación {idx}:")
                                        print(f"      ID: {var.get('id')}")
                                        print(f"      Precio: {var.get('price')}")
                                        print(f"      Regular: {var.get('regular_price')}")
                                        print(f"      Oferta: {var.get('sale_price')}")
                                        attrs = var.get('attributes', [])
                                        if attrs:
                                            attr_str = ', '.join([f"{a.get('name', '')}={a.get('option', '')}" for a in attrs])
                                            print(f"      Atributos: {attr_str}")
                    
                    # Mostrar raw data para debugging
                    print(f"\n🔍 Datos raw de precios:")
                    price_data = {
                        'price': data.get('price'),
                        'regular_price': data.get('regular_price'),
                        'sale_price': data.get('sale_price'),
                        'price_html': data.get('price_html', '').replace('\\', '')[:100] if data.get('price_html') else 'N/A'
                    }
                    print(json.dumps(price_data, indent=2))
                    
                else:
                    print(f"\n❌ Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            print(f"\n❌ Error de conexión: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Verificar el producto Gabarron v-25 dc
    asyncio.run(check_product_direct(25489))