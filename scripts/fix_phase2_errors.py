#!/usr/bin/env python3
"""
Script para solucionar errores comunes de la Fase 2
Diagnostica y corrige problemas de configuración
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path  
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import HybridDatabaseService
from services.embedding_service import EmbeddingService
from services.woocommerce import WooCommerceService
from config.settings import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_embedding_service():
    """Corregir servicio de embeddings"""
    print("🔧 1. Corrigiendo servicio de embeddings...")
    
    try:
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        
        if embedding_service.initialized:
            print("   ✅ Servicio de embeddings inicializado correctamente")
            
            # Prueba rápida
            test_embedding = await embedding_service.generate_embedding("test")
            if test_embedding and len(test_embedding) == 1536:
                print("   ✅ Generación de embeddings funcionando")
                return True
            else:
                print("   ❌ Error en generación de embeddings")
                return False
        else:
            print("   ❌ No se pudo inicializar el servicio de embeddings")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def fix_database_service():
    """Corregir servicio de base de datos"""
    print("🔧 2. Corrigiendo servicio de base de datos...")
    
    try:
        db_service = HybridDatabaseService()
        await db_service.initialize()
        
        if db_service.initialized:
            print("   ✅ Base de datos inicializada correctamente")
            
            # Verificar esquema
            stats = await db_service.get_statistics()
            print(f"   📊 Entradas existentes: {stats.get('active_entries', 0)}")
            
            return True
        else:
            print("   ❌ No se pudo inicializar la base de datos")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def check_woocommerce_config():
    """Verificar configuración de WooCommerce"""
    print("🔧 3. Verificando configuración de WooCommerce...")
    
    # Verificar variables de entorno
    required_vars = [
        'WOOCOMMERCE_API_URL',
        'WOOCOMMERCE_CONSUMER_KEY', 
        'WOOCOMMERCE_CONSUMER_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not hasattr(settings, var.lower()) or not getattr(settings, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"   ❌ Variables faltantes: {', '.join(missing_vars)}")
        print("\n   📝 Configuración requerida en .env:")
        print("   WOOCOMMERCE_API_URL=https://elcorteelectrico.com/wp-json/wc/v3")
        print("   WOOCOMMERCE_CONSUMER_KEY=ck_tu_consumer_key_aqui")
        print("   WOOCOMMERCE_CONSUMER_SECRET=cs_tu_consumer_secret_aqui")
        print("\n   🔗 Para obtener las credenciales:")
        print("   1. Ve a WordPress Admin > WooCommerce > Configuración > Avanzado > API REST")
        print("   2. Crea nueva clave API con permisos 'Lectura/Escritura'")
        print("   3. Copia Consumer Key y Consumer Secret")
        return False
    
    # Probar conexión
    try:
        wc_service = WooCommerceService()
        categories = await wc_service.get_product_categories(per_page=1)
        
        if categories is not None:
            print("   ✅ Conexión WooCommerce exitosa")
            print(f"   🏪 URL: {settings.woocommerce_api_url}")
            return True
        else:
            print("   ❌ Error de autenticación con WooCommerce")
            print("   💡 Verifica que las credenciales sean correctas")
            return False
            
    except Exception as e:
        print(f"   ❌ Error conectando con WooCommerce: {e}")
        if "401" in str(e):
            print("   💡 Error 401: Credenciales incorrectas")
        elif "404" in str(e):
            print("   💡 Error 404: URL de API incorrecta")
        return False

async def insert_test_data():
    """Insertar datos de prueba si no existen"""
    print("🔧 4. Insertando datos de prueba...")
    
    try:
        # Reutilizar servicios ya inicializados
        db_service = HybridDatabaseService()
        await db_service.initialize()
        
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        
        # Verificar si ya hay datos
        stats = await db_service.get_statistics()
        if stats.get('active_entries', 0) > 0:
            print(f"   ℹ️ Ya existen {stats.get('active_entries', 0)} entradas")
            return True
        
        # Datos básicos de empresa
        company_data = [
            {
                "title": "Política de Devoluciones",
                "content": "Aceptamos devoluciones dentro de 30 días de la compra. Los productos deben estar en condición original. Contacta nuestro servicio al cliente para iniciar el proceso."
            },
            {
                "title": "Métodos de Pago",
                "content": "Aceptamos tarjetas de crédito, débito, transferencias bancarias y pago contra entrega. Todos los pagos son procesados de forma segura."
            },
            {
                "title": "Envíos y Entregas",
                "content": "Realizamos envíos a toda España. Tiempo de entrega: 2-5 días laborables. Envío gratuito en pedidos superiores a 50€."
            },
            {
                "title": "Productos Eléctricos",
                "content": "Especialistas en recambios eléctricos: cables, interruptores, enchufes, iluminación, protección eléctrica, automatización y material de instalación."
            },
            {
                "title": "Soporte Técnico",
                "content": "Nuestro equipo técnico está disponible para asesorarte en la selección de productos eléctricos. Consultas técnicas gratuitas."
            }
        ]
        
        inserted = 0
        for data in company_data:
            try:
                # Generar embedding
                embedding = await embedding_service.generate_embedding(
                    f"{data['title']} {data['content']}"
                )
                
                # Insertar en base de datos
                await db_service.upsert_knowledge(
                    content_type="company_info",
                    title=data['title'],
                    content=data['content'],
                    embedding=embedding,
                    external_id=f"info_{inserted + 1}",
                    metadata={"source": "setup", "category": "empresa"}
                )
                
                inserted += 1
                
            except Exception as e:
                print(f"   ⚠️ Error insertando '{data['title']}': {e}")
        
        print(f"   ✅ {inserted} entradas de datos básicos insertadas")
        return inserted > 0
        
    except Exception as e:
        print(f"   ❌ Error insertando datos de prueba: {e}")
        return False

async def test_hybrid_search():
    """Probar búsqueda híbrida"""
    print("🔧 5. Probando búsqueda híbrida...")
    
    try:
        # Reutilizar servicios ya inicializados
        db_service = HybridDatabaseService()
        await db_service.initialize()
        
        embedding_service = EmbeddingService()
        await embedding_service.initialize()
        
        # Prueba de búsqueda
        test_query = "política de devoluciones"
        print(f"   🔍 Buscando: '{test_query}'")
        
        # Generar embedding
        embedding = await embedding_service.generate_embedding(test_query)
        
        # Búsqueda híbrida
        results = await db_service.hybrid_search(
            query_text=test_query,
            query_embedding=embedding,
            limit=3
        )
        
        if results:
            print(f"   ✅ {len(results)} resultados encontrados")
            for i, result in enumerate(results[:2], 1):
                print(f"      {i}. {result.get('title', 'Sin título')} (score: {result.get('score', 0):.4f})")
            return True
        else:
            print("   ⚠️ No se encontraron resultados")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en búsqueda híbrida: {e}")
        return False

async def main():
    """Función principal de corrección"""
    print("🔧 CORRECCIÓN DE ERRORES FASE 2")
    print("=" * 50)
    
    fixes_applied = 0
    total_fixes = 5
    
    # 1. Corregir servicio de embeddings
    if await fix_embedding_service():
        fixes_applied += 1
    
    # 2. Corregir servicio de base de datos
    if await fix_database_service():
        fixes_applied += 1
    
    # 3. Verificar WooCommerce
    if await check_woocommerce_config():
        fixes_applied += 1
    
    # 4. Insertar datos de prueba
    if await insert_test_data():
        fixes_applied += 1
    
    # 5. Probar búsqueda híbrida
    if await test_hybrid_search():
        fixes_applied += 1
    
    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE CORRECCIONES")
    print("=" * 50)
    print(f"✅ Correcciones exitosas: {fixes_applied}/{total_fixes}")
    print(f"❌ Problemas pendientes: {total_fixes - fixes_applied}")
    
    if fixes_applied >= 4:  # WooCommerce puede fallar por credenciales
        print("\n🎉 ¡SISTEMA BÁSICO FUNCIONANDO!")
        print("\n🔄 Próximos pasos:")
        if fixes_applied < total_fixes:
            print("   1. Configura las credenciales de WooCommerce en .env")
            print("   2. Ejecuta: python scripts/test_woocommerce.py")
        print("   3. Ejecuta: python scripts/setup_phase2.py")
        print("   4. Inicia la aplicación: python app_v2.py")
    else:
        print("\n❌ PROBLEMAS CRÍTICOS DETECTADOS")
        print("   Revisa los errores arriba y configura correctamente:")
        print("   • Variables de entorno en .env")
        print("   • Conexión a PostgreSQL")
        print("   • API Key de OpenAI")

if __name__ == "__main__":
    asyncio.run(main()) 