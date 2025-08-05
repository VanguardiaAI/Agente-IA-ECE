#!/usr/bin/env python3
"""
Script para debuggear búsqueda de pedidos por email
"""

import asyncio
import sys
from pathlib import Path
import json

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.woocommerce import WooCommerceService

async def debug_order_search(email: str):
    """Debuggear paso a paso la búsqueda de pedidos"""
    
    try:
        wc_service = WooCommerceService()
        
        print(f"🔍 Debuggeando búsqueda de pedidos para: {email}")
        print("=" * 60)
        
        # Paso 1: Buscar cliente
        print("\n1️⃣ Buscando cliente por email...")
        customers = await wc_service._make_request("GET", "customers", params={"email": email})
        
        if customers:
            print(f"✅ Cliente encontrado:")
            for customer in customers:
                print(f"   - ID: {customer.get('id')}")
                print(f"   - Nombre: {customer.get('first_name')} {customer.get('last_name')}")
                print(f"   - Email: {customer.get('email')}")
                print(f"   - Registrado: {customer.get('date_created')}")
            
            # Paso 2: Buscar pedidos del cliente
            customer_id = customers[0].get('id')
            print(f"\n2️⃣ Buscando pedidos del cliente ID: {customer_id}")
            
            # Intentar diferentes formas de buscar pedidos
            print("\n   Método 1: Por customer ID...")
            orders1 = await wc_service._make_request("GET", "orders", params={"customer": customer_id})
            print(f"   Pedidos encontrados: {len(orders1) if orders1 else 0}")
            
            print("\n   Método 2: Por customer ID con más resultados...")
            orders2 = await wc_service._make_request("GET", "orders", params={"customer": customer_id, "per_page": 100})
            print(f"   Pedidos encontrados: {len(orders2) if orders2 else 0}")
            
            print("\n   Método 3: Todos los pedidos recientes...")
            all_orders = await wc_service._make_request("GET", "orders", params={"per_page": 100, "orderby": "date", "order": "desc"})
            print(f"   Total pedidos en sistema: {len(all_orders) if all_orders else 0}")
            
            # Buscar manualmente por email en todos los pedidos
            if all_orders:
                print(f"\n3️⃣ Buscando pedidos con email {email} en todos los pedidos...")
                matching_orders = []
                for order in all_orders:
                    billing = order.get('billing', {})
                    if billing.get('email', '').lower() == email.lower():
                        matching_orders.append(order)
                
                print(f"   Pedidos encontrados con ese email: {len(matching_orders)}")
                
                if matching_orders:
                    print("\n📦 Pedidos encontrados:")
                    for order in matching_orders[:5]:  # Mostrar máximo 5
                        print(f"\n   Pedido #{order.get('id')}")
                        print(f"   - Fecha: {order.get('date_created')}")
                        print(f"   - Estado: {order.get('status')}")
                        print(f"   - Total: {order.get('total')}€")
                        print(f"   - Cliente ID en pedido: {order.get('customer_id')}")
                        print(f"   - Email en billing: {order.get('billing', {}).get('email')}")
        else:
            print("❌ No se encontró ningún cliente con ese email")
            
            # Intentar buscar en todos los pedidos
            print("\n🔄 Buscando directamente en pedidos recientes...")
            all_orders = await wc_service._make_request("GET", "orders", params={"per_page": 50})
            
            if all_orders:
                found = False
                for order in all_orders:
                    billing = order.get('billing', {})
                    if billing.get('email', '').lower() == email.lower():
                        if not found:
                            print("\n✅ Pedido encontrado sin cliente registrado:")
                            found = True
                        print(f"\n   Pedido #{order.get('id')}")
                        print(f"   - Email: {billing.get('email')}")
                        print(f"   - Nombre: {billing.get('first_name')} {billing.get('last_name')}")
                        print(f"   - Estado: {order.get('status')}")
                        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Probar con el email real
    asyncio.run(debug_order_search("mtinoco37@gmail.com"))