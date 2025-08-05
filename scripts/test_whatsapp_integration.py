#!/usr/bin/env python3
"""
Script para probar la integración completa de WhatsApp con el agente
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_whatsapp_integration():
    """Probar diferentes escenarios de conversación"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Crear agente
        agent = HybridCustomerAgent()
        
        print("=" * 80)
        print("🧪 PRUEBA DE INTEGRACIÓN WHATSAPP - EVA ASSISTANT")
        print("=" * 80)
        
        # Escenarios de prueba
        test_scenarios = [
            {
                "name": "Búsqueda exitosa de productos",
                "messages": ["Busco ventiladores Gabarron"]
            },
            {
                "name": "Producto no encontrado (debe escalar)",
                "messages": ["Busco un producto xyz123 que no existe"]
            },
            {
                "name": "Cliente frustrado (debe escalar)",
                "messages": [
                    "necesito ayuda con un ventilador",
                    "no entiendo nada",
                    "esto no sirve, quiero hablar con una persona"
                ]
            },
            {
                "name": "Consulta urgente (debe escalar)",
                "messages": ["URGENTE! Necesito 50 ventiladores para hoy mismo"]
            },
            {
                "name": "Problema de garantía (debe escalar)",
                "messages": ["El ventilador que compré llegó roto, necesito la garantía"]
            },
            {
                "name": "Solicitud de devolución (debe escalar)",
                "messages": ["Quiero devolver mi pedido y que me devuelvan el dinero"]
            },
            {
                "name": "Consulta técnica compleja (debe escalar)",
                "messages": ["Necesito el esquema eléctrico para instalar el ventilador en trifásica"]
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n\n{'='*60}")
            print(f"📋 ESCENARIO: {scenario['name']}")
            print(f"{'='*60}")
            
            # Resetear sesión para cada escenario
            agent.conversation_state.conversation_history.clear()
            
            for message in scenario['messages']:
                print(f"\n👤 Usuario: {message}")
                print("-" * 50)
                
                # Procesar mensaje
                response = await agent.process_message(
                    message=message,
                    user_id="test_whatsapp_user"
                )
                
                print(f"\n🤖 Eva:")
                print(response)
                
                # Verificar si hay enlace de WhatsApp en la respuesta
                if "wa.me" in response:
                    print("\n✅ ESCALAMIENTO DETECTADO - Enlace WhatsApp incluido")
                
                # Pequeña pausa entre mensajes
                await asyncio.sleep(0.5)
        
        # Ejemplo de formato completo
        print("\n\n" + "="*80)
        print("📱 EJEMPLO DE RESPUESTA COMPLETA EN WHATSAPP")
        print("="*80)
        
        sample_response = """
🔍 *Productos encontrados:*

📦 *Gabarron ventilador de techo v-25 dc*
💰 ~266.2€~ *206.31€* ¡OFERTA!
✅ Disponible
📋 Ref: 90920070
🔗 Ver producto: https://staging.elcorteelectrico.com/producto/gabarron-v25-dc/

📦 *Gabarron ventilador ventur dc*
💰 *101.63€* (IVA incluido)
✅ Disponible
📋 Ref: 90920065
🔗 Ver producto: https://staging.elcorteelectrico.com/producto/gabarron-ventur/

💬 *¿Necesitas ayuda personalizada?*
Chatea con un especialista: https://wa.me/34614218122?text=Hola%2C%20necesito%20ayuda%20con%20un%20producto
"""
        print(sample_response)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_whatsapp_integration())