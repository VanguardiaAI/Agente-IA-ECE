#!/usr/bin/env python3
"""
Script para verificar la conexión con 360Dialog
"""

import requests
import json
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

def test_connection():
    """
    Prueba la conexión con 360Dialog y muestra información de la cuenta
    """
    
    # Verificar configuración
    api_key = getattr(settings, 'WHATSAPP_360DIALOG_API_KEY', None)
    
    print("🔍 Verificando configuración...")
    print("=" * 50)
    
    if not api_key:
        print("❌ WHATSAPP_360DIALOG_API_KEY no está configurada")
        print("\nAsegúrate de tener en tu archivo .env:")
        print("WHATSAPP_360DIALOG_API_KEY=tu_api_key_aqui")
        return
    
    print(f"✅ API Key encontrada: {api_key[:10]}...")
    
    # Headers
    headers = {
        "D360-API-KEY": api_key
    }
    
    # 1. Verificar estado de la API
    print("\n📡 Probando conexión con 360Dialog...")
    
    try:
        # Obtener información del cliente
        response = requests.get(
            "https://waba-v2.360dialog.io/v1/account",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Conexión exitosa!")
            account_info = response.json()
            print(f"\n📋 Información de la cuenta:")
            print(json.dumps(account_info, indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
            if response.status_code == 401:
                print("\n⚠️  La API key parece ser inválida")
                print("   Verifica en el panel de 360Dialog:")
                print("   1. Ve a Settings > API Keys")
                print("   2. Copia la API key completa")
                print("   3. Actualiza tu archivo .env")
        
        # 2. Verificar webhook actual
        print("\n🔗 Verificando configuración de webhook...")
        webhook_response = requests.get(
            "https://waba-v2.360dialog.io/v1/configs/webhook",
            headers=headers
        )
        
        if webhook_response.status_code == 200:
            webhook_config = webhook_response.json()
            current_url = webhook_config.get('url', '')
            
            if current_url:
                print(f"✅ Webhook configurado: {current_url}")
            else:
                print("⚠️  No hay webhook configurado")
                print("\nPara configurar el webhook:")
                print("1. Ejecuta ngrok: ngrok http 8080")
                print("2. Copia el subdominio (ej: abc123)")
                print("3. Ejecuta: python scripts/configure_360dialog_webhook.py --ngrok abc123")
        
        # 3. Verificar números de teléfono
        print("\n📱 Verificando números configurados...")
        phone_response = requests.get(
            "https://waba-v2.360dialog.io/v1/account/phone_numbers",
            headers=headers
        )
        
        if phone_response.status_code == 200:
            phones = phone_response.json()
            if phones:
                print("✅ Números encontrados:")
                for phone in phones:
                    print(f"   - {phone.get('display_phone_number', 'N/A')} ({phone.get('verified_name', 'N/A')})")
            else:
                print("⚠️  No hay números configurados")
                
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        print("\nPosibles causas:")
        print("- No hay conexión a internet")
        print("- La API key es incorrecta")
        print("- El servidor de 360Dialog no está disponible")

def main():
    print("🌐 360Dialog Connection Test")
    print("=" * 50)
    test_connection()
    print("\n" + "=" * 50)
    print("📚 Documentación: https://docs.360dialog.com/")

if __name__ == "__main__":
    main()