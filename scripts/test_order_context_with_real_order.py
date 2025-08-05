#!/usr/bin/env python3
"""
Script para probar que el contexto de pedidos se mantiene con pedidos reales
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_order_context_with_real_order():
    """Simular conversación sobre pedidos con contexto usando un email real"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Crear agente
        agent = HybridCustomerAgent()
        
        print("=" * 80)
        print("🧪 PRUEBA DE CONTEXTO CON PEDIDOS REALES")
        print("=" * 80)
        
        # Conversación simulada con email real
        conversation = [
            ("Quiero saber sobre mis pedidos, mi email es mtinoco37@gmail.com", "Primera consulta con email real"),
            ("sobre ese pedido, cuando llega?", "Pregunta de seguimiento sobre entrega"),
            ("¿puedes darme más detalles del pedido?", "Solicitud de más información"),
        ]
        
        for message, description in conversation:
            print(f"\n\n{'='*60}")
            print(f"📝 {description}")
            print(f"{'='*60}")
            print(f"\n👤 Usuario: {message}")
            
            # Procesar mensaje
            response = await agent.process_message(
                message=message,
                user_id="test_real_order_user"
            )
            
            print(f"\n🤖 Eva:\n{response}")
            
            # Verificar que mantiene contexto
            if "ese pedido" in message.lower():
                if "necesito" in response and "email" in response and "número de pedido" in response:
                    print("\n❌ ERROR: Perdió el contexto del pedido anterior")
                elif "Sobre el pedido #" in response or "como te mencioné" in response:
                    print("\n✅ CORRECTO: Mantuvo el contexto del pedido")
                elif "¿Sobre cuál pedido" in response:
                    print("\n⚠️ NOTA: Pidió aclaración (válido si hay múltiples pedidos)")
            
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_order_context_with_real_order())