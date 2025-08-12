#!/usr/bin/env python3
"""
Script para probar que el sistema maneja correctamente el contexto sin triggers mecánicos
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_product_context():
    """Prueba el manejo de contexto cuando el usuario se refiere a productos mostrados"""
    
    print("🧪 TEST: Manejo de contexto sin triggers mecánicos")
    print("=" * 60)
    
    # Inicializar agente
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    # Conversación de prueba
    test_conversation = [
        ("Hola, busco un termo eléctrico", "Búsqueda inicial de productos"),
        ("quiero el más barato", "Selección de producto mostrado - NO debe buscar nuevos productos"),
        ("dame más información sobre ese", "Pregunta sobre producto seleccionado"),
        ("y cuánto tarda en llegar?", "Pregunta de seguimiento"),
        ("busco ventiladores", "Nueva búsqueda de productos diferentes"),
        ("el primero está bien", "Selección del primer ventilador mostrado")
    ]
    
    print("\n🔄 Iniciando conversación de prueba...\n")
    
    for i, (message, description) in enumerate(test_conversation, 1):
        print(f"\n{'='*60}")
        print(f"PRUEBA {i}: {description}")
        print(f"{'='*60}")
        print(f"👤 Usuario: {message}")
        
        # Procesar mensaje
        response = await agent.process_message(message, user_id="test_user", platform="wordpress")
        
        # Verificar la respuesta
        print(f"\n🤖 Respuesta: {response[:200]}..." if len(response) > 200 else f"\n🤖 Respuesta: {response}")
        
        # Analizar si se hizo una búsqueda cuando no debía
        if "quiero el más barato" in message or "el primero está bien" in message:
            if "opciones que coinciden" in response or "productos encontrados" in response:
                print("\n❌ ERROR: Se realizó una nueva búsqueda cuando debía referirse a productos mostrados")
            else:
                print("\n✅ CORRECTO: Se refirió a los productos mostrados sin hacer nueva búsqueda")
        
        await asyncio.sleep(1)  # Pausa entre mensajes
    
    # Mostrar estadísticas
    stats = agent.get_conversation_stats()
    print(f"\n\n📊 Estadísticas de la conversación:")
    print(f"- Turnos: {stats['turn_count']}")
    print(f"- Última estrategia: {stats['last_strategy_used']}")
    print(f"- Sistema multi-agente: {'Habilitado' if stats['multi_agent_enabled'] else 'Deshabilitado'}")
    
    print("\n✅ Prueba completada")

async def main():
    """Función principal"""
    try:
        await test_product_context()
    except KeyboardInterrupt:
        print("\n\n🛑 Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())