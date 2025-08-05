#!/usr/bin/env python3
"""
Script para probar escenarios donde SÍ y NO se debe escalar
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_escalation_scenarios():
    """Probar diferentes escenarios de escalamiento"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        print("=" * 80)
        print("🧪 PRUEBAS DE ESCALAMIENTO - CUÁNDO SÍ Y CUÁNDO NO")
        print("=" * 80)
        
        # Escenario 1: NO debe escalar - Búsqueda normal
        print("\n\n✅ ESCENARIO 1: Búsqueda normal (NO debe escalar)")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message("Busco un ventilador silencioso", "user1")
        print(f"\n👤 Usuario: Busco un ventilador silencioso")
        print(f"\n🤖 Eva:\n{response}")
        
        if "wa.me" in response:
            print("\n❌ ERROR: No debería haber escalado")
        else:
            print("\n✅ CORRECTO: No escaló innecesariamente")
        
        # Escenario 2: NO debe escalar - Consulta de información
        print("\n\n✅ ESCENARIO 2: Consulta de información (NO debe escalar)")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message("¿Cuánto cuesta el ventilador gabarron?", "user2")
        print(f"\n👤 Usuario: ¿Cuánto cuesta el ventilador gabarron?")
        print(f"\n🤖 Eva:\n{response}")
        
        if "wa.me" in response:
            print("\n❌ ERROR: No debería haber escalado")
        else:
            print("\n✅ CORRECTO: No escaló innecesariamente")
        
        # Escenario 3: SÍ debe escalar - Producto no encontrado
        print("\n\n❌ ESCENARIO 3: Producto no existe (SÍ debe escalar)")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message("Necesito el modelo XYZ789 urgente", "user3")
        print(f"\n👤 Usuario: Necesito el modelo XYZ789 urgente")
        print(f"\n🤖 Eva:\n{response}")
        
        if "wa.me" in response:
            print("\n✅ CORRECTO: Escaló apropiadamente")
        else:
            print("\n❌ ERROR: Debería haber escalado")
        
        # Escenario 4: SÍ debe escalar - Cliente pide humano
        print("\n\n❌ ESCENARIO 4: Cliente pide humano (SÍ debe escalar)")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message("No me sirves, quiero hablar con una persona real", "user4")
        print(f"\n👤 Usuario: No me sirves, quiero hablar con una persona real")
        print(f"\n🤖 Eva:\n{response}")
        
        if "wa.me" in response:
            print("\n✅ CORRECTO: Escaló cuando se pidió explícitamente")
        else:
            print("\n❌ ERROR: Debería haber escalado")
        
        # Escenario 5: SÍ debe escalar - Devolución
        print("\n\n❌ ESCENARIO 5: Solicitud de devolución (SÍ debe escalar)")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message("Quiero devolver mi pedido y recuperar mi dinero", "user5")
        print(f"\n👤 Usuario: Quiero devolver mi pedido y recuperar mi dinero")
        print(f"\n🤖 Eva:\n{response}")
        
        if "wa.me" in response:
            print("\n✅ CORRECTO: Escaló para gestión de devolución")
        else:
            print("\n❌ ERROR: Debería haber escalado")
        
        # Escenario 6: NO debe escalar - Stock disponible
        print("\n\n✅ ESCENARIO 6: Verificación de stock (NO debe escalar)")
        print("-" * 60)
        agent = HybridCustomerAgent()
        
        response = await agent.process_message("¿Hay stock del ventilador gabarron v-25?", "user6")
        print(f"\n👤 Usuario: ¿Hay stock del ventilador gabarron v-25?")
        print(f"\n🤖 Eva:\n{response}")
        
        if "wa.me" in response:
            print("\n❌ ERROR: No debería haber escalado")
        else:
            print("\n✅ CORRECTO: No escaló innecesariamente")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_escalation_scenarios())