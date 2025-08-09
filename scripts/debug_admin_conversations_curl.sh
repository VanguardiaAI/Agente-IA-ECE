#!/bin/bash

# Script para debuggear el problema de carga de conversaciones en el admin usando curl

echo "🔍 Debuggeando problema de carga de conversaciones en admin..."
echo "==============================================================="

BASE_URL="http://localhost:8080"

# Función para hacer peticiones con curl y mostrar resultados
test_endpoint() {
    local url=$1
    local description=$2
    local extra_args=$3
    
    echo ""
    echo "📡 Probando $description..."
    echo "   URL: $url"
    
    # Hacer la petición
    response=$(curl -s -w "HTTP_STATUS:%{http_code}" $extra_args "$url" 2>/dev/null)
    
    # Separar el cuerpo de la respuesta del código HTTP
    http_code=$(echo "$response" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
    body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    if [ "$http_code" = "200" ]; then
        echo "   ✅ Status: $http_code"
        echo "   📊 Respuesta (primeros 300 chars):"
        echo "$body" | head -c 300
        echo ""
        
        # Si es JSON, intentar parsear estructura básica
        if echo "$body" | python3 -m json.tool > /dev/null 2>&1; then
            echo "   ✅ JSON válido"
            
            # Extraer información clave si es el endpoint de conversaciones
            if [[ "$url" == *"conversations"* ]]; then
                conversations_count=$(echo "$body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, dict) and 'conversations' in data:
        print(len(data['conversations']))
    elif isinstance(data, list):
        print(len(data))
    else:
        print('Estructura inesperada')
except:
    print('Error parseando JSON')
" 2>/dev/null)
                echo "   📋 Conversaciones en respuesta: $conversations_count"
                
                # Mostrar claves principales del JSON
                keys=$(echo "$body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, dict):
        print(', '.join(data.keys()))
    else:
        print('Lista de', len(data), 'elementos')
except:
    print('Error')
" 2>/dev/null)
                echo "   🔑 Claves principales: $keys"
            fi
        else
            echo "   ⚠️  Respuesta no es JSON válido"
        fi
        
    elif [ "$http_code" = "401" ]; then
        echo "   🔐 Status: $http_code - Requiere autenticación"
    elif [ "$http_code" = "404" ]; then
        echo "   ❌ Status: $http_code - Endpoint no encontrado"
    elif [ "$http_code" = "500" ]; then
        echo "   💥 Status: $http_code - Error interno del servidor"
        echo "   📄 Error: $body"
    else
        echo "   ❓ Status: $http_code"
        echo "   📄 Respuesta: $body"
    fi
}

# 1. Probar endpoint de métricas (este funciona)
test_endpoint "$BASE_URL/api/admin/metrics/summary" "Métricas del Dashboard"

# 2. Probar endpoint de conversaciones (el problemático)
test_endpoint "$BASE_URL/api/admin/conversations" "Lista de Conversaciones"

# 3. Probar con parámetros como lo hace el frontend
test_endpoint "$BASE_URL/api/admin/conversations?limit=10&offset=0" "Conversaciones con Parámetros"

# 4. Probar health check
test_endpoint "$BASE_URL/health" "Health Check"

# 5. Verificar si hay logs de error recientes
echo ""
echo "📋 Verificando logs de errores recientes..."
if command -v docker &> /dev/null; then
    echo "   🐳 Logs del contenedor eva-web-prod (últimas 20 líneas):"
    docker logs eva-web-prod --tail 20 2>/dev/null | grep -i error || echo "   ✅ No hay errores recientes en logs"
else
    echo "   ⚠️  Docker no disponible para revisar logs"
fi

# 6. Verificar base de datos directamente si es posible
echo ""
echo "🗄️  Verificando base de datos..."

# Intentar usar el script de Python simple para verificar BD
if python3 -c "import asyncpg" 2>/dev/null; then
    echo "   📊 Ejecutando verificación de base de datos..."
    python3 << 'EOF'
import asyncio
import asyncpg
import os
import sys

async def check_db():
    try:
        # Cargar variables de .env
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value.strip("\"'")
        
        # Conectar a BD
        conn = await asyncpg.connect(
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            user=os.environ.get("POSTGRES_USER", "eva_user"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            database=os.environ.get("POSTGRES_DB", "eva_db")
        )
        
        # Contar conversaciones
        total = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        print(f"   ✅ Total conversaciones en BD: {total}")
        
        # Últimas conversaciones
        if total > 0:
            recent = await conn.fetch("""
                SELECT conversation_id, platform, started_at, messages_count
                FROM conversations 
                ORDER BY started_at DESC 
                LIMIT 3
            """)
            print("   📋 Últimas 3 conversaciones:")
            for i, conv in enumerate(recent, 1):
                print(f"      {i}. {conv['platform']} | {conv['started_at']} | {conv['messages_count']} msgs")
        
        await conn.close()
        
    except Exception as e:
        print(f"   ❌ Error verificando BD: {e}")

asyncio.run(check_db())
EOF
else
    echo "   ⚠️  asyncpg no disponible, no se puede verificar BD directamente"
fi

echo ""
echo "📋 RESUMEN DEL DIAGNÓSTICO:"
echo "=========================="
echo ""
echo "Si ves:"
echo "• ✅ Métricas funcionan + ❌ Conversaciones fallan = Problema en endpoint específico"
echo "• 🔐 Status 401 en conversaciones = Problema de autenticación"
echo "• 💥 Status 500 = Error interno del servidor (revisar logs)"
echo "• ✅ BD tiene conversaciones + ❌ API no las devuelve = Problema en get_conversation_details"
echo ""
echo "Próximo paso: Revisar logs detallados del servidor para el error específico"
echo ""