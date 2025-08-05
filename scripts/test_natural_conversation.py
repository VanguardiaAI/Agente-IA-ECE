#!/usr/bin/env python3
"""
Script para probar conversaciones naturales con contexto
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_natural_conversation():
    """Simular una conversación natural con seguimiento"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Crear agente
        agent = HybridCustomerAgent()
        
        print("=" * 80)
        print("🧪 PRUEBA DE CONVERSACIÓN NATURAL")
        print("=" * 80)
        
        # Conversación simulada
        conversation = [
            "Hola, busco ventiladores silenciosos",
            "¿Cuál es la diferencia entre el Varys y el Ventur?",
            "Me interesa más el que sea más silencioso",
            "¿El Varys tiene garantía?",
            "Perfecto, ¿cuánto tarda el envío?"
        ]
        
        print("\n📱 Simulando conversación en WhatsApp:")
        print("-" * 60)
        
        for i, message in enumerate(conversation):
            print(f"\n👤 Usuario: {message}")
            
            # Procesar mensaje
            response = await agent.process_message(
                message=message,
                user_id="test_natural_user"
            )
            
            print(f"\n🤖 Eva: {response}")
            
            # Verificar que no escale innecesariamente
            if "wa.me" in response and i < 3:  # Las primeras 3 no deberían escalar
                print("\n⚠️ ALERTA: Escaló cuando no debería")
            
            print("\n" + "-" * 60)
            
            # Pausa entre mensajes
            await asyncio.sleep(0.5)
        
        # Segunda conversación: con necesidad de escalamiento
        print("\n\n" + "="*80)
        print("📱 CONVERSACIÓN QUE SÍ REQUIERE ESCALAMIENTO:")
        print("="*80)
        
        agent2 = HybridCustomerAgent()  # Nuevo agente para conversación limpia
        
        escalation_conversation = [
            "Busco el modelo específico ABC123",
            "No, necesito exactamente ese modelo",
            "Esto no me sirve, necesito hablar con alguien"
        ]
        
        for message in escalation_conversation:
            print(f"\n👤 Usuario: {message}")
            
            response = await agent2.process_message(
                message=message,
                user_id="test_escalation_user"
            )
            
            print(f"\n🤖 Eva: {response}")
            
            if "wa.me" in response:
                print("\n✅ Escalamiento detectado correctamente")
            
            print("\n" + "-" * 60)
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_natural_conversation())