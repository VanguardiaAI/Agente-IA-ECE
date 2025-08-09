#!/usr/bin/env python3
"""
Script para migrar la base de datos de producción con las tablas de conversaciones
y métricas necesarias para el nuevo sistema de tracking.

IMPORTANTE: Este script está diseñado para ser ejecutado SOLO EN PRODUCCIÓN
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path
from datetime import datetime

# Agregar el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings

async def check_existing_tables(conn):
    """Verificar qué tablas ya existen en la base de datos"""
    
    print("🔍 Verificando tablas existentes...")
    
    # Lista de tablas que necesitamos
    required_tables = [
        'conversations',
        'conversation_messages', 
        'metrics_hourly',
        'metrics_daily',
        'popular_topics',
        'metric_events',
        'tool_metrics',
        'admin_users',
        'bot_settings',
        'knowledge_base'
    ]
    
    existing_tables = []
    missing_tables = []
    
    for table in required_tables:
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            );
        """, table)
        
        if exists:
            existing_tables.append(table)
            print(f"   ✅ {table} - existe")
        else:
            missing_tables.append(table)
            print(f"   ❌ {table} - falta")
    
    return existing_tables, missing_tables

async def backup_existing_data(conn):
    """Crear backup de datos importantes existentes"""
    
    print("\n💾 Creando backup de datos existentes...")
    
    try:
        # Verificar si hay tablas con datos importantes
        tables_to_backup = ['knowledge_base', 'admin_users', 'bot_settings']
        
        for table in tables_to_backup:
            exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            """)
            
            if exists:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   📊 {table}: {count} registros")
                
                if count > 0:
                    # Crear tabla de backup
                    backup_table = f"{table}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    await conn.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM {table}")
                    print(f"   ✅ Backup creado: {backup_table}")
        
        print("   ✅ Backup completado")
        
    except Exception as e:
        print(f"   ⚠️  Warning en backup: {e}")
        # No fallar por problemas de backup

async def execute_sql_file(conn, sql_file_path, description):
    """Ejecutar un archivo SQL específico"""
    
    print(f"\n🔧 Ejecutando {description}...")
    
    try:
        if not sql_file_path.exists():
            print(f"   ❌ Archivo no encontrado: {sql_file_path}")
            return False
            
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Ejecutar el script completo
        await conn.execute(sql_script)
        print(f"   ✅ {description} ejecutado correctamente")
        return True
        
    except Exception as e:
        print(f"   ❌ Error ejecutando {description}: {e}")
        return False

async def verify_migration(conn):
    """Verificar que la migración se completó correctamente"""
    
    print("\n✅ Verificando migración...")
    
    # Verificar tablas críticas
    critical_tables = ['conversations', 'conversation_messages', 'knowledge_base']
    
    for table in critical_tables:
        exists = await conn.fetchval(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = '{table}'
            );
        """)
        
        if exists:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"   ✅ {table}: OK ({count} registros)")
        else:
            print(f"   ❌ {table}: FALTA")
            return False
    
    # Verificar funciones críticas
    functions_check = await conn.fetchval("""
        SELECT COUNT(*) FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name IN ('find_or_create_conversation', 'cleanup_old_metrics_data')
    """)
    
    print(f"   📊 Funciones disponibles: {functions_check}")
    
    return True

async def migrate_production_database():
    """Ejecutar la migración completa de la base de datos de producción"""
    
    print("🚀 INICIANDO MIGRACIÓN DE BASE DE DATOS DE PRODUCCIÓN")
    print("=" * 60)
    
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL no está configurada")
        return False
    
    print(f"🔗 Conectando a base de datos...")
    print(f"   Host: {settings.POSTGRES_HOST}")
    print(f"   Database: {settings.POSTGRES_DB}")
    
    try:
        # Conectar a la base de datos
        conn = await asyncpg.connect(settings.DATABASE_URL)
        print("✅ Conexión exitosa")
        
        # 1. Verificar estado actual
        existing_tables, missing_tables = await check_existing_tables(conn)
        
        if not missing_tables:
            print("\n🎉 ¡Todas las tablas ya existen! La migración no es necesaria.")
            await conn.close()
            return True
        
        print(f"\n📋 Tablas faltantes: {missing_tables}")
        
        # 2. Crear backup de datos existentes
        await backup_existing_data(conn)
        
        # 3. Ejecutar scripts de migración en orden
        scripts_dir = Path(__file__).parent
        
        migration_scripts = [
            (scripts_dir / "init_database.sql", "Inicialización de base de datos"),
            (scripts_dir / "create_metrics_tables.sql", "Tablas de métricas y conversaciones"),
            (scripts_dir / "create_admin_tables.sql", "Tablas de administración"),
        ]
        
        for script_path, description in migration_scripts:
            if script_path.exists():
                success = await execute_sql_file(conn, script_path, description)
                if not success and "metrics" in description:
                    print("   ⚠️  Las tablas de métricas son críticas para el funcionamiento")
            else:
                print(f"   ⚠️  Script opcional no encontrado: {script_path.name}")
        
        # 4. Verificar migración
        success = await verify_migration(conn)
        
        await conn.close()
        
        if success:
            print("\n🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
            print("\n📋 PRÓXIMOS PASOS:")
            print("   1. Reiniciar los servicios de producción:")
            print("      ./scripts/docker-production.sh restart")
            print("   2. Verificar que el dashboard muestra estadísticas correctas")
            print("   3. Probar que las conversaciones se registran")
            return True
        else:
            print("\n❌ MIGRACIÓN FALLÓ - Revisar errores anteriores")
            return False
            
    except Exception as e:
        print(f"❌ Error crítico en migración: {e}")
        import traceback
        traceback.print_exc()
        return False

async def dry_run_migration():
    """Ejecutar una simulación de la migración para verificar qué se haría"""
    
    print("🔍 SIMULACIÓN DE MIGRACIÓN (DRY RUN)")
    print("=" * 40)
    
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        print("✅ Conexión exitosa")
        
        existing_tables, missing_tables = await check_existing_tables(conn)
        
        print(f"\n📊 RESUMEN:")
        print(f"   Tablas existentes: {len(existing_tables)}")
        print(f"   Tablas faltantes: {len(missing_tables)}")
        
        if missing_tables:
            print(f"\n📋 Se crearían las siguientes tablas:")
            for table in missing_tables:
                print(f"   - {table}")
        else:
            print(f"\n✅ No se requiere migración")
        
        await conn.close()
        return len(missing_tables) > 0
        
    except Exception as e:
        print(f"❌ Error en dry run: {e}")
        return False

if __name__ == "__main__":
    print("🗄️  MIGRACIÓN DE BASE DE DATOS DE PRODUCCIÓN")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        print("Ejecutando simulación...")
        needs_migration = asyncio.run(dry_run_migration())
        if needs_migration:
            print("\n⚠️  Se requiere migración. Ejecuta sin --dry-run para aplicar cambios.")
            sys.exit(1)
        else:
            print("\n✅ No se requiere migración.")
            sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("Ejecutando migración forzada...")
        success = asyncio.run(migrate_production_database())
        sys.exit(0 if success else 1)
    else:
        print("\nUSO:")
        print("  python scripts/migrate_production_database.py --dry-run    # Simular migración")
        print("  python scripts/migrate_production_database.py --force      # Ejecutar migración")
        print("\n⚠️  IMPORTANTE: Crear backup manual antes de ejecutar con --force")
        sys.exit(1)