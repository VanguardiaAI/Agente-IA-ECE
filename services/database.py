"""
Servicio de base de datos PostgreSQL para búsqueda híbrida
Maneja la base de conocimiento con vectores y búsqueda de texto completo
"""

import asyncio
import asyncpg
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from config.settings import settings, HYBRID_SEARCH_CONFIG
import logging

logger = logging.getLogger(__name__)

class HybridDatabaseService:
    """Servicio de base de datos para búsqueda híbrida semántica + texto"""
    
    def __init__(self):
        self.pool = None
        self.initialized = False
    
    async def initialize(self):
        """Inicializar el pool de conexiones y crear esquema"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            await self._create_schema()
            self.initialized = True
            logger.info("✅ Servicio de base de datos híbrida inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise
    
    async def _create_schema(self):
        """Crear esquema de base de datos con extensiones y tablas"""
        async with self.pool.acquire() as conn:
            # Habilitar extensiones necesarias
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
            
            # Tabla principal de conocimiento
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id SERIAL PRIMARY KEY,
                    content_type VARCHAR(50) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    search_vector tsvector,
                    external_id VARCHAR(255),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                );
            """)
            
            # Índices para búsqueda vectorial (HNSW para alta performance)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_hnsw 
                ON knowledge_base USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            
            # Índices para búsqueda de texto completo (GIN)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_search_vector 
                ON knowledge_base USING gin(search_vector);
            """)
            
            # Índices adicionales para optimización
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_content_type 
                ON knowledge_base(content_type);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_external_id 
                ON knowledge_base(external_id);
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_active 
                ON knowledge_base(is_active) WHERE is_active = true;
            """)
            
            # Función trigger para auto-actualizar tsvector
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_search_vector() 
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('spanish', 
                        COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.content, '')
                    );
                    NEW.updated_at := CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # Trigger para actualizar automáticamente el vector de búsqueda
            await conn.execute("""
                DROP TRIGGER IF EXISTS trigger_update_search_vector ON knowledge_base;
                CREATE TRIGGER trigger_update_search_vector
                    BEFORE INSERT OR UPDATE ON knowledge_base
                    FOR EACH ROW EXECUTE FUNCTION update_search_vector();
            """)
            
            logger.info("✅ Esquema de base de datos creado exitosamente")
    
    async def insert_knowledge(
        self,
        content_type: str,
        title: str,
        content: str,
        embedding: List[float],
        external_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Insertar nuevo conocimiento en la base de datos"""
        if not self.initialized:
            raise Exception("Base de datos no inicializada")
        
        # Convertir embedding a string para PostgreSQL
        embedding_str = str(embedding) if embedding else None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO knowledge_base (
                    content_type, title, content, embedding, external_id, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, content_type, title, content, embedding_str, external_id, 
                json.dumps(metadata or {}))
            
            return row['id']
    
    async def update_knowledge(
        self,
        knowledge_id: int,
        title: str = None,
        content: str = None,
        embedding: List[float] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Actualizar conocimiento existente"""
        if not self.initialized:
            raise Exception("Base de datos no inicializada")
        
        updates = []
        values = []
        param_count = 1
        
        if title is not None:
            updates.append(f"title = ${param_count}")
            values.append(title)
            param_count += 1
        
        if content is not None:
            updates.append(f"content = ${param_count}")
            values.append(content)
            param_count += 1
        
        if embedding is not None:
            updates.append(f"embedding = ${param_count}")
            values.append(str(embedding))
            param_count += 1
        
        if metadata is not None:
            updates.append(f"metadata = ${param_count}")
            values.append(json.dumps(metadata))
            param_count += 1
        
        if not updates:
            return False
        
        values.append(knowledge_id)
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(f"""
                UPDATE knowledge_base 
                SET {', '.join(updates)}
                WHERE id = ${param_count}
            """, *values)
            
            return result.split()[-1] == '1'
    
    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        content_types: List[str] = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Búsqueda que GARANTIZA encontrar productos con términos técnicos"""
        if not self.initialized:
            raise Exception("Base de datos no inicializada")
        
        limit = limit or HYBRID_SEARCH_CONFIG["final_limit"]
        max_results = HYBRID_SEARCH_CONFIG["max_results"]
        vector_weight = HYBRID_SEARCH_CONFIG["vector_weight"]
        text_weight = HYBRID_SEARCH_CONFIG["text_weight"]
        min_similarity = HYBRID_SEARCH_CONFIG["min_similarity"]
        
        # Detectar términos técnicos (solo códigos específicos, NO palabras comunes)
        technical_terms = self._extract_technical_terms(query_text)
        
        # Log para debugging
        logger.info(f"🔍 Búsqueda: '{query_text}' - Términos técnicos: {technical_terms}")
        
        async with self.pool.acquire() as conn:
            all_results = {}
            
            # PASO 1: Si hay términos técnicos, buscar PRIMERO productos que los contengan
            if technical_terms:
                for term in technical_terms:
                    # Ignorar palabras comunes que se hayan colado
                    if term.lower() in ['busco', 'quiero', 'necesito', 'un', 'una', 'el', 'la', 'los', 'las']:
                        continue
                    
                    logger.info(f"   Buscando productos con término '{term}'...")
                    
                    # Construir filtro de tipo
                    type_filter = ""
                    if content_types:
                        type_filter = f"AND content_type = ANY(ARRAY{content_types}::text[])"
                    
                    # Búsqueda DIRECTA de productos con el término en el título (normalizar acentos)
                    exact_title_query = f"""
                        SELECT id, title, content, content_type, metadata, external_id
                        FROM knowledge_base 
                        WHERE is_active = true 
                        AND (UPPER(unaccent(title)) LIKE '%' || UPPER(unaccent($1)) || '%'
                             OR UPPER(title) LIKE '%' || UPPER($1) || '%')
                        {type_filter}
                        ORDER BY title
                        LIMIT 30
                    """
                    
                    rows = await conn.fetch(exact_title_query, term)
                    logger.info(f"   ✅ Encontrados {len(rows)} productos con '{term}' en título")
                    
                    for row in rows:
                        result = dict(row)
                        if result['metadata']:
                            result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                        result['rrf_score'] = 1000.0  # Score MUY ALTO para coincidencias exactas en título
                        result['match_type'] = 'exact_title'
                        result['matched_term'] = term
                        
                        # Usar ID como clave para evitar duplicados
                        if result['id'] not in all_results:
                            all_results[result['id']] = result
            
            # PASO 2: Búsqueda híbrida normal para completar resultados (si es necesario)
            if len(all_results) < limit:
                # Si hay términos técnicos pero no se encontraron productos, usar solo los términos técnicos
                search_text = query_text
                if technical_terms and len(all_results) == 0:
                    # Usar solo términos técnicos para búsqueda de texto, manteniendo embedding original
                    search_text = ' '.join(technical_terms)
                    logger.info(f"   🔧 Usando términos técnicos para búsqueda: '{search_text}'")
                
                # Construir filtros
                type_filter = ""
                params = [str(query_embedding), search_text, max_results]
                
                if content_types:
                    type_filter = f"AND content_type = ANY(${len(params) + 1})"
                    params.append(content_types)
                
                # Excluir IDs ya encontrados
                if all_results:
                    exclude_ids = list(all_results.keys())
                    type_filter += f" AND id NOT IN ({','.join(str(id) for id in exclude_ids)})"
                
                # Búsqueda híbrida NORMAL (vector + texto)
                query = f"""
                WITH vector_search AS (
                    SELECT id, title, content, content_type, metadata, external_id,
                           (1 - (embedding <=> $1)) as vector_similarity,
                           ROW_NUMBER() OVER (ORDER BY embedding <=> $1) as vector_rank
                    FROM knowledge_base 
                    WHERE is_active = true 
                    AND (1 - (embedding <=> $1)) >= {min_similarity}
                    {type_filter}
                    ORDER BY embedding <=> $1
                    LIMIT $3
                ),
                text_search AS (
                    SELECT id, title, content, content_type, metadata, external_id,
                           ts_rank_cd(search_vector, plainto_tsquery('spanish', $2)) as text_score,
                           ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_vector, plainto_tsquery('spanish', $2)) DESC) as text_rank
                    FROM knowledge_base 
                    WHERE is_active = true 
                    AND search_vector @@ plainto_tsquery('spanish', $2)
                    {type_filter}
                    ORDER BY ts_rank_cd(search_vector, plainto_tsquery('spanish', $2)) DESC
                    LIMIT $3
                ),
                combined AS (
                    SELECT 
                        COALESCE(v.id, t.id) as id,
                        COALESCE(v.title, t.title) as title,
                        COALESCE(v.content, t.content) as content,
                        COALESCE(v.content_type, t.content_type) as content_type,
                        COALESCE(v.metadata, t.metadata) as metadata,
                        COALESCE(v.external_id, t.external_id) as external_id,
                        COALESCE(v.vector_similarity, 0) as vector_similarity,
                        COALESCE(t.text_score, 0) as text_score,
                        COALESCE(v.vector_rank, 999999) as vector_rank,
                        COALESCE(t.text_rank, 999999) as text_rank,
                        -- RRF Score base
                        ({vector_weight} * (1.0 / (60 + COALESCE(v.vector_rank, 999999))) + 
                         {text_weight} * (1.0 / (60 + COALESCE(t.text_rank, 999999)))) as base_rrf_score
                    FROM vector_search v
                    FULL OUTER JOIN text_search t ON v.id = t.id
                )
                SELECT *,
                       base_rrf_score as rrf_score
                FROM combined
                ORDER BY base_rrf_score DESC
                LIMIT {max_results}
            """
            
                rows = await conn.fetch(query, *params)
                
                # Agregar resultados de búsqueda híbrida a los resultados existentes
                for row in rows:
                    result = dict(row)
                    # Parsear metadata JSON
                    if result['metadata']:
                        result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                    
                    # Convertir scores a float (score bajo para búsqueda normal)
                    result['rrf_score'] = float(result.get('rrf_score', 0))
                    result['match_type'] = 'hybrid'
                    
                    # Solo agregar si no está ya en los resultados
                    if result['id'] not in all_results:
                        all_results[result['id']] = result
            
            # Convertir diccionario a lista
            final_results = list(all_results.values())
            
            # Ordenar por score (los productos con términos técnicos tendrán scores mucho más altos)
            final_results.sort(key=lambda x: float(x.get('rrf_score', 0)), reverse=True)
            
            # Log de resultados
            if technical_terms:
                logger.info(f"📊 Resultados finales para '{query_text}':")
                logger.info(f"   - Productos con términos técnicos: {len([r for r in final_results if r.get('match_type') in ['exact_title', 'exact_content']])}")
                logger.info(f"   - Productos de búsqueda híbrida: {len([r for r in final_results if r.get('match_type') == 'hybrid'])}")
                if final_results:
                    logger.info(f"   Top 3:")
                    for i, r in enumerate(final_results[:3]):
                        logger.info(f"     {i+1}. {r.get('title', 'Sin título')} (Score: {r.get('rrf_score', 0):.1f}, Tipo: {r.get('match_type', 'unknown')})")
            
            return final_results[:limit]
    
    async def vector_search(
        self,
        query_embedding: List[float],
        content_types: List[str] = None,
        limit: int = 10,
        min_similarity: float = None
    ) -> List[Dict[str, Any]]:
        """Búsqueda puramente vectorial"""
        if not self.initialized:
            raise Exception("Base de datos no inicializada")
        
        min_sim = min_similarity or HYBRID_SEARCH_CONFIG["min_similarity"]
        
        async with self.pool.acquire() as conn:
            type_filter = ""
            params = [str(query_embedding), limit]
            
            if content_types:
                type_filter = f"AND content_type = ANY(${len(params) + 1})"
                params.append(content_types)
            
            query = f"""
                SELECT id, title, content, content_type, metadata, external_id,
                       (1 - (embedding <=> $1)) as similarity
                FROM knowledge_base 
                WHERE is_active = true 
                AND (1 - (embedding <=> $1)) >= {min_sim}
                {type_filter}
                ORDER BY embedding <=> $1
                LIMIT $2
            """
            
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                results.append(result)
            
            return results
    
    async def text_search(
        self,
        query_text: str,
        content_types: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Búsqueda puramente textual"""
        if not self.initialized:
            raise Exception("Base de datos no inicializada")
        
        async with self.pool.acquire() as conn:
            type_filter = ""
            params = [query_text, limit]
            
            if content_types:
                type_filter = f"AND content_type = ANY(${len(params) + 1})"
                params.append(content_types)
            
            query = f"""
                SELECT id, title, content, content_type, metadata, external_id,
                       ts_rank_cd(search_vector, plainto_tsquery('spanish', $1)) as score
                FROM knowledge_base 
                WHERE is_active = true 
                AND search_vector @@ plainto_tsquery('spanish', $1)
                {type_filter}
                ORDER BY ts_rank_cd(search_vector, plainto_tsquery('spanish', $1)) DESC
                LIMIT $2
            """
            
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                results.append(result)
            
            return results
    
    async def get_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Obtener conocimiento por ID externo"""
        if not self.initialized:
            return None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM knowledge_base 
                WHERE external_id = $1 AND is_active = true
            """, external_id)
            
            if row:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                return result
            
            return None
    
    async def delete_knowledge(self, knowledge_id: int) -> bool:
        """Eliminar conocimiento (soft delete)"""
        if not self.initialized:
            return False
        
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE knowledge_base 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, knowledge_id)
            
            return result.split()[-1] == '1'
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de la base de conocimiento"""
        if not self.initialized:
            return {}
        
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(*) FILTER (WHERE is_active = true) as active_entries,
                    COUNT(*) FILTER (WHERE content_type = 'product') as products,
                    COUNT(*) FILTER (WHERE content_type = 'product' AND is_active = true) as active_products,
                    COUNT(*) FILTER (WHERE content_type = 'category') as categories,
                    COUNT(*) FILTER (WHERE content_type = 'company_info') as company_info,
                    COUNT(*) FILTER (WHERE content_type = 'faq') as faqs,
                    COUNT(DISTINCT content_type) as content_types,
                    AVG(LENGTH(content)) as avg_content_length,
                    MIN(created_at) as oldest_entry,
                    MAX(updated_at) as newest_update
                FROM knowledge_base
            """)
            
            # Estadísticas por tipo de contenido
            type_stats = await conn.fetch("""
                SELECT content_type, COUNT(*) as count
                FROM knowledge_base 
                WHERE is_active = true
                GROUP BY content_type
                ORDER BY count DESC
            """)
            
            return {
                "total_entries": stats['total_entries'],
                "active_entries": stats['active_entries'],
                "products": stats['products'],
                "active_products": stats['active_products'],
                "categories": stats['categories'],
                "company_info": stats['company_info'],
                "faqs": stats['faqs'],
                "content_types": stats['content_types'],
                "avg_content_length": round(stats['avg_content_length'] or 0, 2),
                "oldest_entry": stats['oldest_entry'].isoformat() if stats['oldest_entry'] else None,
                "newest_update": stats['newest_update'].isoformat() if stats['newest_update'] else None,
                "by_content_type": [dict(row) for row in type_stats]
            }
    
    async def get_knowledge_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Obtener entrada de conocimiento por ID externo"""
        if not self.initialized:
            return None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, content_type, title, content, external_id, metadata, 
                       created_at, updated_at, is_active
                FROM knowledge_base 
                WHERE external_id = $1
            """, external_id)
            
            if row:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                return result
            
            return None
    
    async def upsert_knowledge(self, content_type: str, title: str, content: str, 
                             embedding: List[float], external_id: str = None, 
                             metadata: Dict = None) -> int:
        """Insertar o actualizar entrada de conocimiento"""
        if not self.initialized:
            return None
        
        async with self.pool.acquire() as conn:
            # Convertir embedding a string para PostgreSQL
            embedding_str = str(embedding)
            
            if external_id:
                # Intentar actualizar primero
                update_query = """
                UPDATE knowledge_base 
                SET title = $2, content = $3, embedding = $4, metadata = $5, 
                    updated_at = CURRENT_TIMESTAMP, is_active = true,
                    search_vector = to_tsvector('spanish', $3)
                WHERE external_id = $1
                RETURNING id;
                """
                
                result = await conn.fetchrow(
                    update_query, external_id, title, content, 
                    embedding_str, json.dumps(metadata or {})
                )
                
                if result:
                    return result['id']
            
            # Si no existe, insertar nuevo
            insert_query = """
            INSERT INTO knowledge_base 
            (content_type, title, content, embedding, external_id, metadata, search_vector)
            VALUES ($1, $2, $3, $4, $5, $6, to_tsvector('spanish', $3))
            RETURNING id;
            """
            
            result = await conn.fetchrow(
                insert_query, content_type, title, content, 
                embedding_str, external_id, json.dumps(metadata or {})
            )
            
            return result['id'] if result else None
    
    async def deactivate_missing_products(self, active_external_ids: set) -> int:
        """Marcar como inactivos los productos que no están en la lista de IDs activos"""
        if not self.initialized or not active_external_ids:
            return 0
        
        async with self.pool.acquire() as conn:
            # Convertir set a lista para PostgreSQL
            active_ids_list = list(active_external_ids)
            
            query = """
            UPDATE knowledge_base 
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE content_type = 'product' 
            AND is_active = true 
            AND external_id != ALL($1)
            """
            
            result = await conn.execute(query, active_ids_list)
            
            # Extraer número de filas afectadas del resultado
            affected_rows = int(result.split()[-1]) if result and result.split() else 0
            return affected_rows
    
    async def get_last_sync_time(self) -> Optional[datetime]:
        """Obtener la fecha de la última sincronización de productos"""
        if not self.initialized:
            return None
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT MAX(updated_at) as last_sync
                FROM knowledge_base 
                WHERE content_type IN ('product', 'category')
            """)
            
            return result['last_sync'] if result and result['last_sync'] else None
    
    def _extract_technical_terms(self, query_text: str) -> List[str]:
        """Extraer términos técnicos específicos (códigos, modelos, SKUs) y términos técnicos relevantes"""
        import re
        
        technical_terms = []
        
        # Palabras comunes a EXCLUIR (verbos, artículos, preposiciones)
        common_words = {
            'busco', 'quiero', 'necesito', 'comprar', 'compro', 'vendo', 'tengo',
            'un', 'una', 'el', 'la', 'los', 'las', 'del', 'de', 'para', 'con', 'sin',
            'tipo', 'modelo', 'marca', 'precio', 'barato', 'caro', 'bueno', 'malo',
            'mejor', 'peor', 'grande', 'pequeño', 'nuevo', 'usado', 'y', 'o', 'pero',
            'que', 'como', 'donde', 'cuando', 'porque', 'si', 'no', 'me', 'te', 'se',
            'en', 'por', 'sobre', 'bajo', 'entre', 'desde', 'hasta', 'hacia', 'contra'
        }
        
        # Términos técnicos específicos que SIEMPRE deben priorizarse
        specific_technical_terms = {
            # Términos originales básicos
            'automático', 'automáticos', 'automatico', 'automaticos', 'dpn', 'led', 'ip65', 'ip44', 'ip20',
            'diferencial', 'diferenciales', 'magnetotérmico', 'magnetotérmicos', 'magnetotermico',
            'interruptor', 'interruptores', 'cable', 'cables', 'hilo', 'hilos',
            'luminaria', 'luminarias', 'lámpara', 'lámparas', 'lampara', 'lamparas',
            'bombilla', 'bombillas', 'foco', 'focos', 'luz', 'luces', 'bombillo', 'bombillos',
            'tubo', 'tubos', 'caja', 'cajas', 'base', 'bases', 'enchufe', 'enchufes',
            'transformador', 'transformadores', 'trafo', 'trafos',
            'contactor', 'contactores', 'relé', 'relés', 'detector', 'detectores', 
            'sensor', 'sensores', 'ventilador', 'ventiladores', 'techo', 'pared', 'industrial',
            'bipolar', 'tripolar', 'tetrapolar', 'monopolar', 'unipolar',
            'vivienda', 'casa', 'hogar', 'doméstico', 'residencial',
            'monofásico', 'trifásico', 'curva',
            
            # Nuevos términos agregados según la tabla
            'pia', 'disyuntor', 'llave', 'protección', 'personas',
            'fusibles', 'fusible', 'plomos', 'plomo', 'cortacircuitos', 'cortacircuito',
            'portero', 'porteros', 'telefonillo', 'telefonillos', 'auricular', 'auriculares',
            'intercomunicador', 'intercomunicadores', 'videoportero', 'videoporteros',
            'visor', 'puerta', 'bridas', 'brida', 'cintillos', 'cintillo', 'fleje',
            'chincho', 'abrazadera', 'abrazaderas', 'precinto', 'precintos',
            'termos', 'termo', 'calentador', 'calentadores', 'agua', 'toalleros', 'toallero',
            'secatoallas', 'radiador', 'radiadores', 'calderas', 'caldera',
            'termoventilador', 'termoventiladores', 'estufa', 'estufas', 'baño',
            'emisores', 'emisor', 'termicos', 'térmicos', 'termico', 'térmico',
            'electrico', 'eléctrico', 'electricos', 'eléctricos', 'inercia', 'termica', 'térmica',
            'calefactor', 'calefactores', 'convector', 'convectores', 'aire', 'convección',
            'portalamparas', 'portalámparas', 'casquillo', 'casquillos',
            'clema', 'clemas', 'regleta', 'regletas', 'borna', 'bornas', 'conector', 'conectores',
            'arco', 'apaga', 'chispas', 'superinmunizado', 'hpi', 'fsi', 'si', 'b-si', 'a-si',
            '1p', '2p', '3p', '4p', '1+n', '3+n', 'miliamperios', 'ma',
            'ladrón', 'ladrones', 'prolongador', 'prolongadores',
            'estanqueidad', 'ip', 'grado', 'protección', 'cetac',
            'industrial', 'industriales', 'control', 'nivel', 'boya', 'boyas',
            'estabilizador', 'estabilizadores', 'regulador', 'reguladores', 'voltaje',
            'controlador', 'controladores', 'afianzador', 'afianzadores',
            'estanco', 'estancos', 'hermetico', 'hermético', 'hermeticos', 'herméticos'
        }
        
        # Sinónimos técnicos - mapeo de términos equivalentes
        technical_synonyms = {
            # Automáticos / Magnetotérmicos
            'automaticos': ['magnetotermico', 'magnetotérmico', 'pia', 'disyuntor'],
            'automatico': ['magnetotermico', 'magnetotérmico', 'pia', 'disyuntor'],
            'automático': ['magnetotérmico', 'pia', 'disyuntor'],
            'automáticos': ['magnetotérmico', 'pia', 'disyuntor'],
            'magnetotermico': ['automatico', 'automático', 'pia', 'disyuntor'],
            'magnetotérmico': ['automático', 'pia', 'disyuntor'],
            'pia': ['automatico', 'automático', 'magnetotermico', 'magnetotérmico', 'disyuntor'],
            'disyuntor': ['automatico', 'automático', 'magnetotermico', 'magnetotérmico', 'pia'],
            
            # Diferenciales
            'diferencial': ['llave diferencial', 'protección de personas'],
            'diferenciales': ['llave diferencial', 'protección de personas'],
            'llave diferencial': ['diferencial', 'protección de personas'],
            'protección de personas': ['diferencial', 'llave diferencial'],
            
            # Fusibles
            'fusibles': ['plomos', 'cortacircuitos'],
            'fusible': ['plomo', 'cortacircuito'],
            'plomos': ['fusibles', 'cortacircuitos'],
            'plomo': ['fusible', 'cortacircuito'],
            'cortacircuitos': ['fusibles', 'plomos'],
            'cortacircuito': ['fusible', 'plomo'],
            
            # Cables
            'cable': ['hilo'],
            'cables': ['hilos'],
            'hilo': ['cable'],
            'hilos': ['cables'],
            
            # Lámparas
            'lampara': ['bombilla', 'foco', 'luz', 'bombillo'],
            'lámpara': ['bombilla', 'foco', 'luz', 'bombillo'],
            'lamparas': ['bombillas', 'focos', 'luces', 'bombillos'],
            'lámparas': ['bombillas', 'focos', 'luces', 'bombillos'],
            'bombilla': ['lampara', 'lámpara', 'foco', 'luz', 'bombillo'],
            'bombillas': ['lamparas', 'lámparas', 'focos', 'luces', 'bombillos'],
            'foco': ['lampara', 'lámpara', 'bombilla', 'luz', 'bombillo'],
            'focos': ['lamparas', 'lámparas', 'bombillas', 'luces', 'bombillos'],
            'luz': ['lampara', 'lámpara', 'bombilla', 'foco', 'bombillo'],
            'luces': ['lamparas', 'lámparas', 'bombillas', 'focos', 'bombillos'],
            'bombillo': ['lampara', 'lámpara', 'bombilla', 'foco', 'luz'],
            'bombillos': ['lamparas', 'lámparas', 'bombillas', 'focos', 'luces'],
            
            # Porteros
            'portero': ['telefonillo', 'auricular', 'intercomunicador'],
            'porteros': ['telefonillos', 'auriculares', 'intercomunicadores'],
            'telefonillo': ['portero', 'auricular', 'intercomunicador'],
            'telefonillos': ['porteros', 'auriculares', 'intercomunicadores'],
            'auricular': ['portero', 'telefonillo', 'intercomunicador'],
            'auriculares': ['porteros', 'telefonillos', 'intercomunicadores'],
            'intercomunicador': ['portero', 'telefonillo', 'auricular'],
            'intercomunicadores': ['porteros', 'telefonillos', 'auriculares'],
            
            # Videoporteros
            'videoportero': ['telefonillo con camara', 'telefonillo con cámara', 'visor de puerta'],
            'videoporteros': ['telefonillos con camara', 'telefonillos con cámara', 'visores de puerta'],
            'telefonillo con camara': ['videoportero', 'visor de puerta'],
            'telefonillo con cámara': ['videoportero', 'visor de puerta'],
            'visor de puerta': ['videoportero', 'telefonillo con camara', 'telefonillo con cámara'],
            
            # Bridas
            'bridas': ['cintillos', 'fleje', 'chincho', 'abrazadera', 'precinto'],
            'brida': ['cintillo', 'fleje', 'chincho', 'abrazadera', 'precinto'],
            'cintillos': ['bridas', 'fleje', 'chincho', 'abrazadera', 'precinto'],
            'cintillo': ['brida', 'fleje', 'chincho', 'abrazadera', 'precinto'],
            'fleje': ['bridas', 'cintillos', 'chincho', 'abrazadera', 'precinto'],
            'chincho': ['bridas', 'cintillos', 'fleje', 'abrazadera', 'precinto'],
            'abrazadera': ['bridas', 'cintillos', 'fleje', 'chincho', 'precinto'],
            'abrazaderas': ['bridas', 'cintillos', 'fleje', 'chincho', 'precinto'],
            'precinto': ['bridas', 'cintillos', 'fleje', 'chincho', 'abrazadera'],
            'precintos': ['bridas', 'cintillos', 'fleje', 'chincho', 'abrazadera'],
            
            # Termos
            'termos': ['calentador de agua'],
            'termo': ['calentador de agua'],
            'calentador de agua': ['termo', 'termos'],
            'calentadores de agua': ['termos'],
            
            # Toalleros
            'toalleros': ['secatoallas', 'radiador toallero'],
            'toallero': ['secatoallas', 'radiador toallero'],
            'secatoallas': ['toallero', 'radiador toallero'],
            'radiador toallero': ['toallero', 'secatoallas'],
            'radiadores toallero': ['toalleros', 'secatoallas'],
            
            # Calderas
            'calderas': ['calentador'],
            'caldera': ['calentador'],
            'calentador': ['caldera'],
            'calentadores': ['calderas'],
            
            # Termoventilador
            'termoventilador': ['estufa con ventilador', 'calentador con ventilador'],
            'termoventiladores': ['estufas con ventilador', 'calentadores con ventilador'],
            'estufa con ventilador': ['termoventilador', 'calentador con ventilador'],
            'calentador con ventilador': ['termoventilador', 'estufa con ventilador'],
            
            # Emisores térmicos
            'emisores termicos': ['radiador electrico', 'radiador eléctrico', 'radiador de inercia termica'],
            'emisor termico': ['radiador electrico', 'radiador eléctrico', 'radiador de inercia termica'],
            'emisores térmicos': ['radiador eléctrico', 'radiador de inercia térmica'],
            'emisor térmico': ['radiador eléctrico', 'radiador de inercia térmica'],
            'radiador electrico': ['emisor termico', 'emisor térmico', 'radiador de inercia termica'],
            'radiador eléctrico': ['emisor térmico', 'radiador de inercia térmica'],
            'radiador de inercia termica': ['emisor termico', 'emisor térmico', 'radiador electrico', 'radiador eléctrico'],
            'radiador de inercia térmica': ['emisor térmico', 'radiador eléctrico'],
            
            # Calefactor
            'calefactor': ['radiador electrico', 'radiador eléctrico', 'estufa', 'calentador de baño'],
            'calefactores': ['radiadores electricos', 'radiadores eléctricos', 'estufas', 'calentadores de baño'],
            'estufa': ['calefactor', 'radiador electrico', 'radiador eléctrico', 'calentador de baño'],
            'estufas': ['calefactores', 'radiadores electricos', 'radiadores eléctricos', 'calentadores de baño'],
            'calentador de baño': ['calefactor', 'radiador electrico', 'radiador eléctrico', 'estufa'],
            'calentadores de baño': ['calefactores', 'radiadores electricos', 'radiadores eléctricos', 'estufas'],
            
            # Convector
            'convector': ['radiador de aire', 'radiador por convección'],
            'convectores': ['radiadores de aire', 'radiadores por convección'],
            'radiador de aire': ['convector', 'radiador por convección'],
            'radiadores de aire': ['convectores', 'radiadores por convección'],
            'radiador por convección': ['convector', 'radiador de aire'],
            'radiadores por convección': ['convectores', 'radiadores de aire'],
            
            # Portalámparas
            'portalamparas': ['casquillo'],
            'portalámparas': ['casquillo'],
            'casquillo': ['portalamparas', 'portalámparas'],
            'casquillos': ['portalamparas', 'portalámparas'],
            
            # Clemas
            'clema': ['regleta', 'borna', 'conector cable'],
            'clemas': ['regletas', 'bornas', 'conectores cable'],
            'regleta': ['clema', 'borna', 'conector cable', 'ladrón', 'prolongador'],
            'regletas': ['clemas', 'bornas', 'conectores cable', 'ladrones', 'prolongadores'],
            'borna': ['clema', 'regleta', 'conector cable'],
            'bornas': ['clemas', 'regletas', 'conectores cable'],
            'conector cable': ['clema', 'regleta', 'borna'],
            'conectores cable': ['clemas', 'regletas', 'bornas'],
            
            # Arco eléctrico
            'arco electrico': ['apaga chispas'],
            'arco eléctrico': ['apaga chispas'],
            'apaga chispas': ['arco electrico', 'arco eléctrico'],
            
            # Superinmunizado
            'superinmunizado': ['diferencial hpi', 'diferencial fsi', 'diferencial si', 'diferencial b-si', 'diferencial a-si'],
            'diferencial hpi': ['superinmunizado'],
            'diferencial fsi': ['superinmunizado'],
            'diferencial si': ['superinmunizado'],
            'diferencial b-si': ['superinmunizado'],
            'diferencial a-si': ['superinmunizado'],
            
            # Polos
            'unipolar': ['1p'],
            '1p': ['unipolar'],
            'bipolar': ['2p', '1+n'],
            '2p': ['bipolar', '1+n'],
            '1+n': ['bipolar', '2p'],
            'tripolar': ['3p'],
            '3p': ['tripolar'],
            'tetrapolar': ['4p', '3+n'],
            '4p': ['tetrapolar', '3+n'],
            '3+n': ['tetrapolar', '4p'],
            
            # Miliamperios
            'miliamperios': ['ma'],
            'ma': ['miliamperios'],
            
            # Regleta (adicional)
            'ladrón': ['regleta', 'prolongador'],
            'ladrones': ['regletas', 'prolongadores'],
            'prolongador': ['regleta', 'ladrón'],
            'prolongadores': ['regletas', 'ladrones'],
            
            # Estanqueidad
            'estanqueidad': ['ip', 'grado de protección'],
            'ip': ['estanqueidad', 'grado de protección'],
            'grado de protección': ['estanqueidad', 'ip'],
            
            # Cetac
            'cetac': ['conector industrial', 'enchufe industrial', 'base industrial'],
            'conector industrial': ['cetac', 'enchufe industrial', 'base industrial'],
            'conectores industriales': ['cetac', 'enchufes industriales', 'bases industriales'],
            'enchufe industrial': ['cetac', 'conector industrial', 'base industrial'],
            'enchufes industriales': ['cetac', 'conectores industriales', 'bases industriales'],
            'base industrial': ['cetac', 'conector industrial', 'enchufe industrial'],
            'bases industriales': ['cetac', 'conectores industriales', 'enchufes industriales'],
            
            # Control de nivel
            'control de nivel': ['boya'],
            'controles de nivel': ['boyas'],
            'boya': ['control de nivel'],
            'boyas': ['controles de nivel'],
            
            # Transformador
            'transformador': ['trafo'],
            'transformadores': ['trafos'],
            'trafo': ['transformador'],
            'trafos': ['transformadores'],
            
            # Estabilizador
            'estabilizador': ['regulador de voltaje', 'controlador de voltaje', 'afianzador'],
            'estabilizadores': ['reguladores de voltaje', 'controladores de voltaje', 'afianzadores'],
            'regulador de voltaje': ['estabilizador', 'controlador de voltaje', 'afianzador'],
            'reguladores de voltaje': ['estabilizadores', 'controladores de voltaje', 'afianzadores'],
            'controlador de voltaje': ['estabilizador', 'regulador de voltaje', 'afianzador'],
            'controladores de voltaje': ['estabilizadores', 'reguladores de voltaje', 'afianzadores'],
            'afianzador': ['estabilizador', 'regulador de voltaje', 'controlador de voltaje'],
            'afianzadores': ['estabilizadores', 'reguladores de voltaje', 'controladores de voltaje'],
            
            # Estanco
            'estanco': ['hermetico', 'hermético'],
            'estancos': ['hermeticos', 'herméticos'],
            'hermetico': ['estanco'],
            'hermético': ['estanco'],
            'hermeticos': ['estancos'],
            'herméticos': ['estancos']
        }
        
        # PASO 1: Buscar términos técnicos específicos conocidos
        words = re.findall(r'\b\w+\b', query_text.lower())
        for word in words:
            if word in specific_technical_terms:
                technical_terms.append(word)
        
        # PASO 2: Patrones para detectar códigos técnicos ESPECÍFICOS
        patterns = [
            r'\b[A-Z]{2,}[0-9]*\b',  # Siglas/códigos como DPN, LED, IP65, C60N
            r'\b[A-Z0-9]+-[A-Z0-9]+\b',  # Códigos con guiones (V-25, IP-65, H07V-K)
            r'\b\d+[Ww]\b',  # Potencias (100W, 50w)
            r'\b\d+[Vv]\b',  # Voltajes (220V, 12v)
            r'\b\d+[Aa]\b',  # Amperajes (10A, 25a)
            r'\b\d+m[Aa]\b',  # Miliamperajes (30mA)
            r'\b\d+mm²?\b',  # Medidas (2.5mm, 1.5mm²)
            r'\b[A-Z]{1}\d{2,}\b',  # Modelos como B22, E27
            r'\bC\d+[A-Z]?\b',  # Curvas C10, C16, C25, etc.
            r'\b\d+[pP]\b',  # Polos (2P, 4P, etc.)
            r'\b\d+\s*polos?\b',  # "2 polos", "4 polo"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_text, re.IGNORECASE)
            for match in matches:
                # Solo agregar si NO es una palabra común
                if match.lower() not in common_words:
                    technical_terms.append(match)
        
        # PASO 3: Buscar palabras en MAYÚSCULAS (códigos técnicos)
        words_caps = query_text.split()
        for word in words_caps:
            clean_word = re.sub(r'[^\w\-]', '', word)
            # Solo si está en mayúsculas, tiene 2+ caracteres y NO es palabra común
            if (len(clean_word) >= 2 and 
                clean_word.isupper() and 
                clean_word.lower() not in common_words and
                not clean_word.isdigit()):  # No solo números
                technical_terms.append(clean_word)
        
        # PASO 4: Expandir términos con sinónimos
        expanded_terms = []
        for term in technical_terms:
            expanded_terms.append(term)
            # Buscar sinónimos para este término
            term_lower = term.lower()
            if term_lower in technical_synonyms:
                # Agregar sinónimos relevantes
                for synonym in technical_synonyms[term_lower]:
                    # Solo agregar sinónimos que sean términos técnicos reconocidos
                    if synonym in specific_technical_terms or re.match(r'\d+[pP]', synonym):
                        expanded_terms.append(synonym)
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_terms = []
        for term in expanded_terms:
            if term.upper() not in seen:
                seen.add(term.upper())
                unique_terms.append(term)
        
        return unique_terms
    
    async def get_pool(self):
        """Obtener el pool de conexiones para uso directo"""
        if not self.initialized or not self.pool:
            await self.initialize()
        return self.pool
    
    async def close(self):
        """Cerrar el pool de conexiones"""
        if self.pool:
            await self.pool.close()
            self.initialized = False

# Instancia global del servicio de base de datos
db_service = HybridDatabaseService() 