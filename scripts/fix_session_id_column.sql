-- Script para agregar la columna session_id a la tabla conversation_logs
-- Esta columna es requerida por el conversation_logger pero no existe en producción

-- Verificar si la columna ya existe antes de agregarla
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'conversation_logs' 
        AND column_name = 'session_id'
    ) THEN
        -- Agregar la columna session_id
        ALTER TABLE conversation_logs 
        ADD COLUMN session_id VARCHAR(255);
        
        -- Crear índice para mejorar el rendimiento
        CREATE INDEX idx_conversation_logs_session_id 
        ON conversation_logs(session_id);
        
        RAISE NOTICE 'Columna session_id agregada exitosamente';
    ELSE
        RAISE NOTICE 'La columna session_id ya existe';
    END IF;
END $$;

-- Verificar la estructura actual de la tabla
\d conversation_logs