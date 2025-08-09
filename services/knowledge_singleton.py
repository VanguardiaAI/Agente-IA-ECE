"""
Singleton para KnowledgeBaseService en entornos multi-worker
"""
import asyncio
from typing import Optional
import logging

from services.knowledge_base import KnowledgeBaseService
from services.database import db_service
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class KnowledgeSingleton:
    """Singleton para asegurar una única instancia de KnowledgeBaseService por worker"""
    _instance: Optional[KnowledgeBaseService] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls) -> KnowledgeBaseService:
        """Obtener o crear la instancia única de KnowledgeBaseService"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    # Asegurar que los servicios dependientes estén inicializados
                    if not db_service.initialized:
                        await db_service.initialize()
                    
                    if not embedding_service.initialized:
                        await embedding_service.initialize()
                    
                    # Crear e inicializar KnowledgeBaseService
                    cls._instance = KnowledgeBaseService()
                    await cls._instance.initialize()
                    
                    logger.info("✅ KnowledgeBaseService singleton creado")
        
        return cls._instance

async def get_knowledge_service() -> KnowledgeBaseService:
    """Función helper para obtener el servicio de knowledge base"""
    return await KnowledgeSingleton.get_instance()