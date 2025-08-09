#!/usr/bin/env python3
"""
Script para probar el endpoint de knowledge document directamente y capturar el error real
"""

import asyncio
import json
import sys
from pathlib import Path

# Agregar path de la aplicación
sys.path.insert(0, '/app' if Path('/app').exists() else '.')

async def test_endpoint():
    try:
        from api.admin.knowledge import update_document, KnowledgeUpdate
        
        print("🔍 Probando endpoint de knowledge document...")
        
        # Crear update request
        update = KnowledgeUpdate(
            content="# Store Info\nInformación de la tienda actualizada",
            title="Store Info"
        )
        
        # Mock admin user
        mock_admin = {"id": 1, "username": "admin"}
        
        print(f"📋 Intentando actualizar: store_info.md")
        print(f"   - Content length: {len(update.content)}")
        print(f"   - Title: {update.title}")
        
        # Intentar la actualización
        result = await update_document(
            filename="store_info.md",
            update=update,
            current_admin=mock_admin
        )
        
        print(f"✅ Success: {result}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"   Tipo: {type(e)}")
        import traceback
        print("\n📋 Traceback completo:")
        traceback.print_exc()

async def test_services():
    try:
        from services.knowledge_singleton import get_knowledge_service
        from services.database import db_service
        from services.embedding_service import embedding_service
        
        print("\n🔍 Verificando servicios...")
        print(f"   - db_service initialized: {db_service.initialized}")
        print(f"   - embedding_service initialized: {getattr(embedding_service, 'initialized', False)}")
        
        # Intentar obtener knowledge service
        knowledge_service = await get_knowledge_service()
        print(f"   - knowledge_service: {knowledge_service}")
        print(f"   - knowledge_service.enabled: {knowledge_service.enabled}")
        
        # Verificar archivo
        file_path = Path("knowledge/store_info.md")
        print(f"   - Archivo existe: {file_path.exists()}")
        if file_path.exists():
            print(f"   - Tamaño: {file_path.stat().st_size} bytes")
        
    except Exception as e:
        print(f"❌ Error en servicios: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Test Knowledge Endpoint")
    print("=" * 40)
    asyncio.run(test_services())
    asyncio.run(test_endpoint())