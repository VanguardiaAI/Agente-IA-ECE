#!/usr/bin/env python3
"""
Script para probar consultas de pedidos mejoradas
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_order_inquiry():
    """Probar diferentes escenarios de consulta de pedidos"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        print("=" * 80)
        print("🧪 PRUEBA DE CONSULTAS DE PEDIDOS MEJORADAS")
        print("=" * 80)
        
        # Escenario 1: Solo email
        print("\n\n✅ ESCENARIO 1: Consulta con solo email")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message(
            "quiero saber mis pedidos, mi email es pablo.ar.luque@gmail.com",
            "test_order_user1"
        )
        
        print(f"\n👤 Usuario: quiero saber mis pedidos, mi email es pablo.ar.luque@gmail.com")
        print(f"\n🤖 Eva:\n{response}")
        
        # Verificar que no invente números
        if "900" in response:
            print("\n❌ ERROR: Inventó un número 900")
        else:
            print("\n✅ CORRECTO: No inventó números falsos")
        
        # Escenario 2: Email sin pedidos
        print("\n\n✅ ESCENARIO 2: Email sin pedidos")
        print("-" * 60)
        agent2 = HybridCustomerAgent()
        
        response = await agent2.process_message(
            "busca mis pedidos: usuario@inexistente.com",
            "test_order_user2"
        )
        
        print(f"\n👤 Usuario: busca mis pedidos: usuario@inexistente.com")
        print(f"\n🤖 Eva:\n{response}")
        
        # Escenario 3: Número y email juntos
        print("\n\n✅ ESCENARIO 3: Número de pedido y email")
        print("-" * 60)
        agent3 = HybridCustomerAgent()
        
        response = await agent3.process_message(
            "quiero info del pedido 12345, mi email es test@example.com",
            "test_order_user3"
        )
        
        print(f"\n👤 Usuario: quiero info del pedido 12345, mi email es test@example.com")
        print(f"\n🤖 Eva:\n{response}")
        
        # Verificar que escale apropiadamente para seguridad
        if "wa.me" in response:
            print("\n✅ CORRECTO: Escaló por seguridad en consulta de pedido específico")
        
        # Escenario 4: Solo número de pedido
        print("\n\n✅ ESCENARIO 4: Solo número de pedido")
        print("-" * 60)
        agent4 = HybridCustomerAgent()
        
        response = await agent4.process_message(
            "necesito información del pedido 54321",
            "test_order_user4"
        )
        
        print(f"\n👤 Usuario: necesito información del pedido 54321")
        print(f"\n🤖 Eva:\n{response}")
        
        # Escenario 5: Sin datos
        print("\n\n✅ ESCENARIO 5: Sin datos de pedido")
        print("-" * 60)
        agent5 = HybridCustomerAgent()
        
        response = await agent5.process_message(
            "quiero saber sobre mi pedido",
            "test_order_user5"
        )
        
        print(f"\n👤 Usuario: quiero saber sobre mi pedido")
        print(f"\n🤖 Eva:\n{response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_order_inquiry())