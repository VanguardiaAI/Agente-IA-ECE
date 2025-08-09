#!/usr/bin/env python3
"""
Script para verificar la configuración del sistema y diagnosticar problemas
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

def check_env_files():
    """Verificar la existencia de archivos de configuración"""
    print("🔍 Verificando archivos de configuración...\n")
    
    files_to_check = [
        ('.env', 'Configuración principal'),
        ('env.agent', 'Configuración del agente'),
        ('.env.example', 'Ejemplo de configuración'),
        ('env.agent.example', 'Ejemplo de configuración del agente'),
        ('.env.development', 'Configuración de desarrollo')
    ]
    
    for file, description in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} encontrado - {description}")
        else:
            print(f"❌ {file} NO encontrado - {description}")
    
    print()

def check_environment():
    """Verificar el modo de entorno"""
    load_dotenv()
    
    env_mode = os.getenv("ENVIRONMENT", "development")
    print(f"🌍 Modo de entorno: {env_mode}")
    
    if env_mode == "development":
        print("   ℹ️  Ejecutando en modo desarrollo - se usarán valores por defecto para configuraciones faltantes")
    else:
        print("   ⚠️  Ejecutando en modo producción - todas las configuraciones son obligatorias")
    
    print()

def check_required_vars():
    """Verificar variables de entorno requeridas"""
    print("🔧 Verificando variables de entorno...\n")
    
    # Variables críticas
    critical_vars = {
        'WOOCOMMERCE_API_URL': 'URL de la API de WooCommerce',
        'WOOCOMMERCE_CONSUMER_KEY': 'Consumer Key de WooCommerce',
        'WOOCOMMERCE_CONSUMER_SECRET': 'Consumer Secret de WooCommerce',
        'POSTGRES_PASSWORD': 'Contraseña de PostgreSQL',
        'OPENAI_API_KEY': 'API Key de OpenAI'
    }
    
    # Variables opcionales
    optional_vars = {
        'WHATSAPP_360DIALOG_API_KEY': 'API Key de WhatsApp (opcional)',
        'SENTRY_DSN': 'DSN de Sentry para monitoreo (opcional)',
        'JWT_SECRET_KEY': 'Secret key para JWT (opcional)'
    }
    
    env_mode = os.getenv("ENVIRONMENT", "development")
    missing_critical = []
    
    print("Variables críticas:")
    for var, description in critical_vars.items():
        value = os.getenv(var)
        if value:
            # Ocultar valores sensibles
            display_value = value[:8] + "..." if len(value) > 10 else "***"
            print(f"  ✅ {var}: {display_value} - {description}")
        else:
            print(f"  ❌ {var}: NO CONFIGURADO - {description}")
            if env_mode == "production":
                missing_critical.append(var)
    
    print("\nVariables opcionales:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            display_value = value[:8] + "..." if len(value) > 10 else "***"
            print(f"  ✅ {var}: {display_value} - {description}")
        else:
            print(f"  ⚪ {var}: No configurado - {description}")
    
    print()
    return missing_critical

def suggest_fixes(missing_vars):
    """Sugerir soluciones para variables faltantes"""
    if not missing_vars:
        return
    
    print("💡 SUGERENCIAS DE SOLUCIÓN:\n")
    
    env_mode = os.getenv("ENVIRONMENT", "development")
    
    if env_mode == "development":
        print("Para desarrollo local, tienes varias opciones:\n")
        print("1. Usar valores por defecto (más simple):")
        print("   cp .env.development .env")
        print("   # Los valores por defecto se usarán automáticamente\n")
        
        print("2. Configurar servicios reales:")
        print("   cp .env.example .env")
        print("   # Luego editar .env con tus credenciales\n")
    else:
        print("En modo producción, debes configurar todas las variables:\n")
        print("1. Copia el archivo de ejemplo:")
        print("   cp .env.example .env\n")
        
        print("2. Edita .env y configura:")
        for var in missing_vars:
            print(f"   {var}=tu_valor_aqui")

def test_imports():
    """Probar importaciones críticas"""
    print("\n📦 Verificando importaciones...\n")
    
    imports_to_test = [
        ('pydantic', 'Pydantic (validación de datos)'),
        ('fastapi', 'FastAPI (servidor web)'),
        ('asyncpg', 'AsyncPG (PostgreSQL async)'),
        ('openai', 'OpenAI SDK'),
        ('woocommerce', 'WooCommerce API'),
        ('pgvector', 'pgvector (búsqueda vectorial)')
    ]
    
    for module, description in imports_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module} - {description}")
        except ImportError:
            print(f"  ❌ {module} - {description} - Instalar con: pip install -r requirements.txt")

def main():
    """Función principal"""
    print("=" * 60)
    print("🔧 DIAGNÓSTICO DE CONFIGURACIÓN - EVA AI")
    print("=" * 60)
    print()
    
    # Verificar archivos
    check_env_files()
    
    # Verificar entorno
    check_environment()
    
    # Verificar variables
    missing_vars = check_required_vars()
    
    # Verificar importaciones
    test_imports()
    
    # Sugerir soluciones
    if missing_vars:
        suggest_fixes(missing_vars)
    
    # Resumen final
    print("\n" + "=" * 60)
    if missing_vars and os.getenv("ENVIRONMENT", "development") == "production":
        print("❌ RESULTADO: Configuración incompleta para producción")
        print(f"   Faltan {len(missing_vars)} variables críticas")
        sys.exit(1)
    else:
        print("✅ RESULTADO: Configuración lista para ejecutar")
        if os.getenv("ENVIRONMENT", "development") == "development":
            print("   Modo desarrollo activo - usando valores por defecto")
    print("=" * 60)

if __name__ == "__main__":
    main()