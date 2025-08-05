#!/usr/bin/env python3
"""
Script de prueba para verificar que el LLM funciona correctamente
"""

import asyncio
import os
from dotenv import load_dotenv
from simple_agent import SimpleCustomerAgent

async def test_llm():
    """Prueba el funcionamiento del LLM"""
    print("🧪 PRUEBA DEL MODELO DE LENGUAJE")
    print("=" * 50)
    
    # Cargar configuración
    load_dotenv("env.agent")
    
    # Verificar API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "tu_anthropic_api_key_real_aqui":
        print("❌ No se ha configurado una API key válida")
        print("   Editando env.agent y agregando tu ANTHROPIC_API_KEY")
        print("   El test usará respuestas simuladas")
        print()
    else:
        print("✅ API key configurada")
        print(f"   Proveedor: {os.getenv('LLM_PROVIDER', 'anthropic')}")
        print(f"   Modelo: {os.getenv('MODEL_NAME', 'claude-3-5-sonnet-20241022')}")
        print()
    
    # Crear agente
    agent = SimpleCustomerAgent()
    
    # Mensajes de prueba
    test_messages = [
        "Hola, ¿cómo estás?",
        "Quiero consultar mi pedido número 12345, mi email es test@email.com",
        "Busco velas de lavanda para regalo",
        "¿Cuánto cuesta el envío?",
        "Tengo un problema con mi pedido"
    ]
    
    print("🤖 Iniciando conversación...")
    greeting = await agent.start_conversation()
    print(f"Agente: {greeting}")
    print()
    
    for i, message in enumerate(test_messages, 1):
        print(f"👤 Usuario: {message}")
        
        try:
            response = await agent.process_message(message)
            print(f"🤖 Agente: {response}")
            
            # Verificar si es una respuesta del LLM o simulada
            if "sk-test-key-for-demo" in os.getenv("ANTHROPIC_API_KEY", ""):
                print("   ⚠️  Respuesta simulada (sin LLM real)")
            else:
                print("   ✅ Respuesta generada por LLM")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("-" * 50)
    
    print("\n🎯 RESUMEN:")
    if api_key and api_key != "tu_anthropic_api_key_real_aqui":
        print("✅ El agente está configurado para usar IA real")
        print("   Las respuestas son generadas por Claude")
    else:
        print("⚠️  El agente está en modo simulado")
        print("   Para activar IA real:")
        print("   1. Obtén una API key de Anthropic: https://console.anthropic.com/")
        print("   2. Edita el archivo 'env.agent'")
        print("   3. Reemplaza 'tu_anthropic_api_key_real_aqui' con tu API key")

if __name__ == "__main__":
    asyncio.run(test_llm()) 