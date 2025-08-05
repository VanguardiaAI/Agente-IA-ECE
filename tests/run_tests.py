#!/usr/bin/env python3
"""
Script maestro para ejecutar todas las pruebas del sistema
"""

import asyncio
import subprocess
import sys
import os
from datetime import datetime

def run_script(script_name: str, description: str) -> bool:
    """Ejecutar un script de prueba"""
    print(f"\n{'='*60}")
    print(f"🚀 EJECUTANDO: {description}")
    print(f"📄 Script: {script_name}")
    print(f"⏰ Hora: {datetime.now().strftime('%H:%M:%S')}")
    print('='*60)
    
    try:
        # Ejecutar el script
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,  # Mostrar output en tiempo real
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} - COMPLETADO EXITOSAMENTE")
            return True
        else:
            print(f"\n❌ {description} - FALLÓ (código: {result.returncode})")
            return False
            
    except FileNotFoundError:
        print(f"\n❌ {description} - ARCHIVO NO ENCONTRADO: {script_name}")
        return False
    except Exception as e:
        print(f"\n❌ {description} - ERROR: {str(e)}")
        return False

def print_header():
    """Imprimir encabezado del sistema de pruebas"""
    print("🧪 SISTEMA DE PRUEBAS - CUSTOMER SERVICE ASSISTANT")
    print("=" * 60)
    print("📅 Fecha:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🐍 Python:", sys.version.split()[0])
    print("📁 Directorio:", os.getcwd())
    print("=" * 60)

def print_summary(results: dict):
    """Imprimir resumen final de todas las pruebas"""
    print("\n" + "="*60)
    print("📋 RESUMEN FINAL DE TODAS LAS PRUEBAS")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests
    
    print(f"📊 Total de suites de prueba: {total_tests}")
    print(f"✅ Suites exitosas: {passed_tests}")
    print(f"❌ Suites fallidas: {failed_tests}")
    
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")
    
    print("\n📝 Detalle por suite:")
    for test_name, success in results.items():
        status = "✅ ÉXITO" if success else "❌ FALLO"
        print(f"   • {test_name}: {status}")
    
    print("\n💡 Recomendaciones:")
    if success_rate == 100:
        print("   🎉 ¡Perfecto! Todos los sistemas funcionan correctamente")
        print("   🚀 El agente está listo para producción")
    elif success_rate >= 80:
        print("   ✅ Sistema en buen estado con problemas menores")
        print("   🔧 Revisa los fallos para optimización")
    elif success_rate >= 60:
        print("   ⚠️  Sistema funcional pero requiere atención")
        print("   🛠️  Corrige los errores antes de usar en producción")
    else:
        print("   🚨 Sistema con problemas críticos")
        print("   ⛔ NO usar en producción hasta corregir errores")
    
    return success_rate >= 80

def main():
    """Función principal del sistema de pruebas"""
    print_header()
    
    # Definir las pruebas a ejecutar
    test_suites = [
        {
            "script": "test_connection.py",
            "name": "Pruebas de Conexión",
            "description": "Verificar conexiones con WooCommerce y MongoDB Atlas",
            "critical": True
        },
        {
            "script": "test_tools.py", 
            "name": "Pruebas de Herramientas",
            "description": "Probar todas las herramientas MCP individualmente",
            "critical": True
        },
        {
            "script": "test_mcp_server.py",
            "name": "Pruebas del Servidor MCP",
            "description": "Probar el servidor MCP completo con simulaciones reales",
            "critical": True
        }
    ]
    
    results = {}
    critical_failures = 0
    
    print(f"\n🎯 Se ejecutarán {len(test_suites)} suites de prueba:")
    for i, suite in enumerate(test_suites, 1):
        critical_mark = "🔴" if suite["critical"] else "🟡"
        print(f"   {i}. {critical_mark} {suite['name']} - {suite['description']}")
    
    print(f"\n⏳ Iniciando ejecución secuencial...")
    
    # Ejecutar cada suite de pruebas
    for suite in test_suites:
        success = run_script(suite["script"], suite["name"])
        results[suite["name"]] = success
        
        if not success and suite["critical"]:
            critical_failures += 1
            print(f"\n⚠️  FALLO CRÍTICO detectado en: {suite['name']}")
    
    # Mostrar resumen final
    overall_success = print_summary(results)
    
    # Determinar código de salida
    if critical_failures > 0:
        print(f"\n🚨 ATENCIÓN: {critical_failures} fallo(s) crítico(s) detectado(s)")
        print("   El sistema NO está listo para uso en producción")
        return False
    elif overall_success:
        print(f"\n🎉 ¡ÉXITO COMPLETO!")
        print("   Todos los sistemas funcionan correctamente")
        print("   El agente está listo para usar")
        return True
    else:
        print(f"\n⚠️  ÉXITO PARCIAL")
        print("   El sistema funciona pero tiene problemas menores")
        print("   Revisa los errores antes de usar en producción")
        return False

if __name__ == "__main__":
    try:
        success = main()
        
        print(f"\n{'='*60}")
        if success:
            print("🏁 PRUEBAS COMPLETADAS - SISTEMA LISTO")
            print("   Ejecuta: python main.py")
        else:
            print("🏁 PRUEBAS COMPLETADAS - REQUIERE ATENCIÓN")
            print("   Revisa los errores antes de continuar")
        print('='*60)
        
        # Código de salida para scripts automatizados
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Pruebas interrumpidas por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error crítico en el sistema de pruebas: {e}")
        sys.exit(1) 