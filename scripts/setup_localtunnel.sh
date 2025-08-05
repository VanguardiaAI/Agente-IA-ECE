#!/bin/bash

echo "🌐 Configurando túnel local para WhatsApp webhooks..."
echo "================================================"

# Verificar si localtunnel está instalado
if ! command -v lt &> /dev/null; then
    echo "📦 Instalando localtunnel..."
    npm install -g localtunnel
fi

echo "✅ localtunnel encontrado"
echo ""
echo "📱 Iniciando túnel para el puerto 8080..."
echo ""
echo "IMPORTANTE: Una vez que localtunnel inicie:"
echo "1. Copia la URL HTTPS que te proporciona"
echo "2. Ejecuta: python scripts/configure_360dialog_webhook.py --url <LA-URL>/api/webhooks/whatsapp"
echo ""
echo "Presiona Ctrl+C para detener el túnel"
echo "================================================"

# Iniciar localtunnel con un subdominio personalizado
lt --port 8080 --subdomain eva-whatsapp-$(date +%s)