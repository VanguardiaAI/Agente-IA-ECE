-- Script simplificado para crear las tablas de administración
-- Sin vistas complejas para evitar errores de compatibilidad

-- Tabla de usuarios administradores
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de configuraciones del bot
CREATE TABLE IF NOT EXISTS bot_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    updated_by INTEGER REFERENCES admin_users(id),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de métricas de conversaciones
CREATE TABLE IF NOT EXISTS conversation_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    hour INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    avg_response_time FLOAT,
    satisfaction_avg FLOAT,
    popular_topics JSONB,
    platform VARCHAR(50) DEFAULT 'whatsapp',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, hour, platform)
);

-- Tabla de logs de actividad del admin
CREATE TABLE IF NOT EXISTS admin_activity_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admin_users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de sesiones de admin
CREATE TABLE IF NOT EXISTS admin_sessions (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admin_users(id),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);
CREATE INDEX IF NOT EXISTS idx_bot_settings_category ON bot_settings(category);
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_date ON conversation_metrics(date);
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_platform ON conversation_metrics(platform);
CREATE INDEX IF NOT EXISTS idx_admin_activity_logs_admin_id ON admin_activity_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_activity_logs_created_at ON admin_activity_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_token ON admin_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires ON admin_sessions(expires_at);

-- Insertar configuraciones iniciales del bot (solo si no existen)
INSERT INTO bot_settings (key, value, category, description) VALUES
    ('bot_name', '"Eva"', 'identity', 'Nombre del asistente virtual'),
    ('welcome_message', '"¡Hola! Soy Eva, tu asistente virtual de El Corte Eléctrico. ¿En qué puedo ayudarte hoy?"', 'identity', 'Mensaje de bienvenida'),
    ('company_name', '"El Corte Eléctrico"', 'identity', 'Nombre de la empresa'),
    ('response_style', '"professional"', 'personality', 'Estilo de respuesta: professional, friendly, casual'),
    ('response_length', '"balanced"', 'personality', 'Longitud de respuestas: brief, balanced, detailed'),
    ('language', '"es"', 'general', 'Idioma principal del bot'),
    ('business_hours', '{"start": "09:00", "end": "19:00", "timezone": "Europe/Madrid", "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}', 'general', 'Horario de atención'),
    ('out_of_hours_message', '"Gracias por contactarnos. Nuestro horario de atención es de lunes a viernes de 9:00 a 19:00. Te responderemos lo antes posible."', 'general', 'Mensaje fuera de horario'),
    ('max_products_display', '5', 'search', 'Número máximo de productos a mostrar'),
    ('search_threshold', '0.3', 'search', 'Umbral mínimo de similitud para búsquedas'),
    ('vector_weight', '0.6', 'search', 'Peso de búsqueda vectorial (0-1)'),
    ('text_weight', '0.4', 'search', 'Peso de búsqueda de texto (0-1)'),
    ('llm_model', '"gpt-4o-mini"', 'ai', 'Modelo de lenguaje a usar'),
    ('llm_temperature', '0.1', 'ai', 'Temperatura del modelo (0-1)'),
    ('llm_max_tokens', '2000', 'ai', 'Máximo de tokens en respuesta'),
    ('enable_escalation', 'true', 'features', 'Habilitar escalamiento a humano'),
    ('escalation_keywords', '["hablar con humano", "agente real", "persona real", "operador", "atención humana"]', 'features', 'Palabras clave para escalamiento'),
    ('enable_order_lookup', 'true', 'features', 'Habilitar búsqueda de pedidos'),
    ('enable_product_search', 'true', 'features', 'Habilitar búsqueda de productos'),
    ('enable_knowledge_base', 'true', 'features', 'Habilitar base de conocimiento')
ON CONFLICT (key) DO NOTHING;