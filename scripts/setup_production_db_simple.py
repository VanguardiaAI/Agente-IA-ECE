#!/usr/bin/env python3
"""
Script simple para configurar la base de datos de producción
Versión Python que maneja mejor las variables de entorno
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

def load_env_file(env_path=".env"):
    """Cargar variables de entorno desde archivo .env"""
    if not os.path.exists(env_path):
        print(f"❌ Archivo {env_path} no encontrado")
        return False
        
    print(f"⚠️  Cargando variables de entorno desde {env_path}...")
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Ignorar comentarios y líneas vacías
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remover comillas
                value = value.strip().strip('"').strip("'")
                os.environ[key.strip()] = value
                print(f"   ✓ Cargada: {key.strip()}")
    
    return True

async def check_connection(connection_params):
    """Verificar conexión a la base de datos"""
    try:
        conn = await asyncpg.connect(**connection_params)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        print("   ✅ Conexión exitosa")
        print(f"   📊 PostgreSQL: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False

async def execute_sql_file(connection_params, sql_file, description):
    """Ejecutar archivo SQL"""
    print(f"🔧 Ejecutando {description}...")
    
    if not os.path.exists(sql_file):
        print(f"   ⚠️  Archivo no encontrado: {sql_file}")
        return False
        
    try:
        conn = await asyncpg.connect(**connection_params)
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        await conn.execute(sql_content)
        await conn.close()
        
        print(f"   ✅ {description} completado")
        return True
        
    except Exception as e:
        print(f"   ❌ Error ejecutando {description}: {e}")
        return False

async def verify_tables(connection_params):
    """Verificar que las tablas críticas existen"""
    print("✅ Verificando migración...")
    
    critical_tables = ['conversations', 'conversation_messages', 'knowledge_base']
    
    try:
        conn = await asyncpg.connect(**connection_params)
        
        for table in critical_tables:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                );
            """, table)
            
            if exists:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   ✅ {table}: OK ({count} registros)")
            else:
                print(f"   ❌ {table}: FALTA")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error verificando tablas: {e}")
        return False

async def main():
    print("🚀 Configurando base de datos de producción...")
    print("================================================")
    
    # Verificar directorio
    if not os.path.exists("scripts/create_metrics_tables.sql"):
        print("❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto")
        sys.exit(1)
    
    # Cargar variables de entorno si no están definidas
    required_vars = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        if not load_env_file():
            sys.exit(1)
        
        # Verificar nuevamente
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            print(f"❌ Error: Variables faltantes: {missing_vars}")
            sys.exit(1)
    
    # Configuración de conexión
    connection_params = {
        'host': os.environ['POSTGRES_HOST'],
        'port': int(os.environ.get('POSTGRES_PORT', 5432)),
        'user': os.environ['POSTGRES_USER'],
        'password': os.environ['POSTGRES_PASSWORD'],
        'database': os.environ['POSTGRES_DB']
    }
    
    print("📊 Configuración de base de datos:")
    print(f"   Host: {connection_params['host']}")
    print(f"   Database: {connection_params['database']}")
    print(f"   User: {connection_params['user']}")
    print(f"   Port: {connection_params['port']}")
    
    # Verificar conexión
    print("🔗 Verificando conexión a base de datos...")
    if not await check_connection(connection_params):
        sys.exit(1)
    
    # Crear backup
    print("💾 Creando backup de seguridad...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_production_{timestamp}.sql"
    
    try:
        cmd = [
            'pg_dump',
            '-h', connection_params['host'],
            '-p', str(connection_params['port']),
            '-U', connection_params['user'],
            '-d', connection_params['database'],
            '--schema-only'
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = connection_params['password']
        
        with open(backup_file, 'w') as f:
            subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.DEVNULL)
        
        print(f"   📁 Backup guardado como: {backup_file}")
        
    except Exception as e:
        print(f"   ⚠️  No se pudo crear backup: {e}")
    
    # Ejecutar migraciones
    print("📥 Aplicando migraciones...")
    
    migrations = [
        ("scripts/init_database.sql", "inicialización de base de datos"),
        ("scripts/create_metrics_tables.sql", "tablas de conversaciones y métricas"),
        ("scripts/create_admin_tables.sql", "tablas de administración"),
        ("scripts/create_admin_tables_simple.sql", "tablas de administración (simple)")
    ]
    
    success_count = 0
    for sql_file, description in migrations:
        if os.path.exists(sql_file):
            if await execute_sql_file(connection_params, sql_file, description):
                success_count += 1
                if "metrics" in description:  # Crítico
                    print(f"   🎯 Migración crítica exitosa")
    
    # Verificar migración
    await verify_tables(connection_params)
    
    print("")
    print("🎉 ¡Migración completada!")
    print("=========================")
    print("")
    print("📋 PRÓXIMOS PASOS:")
    print("1. Reiniciar servicios de producción:")
    print("   ./scripts/docker-production.sh restart")
    print("")
    print("2. Verificar que el dashboard funciona:")
    print("   curl http://localhost:8080/api/admin/metrics/summary")
    print("")
    print(f"📁 Backup guardado en: {backup_file}")

if __name__ == "__main__":
    asyncio.run(main())