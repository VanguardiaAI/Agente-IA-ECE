#!/usr/bin/env python3
"""
Script para eliminar TODOS los triggers de la base de datos
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import db_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def remove_all_triggers():
    """Eliminar todos los triggers de la base de datos"""
    
    print("🗑️ Eliminando triggers de la base de datos...")
    
    # Inicializar servicio
    await db_service.initialize()
    
    async with db_service.pool.acquire() as conn:
        # 1. Eliminar el trigger
        print("\n📌 Eliminando trigger update_search_vector...")
        try:
            await conn.execute("DROP TRIGGER IF EXISTS trigger_update_search_vector ON knowledge_base CASCADE;")
            print("✅ Trigger eliminado")
        except Exception as e:
            print(f"⚠️ Error eliminando trigger: {e}")
        
        # 2. Eliminar la función
        print("\n📌 Eliminando función update_search_vector...")
        try:
            await conn.execute("DROP FUNCTION IF EXISTS update_search_vector() CASCADE;")
            print("✅ Función eliminada")
        except Exception as e:
            print(f"⚠️ Error eliminando función: {e}")
        
        # 3. Verificar que no queden triggers
        print("\n🔍 Verificando triggers restantes...")
        rows = await conn.fetch("""
            SELECT 
                trigger_name,
                event_object_table,
                action_statement
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
        """)
        
        if rows:
            print(f"⚠️ Aún quedan {len(rows)} triggers:")
            for row in rows:
                print(f"   - {row['trigger_name']} en tabla {row['event_object_table']}")
        else:
            print("✅ No quedan triggers en la base de datos")
        
        # 4. Actualizar manualmente search_vector para registros existentes
        print("\n📝 Actualizando search_vector manualmente para registros existentes...")
        try:
            await conn.execute("""
                UPDATE knowledge_base 
                SET search_vector = to_tsvector('spanish', 
                    COALESCE(title, '') || ' ' || COALESCE(content, '')
                )
                WHERE search_vector IS NULL
            """)
            print("✅ search_vector actualizado")
        except Exception as e:
            print(f"⚠️ Error actualizando search_vector: {e}")
    
    await db_service.close()
    
    print("\n✅ Proceso completado")
    print("\n⚠️ IMPORTANTE: El search_vector ya NO se actualizará automáticamente.")
    print("Deberás actualizar el código para manejar esto manualmente cuando insertes o actualices registros.")

if __name__ == "__main__":
    asyncio.run(remove_all_triggers())