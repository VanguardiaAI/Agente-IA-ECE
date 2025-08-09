#!/usr/bin/env python3
"""
Script de diagnóstico para el error de knowledge documents en producción
"""

import asyncio
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_knowledge_service():
    """Probar el servicio de knowledge base"""
    try:
        # Importar después de configurar el path
        sys.path.insert(0, '/app' if Path('/app').exists() else '.')
        
        from services.knowledge_base import knowledge_service
        from services.database import db_service
        from services.embedding_service import embedding_service
        
        print("\n🔍 1. Verificando estado de servicios:")
        print(f"   - knowledge_service: {knowledge_service}")
        print(f"   - db_service inicializado: {db_service.initialized}")
        print(f"   - db_service pool: {db_service.pool}")
        print(f"   - embedding_service: {embedding_service}")
        print(f"   - knowledge_service.enabled: {knowledge_service.enabled}")
        
        print("\n🔍 2. Intentando inicializar knowledge_service:")
        if not db_service.initialized:
            print("   ⚠️  db_service no está inicializado, inicializando...")
            await db_service.initialize()
            
        await knowledge_service.initialize()
        print(f"   ✅ knowledge_service inicializado: {knowledge_service.enabled}")
        
        print("\n🔍 3. Probando actualización de documento:")
        test_file = Path("knowledge/store_info.md")
        if test_file.exists():
            print(f"   - Archivo existe: {test_file}")
            success = await knowledge_service.load_markdown_file(test_file, "general")
            print(f"   - Resultado de carga: {success}")
        else:
            print(f"   - ❌ Archivo no existe: {test_file}")
            
        print("\n🔍 4. Verificando tabla knowledge_base:")
        pool = db_service.pool
        if pool:
            async with pool.acquire() as conn:
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'knowledge_base'
                    )
                """)
                print(f"   - Tabla knowledge_base existe: {exists}")
                
                if exists:
                    count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_base")
                    print(f"   - Registros en knowledge_base: {count}")
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()

async def test_endpoint_directly():
    """Probar el endpoint directamente"""
    try:
        sys.path.insert(0, '/app' if Path('/app').exists() else '.')
        
        from api.admin.knowledge import update_document
        from api.admin.knowledge import KnowledgeUpdate
        
        print("\n🔍 5. Probando función update_document directamente:")
        
        # Simular request
        update = KnowledgeUpdate(
            content="# Test\nContenido de prueba",
            title="Test Document"
        )
        
        # Simular admin (sin autenticación real)
        fake_admin = {"id": 1, "username": "test"}
        
        # Intentar actualizar
        try:
            result = await update_document(
                filename="test.md",
                update=update,
                current_admin=fake_admin
            )
            print(f"   ✅ Resultado: {result}")
        except Exception as e:
            print(f"   ❌ Error en endpoint: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Error importando endpoint: {e}")

if __name__ == "__main__":
    print("🔧 Diagnóstico de Knowledge Service Error")
    print("=" * 50)
    asyncio.run(test_knowledge_service())
    asyncio.run(test_endpoint_directly())