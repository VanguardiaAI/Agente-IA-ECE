#!/usr/bin/env python3
"""
Script simple para probar las correcciones de logging sin usar OpenAI
"""

import asyncio
import sys
import os
from datetime import datetime

# Configurar el path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importaciones
from services.conversation_logger import PostgreSQLConversationLogger

async def test_conversation_logger():
    """Probar el conversation logger corregido"""
    print("🧪 Probando PostgreSQL Conversation Logger...")
    
    logger = PostgreSQLConversationLogger()
    
    try:
        # Inicializar
        await logger.initialize()
        
        if not logger.enabled:
            print("⚠️ Conversation logger está deshabilitado (configuración)")
            return True
        
        print("✅ Logger inicializado correctamente")
        
        # Probar log_message (método correcto)
        await logger.log_message(
            session_id="test_session_fixes",
            user_id="test_user",
            message_type="test",
            content="User: Prueba de correcciones\nAssistant: Sistema funcionando correctamente",
            metadata={
                "test_fix": True,
                "strategy": "test_strategy",
                "timestamp": datetime.now().isoformat()
            },
            response_time_ms=500,
            strategy="test_strategy"
        )
        
        print("✅ log_message funcionando correctamente")
        
        # Probar analytics
        stats = await logger.get_analytics(1)
        if stats:
            print(f"✅ Analytics funcionando: {stats.get('total_messages', 0)} mensajes")
        else:
            print("⚠️ Analytics no devolvió datos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en conversation logger: {e}")
        return False
    
    finally:
        try:
            await logger.close()
            print("✅ Logger cerrado correctamente")
        except Exception as e:
            print(f"⚠️ Error cerrando logger: {e}")

async def test_hybrid_agent_imports():
    """Probar que las importaciones del agente híbrido funcionan"""
    print("\n🧪 Probando importaciones del agente híbrido...")
    
    try:
        from src.agent.hybrid_agent import HybridCustomerAgent
        print("✅ HybridCustomerAgent importado correctamente")
        
        # Probar inicialización básica (sin initialize)
        agent = HybridCustomerAgent()
        print("✅ Instancia creada correctamente")
        
        # Verificar que usa los nuevos modelos
        if hasattr(agent, '_fallback_strategy_selection'):
            result = agent._fallback_strategy_selection("hola")
            print(f"✅ Fallback strategy funcionando: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en imports del agente: {e}")
        return False

async def test_database_imports():
    """Probar que las importaciones de base de datos funcionan"""
    print("\n🧪 Probando importaciones de base de datos...")
    
    try:
        from services.database import HybridDatabaseService
        print("✅ HybridDatabaseService importado correctamente")
        
        from services.embedding_service import EmbeddingService
        print("✅ EmbeddingService importado correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en imports de base de datos: {e}")
        return False

async def test_basic_functionality():
    """Probar funcionalidad básica sin servicios externos"""
    print("\n🧪 Probando funcionalidad básica...")
    
    try:
        from src.agent.hybrid_agent import HybridCustomerAgent
        
        agent = HybridCustomerAgent()
        
        # Probar métodos que no requieren inicialización
        result1 = agent._fallback_strategy_selection("hola")
        print(f"✅ Estrategia para 'hola': {result1}")
        
        result2 = agent._fallback_strategy_selection("busco productos")
        print(f"✅ Estrategia para 'busco productos': {result2}")
        
        result3 = agent._fallback_strategy_selection("")
        print(f"✅ Estrategia para mensaje vacío: {result3}")
        
        # Probar respuesta de fallback
        fallback = agent._get_fallback_response("hola")
        print(f"✅ Respuesta fallback: {fallback[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en funcionalidad básica: {e}")
        return False

async def main():
    """Función principal"""
    print("🚀 PRUEBAS DE CORRECCIONES BÁSICAS")
    print("=" * 50)
    print(f"⏰ Hora: {datetime.now()}")
    print("=" * 50)
    
    tests = [
        ("Imports de Base de Datos", test_database_imports),
        ("Imports del Agente Híbrido", test_hybrid_agent_imports),
        ("Funcionalidad Básica", test_basic_functionality),
        ("Conversation Logger", test_conversation_logger)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = await test_func()
            if success:
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN: {passed}/{total} pruebas exitosas")
    print(f"📈 Tasa de éxito: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ¡Todas las correcciones funcionan correctamente!")
        print("\n💡 Próximos pasos:")
        print("   1. Configurar OpenAI API Key para pruebas completas")
        print("   2. Ejecutar: python scripts/test_phase3_integration_fixed.py")
        return 0
    else:
        print("⚠️ Algunas correcciones necesitan revisión")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 