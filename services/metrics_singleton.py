"""
Singleton para MetricsService que garantiza una sola instancia por worker
"""

import asyncio
from typing import Optional
from services.metrics_service import MetricsService
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MetricsSingleton:
    """Singleton para manejar la instancia de MetricsService"""
    
    _instance: Optional[MetricsService] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls) -> MetricsService:
        """Obtener la instancia única de MetricsService, creándola si es necesario"""
        if cls._instance is None:
            async with cls._lock:
                # Double-check pattern
                if cls._instance is None:
                    logger.info("Creando nueva instancia de MetricsService...")
                    cls._instance = MetricsService(settings.DATABASE_URL)
                    await cls._instance.initialize()
                    logger.info("MetricsService inicializado correctamente en este worker")
        
        return cls._instance
    
    @classmethod
    async def close(cls):
        """Cerrar la instancia si existe"""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None

# Función helper para obtener el servicio
async def get_metrics_service() -> MetricsService:
    """Obtener la instancia de MetricsService"""
    return await MetricsSingleton.get_instance()