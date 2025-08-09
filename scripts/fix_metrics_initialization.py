#!/usr/bin/env python3
"""
Script para verificar y corregir la inicialización del MetricsService
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

async def check_metrics_initialization():
    """Verificar el estado de inicialización del MetricsService"""
    
    print("🔍 Verificando inicialización del MetricsService...")
    print("=" * 60)
    
    # Test 1: Importar y verificar la variable global
    print("\n📋 Test 1: Verificando variable global metrics_service")
    try:
        from app import metrics_service
        if metrics_service is None:
            print("❌ metrics_service es None en app.py")
        else:
            print("✅ metrics_service está definido")
            print(f"   Tipo: {type(metrics_service)}")
            print(f"   Pool: {metrics_service.pool}")
    except ImportError as e:
        print(f"❌ Error importando: {e}")
    
    # Test 2: Verificar si se puede crear una instancia nueva
    print("\n📋 Test 2: Creando nueva instancia de MetricsService")
    try:
        from services.metrics_service import MetricsService
        from config.settings import settings
        
        # Crear nueva instancia
        test_service = MetricsService(settings.DATABASE_URL)
        await test_service.initialize()
        print("✅ Nueva instancia creada e inicializada")
        
        # Probar una query simple
        async with test_service.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
            print(f"   ✅ Query exitosa: {count} conversaciones en BD")
        
        await test_service.close()
        
    except Exception as e:
        print(f"❌ Error creando instancia: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Verificar el startup_event
    print("\n📋 Test 3: Verificando función startup_event")
    try:
        from app import startup_event
        print("✅ startup_event importado correctamente")
        
        # Verificar si hay algún error en el startup
        print("\n🔄 Ejecutando startup_event manualmente...")
        await startup_event()
        
        # Verificar de nuevo después del startup
        from app import metrics_service as ms_after
        if ms_after is not None:
            print("✅ metrics_service inicializado después de startup_event")
        else:
            print("❌ metrics_service sigue siendo None después de startup")
            
    except Exception as e:
        print(f"❌ Error en startup_event: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Diagnóstico de inicialización del MetricsService")
    asyncio.run(check_metrics_initialization())