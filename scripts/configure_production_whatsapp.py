#!/usr/bin/env python3
"""
Script para configurar WhatsApp 360Dialog para producción
Configura webhook URL para ia.elcorteelectrico.com
"""

import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from services.whatsapp_360dialog_service import WhatsApp360DialogService
from config.settings import settings

async def configure_production_webhook():
    """Configurar webhook de WhatsApp para producción"""
    
    print("🔧 Configurando WhatsApp 360Dialog para Producción")
    print("=" * 60)
    
    # URLs de producción
    production_webhook_url = "https://ia.elcorteelectrico.com/api/webhooks/whatsapp"
    production_verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    
    if not production_verify_token:
        print("❌ Error: WHATSAPP_WEBHOOK_VERIFY_TOKEN no configurado")
        print("   Asegúrate de configurar esta variable en .env.production")
        return False
    
    print(f"📱 Webhook URL: {production_webhook_url}")
    print(f"🔐 Verify Token: {production_verify_token[:10]}***")
    print()
    
    try:
        # Inicializar servicio de WhatsApp
        whatsapp_service = WhatsApp360DialogService()
        
        # Configurar webhook
        print("⚙️  Configurando webhook...")
        success = await whatsapp_service.configure_webhook(
            webhook_url=production_webhook_url,
            verify_token=production_verify_token
        )
        
        if success:
            print("✅ Webhook configurado exitosamente")
            
            # Verificar configuración
            print("\n🔍 Verificando configuración...")
            webhook_info = await whatsapp_service.get_webhook_info()
            
            if webhook_info:
                print("📋 Información del webhook:")
                print(f"   URL: {webhook_info.get('webhook_url', 'N/A')}")
                print(f"   Estado: {webhook_info.get('status', 'N/A')}")
                print(f"   Eventos: {webhook_info.get('subscribed_events', 'N/A')}")
            
            # Probar conexión
            print("\n🧪 Probando conexión con API...")
            api_status = await whatsapp_service.test_connection()
            
            if api_status:
                print("✅ Conexión con API exitosa")
                print(f"   Número de WhatsApp Business: {api_status.get('phone_number', 'N/A')}")
                print(f"   Estado: {api_status.get('status', 'N/A')}")
            else:
                print("⚠️  No se pudo obtener información de la API")
            
            print("\n🎉 ¡Configuración de producción completada!")
            print("\n📝 Próximos pasos:")
            print("   1. Verifica que el dominio ia.elcorteelectrico.com esté accesible")
            print("   2. Configura el certificado SSL")
            print("   3. Prueba enviando un mensaje de WhatsApp")
            
            return True
            
        else:
            print("❌ Error configurando webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_production_setup():
    """Probar configuración de producción"""
    
    print("\n🧪 PRUEBA DE CONFIGURACIÓN DE PRODUCCIÓN")
    print("=" * 60)
    
    try:
        whatsapp_service = WhatsApp360DialogService()
        
        # 1. Verificar credenciales
        print("1️⃣ Verificando credenciales...")
        api_key = os.getenv("WHATSAPP_360DIALOG_API_KEY")
        if api_key:
            print(f"   ✅ API Key: {api_key[:10]}***")
        else:
            print("   ❌ API Key no configurada")
            return False
        
        # 2. Verificar número de teléfono
        print("2️⃣ Verificando número de WhatsApp Business...")
        phone_number = os.getenv("WHATSAPP_PHONE_NUMBER")
        if phone_number:
            print(f"   ✅ Número: +{phone_number}")
        else:
            print("   ❌ Número no configurado")
            return False
        
        # 3. Verificar webhook
        print("3️⃣ Verificando webhook...")
        webhook_info = await whatsapp_service.get_webhook_info()
        if webhook_info:
            webhook_url = webhook_info.get('webhook_url', 'N/A')
            if 'ia.elcorteelectrico.com' in webhook_url:
                print(f"   ✅ Webhook: {webhook_url}")
            else:
                print(f"   ⚠️  Webhook no apunta a producción: {webhook_url}")
        else:
            print("   ❌ No se pudo obtener información del webhook")
        
        # 4. Verificar templates de mensaje
        print("4️⃣ Verificando templates...")
        try:
            from services.whatsapp_templates import template_manager
            templates = await template_manager.get_available_templates()
            if templates:
                print(f"   ✅ Templates disponibles: {len(templates)}")
                for template in templates[:3]:  # Mostrar primeros 3
                    print(f"      - {template.get('name', 'N/A')}")
            else:
                print("   ⚠️  No se encontraron templates")
        except Exception as e:
            print(f"   ⚠️  Error verificando templates: {e}")
        
        print("\n✅ Configuración de producción verificada")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

async def main():
    """Función principal"""
    
    print("🚀 CONFIGURACIÓN DE WHATSAPP PARA PRODUCCIÓN")
    print("=" * 70)
    print("   Dominio: ia.elcorteelectrico.com")
    print("   Proveedor: 360Dialog")
    print("=" * 70)
    print()
    
    # Verificar variables de entorno críticas
    required_vars = [
        "WHATSAPP_360DIALOG_API_KEY",
        "WHATSAPP_PHONE_NUMBER",
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
        "WHATSAPP_BUSINESS_ACCOUNT_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Variables de entorno faltantes:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Configura estas variables en .env.production")
        return
    
    # Menú de opciones
    while True:
        print("\n📋 Opciones:")
        print("1. Configurar webhook para producción")
        print("2. Probar configuración actual")
        print("3. Mostrar URLs de producción")
        print("4. Salir")
        
        choice = input("\nSelecciona una opción (1-4): ").strip()
        
        if choice == "1":
            await configure_production_webhook()
        elif choice == "2":
            await test_production_setup()
        elif choice == "3":
            print("\n📝 URLs de Producción:")
            print(f"   Webhook WhatsApp: https://ia.elcorteelectrico.com/api/webhooks/whatsapp")
            print(f"   Webhook Carritos: https://ia.elcorteelectrico.com/webhook/cart-abandoned")
            print(f"   Dashboard: https://ia.elcorteelectrico.com/")
            print(f"   API Health: https://ia.elcorteelectrico.com/health")
        elif choice == "4":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    asyncio.run(main())