#!/usr/bin/env python3
"""
Script de configuración para Fase 1: Sistema de Búsqueda Híbrida
Configura PostgreSQL con pgvector y crea la base de datos inicial
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.conversation_logger import conversation_logger
from services.embedding_service import embedding_service
from config.settings import settings
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_dependencies():
    """Verificar que todas las dependencias estén instaladas"""
    print("🔍 Verificando dependencias...")
    
    try:
        import asyncpg
        print("✅ asyncpg instalado")
    except ImportError:
        print("❌ asyncpg no instalado. Ejecuta: pip install asyncpg")
        return False
    
    try:
        import openai
        print("✅ openai instalado")
    except ImportError:
        print("❌ openai no instalado. Ejecuta: pip install openai")
        return False
    
    try:
        import numpy
        print("✅ numpy instalado")
    except ImportError:
        print("❌ numpy no instalado. Ejecuta: pip install numpy")
        return False
    
    return True

async def check_environment():
    """Verificar variables de entorno necesarias"""
    print("\n🔧 Verificando configuración...")
    
    required_vars = [
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not hasattr(settings, var) or not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("📝 Configura estas variables en tu archivo .env")
        return False
    
    print("✅ Variables de entorno configuradas")
    return True

async def test_postgresql_connection():
    """Probar conexión a PostgreSQL"""
    print("\n🐘 Probando conexión a PostgreSQL...")
    
    try:
        import asyncpg
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Verificar extensión vector
        result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        if not result:
            print("⚠️  Extensión pgvector no encontrada. Intentando instalar...")
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print("✅ Extensión pgvector instalada")
            except Exception as e:
                print(f"❌ Error instalando pgvector: {e}")
                print("📝 Instala pgvector manualmente: https://github.com/pgvector/pgvector")
                await conn.close()
                return False
        else:
            print("✅ Extensión pgvector disponible")
        
        await conn.close()
        print("✅ Conexión a PostgreSQL exitosa")
        return True
        
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        print("📝 Verifica que PostgreSQL esté corriendo y las credenciales sean correctas")
        return False

async def test_openai_connection():
    """Probar conexión a OpenAI"""
    print("\n🤖 Probando conexión a OpenAI...")
    
    try:
        success = await embedding_service.test_connection()
        if success:
            print("✅ Conexión a OpenAI exitosa")
            return True
        else:
            print("❌ Error conectando a OpenAI")
            return False
    except Exception as e:
        print(f"❌ Error probando OpenAI: {e}")
        print("📝 Verifica tu OPENAI_API_KEY")
        return False

async def initialize_database():
    """Inicializar base de datos y esquemas"""
    print("\n🏗️  Inicializando base de datos...")
    
    try:
        # Inicializar servicio principal
        await db_service.initialize()
        print("✅ Servicio de base de datos híbrida inicializado")
        
        # Inicializar logger de conversaciones
        await conversation_logger.initialize()
        print("✅ Logger de conversaciones inicializado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        return False

async def create_sample_data():
    """Crear datos de ejemplo para probar el sistema"""
    print("\n📝 Creando datos de ejemplo...")
    
    try:
        # Información de empresa de ejemplo
        company_info = [
            {
                "title": "Política de Devoluciones",
                "content": "Aceptamos devoluciones dentro de 30 días de la compra. Los productos deben estar en su estado original. Los gastos de envío de devolución corren por cuenta del cliente excepto en casos de productos defectuosos.",
                "category": "politicas"
            },
            {
                "title": "Horarios de Atención",
                "content": "Nuestro horario de atención al cliente es de lunes a viernes de 9:00 AM a 6:00 PM, y sábados de 9:00 AM a 2:00 PM. Estamos cerrados los domingos y días festivos.",
                "category": "atencion"
            },
            {
                "title": "Métodos de Pago",
                "content": "Aceptamos tarjetas de crédito (Visa, MasterCard, American Express), transferencias bancarias, y pagos en efectivo en nuestra tienda física. También ofrecemos financiamiento para compras mayores a $500.",
                "category": "pagos"
            },
            {
                "title": "Instalación de Productos Eléctricos",
                "content": "Ofrecemos servicio de instalación profesional para productos eléctricos complejos. Nuestros técnicos certificados pueden instalar paneles eléctricos, sistemas de iluminación, y motores industriales. El costo de instalación se cotiza por separado.",
                "category": "servicios"
            },
            {
                "title": "Garantías de Productos",
                "content": "Todos nuestros productos eléctricos vienen con garantía del fabricante. Los cables y conectores tienen 1 año de garantía, los motores 2 años, y los paneles eléctricos 3 años. Cubrimos defectos de fabricación y fallas prematuras.",
                "category": "garantias"
            }
        ]
        
        # Insertar información de empresa
        for info in company_info:
            embedding = await embedding_service.generate_company_info_embedding(info)
            await db_service.insert_knowledge(
                content_type="company_info",
                title=info["title"],
                content=info["content"],
                embedding=embedding,
                metadata={"category": info["category"]}
            )
        
        print(f"✅ Insertados {len(company_info)} registros de información de empresa")
        
        # Verificar estadísticas
        stats = await db_service.get_statistics()
        print(f"📊 Estadísticas de la base de conocimiento:")
        print(f"   - Total de entradas: {stats.get('total_entries', 0)}")
        print(f"   - Entradas activas: {stats.get('active_entries', 0)}")
        print(f"   - Tipos de contenido: {stats.get('content_types', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando datos de ejemplo: {e}")
        return False

async def test_hybrid_search():
    """Probar búsqueda híbrida"""
    print("\n🔍 Probando búsqueda híbrida...")
    
    try:
        # Probar búsqueda
        query = "política de devoluciones"
        query_embedding = await embedding_service.generate_embedding(query)
        
        results = await db_service.hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            limit=3
        )
        
        print(f"✅ Búsqueda híbrida exitosa - {len(results)} resultados encontrados")
        
        if results:
            print("📋 Resultados de ejemplo:")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result['title']}")
                print(f"      Tipo: {result['content_type']}")
                print(f"      Puntuación: {result.get('rrf_score', 0):.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando búsqueda híbrida: {e}")
        return False

async def cleanup():
    """Limpiar conexiones"""
    try:
        await db_service.close()
        await conversation_logger.close()
        print("✅ Conexiones cerradas correctamente")
    except:
        pass

async def main():
    """Función principal de configuración"""
    print("🚀 CONFIGURACIÓN FASE 1: Sistema de Búsqueda Híbrida")
    print("=" * 60)
    
    try:
        # Verificar dependencias
        if not await check_dependencies():
            return False
        
        # Verificar configuración
        if not await check_environment():
            return False
        
        # Probar conexiones
        if not await test_postgresql_connection():
            return False
        
        if not await test_openai_connection():
            return False
        
        # Inicializar base de datos
        if not await initialize_database():
            return False
        
        # Crear datos de ejemplo
        if not await create_sample_data():
            return False
        
        # Probar búsqueda
        if not await test_hybrid_search():
            return False
        
        print("\n🎉 FASE 1 CONFIGURADA EXITOSAMENTE")
        print("=" * 60)
        print("✅ PostgreSQL con pgvector configurado")
        print("✅ OpenAI embeddings funcionando")
        print("✅ Base de conocimiento inicializada")
        print("✅ Búsqueda híbrida operativa")
        print("\n📋 Próximos pasos:")
        print("   1. Ejecutar sincronización de productos WooCommerce")
        print("   2. Configurar webhooks en WooCommerce")
        print("   3. Integrar herramientas de búsqueda en FastMCP")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la configuración: {e}")
        return False
    
    finally:
        await cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 