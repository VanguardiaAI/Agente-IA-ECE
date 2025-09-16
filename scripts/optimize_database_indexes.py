#!/usr/bin/env python
"""
Script para optimizar los índices de la base de datos PostgreSQL
para mejorar el rendimiento de las búsquedas
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
load_dotenv('env.agent')

async def optimize_indexes():
    """Crea y optimiza índices para mejorar el rendimiento de búsquedas"""
    
    # Configuración de conexión
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'eva_knowledge'),
        'user': os.getenv('POSTGRES_USER', 'eva_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'eva_pass')
    }
    
    try:
        # Conectar a la base de datos
        conn = await asyncpg.connect(**db_config)
        print("✅ Conectado a PostgreSQL")
        
        # Lista de índices a crear
        indexes = [
            # Índice GIN para búsqueda de texto con trigramas (más rápido para LIKE)
            {
                'name': 'idx_products_title_trgm',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_products_title_trgm 
                    ON knowledge_base USING gin(title gin_trgm_ops)
                    WHERE content_type = 'product'
                """,
                'description': 'Índice GIN para búsqueda rápida en títulos de productos'
            },
            
            # Índice GIN para búsqueda en contenido
            {
                'name': 'idx_products_content_trgm',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_products_content_trgm 
                    ON knowledge_base USING gin(content gin_trgm_ops)
                    WHERE content_type = 'product'
                """,
                'description': 'Índice GIN para búsqueda rápida en contenido de productos'
            },
            
            # Índice para búsqueda vectorial optimizada
            {
                'name': 'idx_products_embedding_ivfflat',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_products_embedding_ivfflat 
                    ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
                    WHERE content_type = 'product'
                """,
                'description': 'Índice IVFFlat para búsqueda vectorial optimizada'
            },
            
            # Índice compuesto para filtrado por tipo y external_id
            {
                'name': 'idx_kb_type_external',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_kb_type_external 
                    ON knowledge_base(content_type, external_id)
                """,
                'description': 'Índice compuesto para búsquedas por tipo y ID externo'
            },
            
            # Índice para metadata JSONB
            {
                'name': 'idx_kb_metadata_gin',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_kb_metadata_gin 
                    ON knowledge_base USING gin(metadata)
                """,
                'description': 'Índice GIN para búsqueda rápida en metadata JSON'
            },
            
            # Índice parcial para productos en stock
            {
                'name': 'idx_products_instock',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_products_instock 
                    ON knowledge_base(external_id) 
                    WHERE content_type = 'product' 
                    AND (metadata->>'stock_status') = 'instock'
                """,
                'description': 'Índice parcial para productos en stock'
            },
            
            # Índice para categorías
            {
                'name': 'idx_categories',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_categories 
                    ON knowledge_base(title) 
                    WHERE content_type = 'category'
                """,
                'description': 'Índice para búsqueda rápida de categorías'
            }
        ]
        
        print("\n📊 Creando/Verificando índices...")
        
        for index in indexes:
            try:
                print(f"\n🔧 {index['name']}: {index['description']}")
                await conn.execute(index['sql'])
                print(f"   ✅ Índice creado/verificado exitosamente")
            except Exception as e:
                print(f"   ⚠️ Error con índice {index['name']}: {e}")
        
        # Actualizar estadísticas de la tabla
        print("\n📈 Actualizando estadísticas de la tabla...")
        await conn.execute("ANALYZE knowledge_base")
        print("   ✅ Estadísticas actualizadas")
        
        # Verificar índices existentes
        print("\n📋 Índices actuales en knowledge_base:")
        existing_indexes = await conn.fetch("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'knowledge_base'
            ORDER BY indexname
        """)
        
        for idx in existing_indexes:
            print(f"   - {idx['indexname']}")
        
        # Obtener estadísticas de la tabla
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(*) FILTER (WHERE content_type = 'product') as products,
                COUNT(*) FILTER (WHERE content_type = 'category') as categories,
                COUNT(*) FILTER (WHERE content_type = 'knowledge') as knowledge,
                pg_size_pretty(pg_total_relation_size('knowledge_base')) as table_size
            FROM knowledge_base
        """)
        
        print("\n📊 Estadísticas de la tabla:")
        print(f"   Total de filas: {stats['total_rows']:,}")
        print(f"   Productos: {stats['products']:,}")
        print(f"   Categorías: {stats['categories']:,}")
        print(f"   Knowledge: {stats['knowledge']:,}")
        print(f"   Tamaño total: {stats['table_size']}")
        
        # Configurar parámetros de rendimiento
        print("\n⚙️ Configurando parámetros de rendimiento...")
        
        # Estos comandos solo funcionan si el usuario tiene permisos
        try:
            await conn.execute("SET work_mem = '256MB'")
            await conn.execute("SET maintenance_work_mem = '512MB'")
            print("   ✅ Parámetros de memoria configurados")
        except:
            print("   ⚠️ No se pudieron configurar parámetros de memoria (requiere permisos)")
        
        print("\n✅ Optimización de índices completada")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error al optimizar índices: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(optimize_indexes())