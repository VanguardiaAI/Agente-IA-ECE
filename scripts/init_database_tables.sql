-- Script de inicialización de tablas para Eva
-- Ejecutar este script para crear todas las tablas necesarias

-- Crear extensión pgvector si no existe
CREATE EXTENSION IF NOT EXISTS vector;

-- Crear tabla de logs de conversación
CREATE TABLE IF NOT EXISTS conversation_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(50),
    content TEXT,
    metadata JSONB
);

-- Crear índices para conversation_logs
CREATE INDEX IF NOT EXISTS idx_session_id ON conversation_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON conversation_logs(timestamp);

-- Verificar que existan las tablas principales
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    woo_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(500),
    sku VARCHAR(200),
    price DECIMAL(10,2),
    stock_quantity INTEGER,
    description TEXT,
    short_description TEXT,
    categories JSONB,
    attributes JSONB,
    images JSONB,
    metadata JSONB,
    embedding vector(1536),
    search_vector tsvector,
    hash VARCHAR(64),
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de categorías
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    woo_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    parent_id INTEGER,
    description TEXT,
    count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de control de sincronización
CREATE TABLE IF NOT EXISTS sync_control (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,
    last_sync_time TIMESTAMP WITH TIME ZONE,
    items_synced INTEGER DEFAULT 0,
    status VARCHAR(20),
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de cambios pendientes
CREATE TABLE IF NOT EXISTS pending_changes (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    change_data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de memoria de conversaciones
CREATE TABLE IF NOT EXISTS conversation_memory (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    message TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de resúmenes de conversación
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    key_points JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de preferencias de usuario
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    preferences JSONB DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de base de conocimientos
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    file_path VARCHAR(500),
    embedding vector(1536),
    search_vector tsvector,
    metadata JSONB DEFAULT '{}',
    hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índices adicionales
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_woo_id ON products(woo_id);
CREATE INDEX IF NOT EXISTS idx_products_search_vector ON products USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_products_embedding ON products USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_categories_woo_id ON categories(woo_id);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_user ON conversation_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_session ON conversation_memory(session_id);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_search_vector ON knowledge_base USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);

-- Crear funciones útiles
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('spanish', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.sku, '')), 'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.short_description, '')), 'B') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.description, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear triggers
DROP TRIGGER IF EXISTS update_products_search_vector ON products;
CREATE TRIGGER update_products_search_vector
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- Mensaje de confirmación
SELECT 'Todas las tablas han sido creadas o verificadas exitosamente' as status;