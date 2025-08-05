"""
API de autenticación para el panel de administración
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import logging

from services.admin_auth import admin_auth_service, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class AdminCreateRequest(BaseModel):
    username: str
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login")
async def login(request: LoginRequest):
    """Endpoint de login para administradores"""
    try:
        result = await admin_auth_service.authenticate_admin(
            request.username, 
            request.password
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        # Registrar actividad
        await admin_auth_service.log_activity(
            result['user']['id'],
            "login",
            details={"username": request.username}
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/logout")
async def logout(current_admin: dict = Depends(get_current_admin)):
    """Endpoint de logout para administradores"""
    try:
        # Registrar actividad antes de cerrar sesión
        await admin_auth_service.log_activity(
            current_admin['id'],
            "logout"
        )
        
        # Invalidar token/sesión
        await admin_auth_service.logout(current_admin['id'], "")
        
        return {"message": "Sesión cerrada exitosamente"}
        
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cerrar sesión"
        )

@router.get("/verify")
async def verify_token(current_admin: dict = Depends(get_current_admin)):
    """Verificar si el token es válido"""
    return {
        "valid": True,
        "user": current_admin
    }

@router.get("/me")
async def get_current_user(current_admin: dict = Depends(get_current_admin)):
    """Obtener información del usuario actual"""
    return current_admin

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Cambiar contraseña del administrador actual"""
    try:
        # Verificar contraseña actual
        from services.database import db_service
        
        pool = db_service.pool
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible"
            )
        
        async with pool.acquire() as conn:
            admin = await conn.fetchrow("""
                SELECT password_hash FROM admin_users WHERE id = $1
            """, current_admin['id'])
            
            if not admin_auth_service.verify_password(
                request.current_password, 
                admin['password_hash']
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Contraseña actual incorrecta"
                )
            
            # Actualizar contraseña
            new_hash = admin_auth_service.hash_password(request.new_password)
            await conn.execute("""
                UPDATE admin_users 
                SET password_hash = $1, updated_at = NOW()
                WHERE id = $2
            """, new_hash, current_admin['id'])
        
        # Registrar actividad
        await admin_auth_service.log_activity(
            current_admin['id'],
            "change_password"
        )
        
        return {"message": "Contraseña actualizada exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar contraseña"
        )

@router.post("/create-admin")
async def create_admin(
    request: AdminCreateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Crear un nuevo administrador (solo para super admin)"""
    try:
        # Por ahora todos los admins pueden crear otros admins
        # En el futuro se puede agregar verificación de permisos
        
        success = await admin_auth_service.create_admin(
            request.username,
            request.email,
            request.password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario o email ya existe"
            )
        
        # Registrar actividad
        await admin_auth_service.log_activity(
            current_admin['id'],
            "create_admin",
            entity_type="admin",
            entity_id=request.username,
            details={"email": request.email}
        )
        
        return {"message": f"Administrador {request.username} creado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear administrador"
        )

@router.get("/activity-logs")
async def get_activity_logs(
    limit: int = 100,
    current_admin: dict = Depends(get_current_admin)
):
    """Obtener logs de actividad recientes"""
    try:
        from services.database import db_service
        
        pool = db_service.pool
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible"
            )
        
        async with pool.acquire() as conn:
            logs = await conn.fetch("""
                SELECT 
                    aal.id,
                    au.username,
                    aal.action,
                    aal.entity_type,
                    aal.entity_id,
                    aal.details,
                    aal.ip_address,
                    aal.created_at
                FROM admin_activity_logs aal
                JOIN admin_users au ON aal.admin_id = au.id
                ORDER BY aal.created_at DESC
                LIMIT $1
            """, limit)
            
            return [
                {
                    "id": log['id'],
                    "username": log['username'],
                    "action": log['action'],
                    "entity_type": log['entity_type'],
                    "entity_id": log['entity_id'],
                    "details": log['details'],
                    "ip_address": log['ip_address'],
                    "created_at": log['created_at'].isoformat() if log['created_at'] else None
                }
                for log in logs
            ]
            
    except Exception as e:
        logger.error(f"Error obteniendo logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener logs de actividad"
        )