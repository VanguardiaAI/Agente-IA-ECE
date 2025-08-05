"""
API de gestión de knowledge base para el panel de administración
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import os
from pathlib import Path
import aiofiles

from services.knowledge_base import knowledge_service
from services.admin_auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/knowledge", tags=["Admin Knowledge"])

class KnowledgeDocument(BaseModel):
    filename: str
    content: str
    category: str
    title: Optional[str] = None

class KnowledgeUpdate(BaseModel):
    content: str
    title: Optional[str] = None

@router.get("/documents")
async def get_all_documents(current_admin: dict = Depends(get_current_admin)):
    """Obtener lista de todos los documentos de knowledge base"""
    try:
        knowledge_dir = Path("knowledge")
        documents = []
        
        for root, dirs, files in os.walk(knowledge_dir):
            root_path = Path(root)
            relative_path = root_path.relative_to(knowledge_dir)
            
            for file in files:
                if file.endswith('.md'):
                    file_path = root_path / file
                    
                    # Leer contenido del archivo
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Determinar categoría
                    category = "general"
                    if "policies" in str(relative_path):
                        category = "policies"
                    elif "faqs" in str(relative_path):
                        category = "faqs"
                    
                    # Extraer título
                    title = "Sin título"
                    for line in content.split('\n'):
                        if line.startswith('# '):
                            title = line[2:].strip()
                            break
                    
                    documents.append({
                        "filename": str(file_path.relative_to(knowledge_dir)),
                        "title": title,
                        "category": category,
                        "size": len(content),
                        "modified": os.path.getmtime(file_path)
                    })
        
        return documents
        
    except Exception as e:
        logger.error(f"Error obteniendo documentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener documentos"
        )

@router.get("/document/{filename:path}")
async def get_document(
    filename: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Obtener contenido de un documento específico"""
    try:
        file_path = Path("knowledge") / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento '{filename}' no encontrado"
            )
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraer título
        title = "Sin título"
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        return {
            "filename": filename,
            "title": title,
            "content": content,
            "modified": os.path.getmtime(file_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo documento {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener documento {filename}"
        )

@router.put("/document/{filename:path}")
async def update_document(
    filename: str,
    update: KnowledgeUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    """Actualizar contenido de un documento"""
    try:
        file_path = Path("knowledge") / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento '{filename}' no encontrado"
            )
        
        # Si se proporciona título, actualizar en el contenido
        content = update.content
        if update.title:
            # Reemplazar o agregar título al inicio
            lines = content.split('\n')
            if lines and lines[0].startswith('# '):
                lines[0] = f"# {update.title}"
            else:
                lines.insert(0, f"# {update.title}\n")
            content = '\n'.join(lines)
        
        # Guardar archivo
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        # Recargar en la base de datos vectorial
        doc_type = "general"
        if "policies" in str(file_path):
            doc_type = "policy"
        elif "faqs" in str(file_path):
            doc_type = "faq"
        
        success = await knowledge_service.load_markdown_file(file_path, doc_type)
        
        if not success:
            logger.warning(f"No se pudo actualizar embeddings para {filename}")
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "update_knowledge",
            entity_type="knowledge",
            entity_id=filename,
            details={"title": update.title}
        )
        
        return {
            "message": f"Documento '{filename}' actualizado exitosamente",
            "embeddings_updated": success
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar documento"
        )

@router.post("/document")
async def create_document(
    document: KnowledgeDocument,
    current_admin: dict = Depends(get_current_admin)
):
    """Crear un nuevo documento"""
    try:
        # Determinar directorio según categoría
        base_dir = Path("knowledge")
        if document.category == "policies":
            target_dir = base_dir / "policies"
        elif document.category == "faqs":
            target_dir = base_dir / "faqs"
        else:
            target_dir = base_dir
        
        # Crear directorio si no existe
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear archivo
        file_path = target_dir / document.filename
        
        if file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El documento '{document.filename}' ya existe"
            )
        
        # Agregar título si se proporciona
        content = document.content
        if document.title:
            if not content.startswith('# '):
                content = f"# {document.title}\n\n{content}"
        
        # Guardar archivo
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        # Cargar en la base de datos vectorial
        doc_type = "general"
        if document.category == "policies":
            doc_type = "policy"
        elif document.category == "faqs":
            doc_type = "faq"
        
        success = await knowledge_service.load_markdown_file(file_path, doc_type)
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "create_knowledge",
            entity_type="knowledge",
            entity_id=str(file_path.relative_to(base_dir)),
            details={"category": document.category, "title": document.title}
        )
        
        return {
            "message": f"Documento '{document.filename}' creado exitosamente",
            "path": str(file_path.relative_to(base_dir)),
            "embeddings_created": success
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear documento"
        )

@router.delete("/document/{filename:path}")
async def delete_document(
    filename: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Eliminar un documento"""
    try:
        file_path = Path("knowledge") / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento '{filename}' no encontrado"
            )
        
        # Eliminar archivo
        os.remove(file_path)
        
        # Eliminar de la base de datos vectorial
        from services.database import db_service
        
        pool = db_service.pool
        if pool:
            async with pool.acquire() as conn:
                # Buscar y eliminar por external_id que contiene el filename
                doc_id_base = Path(filename).stem
                await conn.execute("""
                    DELETE FROM knowledge_base 
                    WHERE external_id LIKE $1
                """, f"%{doc_id_base}%")
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "delete_knowledge",
            entity_type="knowledge",
            entity_id=filename
        )
        
        return {"message": f"Documento '{filename}' eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar documento"
        )

@router.post("/reload")
async def reload_all_documents(current_admin: dict = Depends(get_current_admin)):
    """Recargar todos los documentos en la base de datos vectorial"""
    try:
        results = await knowledge_service.load_all_documents()
        
        # Registrar actividad
        from services.admin_auth import admin_auth_service
        await admin_auth_service.log_activity(
            current_admin['id'],
            "reload_knowledge",
            details=results
        )
        
        return {
            "message": "Documentos recargados exitosamente",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error recargando documentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recargar documentos"
        )

@router.post("/search")
async def search_knowledge(
    query: str,
    limit: int = 5,
    current_admin: dict = Depends(get_current_admin)
):
    """Buscar en la base de conocimientos"""
    try:
        results = await knowledge_service.search_knowledge(query, limit=limit)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error buscando en knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar en knowledge base"
        )