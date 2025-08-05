#!/usr/bin/env python3
"""
Script para probar búsqueda de pedido real
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.woocommerce import WooCommerceService

async def test_real_order():
    """Probar con el email real del pedido"""
    
    try:
        wc_service = WooCommerceService()
        email = "mtinoco37@gmail.com"
        
        print(f"🔍 Buscando pedidos para: {email}")
        print("=" * 60)
        
        # Usar el método actualizado
        orders = await wc_service.search_orders_by_customer(email)
        
        if orders:
            print(f"\n✅ Encontrados {len(orders)} pedido(s):")
            for order in orders:
                print(f"\n📦 Pedido #{order.get('id')}")
                print(f"   Fecha: {order.get('date_created')}")
                print(f"   Estado: {order.get('status')}")
                print(f"   Total: {order.get('total')}€")
                print(f"   Método de pago: {order.get('payment_method_title')}")
                
                billing = order.get('billing', {})
                print(f"   Cliente: {billing.get('first_name')} {billing.get('last_name')}")
                print(f"   Email: {billing.get('email')}")
                print(f"   Teléfono: {billing.get('phone')}")
        else:
            print("\n❌ No se encontraron pedidos")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_order())