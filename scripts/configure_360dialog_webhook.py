#!/usr/bin/env python3
"""
Script para configurar el webhook en 360Dialog via API
"""

import requests
import json
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

def configure_webhook(webhook_url: str):
    """
    Configura el webhook en 360Dialog
    
    Args:
        webhook_url: URL completa del webhook (debe ser HTTPS)
    """
    
    # Verificar que tenemos API key
    api_key = getattr(settings, 'WHATSAPP_360DIALOG_API_KEY', None)
    if not api_key:
        print("❌ Error: WHATSAPP_360DIALOG_API_KEY no está configurada en .env")
        return False
    
    # Headers para la API
    headers = {
        "D360-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    # Endpoint para configurar webhook
    # Usar el endpoint correcto según la documentación
    api_url = "https://waba.360dialog.io/v1/configs/webhook"
    
    # Payload con la URL del webhook
    payload = {
        "url": webhook_url
    }
    
    print(f"🔧 Configurando webhook en 360Dialog...")
    print(f"📍 URL: {webhook_url}")
    
    try:
        # Hacer la petición
        # Intentar primero con POST
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print("✅ Webhook configurado exitosamente!")
            result = response.json()
            print(f"📋 Respuesta: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error al configurar webhook: {response.status_code}")
            print(f"📋 Respuesta: {response.text}")
            
            # Si es error 401, el problema es la API key
            if response.status_code == 401:
                print("\n⚠️  La API key parece ser inválida o no tener permisos")
                print("   Verifica tu API key en el panel de 360Dialog")
            
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def get_webhook_status():
    """
    Obtiene el estado actual del webhook
    """
    api_key = getattr(settings, 'WHATSAPP_360DIALOG_API_KEY', None)
    if not api_key:
        print("❌ Error: WHATSAPP_360DIALOG_API_KEY no está configurada")
        return
    
    headers = {
        "D360-API-KEY": api_key
    }
    
    # Endpoint para obtener configuración
    api_url = "https://waba.360dialog.io/v1/configs/webhook"
    
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            config = response.json()
            print("\n📊 Estado actual del webhook:")
            print(f"URL: {config.get('url', 'No configurada')}")
            print(f"Headers: {config.get('headers', {})}")
        else:
            print(f"❌ Error obteniendo estado: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Configurar webhook de 360Dialog')
    parser.add_argument('--url', help='URL del webhook (debe ser HTTPS)')
    parser.add_argument('--status', action='store_true', help='Ver estado actual del webhook')
    parser.add_argument('--ngrok', help='Usar URL de ngrok (ej: abc123)')
    
    args = parser.parse_args()
    
    print("🌐 360Dialog Webhook Configuration Tool")
    print("=" * 50)
    
    if args.status:
        get_webhook_status()
    elif args.url:
        # Verificar que es HTTPS
        if not args.url.startswith('https://'):
            print("❌ Error: La URL debe usar HTTPS")
            print("   Ejemplo: https://tu-dominio.com/api/webhooks/whatsapp")
            sys.exit(1)
        
        configure_webhook(args.url)
    elif args.ngrok:
        # Construir URL de ngrok
        ngrok_url = f"https://{args.ngrok}.ngrok.io/api/webhooks/whatsapp"
        configure_webhook(ngrok_url)
    else:
        print("Uso:")
        print("  Ver estado actual:")
        print("    python configure_360dialog_webhook.py --status")
        print("")
        print("  Configurar con URL completa:")
        print("    python configure_360dialog_webhook.py --url https://tu-dominio.com/api/webhooks/whatsapp")
        print("")
        print("  Configurar con ngrok:")
        print("    python configure_360dialog_webhook.py --ngrok abc123")
        print("")
        print("Nota: Primero debes tener ngrok ejecutándose:")
        print("  ngrok http 8080")

if __name__ == "__main__":
    main()