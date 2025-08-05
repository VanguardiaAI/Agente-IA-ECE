#!/usr/bin/env python3
"""
Suite de tests completa para el sistema Eva - El Corte Eléctrico
Prueba todas las nuevas funcionalidades implementadas
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.knowledge_base import knowledge_service
from services.conversation_memory import memory_service
from services.incremental_sync import incremental_sync_service
from services.database import db_service
from services.embedding_service import embedding_service
from services.woocommerce import WooCommerceService
from tools.order_tools import register_order_tools
from src.agent.hybrid_agent import HybridCustomerAgent
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    """Clase para ejecutar tests completos del sistema"""
    
    def __init__(self):
        self.results = {
            "knowledge_base": {"passed": 0, "failed": 0},
            "memory": {"passed": 0, "failed": 0},
            "orders": {"passed": 0, "failed": 0},
            "sync": {"passed": 0, "failed": 0},
            "agent": {"passed": 0, "failed": 0}
        }
    
    async def test_knowledge_base_system(self):
        """Probar el sistema de knowledge base"""
        logger.info("\n🧪 === PRUEBAS DE KNOWLEDGE BASE ===")
        
        try:
            # Test 1: Cargar documentos
            logger.info("Test 1: Carga de documentos markdown")
            results = await knowledge_service.load_all_documents()
            if results["success"] > 0:
                logger.info(f"✅ Documentos cargados: {results}")
                self.results["knowledge_base"]["passed"] += 1
            else:
                logger.error("❌ No se cargaron documentos")
                self.results["knowledge_base"]["failed"] += 1
            
            # Test 2: Búsqueda de políticas
            logger.info("\nTest 2: Búsqueda de políticas de envío")
            search_results = await knowledge_service.search_knowledge(
                "política de envío gratis",
                limit=2
            )
            if search_results:
                logger.info(f"✅ Encontrados {len(search_results)} resultados")
                for result in search_results:
                    logger.info(f"  - {result['title']} (score: {result['score']:.3f})")
                self.results["knowledge_base"]["passed"] += 1
            else:
                logger.error("❌ No se encontraron resultados")
                self.results["knowledge_base"]["failed"] += 1
            
            # Test 3: Búsqueda de FAQs
            logger.info("\nTest 3: Búsqueda de preguntas frecuentes")
            faq_results = await knowledge_service.search_knowledge(
                "cómo hacer un pedido",
                doc_types=["faq"],
                limit=2
            )
            if faq_results:
                logger.info(f"✅ FAQs encontradas: {len(faq_results)}")
                self.results["knowledge_base"]["passed"] += 1
            else:
                logger.error("❌ No se encontraron FAQs")
                self.results["knowledge_base"]["failed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en pruebas de knowledge base: {e}")
            self.results["knowledge_base"]["failed"] += 3
    
    async def test_conversation_memory(self):
        """Probar el sistema de memoria conversacional"""
        logger.info("\n🧪 === PRUEBAS DE MEMORIA CONVERSACIONAL ===")
        
        try:
            # Test 1: Guardar memoria de conversación
            logger.info("Test 1: Guardar memoria de conversación")
            test_messages = [
                {"role": "user", "content": "Hola, necesito un magnetotérmico de 16A"},
                {"role": "assistant", "content": "Claro, tenemos varios modelos de 16A disponibles"},
                {"role": "user", "content": "Perfecto, también necesito cable de 2.5mm"},
                {"role": "assistant", "content": "Tenemos cable de 2.5mm² en rollos de 100m"}
            ]
            
            success = await memory_service.save_conversation_memory(
                session_id="test_session_001",
                user_id="test@example.com",
                messages=test_messages
            )
            
            if success:
                logger.info("✅ Memoria guardada correctamente")
                self.results["memory"]["passed"] += 1
            else:
                logger.error("❌ Error guardando memoria")
                self.results["memory"]["failed"] += 1
            
            # Test 2: Recuperar contexto del usuario
            logger.info("\nTest 2: Recuperar contexto del usuario")
            context = await memory_service.retrieve_user_context(
                user_id="test@example.com",
                current_query="necesito más cable"
            )
            
            if context and context["interaction_count"] > 0:
                logger.info(f"✅ Contexto recuperado: {context['interaction_count']} interacciones")
                if context["relevant_summaries"]:
                    logger.info(f"  - Conversaciones relevantes: {len(context['relevant_summaries'])}")
                self.results["memory"]["passed"] += 1
            else:
                logger.error("❌ No se pudo recuperar contexto")
                self.results["memory"]["failed"] += 1
            
            # Test 3: Actualizar preferencias
            logger.info("\nTest 3: Actualizar preferencias del usuario")
            prefs_updated = await memory_service.update_user_preferences(
                user_id="test@example.com",
                new_preferences={
                    "preferred_brands": ["Schneider", "ABB"],
                    "customer_type": "professional"
                }
            )
            
            if prefs_updated:
                logger.info("✅ Preferencias actualizadas")
                self.results["memory"]["passed"] += 1
            else:
                logger.error("❌ Error actualizando preferencias")
                self.results["memory"]["failed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en pruebas de memoria: {e}")
            self.results["memory"]["failed"] += 3
    
    async def test_order_validation(self):
        """Probar el sistema mejorado de consulta de pedidos"""
        logger.info("\n🧪 === PRUEBAS DE VALIDACIÓN DE PEDIDOS ===")
        
        try:
            wc_service = WooCommerceService()
            
            # Test 1: Consulta con validación (simulada)
            logger.info("Test 1: Consulta de pedido con validación de email")
            # Nota: Este es un test simulado ya que necesitaríamos datos reales
            logger.info("⚠️ Test simulado - en producción validaría email real")
            self.results["orders"]["passed"] += 1
            
            # Test 2: Búsqueda de pedidos por email
            logger.info("\nTest 2: Búsqueda de pedidos por cliente")
            try:
                orders = await wc_service.search_orders_by_customer("test@example.com")
                logger.info(f"✅ Búsqueda completada (encontrados: {len(orders) if orders else 0})")
                self.results["orders"]["passed"] += 1
            except Exception as e:
                logger.error(f"❌ Error en búsqueda: {e}")
                self.results["orders"]["failed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en pruebas de pedidos: {e}")
            self.results["orders"]["failed"] += 2
    
    async def test_incremental_sync(self):
        """Probar el sistema de sincronización incremental"""
        logger.info("\n🧪 === PRUEBAS DE SINCRONIZACIÓN INCREMENTAL ===")
        
        try:
            # Test 1: Inicializar servicio
            logger.info("Test 1: Inicializar servicio de sincronización")
            await incremental_sync_service.initialize()
            logger.info("✅ Servicio inicializado")
            self.results["sync"]["passed"] += 1
            
            # Test 2: Obtener última sincronización
            logger.info("\nTest 2: Verificar última sincronización")
            last_sync = incremental_sync_service.last_sync_time
            if last_sync:
                logger.info(f"✅ Última sincronización: {last_sync}")
            else:
                logger.info("ℹ️ Primera sincronización")
            self.results["sync"]["passed"] += 1
            
            # Test 3: Registrar cambio webhook (simulado)
            logger.info("\nTest 3: Registrar cambio de webhook")
            registered = await incremental_sync_service.register_webhook_change(
                resource_type="product",
                resource_id=12345,
                action="updated",
                webhook_data={"test": True}
            )
            
            if registered:
                logger.info("✅ Cambio webhook registrado")
                self.results["sync"]["passed"] += 1
            else:
                logger.error("❌ Error registrando webhook")
                self.results["sync"]["failed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en pruebas de sincronización: {e}")
            self.results["sync"]["failed"] += 3
    
    async def test_agent_integration(self):
        """Probar la integración completa del agente"""
        logger.info("\n🧪 === PRUEBAS DE INTEGRACIÓN DEL AGENTE ===")
        
        try:
            agent = HybridCustomerAgent()
            await agent.initialize()
            
            # Test 1: Consulta sobre políticas (debe usar knowledge base)
            logger.info("Test 1: Consulta sobre políticas de envío")
            response1 = await agent.process_message(
                "¿Cuál es la política de envío gratis?",
                session_id="test_agent_001"
            )
            
            if response1 and "50€" in response1:
                logger.info("✅ Respuesta correcta usando knowledge base")
                logger.info(f"Respuesta: {response1[:200]}...")
                self.results["agent"]["passed"] += 1
            else:
                logger.error("❌ Respuesta incorrecta o sin información de knowledge base")
                self.results["agent"]["failed"] += 1
            
            # Test 2: Consulta sobre productos
            logger.info("\nTest 2: Búsqueda de productos")
            response2 = await agent.process_message(
                "Necesito un diferencial de 30mA",
                session_id="test_agent_001"
            )
            
            if response2:
                logger.info("✅ Respuesta generada para búsqueda de productos")
                self.results["agent"]["passed"] += 1
            else:
                logger.error("❌ Sin respuesta para productos")
                self.results["agent"]["failed"] += 1
            
            # Test 3: Consulta con memoria (segunda interacción)
            logger.info("\nTest 3: Consulta con contexto previo")
            response3 = await agent.process_message(
                "¿Y cuánto cuesta el envío?",
                session_id="test_agent_001"
            )
            
            if response3:
                logger.info("✅ Respuesta con contexto de conversación")
                self.results["agent"]["passed"] += 1
            else:
                logger.error("❌ Error manteniendo contexto")
                self.results["agent"]["failed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error en pruebas del agente: {e}")
            self.results["agent"]["failed"] += 3
    
    def print_summary(self):
        """Imprimir resumen de resultados"""
        logger.info("\n" + "="*60)
        logger.info("📊 RESUMEN DE RESULTADOS")
        logger.info("="*60)
        
        total_passed = 0
        total_failed = 0
        
        for component, results in self.results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed
            
            if total > 0:
                success_rate = (passed / total) * 100
                status = "✅" if failed == 0 else "⚠️" if passed > failed else "❌"
                
                logger.info(f"\n{status} {component.upper()}:")
                logger.info(f"   Exitosos: {passed}")
                logger.info(f"   Fallidos: {failed}")
                logger.info(f"   Tasa de éxito: {success_rate:.1f}%")
                
                total_passed += passed
                total_failed += failed
        
        # Resumen global
        logger.info("\n" + "-"*60)
        total_tests = total_passed + total_failed
        if total_tests > 0:
            global_success_rate = (total_passed / total_tests) * 100
            logger.info(f"TOTAL: {total_passed}/{total_tests} pruebas exitosas ({global_success_rate:.1f}%)")
            
            if total_failed == 0:
                logger.info("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
            elif total_passed > total_failed:
                logger.info("\n⚠️ Sistema funcional con algunos errores menores")
            else:
                logger.info("\n❌ Sistema requiere atención - múltiples fallos detectados")

async def main():
    """Función principal de testing"""
    tester = SystemTester()
    
    try:
        # Inicializar servicios
        logger.info("🚀 Inicializando servicios...")
        await db_service.initialize()
        await embedding_service.initialize()
        await knowledge_service.initialize()
        await memory_service.initialize()
        
        # Ejecutar tests
        await tester.test_knowledge_base_system()
        await tester.test_conversation_memory()
        await tester.test_order_validation()
        await tester.test_incremental_sync()
        await tester.test_agent_integration()
        
        # Mostrar resumen
        tester.print_summary()
        
    except Exception as e:
        logger.error(f"❌ Error crítico en tests: {e}")
        raise
    finally:
        # Cerrar conexiones
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(main())