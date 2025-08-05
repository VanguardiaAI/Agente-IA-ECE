-- Tablas para el sistema de métricas y análisis

-- Tabla de conversaciones (con retención de 30 días)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL, -- 'wordpress', 'whatsapp', 'test'
    channel_details JSONB DEFAULT '{}', -- Detalles específicos del canal
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'ended', 'abandoned'
    messages_count INTEGER DEFAULT 0,
    user_messages_count INTEGER DEFAULT 0,
    bot_messages_count INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER, -- Tiempo promedio de respuesta en milisegundos
    user_satisfaction INTEGER, -- 1-5 rating opcional
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índice en conversation_id para foreign keys
CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);

-- Tabla de mensajes individuales (con retención de 7 días para detalles)
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL,
    message_id VARCHAR(100) UNIQUE,
    sender_type VARCHAR(20) NOT NULL, -- 'user', 'bot', 'system'
    content TEXT,
    intent VARCHAR(100), -- Intención detectada
    entities JSONB DEFAULT '[]', -- Entidades extraídas
    confidence FLOAT, -- Confianza del modelo
    response_time_ms INTEGER, -- Tiempo de respuesta
    tools_used JSONB DEFAULT '[]', -- Herramientas MCP utilizadas
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

-- Tabla de métricas agregadas por hora (retención permanente)
CREATE TABLE IF NOT EXISTS metrics_hourly (
    id SERIAL PRIMARY KEY,
    hour_timestamp TIMESTAMP NOT NULL,
    platform VARCHAR(50) NOT NULL,
    total_conversations INTEGER DEFAULT 0,
    new_conversations INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    avg_messages_per_conversation FLOAT DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    successful_resolutions INTEGER DEFAULT 0,
    abandoned_conversations INTEGER DEFAULT 0,
    peak_concurrent_conversations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(hour_timestamp, platform)
);

-- Tabla de métricas diarias (retención permanente)
CREATE TABLE IF NOT EXISTS metrics_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    platform VARCHAR(50) NOT NULL,
    total_conversations INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    avg_messages_per_conversation FLOAT DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    avg_session_duration_minutes FLOAT DEFAULT 0,
    successful_resolutions INTEGER DEFAULT 0,
    abandoned_conversations INTEGER DEFAULT 0,
    user_satisfaction_avg FLOAT,
    peak_hour INTEGER, -- Hora con más actividad (0-23)
    peak_conversations INTEGER, -- Número de conversaciones en hora pico
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, platform)
);

-- Tabla de temas y consultas populares
CREATE TABLE IF NOT EXISTS popular_topics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    topic VARCHAR(200) NOT NULL,
    category VARCHAR(100), -- 'product', 'order', 'support', 'faq'
    count INTEGER DEFAULT 1,
    sample_queries JSONB DEFAULT '[]', -- Ejemplos de consultas
    avg_resolution_time_minutes FLOAT,
    success_rate FLOAT, -- Porcentaje de resolución exitosa
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, topic)
);

-- Tabla de eventos especiales (errores, eventos importantes)
CREATE TABLE IF NOT EXISTS metric_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- 'error', 'milestone', 'alert'
    severity VARCHAR(20) DEFAULT 'info', -- 'info', 'warning', 'error', 'critical'
    title VARCHAR(200),
    description TEXT,
    platform VARCHAR(50),
    conversation_id VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de rendimiento de herramientas MCP
CREATE TABLE IF NOT EXISTS tool_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    avg_execution_time_ms INTEGER DEFAULT 0,
    error_messages JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, tool_name)
);

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_platform ON conversations(platform);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON conversations(started_at);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON conversation_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_intent ON conversation_messages(intent);

CREATE INDEX IF NOT EXISTS idx_metrics_hourly_timestamp ON metrics_hourly(hour_timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_daily_date ON metrics_daily(date);
CREATE INDEX IF NOT EXISTS idx_popular_topics_date ON popular_topics(date);
CREATE INDEX IF NOT EXISTS idx_metric_events_created_at ON metric_events(created_at);

-- Vista para estadísticas rápidas del dashboard
CREATE OR REPLACE VIEW dashboard_stats AS
SELECT 
    (SELECT COUNT(*) FROM conversations WHERE DATE(started_at) = CURRENT_DATE) as conversations_today,
    (SELECT COUNT(DISTINCT user_id) FROM conversations WHERE DATE(started_at) = CURRENT_DATE) as unique_users_today,
    (SELECT COUNT(*) FROM conversations WHERE DATE(started_at) >= CURRENT_DATE - INTERVAL '7 days') as conversations_week,
    (SELECT COUNT(DISTINCT user_id) FROM conversations WHERE DATE(started_at) >= CURRENT_DATE - INTERVAL '7 days') as unique_users_week,
    (SELECT AVG(messages_count) FROM conversations WHERE DATE(started_at) = CURRENT_DATE) as avg_messages_today,
    (SELECT AVG(avg_response_time_ms) FROM conversations WHERE DATE(started_at) = CURRENT_DATE AND avg_response_time_ms IS NOT NULL) as avg_response_time_today,
    (SELECT json_object_agg(platform, count) FROM (
        SELECT platform, COUNT(*) as count 
        FROM conversations 
        WHERE DATE(started_at) = CURRENT_DATE 
        GROUP BY platform
    ) as platform_counts) as platforms_distribution,
    (SELECT array_to_json(array_agg(row_to_json(t))) FROM (
        SELECT topic, count 
        FROM popular_topics 
        WHERE date = CURRENT_DATE 
        ORDER BY count DESC 
        LIMIT 5
    ) t) as top_topics_today;

-- Función para limpiar datos antiguos (ejecutar diariamente)
CREATE OR REPLACE FUNCTION cleanup_old_metrics_data()
RETURNS void AS $$
BEGIN
    -- Eliminar mensajes detallados de más de 7 días
    DELETE FROM conversation_messages 
    WHERE created_at < NOW() - INTERVAL '7 days';
    
    -- Eliminar conversaciones de más de 30 días
    DELETE FROM conversations 
    WHERE started_at < NOW() - INTERVAL '30 days';
    
    -- Eliminar eventos de más de 90 días
    DELETE FROM metric_events 
    WHERE created_at < NOW() - INTERVAL '90 days'
    AND severity NOT IN ('error', 'critical');
    
    -- Eliminar temas populares de más de 90 días
    DELETE FROM popular_topics 
    WHERE date < CURRENT_DATE - INTERVAL '90 days';
    
    RAISE NOTICE 'Limpieza de métricas completada';
END;
$$ LANGUAGE plpgsql;

-- Función para agregar métricas por hora
CREATE OR REPLACE FUNCTION aggregate_hourly_metrics()
RETURNS void AS $$
DECLARE
    current_hour TIMESTAMP;
BEGIN
    current_hour := date_trunc('hour', NOW() - INTERVAL '1 hour');
    
    -- Agregar métricas para cada plataforma
    INSERT INTO metrics_hourly (
        hour_timestamp, platform, total_conversations, new_conversations,
        unique_users, total_messages, avg_messages_per_conversation,
        avg_response_time_ms, successful_resolutions, abandoned_conversations
    )
    SELECT 
        current_hour,
        platform,
        COUNT(*) as total_conversations,
        COUNT(CASE WHEN date_trunc('hour', started_at) = current_hour THEN 1 END) as new_conversations,
        COUNT(DISTINCT user_id) as unique_users,
        SUM(messages_count) as total_messages,
        AVG(messages_count) as avg_messages_per_conversation,
        AVG(avg_response_time_ms) as avg_response_time_ms,
        COUNT(CASE WHEN status = 'ended' AND user_satisfaction >= 4 THEN 1 END) as successful_resolutions,
        COUNT(CASE WHEN status = 'abandoned' THEN 1 END) as abandoned_conversations
    FROM conversations
    WHERE started_at >= current_hour AND started_at < current_hour + INTERVAL '1 hour'
    GROUP BY platform
    ON CONFLICT (hour_timestamp, platform) 
    DO UPDATE SET
        total_conversations = EXCLUDED.total_conversations,
        new_conversations = EXCLUDED.new_conversations,
        unique_users = EXCLUDED.unique_users,
        total_messages = EXCLUDED.total_messages,
        avg_messages_per_conversation = EXCLUDED.avg_messages_per_conversation,
        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
        successful_resolutions = EXCLUDED.successful_resolutions,
        abandoned_conversations = EXCLUDED.abandoned_conversations,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Función para agregar métricas diarias
CREATE OR REPLACE FUNCTION aggregate_daily_metrics()
RETURNS void AS $$
BEGIN
    INSERT INTO metrics_daily (
        date, platform, total_conversations, unique_users,
        total_messages, avg_messages_per_conversation,
        avg_response_time_ms, avg_session_duration_minutes,
        successful_resolutions, abandoned_conversations,
        user_satisfaction_avg, peak_hour, peak_conversations
    )
    SELECT 
        CURRENT_DATE - INTERVAL '1 day',
        platform,
        COUNT(*) as total_conversations,
        COUNT(DISTINCT user_id) as unique_users,
        SUM(messages_count) as total_messages,
        AVG(messages_count) as avg_messages_per_conversation,
        AVG(avg_response_time_ms) as avg_response_time_ms,
        AVG(EXTRACT(EPOCH FROM (ended_at - started_at))/60) as avg_session_duration_minutes,
        COUNT(CASE WHEN status = 'ended' AND user_satisfaction >= 4 THEN 1 END) as successful_resolutions,
        COUNT(CASE WHEN status = 'abandoned' THEN 1 END) as abandoned_conversations,
        AVG(user_satisfaction) as user_satisfaction_avg,
        mode() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM started_at)) as peak_hour,
        MAX(hourly_count) as peak_conversations
    FROM conversations
    LEFT JOIN LATERAL (
        SELECT COUNT(*) as hourly_count
        FROM conversations c2
        WHERE DATE(c2.started_at) = DATE(conversations.started_at)
        AND EXTRACT(HOUR FROM c2.started_at) = EXTRACT(HOUR FROM conversations.started_at)
        AND c2.platform = conversations.platform
    ) as hourly ON true
    WHERE DATE(started_at) = CURRENT_DATE - INTERVAL '1 day'
    GROUP BY platform
    ON CONFLICT (date, platform) 
    DO UPDATE SET
        total_conversations = EXCLUDED.total_conversations,
        unique_users = EXCLUDED.unique_users,
        total_messages = EXCLUDED.total_messages,
        avg_messages_per_conversation = EXCLUDED.avg_messages_per_conversation,
        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
        avg_session_duration_minutes = EXCLUDED.avg_session_duration_minutes,
        successful_resolutions = EXCLUDED.successful_resolutions,
        abandoned_conversations = EXCLUDED.abandoned_conversations,
        user_satisfaction_avg = EXCLUDED.user_satisfaction_avg,
        peak_hour = EXCLUDED.peak_hour,
        peak_conversations = EXCLUDED.peak_conversations,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;