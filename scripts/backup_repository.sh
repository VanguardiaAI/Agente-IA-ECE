#!/bin/bash
# Script de backup completo del repositorio

set -e

# Configuración
REPO_URL="https://github.com/VanguardiaAI/Agente-IA-ECE.git"
BACKUP_DIR="$HOME/Desktop/Backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="Agente-IA-ECE-backup-$DATE"

echo "🔄 Iniciando backup del repositorio..."

# Crear directorio de backup si no existe
mkdir -p "$BACKUP_DIR"

# 1. Crear tag de la versión actual
echo "🏷️ Creando tag de versión actual..."
git tag -a "backup-$DATE" -m "Backup before search improvements - $DATE"
git push origin "backup-$DATE"

# 2. Crear branch de backup
echo "🌿 Creando branch de backup..."
git checkout -b "backup-pre-search-improvements-$DATE"
git push origin "backup-pre-search-improvements-$DATE"

# 3. Clonar copia completa
echo "📦 Clonando copia completa..."
cd "$BACKUP_DIR"
git clone --recursive "$REPO_URL" "$BACKUP_NAME"

# 4. Crear archivo de información
echo "📄 Creando archivo de información..."
cd "$BACKUP_NAME"
cat > BACKUP_INFO.txt << EOF
BACKUP INFORMATION
==================
Date: $(date)
Repository: $REPO_URL
Branch: $(git branch --show-current)
Commit: $(git rev-parse HEAD)
Commit Message: $(git log -1 --pretty=%B)
Files Changed: $(git status --porcelain | wc -l)

RESTORE INSTRUCTIONS:
1. Para restaurar código: cp -r . /path/to/project/
2. Para restaurar git: git reset --hard $(git rev-parse HEAD)
3. Para revertir branch: git checkout backup-pre-search-improvements-$DATE
4. Para revertir tag: git checkout backup-$DATE

BRANCHES DISPONIBLES:
$(git branch -a)

TAGS DISPONIBLES:
$(git tag -l | tail -10)
EOF

# 5. Comprimir backup
echo "🗜️ Comprimiendo backup..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"

# 6. Información final
echo "✅ Backup completado:"
echo "   📁 Directorio: $BACKUP_DIR/$BACKUP_NAME"
echo "   📦 Archivo: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "   🏷️ Tag: backup-$DATE"
echo "   🌿 Branch: backup-pre-search-improvements-$DATE"
echo ""
echo "Para restaurar:"
echo "   cd $BACKUP_DIR && tar -xzf $BACKUP_NAME.tar.gz"
echo "   git checkout backup-$DATE"

# Volver al directorio original
cd - > /dev/null

echo "🎉 Backup completado exitosamente!"