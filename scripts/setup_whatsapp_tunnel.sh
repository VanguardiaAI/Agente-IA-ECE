#!/bin/bash

echo "🌐 Configurando túnel para WhatsApp webhooks..."
echo "================================================"

# Verificar si ngrok está instalado
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok no está instalado"
    echo ""
    echo "Para instalar ngrok:"
    echo "1. Visita https://ngrok.com/download"
    echo "2. O instala con Homebrew: brew install ngrok"
    echo "3. Crea una cuenta gratuita en ngrok.com"
    echo "4. Configura tu authtoken: ngrok config add-authtoken <tu-token>"
    exit 1
fi

echo "✅ ngrok encontrado"
echo ""
echo "📱 Iniciando túnel para el puerto 8080..."
echo ""
echo "IMPORTANTE: Una vez que ngrok inicie:"
echo "1. Copia la URL HTTPS que te proporciona (ej: https://abc123.ngrok.io)"
echo "2. En 360Dialog, configura el webhook como: https://abc123.ngrok.io/api/webhooks/whatsapp"
echo "3. Usa el verify token: 3DJPvQQXpufwvGX7TNj7FP6rjPWYoRtZCIi5imjs6UA"
echo ""
echo "Presiona Ctrl+C para detener el túnel"
echo "================================================"

# Iniciar ngrok
ngrok http 8080