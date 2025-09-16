#!/bin/bash

# Script de limpieza para preparar el proyecto para producción
# IMPORTANTE: Hacer backup antes de ejecutar este script

echo "=== LIMPIEZA PARA PRODUCCIÓN ==="
echo "Este script eliminará archivos de desarrollo y sensibles"
echo "¿Estás seguro de que quieres continuar? (y/n)"
read -r response

if [[ "$response" != "y" ]]; then
    echo "Operación cancelada"
    exit 1
fi

echo ""
echo "1. Eliminando archivos de log..."
find . -name "*.log" -type f -delete
echo "✓ Logs eliminados"

echo ""
echo "2. Eliminando scripts de test de desarrollo..."
# Mantener tests/ pero eliminar scripts de test individuales
find ./scripts -name "test_*.py" -type f -delete
find ./scripts -name "debug_*.py" -type f -delete
echo "✓ Scripts de test eliminados"

echo ""
echo "3. Eliminando archivos de documentación temporal..."
rm -f PENDING_CLEANUP.md
rm -f PRODUCTION_READY_REPORT.md
rm -f AGENT_PIPELINE_REDESIGN.md
rm -f IMPROVEMENT_SUMMARY.md
rm -f MISSION_REFINEMENT.md
echo "✓ Documentación temporal eliminada"

echo ""
echo "4. Eliminando resultados de pruebas..."
rm -rf test_results/
rm -f test_results*.json
rm -f *test_report*.json
echo "✓ Resultados de pruebas eliminados"

echo ""
echo "5. Eliminando directorios temporales..."
rm -rf .playwright-mcp/
rm -rf chatbot-widget-manaslu/
rm -rf eva-chatbot-widget-manaslu-mockup/
echo "✓ Directorios temporales eliminados"

echo ""
echo "6. Eliminando archivos ZIP del widget..."
find . -name "eva-chatbot-widget*.zip" -type f -delete
echo "✓ Archivos ZIP eliminados"

echo ""
echo "7. Removiendo archivos sensibles del control de versiones..."
# Solo si están en git
if git ls-files --error-unmatch .env 2>/dev/null; then
    git rm --cached .env
    echo "✓ .env removido del repositorio"
fi

if git ls-files --error-unmatch env.agent 2>/dev/null; then
    git rm --cached env.agent
    echo "✓ env.agent removido del repositorio"
fi

# Verificar si existe la carpeta de datos de postgres en git
if git ls-files --error-unmatch docker/postgres/data/ 2>/dev/null; then
    git rm -r --cached docker/postgres/data/
    echo "✓ docker/postgres/data/ removido del repositorio"
fi

echo ""
echo "=== LIMPIEZA COMPLETADA ==="
echo ""
echo "IMPORTANTE - Próximos pasos:"
echo "1. Revisa los cambios con: git status"
echo "2. Si todo está bien, ejecuta: git commit -m 'Clean up for production deployment'"
echo "3. Asegúrate de que .env y env.agent tengan los valores correctos de producción"
echo "4. Verifica que docker/postgres/data/ no esté en el repositorio"
echo ""
echo "ARCHIVOS DE CONFIGURACIÓN:"
echo "- Usa env.example como plantilla para crear .env"
echo "- Usa env.agent.example como plantilla para crear env.agent"
echo "- Usa env.production.example como referencia para producción"