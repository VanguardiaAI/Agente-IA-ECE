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
        
        # Verificar si el usuario ya existe
        username = "admin"
        password = "EvaAdmin2025!ElCorte"
        email = "admin@elcorteelectrico.com"
        
        # Intentar verificar si ya existe
        exists = await auth.verify_admin(username, password)
        if exists:
            print(f"✅ El usuario '{username}' ya existe y la contraseña es correcta")
            return
        
        # Crear el usuario
        print(f"🔨 Creando usuario administrador '{username}'...")
        result = await auth.create_admin(username, password, email)
        
        if result:
            print(f"✅ Usuario administrador creado exitosamente")
            print(f"   - Usuario: {username}")
            print(f"   - Email: {email}")
            print(f"   - Contraseña: {password}")
            print(f"\n🌐 Ahora puedes acceder a: http://ia.elcorteelectrico.com:8080/admin/login")
        else:
            print("❌ Error al crear el usuario (puede que ya exista)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())