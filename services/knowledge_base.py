"""
Sistema de Base de Conocimientos para El Corte Eléctrico
Carga y gestiona documentos .md como fuente de conocimiento para RAG
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json

from services.database import db_service
from services.embedding_service import embedding_service
from config.settings import settings

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """Servicio para gestionar la base de conocimientos de la empresa"""
    
    def __init__(self):
        self.knowledge_dir = Path("knowledge")
        self.db_service = db_service
        self.embedding_service = embedding_service
        self.enabled = True
        
    async def initialize(self):
        """Inicializar el servicio y crear tabla si es necesario"""
        try:
            await self._create_knowledge_table()
            logger.info("✅ Sistema de Knowledge Base inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando Knowledge Base: {e}")
            self.enabled = False
    
    async def _create_knowledge_table(self):
        """Crear tabla para almacenar documentos de conocimiento"""
        # Usar el pool directamente del db_service
        pool = self.db_service.pool
        if not pool:
            logger.error("No hay pool de conexiones disponible")
            return
        async with pool.acquire() as conn:
            # Crear extensión vector si no existe
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # La tabla knowledge_base ya existe con estructura diferente
            # No necesitamos crearla
            
            # Los índices ya existen en la tabla
    
    def _calculate_hash(self, content: str) -> str:
        """Calcular hash del contenido para detectar cambios"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _split_content(self, content: str, max_length: int = 1500) -> List[str]:
        """Dividir contenido largo en chunks manejables"""
        # Dividir por párrafos primero
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si el párrafo solo cabe en un nuevo chunk
            if len(current_chunk) + len(paragraph) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Si un chunk es muy largo, dividirlo por oraciones
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_length:
                sentences = chunk.split('. ')
                sub_chunk = ""
                for sentence in sentences:
                    if len(sub_chunk) + len(sentence) + 2 > max_length:
                        if sub_chunk:
                            final_chunks.append(sub_chunk.strip())
                        sub_chunk = sentence + "."
                    else:
                        if sub_chunk:
                            sub_chunk += " "
                        sub_chunk += sentence + "."
                if sub_chunk:
                    final_chunks.append(sub_chunk.strip())
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    async def load_markdown_file(self, file_path: Path, doc_type: str = "general") -> bool:
        """Cargar un archivo markdown en la base de conocimientos"""
        try:
            # Leer contenido del archivo
            content = file_path.read_text(encoding='utf-8')
            title = self._extract_title(content)
            doc_id = f"{doc_type}_{file_path.stem}"
            
            # Calcular hash para detectar cambios
            content_hash = self._calculate_hash(content)
            
            # Verificar si ya existe y si cambió
            pool = self.db_service.pool
            if not pool:
                logger.error("No hay pool de conexiones disponible")
                return False
            async with pool.acquire() as conn:
                # Buscar si ya existe por external_id
                existing = await conn.fetchrow(
                    "SELECT id, metadata FROM knowledge_base WHERE external_id = $1 AND content_type = $2",
                    doc_id, doc_type
                )
                
                if existing and existing['metadata'] and existing['metadata'].get('hash') == content_hash:
                    logger.info(f"ℹ️ Documento {doc_id} sin cambios, omitiendo")
                    return True
                
                # Si cambió o es nuevo, eliminar versión anterior
                if existing:
                    await conn.execute(
                        "DELETE FROM knowledge_base WHERE external_id = $1",
                        doc_id
                    )
                    logger.info(f"🔄 Actualizando documento {doc_id}")
            
            # Dividir en chunks si es muy largo
            chunks = self._split_content(content)
            total_chunks = len(chunks)
            
            # Procesar cada chunk
            for idx, chunk_content in enumerate(chunks):
                chunk_doc_id = f"{doc_id}_chunk_{idx}" if total_chunks > 1 else doc_id
                
                # Generar embedding
                embedding = await self.embedding_service.generate_embedding(
                    f"{title}\n\n{chunk_content}"
                )
                
                if not embedding:
                    logger.error(f"Error generando embedding para {chunk_doc_id}")
                    continue
                
                # Preparar metadata
                metadata = {
                    "file_name": file_path.name,
                    "doc_type": doc_type,
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "original_doc_id": doc_id,
                    "hash": content_hash
                }
                
                # Insertar en base de datos usando estructura existente
                async with pool.acquire() as conn:
                    # Convertir embedding a formato pgvector
                    embedding_str = f"[{','.join(map(str, embedding))}]"
                    
                    # Verificar si ya existe y eliminar
                    existing = await conn.fetchrow(
                        "SELECT id FROM knowledge_base WHERE external_id = $1",
                        chunk_doc_id
                    )
                    if existing:
                        await conn.execute(
                            "DELETE FROM knowledge_base WHERE external_id = $1",
                            chunk_doc_id
                        )
                    
                    # Insertar nuevo documento
                    await conn.execute("""
                        INSERT INTO knowledge_base 
                        (content_type, title, content, external_id, 
                         embedding, metadata, is_active)
                        VALUES ($1, $2, $3, $4, $5::vector, $6, true)
                    """, doc_type, title, chunk_content, chunk_doc_id,
                        embedding_str, json.dumps(metadata))
            
            logger.info(f"✅ Documento {doc_id} cargado exitosamente ({total_chunks} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando {file_path}: {e}")
            return False
    
    def _extract_title(self, content: str) -> str:
        """Extraer título del documento markdown"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Documento sin título"
    
    async def load_all_documents(self) -> Dict[str, int]:
        """Cargar todos los documentos de la carpeta knowledge"""
        if not self.knowledge_dir.exists():
            logger.error(f"❌ Directorio {self.knowledge_dir} no existe")
            return {}
        
        results = {"success": 0, "failed": 0}
        
        # Mapeo de carpetas a tipos de documento
        type_mapping = {
            "policies": "policy",
            "faqs": "faq",
            ".": "general"  # Archivos en raíz
        }
        
        # Procesar archivos markdown
        for root, dirs, files in os.walk(self.knowledge_dir):
            root_path = Path(root)
            relative_path = root_path.relative_to(self.knowledge_dir)
            
            # Determinar tipo de documento según carpeta
            doc_type = "general"
            for folder, dtype in type_mapping.items():
                if folder in str(relative_path) or str(relative_path) == ".":
                    doc_type = dtype
                    break
            
            # Procesar archivos .md
            for file in files:
                if file.endswith('.md'):
                    file_path = root_path / file
                    success = await self.load_markdown_file(file_path, doc_type)
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
        
        logger.info(f"📚 Carga completa: {results['success']} exitosos, {results['failed']} fallidos")
        return results
    
    async def search_knowledge(self, query: str, doc_types: Optional[List[str]] = None, 
                             limit: int = 5) -> List[Dict[str, Any]]:
        """Buscar en la base de conocimientos usando búsqueda híbrida"""
        try:
            # Generar embedding para la consulta
            query_embedding = await self.embedding_service.generate_embedding(query)
            if not query_embedding:
                logger.error("Error generando embedding para búsqueda")
                return []
            
            pool = self.db_service.pool
            if not pool:
                logger.error("No hay pool de conexiones disponible")
                return []
            
            # Construir filtro de tipos si se especifica
            type_filter = ""
            # Convertir embedding a formato pgvector
            query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
            params = [query_embedding_str, query, limit]
            if doc_types:
                placeholders = ','.join([f'${i}' for i in range(4, 4 + len(doc_types))])
                type_filter = f"AND content_type IN ({placeholders})"
                params.extend(doc_types)
            
            # Búsqueda híbrida: vector + texto
            async with pool.acquire() as conn:
                results = await conn.fetch(f"""
                    WITH vector_search AS (
                        SELECT 
                            external_id, title, content, content_type, metadata,
                            1 - (embedding <=> $1::vector) AS vector_score
                        FROM knowledge_base
                        WHERE embedding IS NOT NULL AND is_active = true
                        {type_filter}
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3 * 2
                    ),
                    text_search AS (
                        SELECT 
                            external_id, title, content, content_type, metadata,
                            ts_rank(search_vector, plainto_tsquery('spanish', $2)) AS text_score
                        FROM knowledge_base
                        WHERE search_vector @@ plainto_tsquery('spanish', $2)
                              AND is_active = true
                        {type_filter}
                        LIMIT $3 * 2
                    ),
                    combined AS (
                        SELECT 
                            COALESCE(v.external_id, t.external_id) AS doc_id,
                            COALESCE(v.title, t.title) AS title,
                            COALESCE(v.content, t.content) AS content,
                            COALESCE(v.content_type, t.content_type) AS doc_type,
                            COALESCE(v.metadata, t.metadata) AS metadata,
                            COALESCE(v.vector_score, 0) * 0.6 + 
                            COALESCE(t.text_score, 0) * 0.4 AS combined_score
                        FROM vector_search v
                        FULL OUTER JOIN text_search t ON v.external_id = t.external_id
                    )
                    SELECT 
                        doc_id, title, content, doc_type, metadata,
                        combined_score
                    FROM combined
                    WHERE combined_score > 0.1
                    ORDER BY combined_score DESC
                    LIMIT $3
                """, *params)
                
                # Formatear resultados
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        "doc_id": row["doc_id"],
                        "title": row["title"],
                        "content": row["content"],
                        "doc_type": row["doc_type"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "score": float(row["combined_score"])
                    })
                
                return formatted_results
                
        except Exception as e:
            logger.error(f"❌ Error en búsqueda de conocimiento: {e}")
            return []
    
    async def get_document_by_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """Obtener todos los documentos de un tipo específico"""
        try:
            pool = self.db_service.pool
            if not pool:
                logger.error("No hay pool de conexiones disponible")
                return []
            async with pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT doc_id, title, content, metadata
                    FROM knowledge_base
                    WHERE doc_type = $1
                    ORDER BY doc_id, chunk_index
                """, doc_type)
                
                return [
                    {
                        "doc_id": row["doc_id"],
                        "title": row["title"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos tipo {doc_type}: {e}")
            return []

# Instancia global del servicio
knowledge_service = KnowledgeBaseService()