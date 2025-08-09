#!/usr/bin/env python3
"""
Script para debuggear por qué los cambios no se persisten en knowledge base
"""

import asyncio
import sys
from pathlib import Path
import hashlib
import time

# Agregar path de la aplicación
sys.path.insert(0, '/app' if Path('/app').exists() else '.')

async def debug_save_process():
    try:
        print("🔍 Debugging knowledge save process...")
        
        # 1. Verificar el archivo antes del cambio
        file_path = Path("knowledge/store_info.md")
        print(f"\n📋 1. Estado inicial del archivo:")
        print(f"   - Existe: {file_path.exists()}")
        
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            original_hash = hashlib.md5(original_content.encode()).hexdigest()
            print(f"   - Tamaño: {len(original_content)} caracteres")
            print(f"   - Hash MD5: {original_hash}")
            print(f"   - Primeras 200 chars: {original_content[:200]}")
        
        # 2. Simular el proceso de guardado
        print(f"\n📋 2. Simulando proceso de guardado:")
        
        from api.admin.knowledge import update_document, KnowledgeUpdate
        
        test_content = f"# Store Info - Test Update\n\nContenido actualizado a las: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\nEste es contenido de prueba."
        
        update = KnowledgeUpdate(
            content=test_content,
            title="Store Info - Test"
        )
        
        mock_admin = {"id": 1, "username": "admin"}
        
        print(f"   - Nuevo contenido ({len(test_content)} chars):")
        print(f"   - Hash nuevo: {hashlib.md5(test_content.encode()).hexdigest()}")
        
        # 3. Ejecutar la actualización
        try:
            result = await update_document(
                filename="store_info.md",
                update=update,
                current_admin=mock_admin
            )
            print(f"   ✅ Resultado del endpoint: {result}")
        except Exception as e:
            print(f"   ❌ Error en endpoint: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 4. Verificar el archivo después del cambio
        print(f"\n📋 3. Estado después del guardado:")
        
        if file_path.exists():
            # Dar un momento para que se escriba el archivo
            await asyncio.sleep(1)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                new_content = f.read()
            new_hash = hashlib.md5(new_content.encode()).hexdigest()
            
            print(f"   - Tamaño después: {len(new_content)} caracteres")
            print(f"   - Hash MD5 después: {new_hash}")
            print(f"   - ¿Cambió el hash? {'SÍ' if new_hash != original_hash else 'NO'}")
            print(f"   - Primeras 200 chars después: {new_content[:200]}")
            
            if new_hash == original_hash:
                print("\n❌ EL ARCHIVO NO CAMBIÓ - Investigando...")
                
                # Verificar permisos
                import os, stat
                file_stat = file_path.stat()
                print(f"   - Permisos: {oct(file_stat.st_mode)}")
                print(f"   - Owner: UID={file_stat.st_uid}, GID={file_stat.st_gid}")
                print(f"   - Proceso actual: UID={os.getuid()}, GID={os.getgid()}")
                
                # Intentar escribir directamente
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("# Test Direct Write\nPrueba de escritura directa")
                    print("   ✅ Escritura directa funcionó")
                except Exception as e:
                    print(f"   ❌ Escritura directa falló: {e}")
                    
        else:
            print("   ❌ Archivo no existe después del guardado")
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

async def check_aiofiles():
    """Verificar si aiofiles funciona correctamente"""
    try:
        import aiofiles
        print(f"\n🔍 Verificando aiofiles:")
        
        test_file = Path("knowledge/test_aiofiles.txt")
        test_content = f"Test aiofiles - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Escribir con aiofiles
        async with aiofiles.open(test_file, 'w', encoding='utf-8') as f:
            await f.write(test_content)
        
        print(f"   ✅ Escritura con aiofiles completada")
        
        # Verificar que se escribió
        if test_file.exists():
            with open(test_file, 'r', encoding='utf-8') as f:
                read_content = f.read()
            print(f"   - Contenido leído: {read_content}")
            print(f"   - ¿Coincide? {'SÍ' if read_content == test_content else 'NO'}")
            
            # Limpiar archivo de prueba
            test_file.unlink()
        else:
            print(f"   ❌ Archivo no existe después de escribir con aiofiles")
            
    except Exception as e:
        print(f"❌ Error con aiofiles: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Debug Knowledge Save Process")
    print("=" * 50)
    asyncio.run(check_aiofiles())
    asyncio.run(debug_save_process())