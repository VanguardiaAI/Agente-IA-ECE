#!/usr/bin/env python3
"""
Script para crear el usuario administrador en la base de datos
"""
import asyncio
import sys
import os
sys.path.append('/app')

from services.admin_auth import AdminAuthService

async def main():
    """Crear usuario admin con las credenciales por defecto"""
    try:
        auth = AdminAuthService()
        
        # Inicializar el servicio
        await auth.initialize()
        
        # Datos del usuario
        username = "admin"
        password = "EvaAdmin2025!ElCorte"
        email = "admin@elcorteelectrico.com"
        
        # Intentar autenticar primero para ver si ya existe
        print(f"🔍 Verificando si el usuario '{username}' ya existe...")
        login_result = await auth.authenticate_admin(username, password)
        
        if login_result:
            print(f"✅ El usuario '{username}' ya existe y la contraseña es correcta")
            print(f"🌐 Puedes acceder a: http://ia.elcorteelectrico.com:8080/admin/login")
            return
        
        # Crear el usuario (nota: el orden es username, email, password)
        print(f"🔨 Creando usuario administrador '{username}'...")
        result = await auth.create_admin(username, email, password)
        
        if result:
            print(f"✅ Usuario administrador creado exitosamente")
            print(f"   - Usuario: {username}")
            print(f"   - Email: {email}")
            print(f"   - Contraseña: {password}")
            print(f"\n🌐 Ahora puedes acceder a: http://ia.elcorteelectrico.com:8080/admin/login")
        else:
            print("❌ Error al crear el usuario (puede que ya exista)")
            print("Intentando hacer login de todas formas...")
            login_test = await auth.authenticate_admin(username, password)
            if login_test:
                print("✅ El usuario existe y puedes hacer login")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())