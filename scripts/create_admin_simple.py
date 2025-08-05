#!/usr/bin/env python3
"""
Script simple para crear el usuario administrador directamente en la base de datos
"""
import asyncio
import asyncpg
import bcrypt
import os

async def main():
    """Crear usuario admin directamente"""
    # Datos de conexión
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://eva_user:VanguardiaAI2025$@postgres:5432/eva_db')
    
    # Datos del usuario
    username = "admin"
    password = "EvaAdmin2025!ElCorte"
    email = "admin@elcorteelectrico.com"
    
    try:
        # Conectar a la base de datos
        print("🔗 Conectando a la base de datos...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Verificar si el usuario ya existe
        existing = await conn.fetchrow("""
            SELECT id, username FROM admin_users 
            WHERE username = $1 OR email = $2
        """, username, email)
        
        if existing:
            print(f"⚠️  El usuario '{username}' ya existe con ID: {existing['id']}")
            
            # Actualizar la contraseña por si acaso
            print("🔐 Actualizando contraseña...")
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            await conn.execute("""
                UPDATE admin_users 
                SET password_hash = $1
                WHERE id = $2
            """, password_hash, existing['id'])
            
            print("✅ Contraseña actualizada exitosamente")
        else:
            # Crear el usuario
            print(f"🔨 Creando usuario '{username}'...")
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            await conn.execute("""
                INSERT INTO admin_users (username, email, password_hash, is_active)
                VALUES ($1, $2, $3, true)
            """, username, email, password_hash)
            
            print("✅ Usuario creado exitosamente")
        
        # Cerrar conexión
        await conn.close()
        
        print(f"\n🎉 Listo! Ahora puedes acceder con:")
        print(f"   - URL: http://ia.elcorteelectrico.com:8080/admin/login")
        print(f"   - Usuario: {username}")
        print(f"   - Contraseña: {password}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())