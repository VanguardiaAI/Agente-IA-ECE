#!/usr/bin/env python3
"""
Script simple para probar la conexión PostgreSQL
No requiere OpenAI API Key
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg
from config.settings import settings

async def test_postgres_connection():
    """Probar conexión básica a PostgreSQL"""
    print("🐘 Probando conexión a PostgreSQL...")
    
    try:
        # Conectar a PostgreSQL
        conn = await asyncpg.connect(settings.DATABASE_URL)
        print("✅ Conexión a PostgreSQL exitosa")
        
        # Verificar extensión vector
        result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        if result:
            print("✅ Extensión pgvector disponible")
        else:
            print("⚠️  Extensión pgvector no encontrada, instalando...")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ Extensión pgvector instalada")
        
        # Probar crear tabla básica
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name TEXT,
                embedding vector(3)
            );
        """)
        print("✅ Tabla de prueba creada")
        
        # Insertar datos de prueba
        await conn.execute("""
            INSERT INTO test_table (name, embedding) 
            VALUES ('test', '[1,2,3]') 
            ON CONFLICT DO NOTHING;
        """)
        print("✅ Datos de prueba insertados")
        
        # Consultar datos
        result = await conn.fetchrow("SELECT * FROM test_table LIMIT 1;")
        if result:
            print(f"✅ Consulta exitosa: {dict(result)}")
        
        # Limpiar tabla de prueba
        await conn.execute("DROP TABLE IF EXISTS test_table;")
        print("✅ Tabla de prueba eliminada")
        
        await conn.close()
        print("✅ Conexión cerrada correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🚀 PRUEBA DE POSTGRESQL")
    print("=" * 40)
    
    try:
        success = await test_postgres_connection()
        
        if success:
            print("\n🎉 POSTGRESQL FUNCIONA CORRECTAMENTE")
            print("=" * 40)
            print("✅ Extensión pgvector instalada")
            print("✅ Conexión estable")
            print("✅ Operaciones CRUD funcionando")
            print("\n📋 Siguiente paso:")
            print("   Configura tu OPENAI_API_KEY en el archivo .env")
            return True
        else:
            print("\n❌ POSTGRESQL NO FUNCIONA")
            return False
            
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 