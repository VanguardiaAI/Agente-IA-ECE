#!/usr/bin/env python3
"""
Script de pruebas para el Agente de Atención al Cliente
Demuestra diferentes escenarios de conversación
"""

import asyncio
import os
from typing import List
from dotenv import load_dotenv

from customer_agent import create_customer_service_agent, run_conversation

# Cargar variables de entorno
load_dotenv("env.agent.example")

class AgentTester:
    def __init__(self):
        self.graph = None
        self.agent = None
    
    async def initialize(self):
        """Inicializa el agente"""
        try:
            self.graph, self.agent = await create_customer_service_agent()
            print("🚀 Agente de atención al cliente inicializado correctamente")
        except Exception as e:
            print(f"❌ Error inicializando agente: {e}")
            raise
    
    async def run_test_scenarios(self):
        """Ejecuta diferentes escenarios de prueba"""
        scenarios = [
            {
                "name": "Consulta de Pedido",
                "description": "Cliente consulta el estado de su pedido",
                "messages": [
                    "Hola, quiero saber sobre mi pedido",
                    "Mi número de orden es 12345 y mi email es cliente@email.com"
                ]
            },
            {
                "name": "Búsqueda de Productos",
                "description": "Cliente busca productos específicos",
                "messages": [
                    "Busco velas aromáticas",
                    "Me interesan de lavanda"
                ]
            },
            {
                "name": "Información de Envíos",
                "description": "Cliente pregunta sobre envíos",
                "messages": [
                    "¿Cuánto cuesta el envío?",
                    "¿Cuánto tiempo tarda en llegar?"
                ]
            },
            {
                "name": "Devoluciones",
                "description": "Cliente pregunta sobre devoluciones",
                "messages": [
                    "Quiero devolver un producto",
                    "El producto llegó defectuoso"
                ]
            },
            {
                "name": "Conversación Compleja",
                "description": "Múltiples intenciones en una conversación",
                "messages": [
                    "Hola, tengo varias preguntas",
                    "Primero, ¿tienen velas de vainilla?",
                    "También quiero saber sobre mi pedido #67890",
                    "Y cuáles son sus políticas de devolución"
                ]
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*60}")
            print(f"🧪 ESCENARIO {i}: {scenario['name']}")
            print(f"📝 {scenario['description']}")
            print(f"{'='*60}")
            
            try:
                await run_conversation(
                    self.graph, 
                    scenario["messages"], 
                    thread_id=f"test_scenario_{i}"
                )
                print(f"\n✅ Escenario {i} completado exitosamente")
            except Exception as e:
                print(f"\n❌ Error en escenario {i}: {e}")
            
            print(f"\n{'='*60}")
    
    async def interactive_mode(self):
        """Modo interactivo para probar el agente"""
        print("\n🎮 MODO INTERACTIVO")
        print("Escribe 'salir' para terminar")
        print("Escribe 'nuevo' para iniciar una nueva conversación")
        print("=" * 50)
        
        thread_id = "interactive_session"
        conversation_started = False
        
        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() == 'nuevo':
                    import uuid
                    thread_id = f"interactive_{uuid.uuid4().hex[:8]}"
                    conversation_started = False
                    print("🔄 Nueva conversación iniciada")
                    continue
                
                if not user_input:
                    continue
                
                if not conversation_started:
                    # Inicializar conversación
                    await run_conversation(
                        self.graph, 
                        [user_input], 
                        thread_id=thread_id
                    )
                    conversation_started = True
                else:
                    # Continuar conversación
                    await run_conversation(
                        self.graph, 
                        [user_input], 
                        thread_id=thread_id
                    )
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

async def main():
    """Función principal"""
    print("🤖 AGENTE DE ATENCIÓN AL CLIENTE - PRUEBAS")
    print("=" * 50)
    
    # Configurar variables por defecto para pruebas
    os.environ.setdefault("LLM_PROVIDER", "anthropic")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-key-for-demo")
    os.environ.setdefault("MODEL_NAME", "claude-3-5-sonnet-20241022")
    os.environ.setdefault("TEMPERATURE", "0.1")
    os.environ.setdefault("MAX_TOKENS", "4000")
    os.environ.setdefault("MCP_SERVER_HOST", "localhost")
    os.environ.setdefault("MCP_SERVER_PORT", "8000")
    
    print("✅ Variables de entorno configuradas para pruebas")
    
    tester = AgentTester()
    await tester.initialize()
    
    print("\n¿Qué tipo de prueba quieres ejecutar?")
    print("1. Ejecutar escenarios de prueba automáticos")
    print("2. Modo interactivo")
    print("3. Ambos")
    
    choice = input("\nElige una opción (1-3): ").strip()
    
    if choice == "1":
        await tester.run_test_scenarios()
    elif choice == "2":
        await tester.interactive_mode()
    elif choice == "3":
        await tester.run_test_scenarios()
        await tester.interactive_mode()
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    asyncio.run(main()) 