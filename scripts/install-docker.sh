#!/bin/bash

# Script para instalar Docker en Ubuntu
# Autor: vanguardia.dev

set -e

echo "=== Instalando Docker en Ubuntu ==="

# 1. Eliminar versiones antiguas si existen
echo "Removiendo versiones antiguas de Docker si existen..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# 2. Actualizar el sistema
echo "Actualizando sistema..."
sudo apt-get update

# 3. Instalar paquetes necesarios
echo "Instalando dependencias..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 4. Crear directorio para keyrings
sudo mkdir -p /etc/apt/keyrings

# 5. Agregar clave GPG de Docker
echo "Agregando clave GPG de Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 6. Eliminar el repositorio mal configurado si existe
sudo rm -f /etc/apt/sources.list.d/docker.list

# 7. Configurar el repositorio correctamente
echo "Configurando repositorio de Docker..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 8. Actualizar índice de paquetes
echo "Actualizando índice de paquetes..."
sudo apt-get update

# 9. Instalar Docker
echo "Instalando Docker..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 10. Instalar Docker Compose standalone
echo "Instalando Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 11. Verificar instalación
echo ""
echo "=== Verificando instalación ==="
docker --version
docker compose version
docker-compose --version 2>/dev/null || echo "docker-compose standalone no instalado (opcional)"

# 12. Habilitar Docker para iniciar con el sistema
sudo systemctl enable docker
sudo systemctl start docker

echo ""
echo "✅ Docker instalado correctamente!"
echo ""
echo "Para usar Docker sin sudo, ejecuta:"
echo "  sudo usermod -aG docker $USER"
echo "  Luego cierra sesión y vuelve a iniciar"