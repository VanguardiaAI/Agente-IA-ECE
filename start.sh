#!/bin/bash

echo "🌟 Eva - Asistente Virtual de Atención al Cliente"
echo "=================================================="

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "🔧 Activando entorno virtual..."
    source venv/bin/activate
fi

# Función para mostrar opciones
show_menu() {
    echo ""
    echo "¿Qué quieres iniciar?"
    echo "1) 🤖 Servidor MCP (Backend)"
    echo "2) 🌐 Interfaz Web Completa"
    echo "3) 🧪 Ejecutar Tests"
    echo "4) 📊 Ver Estructura del Proyecto"
    echo "5) ❌ Salir"
}

# Función para mostrar estructura
show_structure() {
    echo ""
    echo "📁 Estructura del Proyecto:"
    echo "├── src/                    # Código fuente principal"
    echo "│   ├── agent/             # Agente de IA mejorado"
    echo "│   └── web/               # Interfaz web moderna"
    echo "├── tests/                 # Suite completa de tests"
    echo "├── docs/                  # Documentación"
    echo "├── scripts/               # Scripts de utilidad"
    echo "├── config/                # Configuración"
    echo "├── tools/                 # Herramientas MCP"
    echo "├── services/              # Servicios de integración"
    echo "└── backup/                # Respaldos de versiones anteriores"
}

# Loop principal
while true; do
    show_menu
    read -p "Selecciona una opción (1-5): " choice
    
    case $choice in
        1)
            echo "🚀 Iniciando Servidor MCP..."
            python3 main.py
            ;;
        2)
            echo "🌐 Iniciando Interfaz Web..."
            echo "Accede a: http://localhost:8000"
            python3 app.py
            ;;
        3)
            echo "🧪 Ejecutando Tests..."
            cd tests/
            python3 run_tests.py
            cd ..
            ;;
        4)
            show_structure
            ;;
        5)
            echo "👋 ¡Hasta luego!"
            exit 0
            ;;
        *)
            echo "❗ Opción inválida. Por favor selecciona 1-5."
            ;;
    esac
done 