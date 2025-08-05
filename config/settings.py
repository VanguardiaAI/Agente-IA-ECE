"""
Configuraciones del sistema para el servidor MCP de Tienda de Recambios Eléctricos
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings(BaseSettings):
    """Configuraciones de la aplicación"""
    
    # Configuración de WooCommerce
    WOOCOMMERCE_API_URL: str
    WOOCOMMERCE_CONSUMER_KEY: str
    WOOCOMMERCE_CONSUMER_SECRET: str
    WOOCOMMERCE_WEBHOOK_SECRET: Optional[str] = None
    
    # Configuración de PostgreSQL (reemplaza MongoDB)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eva_db"
    POSTGRES_USER: str = "eva_user"
    POSTGRES_PASSWORD: str
    DATABASE_URL: Optional[str] = None
    
    # Configuración de OpenAI para embeddings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 8192
    
    # Configuración del servidor MCP
    MCP_SERVER_NAME: str = "Customer Service Assistant"
    MCP_HOST: str = "localhost"
    MCP_PORT: int = 8000
    
    # Configuración general
    DEBUG: bool = False
    ENABLE_CONVERSATION_LOGGING: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Configuración de seguridad (opcional)
    JWT_SECRET_KEY: Optional[str] = None
    CORS_ORIGINS: Optional[str] = None
    
    # Configuración de rate limiting (opcional)
    RATE_LIMIT_REQUESTS: Optional[int] = None
    RATE_LIMIT_WINDOW: Optional[int] = None
    
    # Configuración de monitoreo (opcional)
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = False
    
    # Configuración de WhatsApp 360Dialog
    WHATSAPP_360DIALOG_API_KEY: Optional[str] = None
    WHATSAPP_360DIALOG_API_URL: str = "https://waba-v2.360dialog.io"
    WHATSAPP_PHONE_NUMBER: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    
    # Configuración de plantillas de WhatsApp
    WHATSAPP_CART_RECOVERY_TEMPLATE: str = "carrito_recuperacion_descuento"
    WHATSAPP_ORDER_CONFIRMATION_TEMPLATE: str = "order_confirmation"
    WHATSAPP_WELCOME_TEMPLATE: str = "welcome_message"
    
    @field_validator('WOOCOMMERCE_API_URL')
    @classmethod
    def validate_woocommerce_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('WOOCOMMERCE_API_URL debe comenzar con http:// o https://')
        return v.rstrip('/')
    
    @field_validator('WOOCOMMERCE_CONSUMER_KEY', 'WOOCOMMERCE_CONSUMER_SECRET')
    @classmethod
    def validate_woocommerce_keys(cls, v):
        if not v:
            raise ValueError('Las claves de WooCommerce son requeridas')
        return v
    
    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def assemble_database_url(cls, v, info):
        if isinstance(v, str):
            return v
        values = info.data
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_HOST')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
    
    @property
    def woocommerce_api_url(self) -> str:
        """URL completa de la API de WooCommerce"""
        return self.WOOCOMMERCE_API_URL
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

# Instancia global de configuración
settings = Settings()

# Configuración de categorías de productos eléctricos
ELECTRICAL_CATEGORIES = {
    "cables": ["cables", "alambres", "conductores", "wires"],
    "conectores": ["conectores", "terminales", "bornes", "connectors"],
    "fusibles": ["fusibles", "breakers", "protecciones", "fuses"],
    "interruptores": ["interruptores", "switches", "conmutadores"],
    "enchufes": ["enchufes", "tomas", "outlets", "plugs"],
    "motores": ["motores", "motors", "bombas", "ventiladores"],
    "transformadores": ["transformadores", "trafo", "transformers"],
    "iluminacion": ["bombillas", "led", "lámparas", "focos", "lighting"],
    "herramientas": ["herramientas", "tools", "multímetros", "pinzas"],
    "automatizacion": ["relés", "contactores", "temporizadores", "plc"]
}

# Configuración de búsqueda híbrida
HYBRID_SEARCH_CONFIG = {
    "vector_weight": 0.6,  # Peso de búsqueda semántica
    "text_weight": 0.4,    # Peso de búsqueda de texto
    "min_similarity": 0.3,  # Similitud mínima para vectores
    "max_results": 30,      # Máximo resultados antes de fusión
    "final_limit": 10       # Límite final de resultados
}

# Configuración de embeddings
EMBEDDING_CONFIG = {
    "chunk_size": 1000,     # Tamaño de chunks para textos largos
    "chunk_overlap": 200,   # Solapamiento entre chunks
    "batch_size": 100       # Tamaño de lote para procesamiento
}

# Configuración de especificaciones técnicas comunes
TECHNICAL_SPECS = {
    "voltage": ["voltaje", "tensión", "V", "volts"],
    "current": ["corriente", "amperaje", "A", "amps"],
    "power": ["potencia", "watts", "W", "kW"],
    "frequency": ["frecuencia", "Hz", "hertz"],
    "phase": ["fase", "monofásico", "trifásico", "bifásico"],
    "protection": ["protección", "IP", "grado", "hermético"],
    "material": ["material", "cobre", "aluminio", "PVC", "caucho"],
    "certification": ["certificación", "CE", "UL", "IEC", "norma"]
} 