#!/usr/bin/env python3
"""
Script para consultar pedidos directamente de WooCommerce
"""

import asyncio
import aiohttp
import base64
import json
from datetime import datetime

# Configuración de WooCommerce
WC_URL = "https://elcorteelectrico.com"
WC_KEY = "ck_7d08edfcdb4c80e03cf5ade6b6abc02c8772900d"
WC_SECRET = "cs_1fe210cfd63d5786ef73ef735412ee8bc41704df"

async def test_orders_api():
    """Probar acceso directo a la API de pedidos"""
    
    # Crear autenticación básica
    credentials = f"{WC_KEY}:{WC_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    print("🔍 Probando acceso a la API de pedidos")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Obtener pedidos recientes
            url = f"{WC_URL}/wp-json/wc/v3/orders?per_page=10&orderby=date&order=desc"
            print(f"\n1️⃣ Obteniendo pedidos recientes...")
            print(f"   URL: {url}")
            
            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status == 200:
                    orders = await response.json()
                    print(f"   ✅ Pedidos obtenidos: {len(orders)}")
                    
                    # Buscar el pedido con el email específico
                    target_email = "mtinoco37@gmail.com"
                    found = False
                    
                    for order in orders:
                        billing = order.get('billing', {})
                        email = billing.get('email', '')
                        
                        if email.lower() == target_email.lower():
                            found = True
                            print(f"\n✅ PEDIDO ENCONTRADO:")
                            print(f"   ID: {order.get('id')}")
                            print(f"   Número: {order.get('number')}")
                            print(f"   Email: {email}")
                            print(f"   Cliente: {billing.get('first_name')} {billing.get('last_name')}")
                            print(f"   Estado: {order.get('status')}")
                            print(f"   Total: {order.get('total')}€")
                            print(f"   Fecha: {order.get('date_created')}")
                            break
                    
                    if not found:
                        print(f"\n⚠️ No se encontró el pedido con email {target_email} en los últimos 10")
                        print("\n📧 Emails encontrados en pedidos recientes:")
                        for i, order in enumerate(orders, 1):
                            billing = order.get('billing', {})
                            print(f"   {i}. {billing.get('email')} - Pedido #{order.get('id')}")
                else:
                    print(f"   ❌ Error {response.status}: {await response.text()}")
            
            # 2. Intentar obtener más pedidos
            print(f"\n2️⃣ Buscando en más pedidos...")
            url = f"{WC_URL}/wp-json/wc/v3/orders?per_page=100"
            
            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status == 200:
                    all_orders = await response.json()
                    print(f"   Total pedidos obtenidos: {len(all_orders)}")
                    
                    # Contar pedidos con el email
                    count = 0
                    for order in all_orders:
                        billing = order.get('billing', {})
                        if billing.get('email', '').lower() == target_email.lower():
                            count += 1
                            if count == 1:  # Mostrar solo el primero
                                print(f"\n   ✅ Pedido encontrado en búsqueda ampliada:")
                                print(f"      ID: {order.get('id')}")
                                print(f"      Fecha: {order.get('date_created')}")
                    
                    if count > 0:
                        print(f"\n   Total pedidos con email {target_email}: {count}")
                    
        except Exception as e:
            print(f"\n❌ Error de conexión: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orders_api())