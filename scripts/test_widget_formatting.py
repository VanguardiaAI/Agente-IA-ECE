#!/usr/bin/env python3
"""
Script de prueba para verificar el formateo correcto del widget de WordPress
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent
from src.utils.whatsapp_utils import format_escalation_message

async def test_formatting():
    """Prueba el formateo de mensajes para diferentes plataformas"""
    print("🔍 Probando formateo de mensajes...\n")
    
    # Test escalation messages for both platforms
    test_cases = [
        ("whatsapp", "Un especialista te atenderá personalmente"),
        ("wordpress", "Un especialista te atenderá personalmente")
    ]
    
    print("1. Probando mensajes de escalamiento:")
    print("-" * 50)
    for platform, expected_text in test_cases:
        message = format_escalation_message(reason="general", platform=platform)
        print(f"\nPlataforma: {platform}")
        print(f"Mensaje:\n{message}")
        print(f"✅ Contiene '{expected_text}': {expected_text in message}")
        print(f"✅ NO contiene asteriscos problemáticos: {'*' not in message if platform == 'wordpress' else 'N/A'}")
        print(f"✅ Contiene enlace wa.me: {'wa.me' in message}")
    
    # Test agent responses
    print("\n\n2. Probando respuestas del agente:")
    print("-" * 50)
    
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    test_messages = [
        "Quiero hablar con un humano",
        "Busco un producto que no existe xyz123",
        "Necesito ayuda urgente"
    ]
    
    for msg in test_messages:
        print(f"\n📨 Mensaje: '{msg}'")
        
        # Test WordPress
        response_wp = await agent.process_message(msg, user_id="test_wp", platform="wordpress")
        print(f"\n📱 WordPress Response:")
        print(response_wp)
        print(f"✅ NO contiene tags HTML visibles: {'<p>' not in response_wp and '<ul>' not in response_wp}")
        print(f"✅ NO contiene asteriscos de formato: {'*Un especialista*' not in response_wp}")
        
        # Test WhatsApp
        response_wa = await agent.process_message(msg, user_id="test_wa", platform="whatsapp")
        print(f"\n💬 WhatsApp Response:")
        print(response_wa[:200] + "..." if len(response_wa) > 200 else response_wa)
        print(f"✅ Puede contener asteriscos: {'*' in response_wa}")
        
        print("\n" + "-" * 30)

if __name__ == "__main__":
    asyncio.run(test_formatting())