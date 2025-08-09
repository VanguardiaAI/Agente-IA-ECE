#!/usr/bin/env python3
"""
Script para buscar un pedido específico por ID
"""

import asyncio
import aiohttp
import base64

# Configuración de WooCommerce
WC_URL = "https://elcorteelectrico.com"
WC_KEY = "ck_7d08edfcdb4c80e03cf5ade6b6abc02c8772900d"
WC_SECRET = "cs_1fe210cfd63d5786ef73ef735412ee8bc41704df"

async def get_specific_order(order_id: str):
    """Obtener un pedido específico por ID"""
    
    # Crear autenticación básica
    credentials = f"{WC_KEY}:{WC_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    print(f"🔍 Buscando pedido específico: #{order_id}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Intentar obtener el pedido directamente
            url = f"{WC_URL}/wp-json/wc/v3/orders/{order_id}"
            print(f"\n📦 URL: {url}")
            
            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status == 200:
                    order = await response.json()
                    print(f"\n✅ Pedido encontrado:")
                    print(f"   ID: {order.get('id')}")
                    print(f"   Número: {order.get('number')}")
                    print(f"   Estado: {order.get('status')}")
                    print(f"   Total: {order.get('total')}€")
                    print(f"   Fecha: {order.get('date_created')}")
                    print(f"   Método de pago: {order.get('payment_method_title')}")
                    
                    billing = order.get('billing', {})
                    print(f"\n👤 Información de facturación:")
                    print(f"   Nombre: {billing.get('first_name')} {billing.get('last_name')}")
                    print(f"   Email: {billing.get('email')}")
                    print(f"   Teléfono: {billing.get('phone')}")
                    print(f"   DNI: {billing.get('dni', 'N/A')}")
                    
                    print(f"\n📍 Dirección:")
                    print(f"   {billing.get('address_1')}")
                    print(f"   {billing.get('postcode')} {billing.get('city')}")
                    print(f"   {billing.get('state')}")
                    
                    return order
                else:
                    print(f"\n❌ Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Buscar el pedido específico mencionado
    asyncio.run(get_specific_order("10000012583"))