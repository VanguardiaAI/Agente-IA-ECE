#!/bin/bash

# Script para listar conversaciones disponibles en producción

echo "📋 Listando conversaciones en producción..."
echo "=========================================="

echo ""
echo "🗄️  Conversaciones en base de datos:"

docker exec -i eva-postgres-prod psql -U eva_user -d eva_db << 'EOF'
-- Mostrar últimas 10 conversaciones
SELECT 
    conversation_id,
    user_id,
    platform,
    started_at,
    messages_count,
    status
FROM conversations 
ORDER BY started_at DESC
LIMIT 10;

-- Contar total por plataforma
SELECT 
    platform,
    COUNT(*) as total,
    COUNT(DISTINCT user_id) as usuarios_unicos
FROM conversations
GROUP BY platform;

-- Verificar si hay mensajes huérfanos
SELECT 
    'Conversaciones con mensajes' as tipo,
    COUNT(DISTINCT c.conversation_id) as total
FROM conversations c
INNER JOIN conversation_messages m ON c.conversation_id = m.conversation_id

UNION ALL

SELECT 
    'Conversaciones sin mensajes' as tipo,
    COUNT(DISTINCT c.conversation_id) as total
FROM conversations c
LEFT JOIN conversation_messages m ON c.conversation_id = m.conversation_id
WHERE m.conversation_id IS NULL;
EOF

echo ""
echo "💡 Toma uno de los conversation_id listados arriba y úsalo para probar:"
echo "   ./scripts/debug_conversation_messages.sh <conversation_id>"
echo ""