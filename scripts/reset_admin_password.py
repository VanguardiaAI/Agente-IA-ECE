#!/usr/bin/env python3
"""
Script para resetear la contraseña del administrador
"""

import asyncio
import sys
from pathlib import Path
import bcrypt

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def reset_admin_password():
    """Resetear la contraseña del admin a la predefinida"""
    try:
        # Inicializar base de datos
        logger.info("📊 Conectando a base de datos...")
        await db_service.initialize()
        
        pool = db_service.pool
        if not pool:
            logger.error("No hay pool de conexiones disponible")
            return False
        
        # La contraseña predefinida
        password = "EvaAdmin2025!ElCorte"
        
        # Hashear la contraseña
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        password_hash = hashed.decode('utf-8')
        
        async with pool.acquire() as conn:
            # Primero verificar si existe la tabla
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'admin_users'
                )
            """)
            
            if not table_exists:
                logger.error("❌ La tabla admin_users no existe. Ejecuta primero: python scripts/setup_admin_panel.py")
                return False
            
            # Verificar si existe el usuario admin
            admin_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM admin_users 
                    WHERE username = 'admin'
                )
            """)
            
            if admin_exists:
                # Actualizar la contraseña
                await conn.execute("""
                    UPDATE admin_users 
                    SET password_hash = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE username = 'admin'
                """, password_hash)
                logger.info("✅ Contraseña del usuario 'admin' actualizada")
            else:
                # Crear el usuario admin
                await conn.execute("""
                    INSERT INTO admin_users (username, email, password_hash, is_active)
                    VALUES ($1, $2, $3, true)
                """, 'admin', 'admin@elcorteelectrico.com', password_hash)
                logger.info("✅ Usuario 'admin' creado")
            
            logger.info("\n" + "="*60)
            logger.info("✅ CONTRASEÑA RESETEADA EXITOSAMENTE")
            logger.info("="*60)
            logger.info("Usuario: admin")
            logger.info("Contraseña: EvaAdmin2025!ElCorte")
            logger.info("URL: http://localhost:8080/admin")
            logger.info("="*60)
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    finally:
        await db_service.close()

async def main():
    """Función principal"""
    await reset_admin_password()

if __name__ == "__main__":
    asyncio.run(main())