#!/usr/bin/env python3
"""
Script para cargar la base de conocimientos desde archivos markdown
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.knowledge_base import knowledge_service
from services.database import db_service
from services.embedding_service import embedding_service
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_knowledge_search(query: str):
    """Probar búsqueda en la base de conocimientos"""
    logger.info(f"\n🔍 Buscando: '{query}'")
    results = await knowledge_service.search_knowledge(query, limit=3)
    
    if not results:
        logger.info("❌ No se encontraron resultados")
        return
    
    for i, result in enumerate(results, 1):
        logger.info(f"\n📄 Resultado {i}:")
        logger.info(f"   Título: {result['title']}")
        logger.info(f"   Tipo: {result['doc_type']}")
        logger.info(f"   Score: {result['score']:.3f}")
        logger.info(f"   Contenido: {result['content'][:200]}...")

async def main():
    """Función principal"""
    try:
        # Inicializar servicios
        logger.info("🚀 Inicializando servicios...")
        await db_service.initialize()
        await embedding_service.initialize()
        await knowledge_service.initialize()
        
        # Cargar todos los documentos
        logger.info("\n📚 Cargando base de conocimientos...")
        results = await knowledge_service.load_all_documents()
        logger.info(f"✅ Carga completada: {results}")
        
        # Realizar pruebas de búsqueda
        logger.info("\n🧪 Ejecutando pruebas de búsqueda...")
        
        test_queries = [
            "política de envíos gratis",
            "cómo devolver un producto",
            "horario de atención",
            "garantía de productos",
            "métodos de pago disponibles",
            "instalación eléctrica",
            "certificaciones de la empresa"
        ]
        
        for query in test_queries:
            await test_knowledge_search(query)
            await asyncio.sleep(0.5)  # Pequeña pausa entre búsquedas
        
        # Mostrar estadísticas
        pool = db_service.pool
        if pool:
            async with pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_base")
                types = await conn.fetch("""
                    SELECT content_type, COUNT(*) as count 
                    FROM knowledge_base 
                    WHERE is_active = true
                    GROUP BY content_type
                """)
                
                logger.info(f"\n📊 Estadísticas finales:")
                logger.info(f"   Total documentos/chunks: {count}")
                logger.info(f"   Por tipo:")
                for row in types:
                    logger.info(f"     - {row['content_type']}: {row['count']}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        # Cerrar conexiones
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(main())