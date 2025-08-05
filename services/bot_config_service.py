"""
Servicio para gestionar configuraciones del bot
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.database import db_service

logger = logging.getLogger(__name__)

class BotConfigService:
    """Servicio para manejar configuraciones del chatbot"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timestamp = None
        self.cache_ttl = 300  # 5 minutos de cache
        
    async def initialize(self):
        """Inicializar el servicio y cargar configuraciones"""
        try:
            await self.load_all_settings()
            logger.info("✅ Servicio de configuración del bot inicializado")
            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando servicio de configuración: {e}")
            return False
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Obtener una configuración específica"""
        try:
            # Verificar cache
            if self._is_cache_valid():
                if key in self.cache:
                    return self.cache[key]
            else:
                await self.load_all_settings()
            
            pool = db_service.pool
            if not pool:
                return default
                
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT value FROM bot_settings WHERE key = $1
                """, key)
                
                if result:
                    value = json.loads(result['value'])
                    self.cache[key] = value
                    return value
                    
            return default
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración {key}: {e}")
            return default
    
    async def set_setting(self, key: str, value: Any, category: str = 'general', 
                          description: str = None, admin_id: int = None) -> bool:
        """Establecer o actualizar una configuración"""
        try:
            pool = db_service.pool
            if not pool:
                return False
                
            async with pool.acquire() as conn:
                # Convertir valor a JSON
                json_value = json.dumps(value)
                
                # Upsert la configuración
                await conn.execute("""
                    INSERT INTO bot_settings (key, value, category, description, updated_by, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        category = EXCLUDED.category,
                        description = COALESCE(EXCLUDED.description, bot_settings.description),
                        updated_by = EXCLUDED.updated_by,
                        updated_at = NOW()
                """, key, json_value, category, description, admin_id)
                
                # Actualizar cache
                self.cache[key] = value
                
                logger.info(f"✅ Configuración actualizada: {key}")
                return True
                
        except Exception as e:
            logger.error(f"Error estableciendo configuración {key}: {e}")
            return False
    
    async def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """Obtener todas las configuraciones de una categoría"""
        try:
            pool = db_service.pool
            if not pool:
                return {}
                
            async with pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT key, value, description 
                    FROM bot_settings 
                    WHERE category = $1
                    ORDER BY key
                """, category)
                
                settings = {}
                for row in results:
                    settings[row['key']] = {
                        'value': json.loads(row['value']),
                        'description': row['description']
                    }
                    
                return settings
                
        except Exception as e:
            logger.error(f"Error obteniendo configuraciones de categoría {category}: {e}")
            return {}
    
    async def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """Obtener todas las configuraciones agrupadas por categoría"""
        try:
            pool = db_service.pool
            if not pool:
                return {}
                
            async with pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT key, value, category, description, updated_at
                    FROM bot_settings
                    ORDER BY category, key
                """)
                
                settings = {}
                for row in results:
                    category = row['category']
                    if category not in settings:
                        settings[category] = {}
                    
                    settings[category][row['key']] = {
                        'value': json.loads(row['value']),
                        'description': row['description'],
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    }
                    
                return settings
                
        except Exception as e:
            logger.error(f"Error obteniendo todas las configuraciones: {e}")
            return {}
    
    async def load_all_settings(self):
        """Cargar todas las configuraciones en cache"""
        try:
            pool = db_service.pool
            if not pool:
                return
                
            async with pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT key, value FROM bot_settings
                """)
                
                self.cache = {}
                for row in results:
                    self.cache[row['key']] = json.loads(row['value'])
                
                self.cache_timestamp = datetime.now()
                logger.info(f"✅ {len(self.cache)} configuraciones cargadas en cache")
                
        except Exception as e:
            logger.error(f"Error cargando configuraciones: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Verificar si el cache es válido"""
        if not self.cache_timestamp:
            return False
        
        age = (datetime.now() - self.cache_timestamp).total_seconds()
        return age < self.cache_ttl
    
    async def reset_to_defaults(self, admin_id: int = None) -> bool:
        """Restablecer todas las configuraciones a valores por defecto"""
        try:
            defaults = {
                'bot_name': 'Eva',
                'welcome_message': '¡Hola! Soy Eva, tu asistente virtual de El Corte Eléctrico. ¿En qué puedo ayudarte hoy?',
                'company_name': 'El Corte Eléctrico',
                'response_style': 'professional',
                'response_length': 'balanced',
                'language': 'es',
                'business_hours': {
                    'start': '09:00',
                    'end': '19:00',
                    'timezone': 'Europe/Madrid',
                    'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                },
                'out_of_hours_message': 'Gracias por contactarnos. Nuestro horario de atención es de lunes a viernes de 9:00 a 19:00. Te responderemos lo antes posible.',
                'max_products_display': 5,
                'search_threshold': 0.3,
                'vector_weight': 0.6,
                'text_weight': 0.4,
                'llm_model': 'gpt-4o-mini',
                'llm_temperature': 0.1,
                'llm_max_tokens': 2000,
                'enable_escalation': True,
                'escalation_keywords': ['hablar con humano', 'agente real', 'persona real', 'operador', 'atención humana'],
                'enable_order_lookup': True,
                'enable_product_search': True,
                'enable_knowledge_base': True
            }
            
            categories = {
                'bot_name': 'identity',
                'welcome_message': 'identity',
                'company_name': 'identity',
                'response_style': 'personality',
                'response_length': 'personality',
                'language': 'general',
                'business_hours': 'general',
                'out_of_hours_message': 'general',
                'max_products_display': 'search',
                'search_threshold': 'search',
                'vector_weight': 'search',
                'text_weight': 'search',
                'llm_model': 'ai',
                'llm_temperature': 'ai',
                'llm_max_tokens': 'ai',
                'enable_escalation': 'features',
                'escalation_keywords': 'features',
                'enable_order_lookup': 'features',
                'enable_product_search': 'features',
                'enable_knowledge_base': 'features'
            }
            
            for key, value in defaults.items():
                category = categories.get(key, 'general')
                await self.set_setting(key, value, category, admin_id=admin_id)
            
            # Limpiar cache para forzar recarga
            self.cache = {}
            self.cache_timestamp = None
            
            logger.info("✅ Configuraciones restablecidas a valores por defecto")
            return True
            
        except Exception as e:
            logger.error(f"Error restableciendo configuraciones: {e}")
            return False
    
    async def export_settings(self) -> Dict[str, Any]:
        """Exportar todas las configuraciones para backup"""
        try:
            settings = await self.get_all_settings()
            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'settings': settings
            }
            return export_data
            
        except Exception as e:
            logger.error(f"Error exportando configuraciones: {e}")
            return {}
    
    async def import_settings(self, import_data: Dict[str, Any], admin_id: int = None) -> bool:
        """Importar configuraciones desde backup"""
        try:
            if 'settings' not in import_data:
                logger.error("Formato de importación inválido")
                return False
            
            settings = import_data['settings']
            
            for category, category_settings in settings.items():
                for key, setting_data in category_settings.items():
                    value = setting_data.get('value')
                    description = setting_data.get('description')
                    
                    await self.set_setting(
                        key, value, category, 
                        description=description, 
                        admin_id=admin_id
                    )
            
            # Limpiar cache para forzar recarga
            self.cache = {}
            self.cache_timestamp = None
            
            logger.info("✅ Configuraciones importadas exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error importando configuraciones: {e}")
            return False

# Instancia global del servicio
bot_config_service = BotConfigService()