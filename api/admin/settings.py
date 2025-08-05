"""
API de configuraciones para el panel de administración
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from services.bot_config_service import bot_config_service
from services.admin_auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/settings", tags=["Admin Settings"])

class SettingUpdate(BaseModel):
    key: str
    value: Any
    category: Optional[str] = "general"
    description: Optional[str] = None

class BulkSettingsUpdate(BaseModel):
    settings: List[SettingUpdate]

@router.get("/")
async def get_all_settings(current_admin: dict = Depends(get_current_admin)):
    """Obtener todas las configuraciones del bot"""
    try:
        settings = await bot_config_service.get_all_settings()
        return settings
        
    except Exception as e:
        logger.error(f"Error obteniendo configuraciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener configuraciones"
        )

@router.get("/category/{category}")
async def get_settings_by_category(
    category: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Obtener configuraciones por categoría"""
    try:
        settings = await bot_config_service.get_settings_by_category(category)
        return settings
        
    except Exception as e:
        logger.error(f"Error obteniendo configuraciones de {category}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener configuraciones de {category}"
        )

@router.get("/{key}")
async def get_setting(
    key: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Obtener una configuración específica"""
    try:
        value = await bot_config_service.get_setting(key)
        
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuración '{key}' no encontrada"
            )
        
        return {"key": key, "value": value}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo configuración {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener configuración {key}"
        )

@router.put("/")
async def update_setting(
    setting: SettingUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    """Actualizar una configuración"""
    try:
        success = await bot_config_service.set_setting(
            key=setting.key,
            value=setting.value,
            category=setting.category,
            description=setting.description,
            admin_id=current_admin['id']
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar configuración"
            )
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "update_setting",
            entity_type="setting",
            entity_id=setting.key,
            details={"value": setting.value, "category": setting.category}
        )
        
        return {
            "message": f"Configuración '{setting.key}' actualizada exitosamente",
            "key": setting.key,
            "value": setting.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando configuración: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar configuración"
        )

@router.put("/bulk")
async def bulk_update_settings(
    request: BulkSettingsUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    """Actualizar múltiples configuraciones"""
    try:
        updated = []
        failed = []
        
        for setting in request.settings:
            success = await bot_config_service.set_setting(
                key=setting.key,
                value=setting.value,
                category=setting.category,
                description=setting.description,
                admin_id=current_admin['id']
            )
            
            if success:
                updated.append(setting.key)
            else:
                failed.append(setting.key)
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "bulk_update_settings",
            details={"updated": updated, "failed": failed}
        )
        
        return {
            "message": f"Actualizadas {len(updated)} configuraciones",
            "updated": updated,
            "failed": failed
        }
        
    except Exception as e:
        logger.error(f"Error en actualización masiva: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar configuraciones"
        )

@router.post("/reset")
async def reset_to_defaults(current_admin: dict = Depends(get_current_admin)):
    """Restablecer todas las configuraciones a valores por defecto"""
    try:
        success = await bot_config_service.reset_to_defaults(admin_id=current_admin['id'])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al restablecer configuraciones"
            )
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "reset_settings"
        )
        
        return {"message": "Configuraciones restablecidas a valores por defecto"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restableciendo configuraciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al restablecer configuraciones"
        )

@router.get("/export/json")
async def export_settings(current_admin: dict = Depends(get_current_admin)):
    """Exportar todas las configuraciones en formato JSON"""
    try:
        export_data = await bot_config_service.export_settings()
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "export_settings"
        )
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exportando configuraciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al exportar configuraciones"
        )

@router.post("/import")
async def import_settings(
    import_data: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """Importar configuraciones desde JSON"""
    try:
        success = await bot_config_service.import_settings(
            import_data,
            admin_id=current_admin['id']
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de importación inválido"
            )
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "import_settings",
            details={"settings_count": len(import_data.get('settings', {}))}
        )
        
        return {"message": "Configuraciones importadas exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importando configuraciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al importar configuraciones"
        )