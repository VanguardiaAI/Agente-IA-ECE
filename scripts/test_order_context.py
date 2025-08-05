#!/usr/bin/env python3
"""
Script para probar que el contexto de pedidos se mantiene
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_order_context():
    """Simular conversación sobre pedidos con contexto"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Crear agente
        agent = HybridCustomerAgent()
        
        print("=" * 80)
        print("🧪 PRUEBA DE CONTEXTO EN CONSULTAS DE PEDIDOS")
        print("=" * 80)
        
        # Conversación simulada
        conversation = [
            ("Quiero saber sobre mis pedidos, mi email es test@example.com", "Primera consulta con email"),
            ("sobre ese pedido, cuando llega?", "Pregunta de seguimiento sobre entrega"),
            ("¿puedes darme el tracking?", "Solicitud de número de seguimiento"),
        ]
        
        for message, description in conversation:
            print(f"\n\n{'='*60}")
            print(f"📝 {description}")
            print(f"{'='*60}")
            print(f"\n👤 Usuario: {message}")
            
            # Procesar mensaje
            response = await agent.process_message(
                message=message,
                user_id="test_context_user"
            )
            
            print(f"\n🤖 Eva:\n{response}")
            
            # Verificar que mantiene contexto
            if "ese pedido" in message.lower() or "tracking" in message.lower():
                if "necesito" in response and "email" in response and "número de pedido" in response:
                    print("\n❌ ERROR: Perdió el contexto del pedido anterior")
                elif "como te mencioné" in response or "como ya te he mencionado" in response:
                    print("\n✅ CORRECTO: Mantuvo el contexto del pedido")
                elif "Sin un pedido existente" in response:
                    print("\n✅ CORRECTO: Reconoció que no hay pedidos previos")
            
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_order_context())