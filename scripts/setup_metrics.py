#!/usr/bin/env python3
"""
Script para configurar las tablas de métricas en la base de datos
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Agregar el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings


async def setup_metrics_tables():
    """Crear tablas de métricas en la base de datos"""
    
    print("🚀 Configurando tablas de métricas...")
    
    try:
        # Conectar a la base de datos
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Leer el script SQL
        sql_file = Path(__file__).parent / "create_metrics_tables.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Ejecutar el script
        print("📝 Creando tablas de métricas...")
        await conn.execute(sql_script)
        
        print("✅ Tablas de métricas creadas exitosamente")
        
        # Verificar que las tablas se crearon
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN (
                'conversations', 
                'conversation_messages', 
                'metrics_hourly',
                'metrics_daily',
                'popular_topics',
                'metric_events',
                'tool_metrics'
            )
        """)
        
        print(f"\n📊 Tablas creadas ({len(tables)}):")
        for table in tables:
            print(f"  - {table['tablename']}")
        
        # Verificar funciones
        functions = await conn.fetch("""
            SELECT proname FROM pg_proc 
            WHERE pronamespace = 'public'::regnamespace
            AND proname IN (
                'cleanup_old_metrics_data',
                'aggregate_hourly_metrics',
                'aggregate_daily_metrics'
            )
        """)
        
        print(f"\n⚙️ Funciones creadas ({len(functions)}):")
        for func in functions:
            print(f"  - {func['proname']}()")
        
        # Verificar vistas
        views = await conn.fetch("""
            SELECT viewname FROM pg_views 
            WHERE schemaname = 'public' 
            AND viewname = 'dashboard_stats'
        """)
        
        if views:
            print(f"\n👁️ Vistas creadas:")
            for view in views:
                print(f"  - {view['viewname']}")
        
        # Cerrar conexión
        await conn.close()
        
        print("\n✅ Configuración de métricas completada exitosamente")
        print("\n📌 Notas importantes:")
        print("  - Las conversaciones se eliminan automáticamente después de 30 días")
        print("  - Los mensajes detallados se eliminan después de 7 días")
        print("  - Las métricas agregadas se mantienen permanentemente")
        print("  - El scheduler de limpieza se ejecuta automáticamente a las 3 AM")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo SQL: {sql_file}")
        return False
        
    except Exception as e:
        print(f"❌ Error configurando métricas: {e}")
        return False


async def test_metrics_service():
    """Probar el servicio de métricas"""
    
    print("\n🧪 Probando servicio de métricas...")
    
    try:
        from services.metrics_service import MetricsService
        
        # Crear instancia del servicio
        metrics = MetricsService(settings.DATABASE_URL)
        await metrics.initialize()
        
        # Crear una conversación de prueba
        print("📝 Creando conversación de prueba...")
        conversation_id = await metrics.start_conversation(
            user_id="test_user_123",
            platform="wordpress",
            channel_details={"test": True}
        )
        print(f"  Conversación creada: {conversation_id}")
        
        # Registrar algunos mensajes
        print("💬 Registrando mensajes...")
        await metrics.track_message(
            conversation_id=conversation_id,
            sender_type="user",
            content="¿Cuál es el precio del producto ABC?",
            intent="product_inquiry"
        )
        
        await asyncio.sleep(0.1)  # Simular delay
        
        await metrics.track_message(
            conversation_id=conversation_id,
            sender_type="bot",
            content="El producto ABC cuesta 25€",
            response_time_ms=150
        )
        
        # Registrar un tema popular
        await metrics.track_topic(
            topic="product_inquiry",
            category="chat",
            query="precio producto",
            resolution_time_minutes=0.5,
            success=True
        )
        
        # Finalizar conversación
        await metrics.end_conversation(
            conversation_id=conversation_id,
            status="ended",
            user_satisfaction=5
        )
        
        print("✅ Conversación de prueba completada")
        
        # Obtener estadísticas
        print("\n📊 Obteniendo estadísticas...")
        stats = await metrics.get_dashboard_stats()
        
        print(f"  Conversaciones hoy: {stats['today']['conversations']}")
        print(f"  Usuarios únicos: {stats['today']['unique_users']}")
        print(f"  Plataformas: {stats['platforms']}")
        
        # Cerrar servicio
        await metrics.close()
        
        print("\n✅ Prueba del servicio completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error probando servicio: {e}")


async def main():
    """Función principal"""
    
    # Configurar tablas
    success = await setup_metrics_tables()
    
    if success:
        # Probar el servicio
        await test_metrics_service()
    
    print("\n🎉 Script completado")


if __name__ == "__main__":
    asyncio.run(main())