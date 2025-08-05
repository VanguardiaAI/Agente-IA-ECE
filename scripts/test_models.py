#!/usr/bin/env python3
"""
Script para probar los modelos GPT-4.1
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_models():
    """Probar los diferentes modelos"""
    
    try:
        # Inicializar servicios
        print("🚀 Inicializando servicios...")
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Crear agente
        agent = HybridCustomerAgent()
        
        print("\n📋 CONFIGURACIÓN DE MODELOS:")
        print(f"   Modelo principal: {agent.model_name}")
        print(f"   Proveedor: {agent.llm_provider}")
        print(f"   Temperatura: {agent.temperature}")
        print(f"   Max tokens: {agent.max_tokens}")
        
        print("\n🧪 PRUEBAS DE FUNCIONAMIENTO:")
        
        # Prueba 1: Saludo simple (debe usar quick_response)
        print("\n1️⃣ Prueba de saludo simple...")
        response = await agent.process_message(
            message="Hola",
            user_id="test_user"
        )
        print(f"   Respuesta: {response[:100]}...")
        
        # Prueba 2: Búsqueda de productos (debe usar tool_assisted)
        print("\n2️⃣ Prueba de búsqueda de productos...")
        response = await agent.process_message(
            message="Busco diferenciales de 40A",
            user_id="test_user"
        )
        print(f"   Respuesta: {response[:200]}...")
        
        # Prueba 3: Consulta de pedido (debe usar tool_assisted)
        print("\n3️⃣ Prueba de consulta de pedido...")
        response = await agent.process_message(
            message="Quiero saber sobre mi pedido, mi email es test@example.com",
            user_id="test_user"
        )
        print(f"   Respuesta: {response[:200]}...")
        
        print("\n✅ Todas las pruebas completadas")
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_models())