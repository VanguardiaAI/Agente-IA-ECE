#!/bin/bash
# Script para configurar PostgreSQL localmente sin Docker

echo "🐘 Configuración de PostgreSQL para desarrollo local"
echo "=================================================="
echo ""

# Verificar si PostgreSQL está instalado
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL no está instalado."
    echo ""
    echo "Para instalar PostgreSQL en macOS:"
    echo "  brew install postgresql@16"
    echo "  brew services start postgresql@16"
    echo ""
    echo "Para instalar PostgreSQL en Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install postgresql postgresql-contrib"
    echo ""
    exit 1
fi

echo "✅ PostgreSQL está instalado"

# Verificar si el servicio está ejecutándose
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL no está ejecutándose."
    echo ""
    echo "Iniciando PostgreSQL..."
    
    # En macOS con Homebrew
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start postgresql@16 2>/dev/null || brew services start postgresql 2>/dev/null
    else
        # En Linux
        sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null
    fi
    
    sleep 3
    
    if ! pg_isready -q; then
        echo "❌ No se pudo iniciar PostgreSQL"
        exit 1
    fi
fi

echo "✅ PostgreSQL está ejecutándose"
echo ""

# Crear usuario y base de datos
echo "📦 Configurando base de datos para Eva..."

# Conectar como superusuario (postgres o el usuario actual)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # En macOS, usar el usuario actual
    PSQL_USER=$USER
else
    # En Linux, usar postgres
    PSQL_USER="postgres"
fi

# Crear usuario eva_user si no existe
psql -U $PSQL_USER -d postgres -c "CREATE USER eva_user WITH PASSWORD 'eva_password';" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Usuario 'eva_user' creado"
else
    echo "ℹ️  Usuario 'eva_user' ya existe"
fi

# Crear base de datos eva_db si no existe
psql -U $PSQL_USER -d postgres -c "CREATE DATABASE eva_db OWNER eva_user;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Base de datos 'eva_db' creada"
else
    echo "ℹ️  Base de datos 'eva_db' ya existe"
fi

# Otorgar todos los privilegios
psql -U $PSQL_USER -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE eva_db TO eva_user;" 2>/dev/null

# Instalar extensión pgvector
echo ""
echo "📦 Instalando extensión pgvector..."
psql -U $PSQL_USER -d eva_db -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Extensión pgvector instalada"
else
    echo "⚠️  No se pudo instalar pgvector. Puede que necesites instalarlo manualmente:"
    echo "   En macOS: brew install pgvector"
    echo "   En Linux: sudo apt-get install postgresql-16-pgvector"
fi

echo ""
echo "✅ ¡Configuración completada!"
echo ""
echo "📋 Detalles de conexión:"
echo "   Host: localhost"
echo "   Puerto: 5432"
echo "   Base de datos: eva_db"
echo "   Usuario: eva_user"
echo "   Contraseña: eva_password"
echo ""
echo "🚀 Ahora puedes ejecutar: python start_services.py"