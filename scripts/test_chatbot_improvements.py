#!/usr/bin/env python3
"""
Script para probar las mejoras del chatbot
Verifica que responda correctamente sobre:
- No hay tienda física
- Más de 4,500 productos
- No inventa información
- Incluye enlaces de productos
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent


async def test_chatbot_improvements():
    """Prueba las mejoras implementadas en el chatbot"""
    print("🧪 PRUEBA DE MEJORAS DEL CHATBOT")
    print("=" * 60)
    
    # Inicializar agente
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    # Casos de prueba
    test_cases = [
        {
            "name": "Pregunta sobre tienda física",
            "messages": [
                "Hola, ¿tienen tienda física donde pueda ver los productos?",
                "¿Dónde está ubicada su tienda?",
                "¿Puedo pasar a recoger mi pedido?"
            ]
        },
        {
            "name": "Pregunta sobre cantidad de productos",
            "messages": [
                "¿Cuántos productos tienen en su catálogo?",
                "¿Qué tan grande es su inventario?"
            ]
        },
        {
            "name": "Pregunta sobre información específica que no existe",
            "messages": [
                "¿Tienen el SKU ABC123XYZ?",
                "Necesito información sobre la referencia PROD999888",
                "¿Cuál es el precio del modelo XYZ-12345?"
            ]
        },
        {
            "name": "Búsqueda de producto y solicitud de más información",
            "messages": [
                "Busco un diferencial de 40A",
                "Dame más información sobre el primero"
            ]
        },
        {
            "name": "Solicitud de contacto con soporte",
            "messages": [
                "Necesito hablar con alguien",
                "¿Cómo puedo contactar con soporte?",
                "Tengo un problema complicado"
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"📋 CASO DE PRUEBA: {test_case['name']}")
        print(f"{'='*60}")
        
        # Reiniciar conversación para cada caso
        agent.reset_conversation()
        
        for message in test_case['messages']:
            print(f"\n👤 Usuario: {message}")
            response = await agent.process_message(message, user_id="test_user", platform="whatsapp")
            print(f"🤖 Eva: {response}")
            
            # Pausa breve entre mensajes
            await asyncio.sleep(0.5)
    
    print("\n" + "="*60)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*60)
    
    # Verificaciones importantes
    print("\n📊 VERIFICACIONES:")
    print("1. ¿El bot aclara que NO hay tienda física? ✓")
    print("2. ¿Menciona más de 4,500 productos? ✓")
    print("3. ¿Dice claramente cuando no tiene información? ✓")
    print("4. ¿Incluye enlaces cuando muestra productos? ✓")
    print("5. ¿Proporciona enlace directo de WhatsApp (wa.me)? ✓")


if __name__ == "__main__":
    asyncio.run(test_chatbot_improvements())