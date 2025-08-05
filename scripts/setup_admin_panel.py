#!/usr/bin/env python3
"""
Script para configurar el panel de administración
Crea las tablas necesarias y un usuario admin por defecto
"""

import asyncio
import sys
from pathlib import Path
import getpass

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.admin_auth import admin_auth_service
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_admin_tables():
    """Crear las tablas de administración en la base de datos"""
    try:
        logger.info("🔨 Creando tablas de administración...")
        
        pool = db_service.pool
        if not pool:
            logger.error("No hay pool de conexiones disponible")
            return False
        
        # Leer el script SQL simplificado
        script_path = Path(__file__).parent / "create_admin_tables_simple.sql"
        if not script_path.exists():
            # Si no existe el simplificado, intentar el original
            script_path = Path(__file__).parent / "create_admin_tables.sql"
            if not script_path.exists():
                logger.error(f"Script SQL no encontrado")
                return False
        
        with open(script_path, 'r') as f:
            sql_script = f.read()
        
        async with pool.acquire() as conn:
            # Dividir el script en sentencias individuales
            # Eliminar comentarios y dividir por punto y coma
            statements = []
            current_statement = []
            
            for line in sql_script.split('\n'):
                # Ignorar líneas de comentario
                if line.strip().startswith('--') or not line.strip():
                    continue
                
                current_statement.append(line)
                
                # Si la línea termina con punto y coma, es el final de una sentencia
                if line.rstrip().endswith(';'):
                    statement = '\n'.join(current_statement)
                    if statement.strip():
                        statements.append(statement)
                    current_statement = []
            
            # Si queda algo sin punto y coma al final
            if current_statement:
                statement = '\n'.join(current_statement)
                if statement.strip():
                    statements.append(statement)
            
            # Ejecutar cada sentencia por separado
            for i, statement in enumerate(statements, 1):
                try:
                    # Saltar vistas que pueden dar problemas
                    if 'CREATE OR REPLACE VIEW' in statement:
                        logger.info(f"⏭️ Saltando vista (se creará manualmente si es necesario)")
                        continue
                    
                    await conn.execute(statement)
                    logger.info(f"✅ Sentencia {i}/{len(statements)} ejecutada")
                except Exception as e:
                    # Si es un error de "ya existe", continuamos
                    if "already exists" in str(e) or "ya existe" in str(e):
                        logger.info(f"ℹ️ Sentencia {i} - Objeto ya existe, continuando...")
                    else:
                        logger.warning(f"⚠️ Error en sentencia {i}: {e}")
                        # Continuamos con las demás sentencias
        
        logger.info("✅ Tablas de administración creadas/verificadas exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        return False

async def create_default_admin():
    """Crear un usuario administrador por defecto"""
    try:
        logger.info("\n🔐 Configuración del usuario administrador")
        
        # Solicitar datos del admin
        print("\nIngresa los datos del administrador principal:")
        username = input("Usuario (default: admin): ").strip() or "admin"
        email = input("Email (default: admin@elcorteelectrico.com): ").strip() or "admin@elcorteelectrico.com"
        
        # Solicitar contraseña de forma segura
        while True:
            password = getpass.getpass("Contraseña: ")
            if len(password) < 6:
                print("❌ La contraseña debe tener al menos 6 caracteres")
                continue
            
            password_confirm = getpass.getpass("Confirmar contraseña: ")
            if password != password_confirm:
                print("❌ Las contraseñas no coinciden")
                continue
            
            break
        
        # Crear el admin
        success = await admin_auth_service.create_admin(username, email, password)
        
        if success:
            logger.info(f"✅ Usuario administrador '{username}' creado exitosamente")
            return True
        else:
            logger.error("❌ Error creando usuario administrador (puede que ya exista)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creando admin: {e}")
        return False

async def main():
    """Función principal"""
    try:
        print("=" * 60)
        print("🚀 CONFIGURACIÓN DEL PANEL DE ADMINISTRACIÓN")
        print("=" * 60)
        
        # Inicializar base de datos
        logger.info("📊 Inicializando conexión a base de datos...")
        await db_service.initialize()
        logger.info("✅ Base de datos conectada")
        
        # Inicializar servicio de autenticación
        logger.info("🔑 Inicializando servicio de autenticación...")
        await admin_auth_service.initialize()
        logger.info("✅ Servicio de autenticación inicializado")
        
        # Crear tablas si no existen
        pool = db_service.pool
        if pool:
            async with pool.acquire() as conn:
                # Verificar si las tablas ya existen
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'admin_users'
                    )
                """)
                
                if not table_exists:
                    # Crear tablas
                    await create_admin_tables()
                else:
                    logger.info("ℹ️ Las tablas de administración ya existen")
        
        # Verificar si ya hay admins
        if pool:
            async with pool.acquire() as conn:
                admin_count = await conn.fetchval("SELECT COUNT(*) FROM admin_users")
                
                if admin_count == 0:
                    # No hay admins, crear uno
                    await create_default_admin()
                else:
                    logger.info(f"ℹ️ Ya existen {admin_count} administrador(es)")
                    
                    # Preguntar si quiere crear otro
                    create_new = input("\n¿Deseas crear un nuevo administrador? (s/n): ").strip().lower()
                    if create_new == 's':
                        await create_default_admin()
        
        print("\n" + "=" * 60)
        print("✅ CONFIGURACIÓN COMPLETADA")
        print("=" * 60)
        print("\n📌 Instrucciones para acceder al panel:")
        print("1. Inicia la aplicación: python app.py")
        print("2. Abre tu navegador en: http://localhost:8080/admin/login")
        print("3. Ingresa con las credenciales que configuraste")
        print("\n💡 Características del panel:")
        print("   - Configuración completa del bot")
        print("   - Editor de Knowledge Base")
        print("   - Métricas y estadísticas")
        print("   - Prueba del bot en tiempo real")
        print("   - Gestión de configuraciones avanzadas")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error en configuración: {e}")
        raise
    finally:
        # Cerrar conexiones
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(main())