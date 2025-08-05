#!/usr/bin/env python3
"""
Script de Configuración Fase 2 - Sistema de Búsqueda Híbrida
Configura sincronización WooCommerce, webhooks y pruebas completas
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import db_service
from services.embedding_service import embedding_service
from services.woocommerce_sync import wc_sync_service
from services.webhook_handler import webhook_handler
from services.woocommerce import WooCommerceService
from config.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Phase2Setup:
    """Configurador para la Fase 2 del sistema"""
    
    def __init__(self):
        self.setup_steps = [
            ("Verificar Fase 1", self.verify_phase1),
            ("Configurar WooCommerce", self.setup_woocommerce),
            ("Sincronización inicial", self.initial_sync),
            ("Probar búsqueda híbrida", self.test_hybrid_search),
            ("Configurar webhooks", self.setup_webhooks),
            ("Pruebas finales", self.final_tests)
        ]
    
    async def run_setup(self):
        """Ejecutar configuración completa de Fase 2"""
        print("🚀 CONFIGURACIÓN FASE 2 - SISTEMA DE BÚSQUEDA HÍBRIDA")
        print("=" * 60)
        print("🔧 Recambios Eléctricos - Sincronización WooCommerce")
        print("=" * 60)
        
        total_steps = len(self.setup_steps)
        passed_steps = 0
        
        for i, (step_name, step_func) in enumerate(self.setup_steps, 1):
            print(f"\n📋 Paso {i}/{total_steps}: {step_name}")
            print("-" * 40)
            
            try:
                success = await step_func()
                if success:
                    print(f"✅ {step_name} - COMPLETADO")
                    passed_steps += 1
                else:
                    print(f"❌ {step_name} - FALLÓ")
                    
            except Exception as e:
                print(f"❌ {step_name} - ERROR: {e}")
                logger.error(f"Error en {step_name}: {e}")
        
        # Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE CONFIGURACIÓN")
        print("=" * 60)
        print(f"✅ Pasos completados: {passed_steps}/{total_steps}")
        print(f"❌ Pasos fallidos: {total_steps - passed_steps}")
        
        if passed_steps == total_steps:
            print("\n🎉 ¡CONFIGURACIÓN FASE 2 COMPLETADA EXITOSAMENTE!")
            print("\n🌐 Sistema listo para producción:")
            print("   • API: http://localhost:8000")
            print("   • Dashboard: http://localhost:8000/")
            print("   • Docs: http://localhost:8000/docs")
            print("   • Webhooks: http://localhost:8000/api/webhooks/woocommerce")
        else:
            print(f"\n⚠️ Configuración incompleta. Revisar errores arriba.")
            return False
        
        return True
    
    async def verify_phase1(self) -> bool:
        """Verificar que la Fase 1 esté funcionando correctamente"""
        try:
            print("🔍 Verificando servicios de Fase 1...")
            
            # Inicializar servicios globales si no están inicializados
            global db_service, embedding_service
            
            # Verificar base de datos
            if not hasattr(db_service, 'initialized') or not db_service.initialized:
                await db_service.initialize()
            
            if not db_service.initialized:
                print("❌ Base de datos no inicializada")
                return False
            
            print("✅ Base de datos PostgreSQL + pgvector")
            
            # Verificar embeddings
            if not hasattr(embedding_service, 'initialized') or not embedding_service.initialized:
                await embedding_service.initialize()
            
            if not embedding_service.initialized:
                print("❌ Servicio de embeddings no inicializado")
                return False
            
            print("✅ Servicio de embeddings OpenAI")
            
            # Verificar datos existentes
            stats = await db_service.get_statistics()
            print(f"📊 Entradas en base de conocimiento: {stats.get('active_entries', 0)}")
            
            if stats.get('active_entries', 0) == 0:
                print("⚠️ No hay datos en la base de conocimiento")
                print("   Ejecutando inserción de datos básicos...")
                await self._insert_basic_data()
            
            return True
            
        except Exception as e:
            print(f"❌ Error verificando Fase 1: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def setup_woocommerce(self) -> bool:
        """Configurar conexión con WooCommerce"""
        try:
            print("🛒 Configurando conexión WooCommerce...")
            
            # Verificar configuración
            if not hasattr(settings, 'WOOCOMMERCE_CONSUMER_KEY'):
                print("❌ WOOCOMMERCE_CONSUMER_KEY no configurado")
                print("   Configura las variables de entorno en .env:")
                print("   WOOCOMMERCE_CONSUMER_KEY=tu_consumer_key")
                print("   WOOCOMMERCE_CONSUMER_SECRET=tu_consumer_secret")
                print("   WOOCOMMERCE_API_URL=https://tu-tienda.com/wp-json/wc/v3")
                return False
            
            # Probar conexión
            wc_service = WooCommerceService()
            
            # Intentar obtener algunas categorías para probar la conexión
            categories = await wc_service.get_product_categories(per_page=1)
            
            if categories is None:
                print("❌ No se pudo conectar con WooCommerce")
                print("   Verifica las credenciales y URL de la API")
                return False
            
            print("✅ Conexión WooCommerce establecida")
            print(f"   API URL: {settings.woocommerce_api_url}")
            
            # Probar obtener productos
            products = await wc_service.get_products(per_page=1)
            if products:
                print(f"✅ Productos disponibles en WooCommerce: {len(products)} (muestra)")
            else:
                print("⚠️ No se encontraron productos en WooCommerce")
            
            return True
            
        except Exception as e:
            print(f"❌ Error configurando WooCommerce: {e}")
            return False
    
    async def initial_sync(self) -> bool:
        """Realizar sincronización inicial de productos"""
        try:
            print("🔄 Iniciando sincronización inicial de productos...")
            
            # Verificar si ya hay productos sincronizados
            stats = await db_service.get_statistics()
            existing_products = stats.get('active_products', 0)
            
            if existing_products > 0:
                print(f"ℹ️ Ya hay {existing_products} productos sincronizados")
                response = input("¿Deseas forzar re-sincronización? (y/N): ").lower()
                force_update = response == 'y'
            else:
                force_update = False
            
            print("⏳ Sincronizando productos... (esto puede tomar varios minutos)")
            
            # Realizar sincronización
            sync_stats = await wc_sync_service.sync_all_products(force_update=force_update)
            
            print(f"📊 Resultados de sincronización:")
            print(f"   • Productos obtenidos: {sync_stats.get('total_fetched', 0)}")
            print(f"   • Productos nuevos: {sync_stats.get('new_products', 0)}")
            print(f"   • Productos actualizados: {sync_stats.get('updated_products', 0)}")
            print(f"   • Categorías sincronizadas: {sync_stats.get('categories_synced', 0)}")
            print(f"   • Errores: {sync_stats.get('errors', 0)}")
            
            if sync_stats.get('errors', 0) > 0:
                print("⚠️ Hubo algunos errores durante la sincronización")
                print("   Revisa los logs para más detalles")
            
            # Verificar resultados
            final_stats = await db_service.get_statistics()
            total_synced = final_stats.get('active_products', 0)
            
            if total_synced > 0:
                print(f"✅ Sincronización completada: {total_synced} productos activos")
                return True
            else:
                print("❌ No se sincronizaron productos")
                return False
                
        except Exception as e:
            print(f"❌ Error en sincronización inicial: {e}")
            return False
    
    async def test_hybrid_search(self) -> bool:
        """Probar funcionalidad de búsqueda híbrida"""
        try:
            print("🔍 Probando búsqueda híbrida...")
            
            test_queries = [
                "cables eléctricos",
                "interruptores",
                "iluminación",
                "conectores",
                "protección eléctrica"
            ]
            
            successful_searches = 0
            
            for query in test_queries:
                try:
                    print(f"   Probando: '{query}'")
                    
                    # Generar embedding
                    embedding = await embedding_service.generate_embedding(query)
                    
                    # Búsqueda híbrida
                    results = await db_service.hybrid_search(
                        query_text=query,
                        query_embedding=embedding,
                        content_types=["product"],
                        limit=3
                    )
                    
                    if results:
                        print(f"     ✅ {len(results)} resultados encontrados")
                        # Mostrar el mejor resultado
                        best = results[0]
                        print(f"     📦 Mejor resultado: {best.get('title', 'Sin título')}")
                        print(f"     📊 Puntuación RRF: {best.get('rrf_score', 0):.3f}")
                        successful_searches += 1
                    else:
                        print(f"     ⚠️ Sin resultados")
                        
                except Exception as e:
                    print(f"     ❌ Error: {e}")
            
            print(f"\n📊 Pruebas de búsqueda: {successful_searches}/{len(test_queries)} exitosas")
            
            if successful_searches >= len(test_queries) // 2:  # Al menos 50% exitosas
                print("✅ Búsqueda híbrida funcionando correctamente")
                return True
            else:
                print("❌ Búsqueda híbrida no está funcionando adecuadamente")
                return False
                
        except Exception as e:
            print(f"❌ Error probando búsqueda híbrida: {e}")
            return False
    
    async def setup_webhooks(self) -> bool:
        """Configurar webhooks de WooCommerce"""
        try:
            print("🔗 Configurando webhooks...")
            
            # Verificar configuración de webhook secret
            webhook_secret = getattr(settings, 'WOOCOMMERCE_WEBHOOK_SECRET', '')
            
            if not webhook_secret:
                print("⚠️ WOOCOMMERCE_WEBHOOK_SECRET no configurado")
                print("   Configura la variable de entorno:")
                print("   WOOCOMMERCE_WEBHOOK_SECRET=tu_webhook_secret")
                print("   (Opcional, pero recomendado para seguridad)")
            else:
                print("✅ Webhook secret configurado")
            
            # Obtener estadísticas de webhooks
            webhook_stats = await webhook_handler.get_webhook_stats()
            
            print(f"📊 Configuración de webhooks:")
            print(f"   • Eventos soportados: {len(webhook_stats.get('supported_events', []))}")
            print(f"   • Secret configurado: {'Sí' if webhook_stats.get('webhook_secret_configured') else 'No'}")
            print(f"   • Estado: {webhook_stats.get('status', 'unknown')}")
            
            print("\n📋 Para completar la configuración de webhooks:")
            print("   1. Ve a tu panel de WooCommerce")
            print("   2. Navega a WooCommerce > Configuración > Avanzado > Webhooks")
            print("   3. Crea webhooks para los siguientes eventos:")
            
            for event in webhook_stats.get('supported_events', []):
                print(f"      • {event}")
            
            print(f"\n   4. URL del webhook: http://tu-dominio.com/api/webhooks/woocommerce")
            print(f"   5. Secret: {webhook_secret if webhook_secret else '(configurar WOOCOMMERCE_WEBHOOK_SECRET)'}")
            
            # Simular procesamiento de webhook para probar
            test_payload = {
                "id": 999999,
                "name": "Producto de Prueba",
                "status": "publish"
            }
            
            test_result = await webhook_handler.handle_webhook(
                event="product.updated",
                payload=test_payload
            )
            
            if test_result.get('status') == 'success':
                print("✅ Manejador de webhooks funcionando correctamente")
                return True
            else:
                print(f"⚠️ Problema con manejador de webhooks: {test_result}")
                return True  # No crítico para el setup
                
        except Exception as e:
            print(f"❌ Error configurando webhooks: {e}")
            return False
    
    async def final_tests(self) -> bool:
        """Pruebas finales del sistema completo"""
        try:
            print("🧪 Ejecutando pruebas finales...")
            
            # Test 1: Estadísticas del sistema
            print("   📊 Obteniendo estadísticas del sistema...")
            db_stats = await db_service.get_statistics()
            sync_status = await wc_sync_service.get_sync_status()
            
            print(f"     • Productos activos: {db_stats.get('active_products', 0)}")
            print(f"     • Categorías: {db_stats.get('categories', 0)}")
            print(f"     • Última sincronización: {sync_status.get('last_sync', 'Nunca')}")
            
            # Test 2: Búsqueda de producto específico
            print("   🔍 Probando búsqueda específica...")
            embedding = await embedding_service.generate_embedding("cable eléctrico")
            results = await db_service.hybrid_search(
                query_text="cable eléctrico",
                query_embedding=embedding,
                content_types=["product"],
                limit=1
            )
            
            if results:
                print(f"     ✅ Encontrado: {results[0].get('title', 'Sin título')}")
            else:
                print("     ⚠️ No se encontraron productos específicos")
            
            # Test 3: Rendimiento de embeddings
            print("   ⚡ Probando rendimiento de embeddings...")
            start_time = datetime.now()
            test_embedding = await embedding_service.generate_embedding("prueba de rendimiento")
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            print(f"     ⏱️ Tiempo de generación: {duration:.2f}s")
            
            if duration < 5.0:  # Menos de 5 segundos es aceptable
                print("     ✅ Rendimiento de embeddings adecuado")
            else:
                print("     ⚠️ Rendimiento de embeddings lento")
            
            print("✅ Pruebas finales completadas")
            return True
            
        except Exception as e:
            print(f"❌ Error en pruebas finales: {e}")
            return False
    
    async def _insert_basic_data(self):
        """Insertar datos básicos de la empresa"""
        basic_data = [
            {
                "content_type": "company_info",
                "title": "Información de la Empresa - Recambios Eléctricos",
                "content": """Somos una empresa especializada en recambios y componentes eléctricos.
                Ofrecemos una amplia gama de productos para instalaciones eléctricas residenciales,
                comerciales e industriales. Nuestro catálogo incluye cables, interruptores,
                conectores, protecciones eléctricas, iluminación y mucho más."""
            },
            {
                "content_type": "company_info", 
                "title": "Política de Devoluciones",
                "content": """Aceptamos devoluciones de productos en un plazo de 30 días desde la compra.
                Los productos deben estar en su estado original y sin usar. Las devoluciones
                por defecto de fábrica se aceptan sin restricciones de tiempo."""
            },
            {
                "content_type": "company_info",
                "title": "Métodos de Pago",
                "content": """Aceptamos los siguientes métodos de pago: tarjetas de crédito y débito,
                transferencias bancarias, PayPal y pago contra entrega. Todos los pagos
                son procesados de forma segura."""
            }
        ]
        
        for data in basic_data:
            embedding = await embedding_service.generate_embedding(data["content"])
            await db_service.insert_knowledge(
                content_type=data["content_type"],
                title=data["title"],
                content=data["content"],
                embedding=embedding
            )

async def main():
    """Función principal"""
    setup = Phase2Setup()
    success = await setup.run_setup()
    
    if success:
        print("\n🎯 PRÓXIMOS PASOS:")
        print("   1. Inicia el servidor: python app_v2.py")
        print("   2. Visita el dashboard: http://localhost:8000/")
        print("   3. Configura webhooks en WooCommerce")
        print("   4. Programa sincronizaciones periódicas")
        sys.exit(0)
    else:
        print("\n❌ CONFIGURACIÓN INCOMPLETA")
        print("   Revisa los errores y vuelve a ejecutar el script")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 