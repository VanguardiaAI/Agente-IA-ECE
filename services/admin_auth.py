"""
Servicio de autenticación para el panel de administración
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg

from services.database import db_service
from config.settings import settings

logger = logging.getLogger(__name__)

class AdminAuthService:
    """Servicio para manejar autenticación de administradores"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY or "your-secret-key-change-in-production"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 horas
        self.security = HTTPBearer()
        
    async def initialize(self):
        """Inicializar el servicio y verificar tablas"""
        try:
            pool = db_service.pool
            if not pool:
                logger.error("No hay pool de conexiones disponible")
                return False
                
            # Solo verificar si las tablas existen
            async with pool.acquire() as conn:
                # Verificar si las tablas existen
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'admin_users'
                    )
                """)
                
                if not table_exists:
                    logger.warning("⚠️ Las tablas de administración no existen. Ejecuta: python scripts/setup_admin_panel.py")
                    return False
                
            logger.info("✅ Servicio de autenticación admin inicializado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando servicio de auth: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """Hashear una contraseña"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar una contraseña contra su hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Crear un token JWT"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    async def authenticate_admin(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Autenticar un administrador"""
        try:
            pool = db_service.pool
            if not pool:
                return None
                
            async with pool.acquire() as conn:
                # Buscar el usuario
                admin = await conn.fetchrow("""
                    SELECT id, username, email, password_hash, is_active
                    FROM admin_users
                    WHERE username = $1 OR email = $1
                """, username)
                
                if not admin:
                    logger.warning(f"Intento de login fallido: usuario {username} no encontrado")
                    return None
                
                if not admin['is_active']:
                    logger.warning(f"Intento de login en cuenta inactiva: {username}")
                    return None
                
                # Verificar contraseña
                if not self.verify_password(password, admin['password_hash']):
                    logger.warning(f"Contraseña incorrecta para usuario: {username}")
                    return None
                
                # Actualizar último login
                await conn.execute("""
                    UPDATE admin_users 
                    SET last_login = NOW() 
                    WHERE id = $1
                """, admin['id'])
                
                # Crear token
                access_token = self.create_access_token(
                    data={
                        "sub": str(admin['id']),
                        "username": admin['username'],
                        "email": admin['email']
                    }
                )
                
                # Guardar sesión
                await conn.execute("""
                    INSERT INTO admin_sessions (admin_id, token_hash, expires_at)
                    VALUES ($1, $2, $3)
                """, admin['id'], 
                    bcrypt.hashpw(access_token[:20].encode(), bcrypt.gensalt()).decode(),
                    datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes))
                
                logger.info(f"✅ Login exitoso para admin: {username}")
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": admin['id'],
                        "username": admin['username'],
                        "email": admin['email']
                    }
                }
                
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return None
    
    async def get_current_admin(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Obtener el admin actual desde el token JWT"""
        token = credentials.credentials
        
        try:
            # Decodificar token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            admin_id = payload.get("sub")
            
            if admin_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verificar que el admin existe y está activo
            pool = db_service.pool
            if not pool:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Base de datos no disponible"
                )
                
            async with pool.acquire() as conn:
                admin = await conn.fetchrow("""
                    SELECT id, username, email, is_active
                    FROM admin_users
                    WHERE id = $1 AND is_active = true
                """, int(admin_id))
                
                if not admin:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Usuario no encontrado o inactivo",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                return {
                    "id": admin['id'],
                    "username": admin['username'],
                    "email": admin['email']
                }
                
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def logout(self, admin_id: int, token: str):
        """Cerrar sesión invalidando el token"""
        try:
            pool = db_service.pool
            if not pool:
                return False
                
            async with pool.acquire() as conn:
                # Invalidar todas las sesiones activas del admin
                await conn.execute("""
                    UPDATE admin_sessions 
                    SET is_active = false 
                    WHERE admin_id = $1 AND is_active = true
                """, admin_id)
                
            logger.info(f"✅ Logout exitoso para admin ID: {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error en logout: {e}")
            return False
    
    async def create_admin(self, username: str, email: str, password: str) -> bool:
        """Crear un nuevo administrador"""
        try:
            pool = db_service.pool
            if not pool:
                return False
                
            async with pool.acquire() as conn:
                # Verificar que no exista
                existing = await conn.fetchrow("""
                    SELECT id FROM admin_users 
                    WHERE username = $1 OR email = $2
                """, username, email)
                
                if existing:
                    logger.warning(f"Intento de crear admin duplicado: {username}")
                    return False
                
                # Crear el admin
                password_hash = self.hash_password(password)
                await conn.execute("""
                    INSERT INTO admin_users (username, email, password_hash)
                    VALUES ($1, $2, $3)
                """, username, email, password_hash)
                
                logger.info(f"✅ Admin creado: {username}")
                return True
                
        except Exception as e:
            logger.error(f"Error creando admin: {e}")
            return False
    
    async def log_activity(self, admin_id: int, action: str, entity_type: str = None, 
                          entity_id: str = None, details: Dict = None, 
                          ip_address: str = None, user_agent: str = None):
        """Registrar actividad del administrador"""
        try:
            pool = db_service.pool
            if not pool:
                return
                
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO admin_activity_logs 
                    (admin_id, action, entity_type, entity_id, details, ip_address, user_agent)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, admin_id, action, entity_type, entity_id, 
                    json.dumps(details) if details else None,
                    ip_address, user_agent)
                    
        except Exception as e:
            logger.error(f"Error registrando actividad: {e}")

# Instancia global del servicio
admin_auth_service = AdminAuthService()

# Función de dependencia para FastAPI
async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Dependencia para obtener el admin actual en endpoints protegidos"""
    return await admin_auth_service.get_current_admin(credentials)