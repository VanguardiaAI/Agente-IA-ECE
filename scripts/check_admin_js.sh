#!/bin/bash

# Script para verificar el estado de los archivos admin.js en producción

echo "🔍 Verificando archivos JavaScript del admin..."
echo "=============================================="

# 1. Verificar que los archivos existen
echo "📂 1. Verificando archivos estáticos..."
if [ -f "static/admin.js" ]; then
    size=$(stat -c%s "static/admin.js" 2>/dev/null || stat -f%z "static/admin.js" 2>/dev/null)
    echo "   ✅ admin.js existe (${size} bytes)"
    
    # Verificar que contiene la función loadConversations
    if grep -q "loadConversations" static/admin.js; then
        echo "   ✅ Contiene función loadConversations"
    else
        echo "   ❌ NO contiene función loadConversations"
    fi
    
    # Verificar errores de sintaxis básicos
    echo "   🔍 Verificando sintaxis básica..."
    if node -c static/admin.js 2>/dev/null; then
        echo "   ✅ Sintaxis JavaScript válida"
    else
        echo "   ❌ Errores de sintaxis JavaScript"
        echo "   Errores encontrados:"
        node -c static/admin.js
    fi
    
else
    echo "   ❌ admin.js NO existe"
fi

if [ -f "static/admin_extras.js" ]; then
    size=$(stat -c%s "static/admin_extras.js" 2>/dev/null || stat -f%z "static/admin_extras.js" 2>/dev/null)
    echo "   ✅ admin_extras.js existe (${size} bytes)"
else
    echo "   ❌ admin_extras.js NO existe"
fi

# 2. Verificar acceso web a los archivos
echo ""
echo "🌐 2. Verificando acceso web a archivos JS..."

test_js_url() {
    local url=$1
    local filename=$2
    
    response=$(curl -s -w "HTTP_STATUS:%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
    body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    if [ "$http_code" = "200" ]; then
        size=${#body}
        echo "   ✅ $filename accesible vía web (${size} bytes)"
        
        # Verificar que contiene funciones esperadas
        if echo "$body" | grep -q "loadConversations"; then
            echo "      ✅ Contiene loadConversations"
        else
            echo "      ❌ NO contiene loadConversations"
        fi
        
        if echo "$body" | grep -q "loadDashboard"; then
            echo "      ✅ Contiene loadDashboard"
        else
            echo "      ❌ NO contiene loadDashboard"
        fi
        
    else
        echo "   ❌ $filename NO accesible vía web (Status: $http_code)"
        if [ "$http_code" = "404" ]; then
            echo "      💡 Archivo no encontrado por el servidor web"
        elif [ "$http_code" = "403" ]; then
            echo "      💡 Permisos incorrectos"
        fi
    fi
}

test_js_url "http://localhost:8080/static/admin.js" "admin.js"
test_js_url "http://localhost:8080/static/admin_extras.js" "admin_extras.js"

# 3. Verificar template HTML
echo ""
echo "📄 3. Verificando template HTML..."
if [ -f "templates/admin_dashboard.html" ]; then
    echo "   ✅ admin_dashboard.html existe"
    
    # Verificar que carga los archivos JS
    if grep -q 'src="/static/admin.js"' templates/admin_dashboard.html; then
        echo "   ✅ HTML carga admin.js"
    else
        echo "   ❌ HTML NO carga admin.js"
    fi
    
    if grep -q 'src="/static/admin_extras.js"' templates/admin_dashboard.html; then
        echo "   ✅ HTML carga admin_extras.js"
    else
        echo "   ❌ HTML NO carga admin_extras.js"
    fi
else
    echo "   ❌ admin_dashboard.html NO existe"
fi

# 4. Verificar logs del servidor web
echo ""
echo "📋 4. Verificando logs del servidor web..."
if command -v docker &> /dev/null; then
    echo "   🔍 Buscando errores 404 en nginx logs..."
    recent_404s=$(docker logs eva-nginx-prod --tail 50 2>/dev/null | grep -i "404\|admin.js\|static" | tail -5 || echo "No hay logs de 404 recientes")
    if [ "$recent_404s" != "No hay logs de 404 recientes" ]; then
        echo "   ⚠️  Errores 404 encontrados:"
        echo "$recent_404s"
    else
        echo "   ✅ No hay errores 404 recientes para archivos estáticos"
    fi
else
    echo "   ⚠️  Docker no disponible para revisar logs"
fi

# 5. Verificar permisos de archivos
echo ""
echo "🔒 5. Verificando permisos de archivos..."
if [ -f "static/admin.js" ]; then
    perms=$(ls -la static/admin.js | cut -d' ' -f1)
    echo "   📋 Permisos admin.js: $perms"
    
    if [[ "$perms" == *"r"* ]]; then
        echo "   ✅ Archivo legible"
    else
        echo "   ❌ Archivo NO legible"
        echo "   💡 Ejecutar: chmod 644 static/admin.js"
    fi
fi

echo ""
echo "🎯 RESUMEN Y SOLUCIONES:"
echo "======================="
echo ""
echo "Si admin.js existe pero loadConversations no está definida:"
echo "• Problema de sintaxis JavaScript → Verificar errores en consola del navegador"
echo "• Archivo no accesible vía web → Verificar permisos y configuración nginx"
echo "• Cache del navegador → Hard refresh (Ctrl+Shift+R)"
echo "• Archivo truncado/corrupto → Comparar tamaño archivo vs web"
echo ""
echo "Próximo paso recomendado:"
echo "1. Verificar consola del navegador (F12) para errores JavaScript"
echo "2. Si hay errores de sintaxis, revisar últimos cambios en admin.js"
echo "3. Si no hay errores, limpiar cache del navegador"
echo ""