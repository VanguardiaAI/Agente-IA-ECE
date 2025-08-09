#!/bin/bash

# Script para debuggear el problema de carga de mensajes de conversación en producción

echo "🔍 Debuggeando problema de mensajes de conversación..."
echo "=================================================="

# Obtener un conversation_id de ejemplo
CONV_ID="${1:-whatsapp_5215610830260_c04690ea}"

echo ""
echo "📋 1. Verificando conversación: $CONV_ID"

# Probar el endpoint directamente
echo ""
echo "🌐 2. Probando endpoint de mensajes..."
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "http://localhost:8080/api/admin/conversations/$CONV_ID/messages" 2>/dev/null)
http_code=$(echo "$response" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   Status HTTP: $http_code"

if [ "$http_code" = "404" ]; then
    echo "   ❌ Conversación no encontrada"
    echo ""
    echo "🗄️  3. Verificando en base de datos directamente..."
    
    # Verificar si la conversación existe en BD
    docker exec -i eva-postgres-prod psql -U eva_user -d eva_db << EOF
-- Verificar si existe la conversación
SELECT EXISTS(
    SELECT 1 FROM conversations 
    WHERE conversation_id = '$CONV_ID'
) as existe;

-- Si existe, mostrar detalles
SELECT 
    conversation_id,
    user_id,
    platform,
    started_at,
    messages_count,
    status
FROM conversations 
WHERE conversation_id = '$CONV_ID';

-- Contar mensajes de esa conversación
SELECT COUNT(*) as total_mensajes
FROM conversation_messages
WHERE conversation_id = '$CONV_ID';

-- Mostrar primeros mensajes si existen
SELECT 
    message_id,
    sender_type,
    LEFT(content, 50) as content_preview,
    created_at
FROM conversation_messages
WHERE conversation_id = '$CONV_ID'
ORDER BY created_at
LIMIT 3;
EOF

elif [ "$http_code" = "200" ]; then
    echo "   ✅ Endpoint funciona correctamente"
    echo "   📊 Respuesta (primeros 200 chars):"
    echo "$body" | head -c 200
else
    echo "   ❓ Status inesperado: $http_code"
    echo "   📄 Respuesta: $body"
fi

echo ""
echo "🔍 4. Verificando logs del servidor..."
docker logs eva-web-prod --tail 20 2>&1 | grep -i "conversation\|error" || echo "No hay errores recientes"

echo ""
echo "📋 DIAGNÓSTICO:"
echo "==============="
echo "Si la conversación existe en BD pero da 404:"
echo "  • Problema en el método get_conversation_by_id"
echo "  • Posible diferencia en el formato del ID"
echo "  • Verificar codificación de caracteres"
echo ""
echo "Si la conversación NO existe en BD:"
echo "  • Los IDs pueden ser diferentes entre local y producción"
echo "  • Verificar sincronización de datos"
echo ""