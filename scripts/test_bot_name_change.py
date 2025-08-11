#!/usr/bin/env python3
"""Script para probar el cambio de nombre del bot"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bot_config_service import bot_config_service
from services.database import db_service
from src.agent.hybrid_agent import HybridCustomerAgent
from services.embedding_service import embedding_service
from services.knowledge_singleton import knowledge_service
from services.conversation_memory import memory_service

async def test_bot_name_change():
    """Prueba el cambio de nombre del bot"""
    print("🧪 Iniciando prueba de cambio de nombre del bot...")
    
    try:
        # Inicializar servicios
        print("\n1️⃣ Inicializando servicios...")
        await db_service.initialize()
        await bot_config_service.initialize()
        await embedding_service.initialize()
        await knowledge_service.initialize()
        
        # Obtener el nombre actual
        current_name = await bot_config_service.get_setting('bot_name', 'Eva')
        print(f"\n✅ Nombre actual del bot: {current_name}")
        
        # Cambiar el nombre a uno de prueba
        test_name = "Asistente"
        print(f"\n2️⃣ Cambiando nombre del bot a: {test_name}")
        success = await bot_config_service.set_setting('bot_name', test_name)
        
        if success:
            print(f"✅ Nombre actualizado exitosamente")
            
            # Verificar que se actualizó
            new_name = await bot_config_service.get_setting('bot_name', 'Eva')
            print(f"✅ Verificación - Nuevo nombre en DB: {new_name}")
            
            # Inicializar el agente híbrido para probar
            print("\n3️⃣ Inicializando agente híbrido con nuevo nombre...")
            agent = HybridCustomerAgent(
                db_service=db_service,
                embedding_service=embedding_service,
                knowledge_service=knowledge_service,
                memory_service=memory_service
            )
            await agent.initialize()
            
            print(f"✅ Nombre del bot en el agente: {agent.bot_name}")
            
            # Probar una respuesta simple
            print("\n4️⃣ Probando respuesta del bot...")
            response = await agent.process_message("Hola, ¿cómo te llamas?")
            print(f"\n🤖 Respuesta del bot: {response}")
            
            # Verificar que el nombre aparezca en la respuesta
            if test_name in response:
                print(f"\n✅ ¡ÉXITO! El bot se identifica correctamente como '{test_name}'")
            else:
                print(f"\n⚠️  ADVERTENCIA: El bot no mencionó su nuevo nombre '{test_name}' en la respuesta")
            
            # Restaurar el nombre original
            print(f"\n5️⃣ Restaurando nombre original: {current_name}")
            await bot_config_service.set_setting('bot_name', current_name)
            print(f"✅ Nombre restaurado")
            
        else:
            print("❌ Error al actualizar el nombre")
            
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cerrar servicios
        if db_service.pool:
            await db_service.pool.close()
        print("\n✅ Prueba completada")

if __name__ == "__main__":
    asyncio.run(test_bot_name_change())