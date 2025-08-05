#!/usr/bin/env python3
"""
Script de inicio para los servicios de Eva
Inicia el servidor MCP y la interfaz web de manera coordinada
"""

import asyncio
import subprocess
import sys
import time
import signal
import os
from typing import List

class ServiceManager:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = True
        
    def start_mcp_server(self):
        """Inicia el servidor MCP en modo HTTP"""
        print("🚀 Iniciando servidor MCP...")
        # Usar el Python del entorno virtual
        python_path = os.path.join("venv", "bin", "python3")
        if not os.path.exists(python_path):
            python_path = sys.executable  # Fallback al Python actual
        
        process = subprocess.Popen([
            python_path, "main.py"
        ])
        self.processes.append(process)
        return process
        
    def start_web_interface(self):
        """Inicia la interfaz web"""
        print("🌐 Iniciando interfaz web...")
        # Usar el Python del entorno virtual
        python_path = os.path.join("venv", "bin", "python3")
        if not os.path.exists(python_path):
            python_path = sys.executable  # Fallback al Python actual
            
        process = subprocess.Popen([
            python_path, "app.py"
        ])
        self.processes.append(process)
        return process
        
    def wait_for_mcp_ready(self, timeout=30):
        """Espera a que el servidor MCP esté listo"""
        import requests
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Probar con la URL correcta y headers apropiados
                response = requests.get(
                    "http://localhost:8000/mcp/", 
                    timeout=2,
                    headers={"Accept": "text/event-stream"}
                )
                # El servidor MCP puede responder con 400, 406 o 200 dependiendo de la configuración
                # Todos estos códigos indican que el servidor está funcionando
                if response.status_code in [200, 400, 406]:
                    print("✅ Servidor MCP está listo")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
            
        print("⚠️ Timeout esperando servidor MCP")
        return False
        
    def signal_handler(self, signum, frame):
        """Maneja señales de terminación"""
        print("\n🛑 Cerrando servicios...")
        self.running = False
        self.cleanup()
        sys.exit(0)
        
    def cleanup(self):
        """Limpia procesos al cerrar"""
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
    def run(self):
        """Ejecuta ambos servicios"""
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            print("🌟 Eva - Sistema de Atención al Cliente")
            print("=" * 50)
            
            # Iniciar servidor MCP
            mcp_process = self.start_mcp_server()
            
            # Esperar a que MCP esté listo (más tiempo para inicialización)
            print("⏳ Esperando a que el servidor MCP esté listo...")
            if not self.wait_for_mcp_ready(timeout=45):
                print("❌ Error: No se pudo iniciar el servidor MCP")
                self.cleanup()
                return
                
            # Dar un poco más de tiempo para estabilización
            time.sleep(3)
            
            # Iniciar interfaz web
            web_process = self.start_web_interface()
            
            # Esperar un poco para que se inicialice
            print("⏳ Esperando a que la interfaz web esté lista...")
            time.sleep(5)
            
            print("\n✅ Servicios iniciados correctamente!")
            print("=" * 50)
            print("🔗 Servidor MCP: http://localhost:8000/mcp")
            print("🌐 Interfaz Web: http://localhost:8080")
            print("=" * 50)
            print("Presiona Ctrl+C para detener todos los servicios")
            
            # Monitorear procesos
            while self.running:
                # Verificar si algún proceso ha terminado
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        print(f"⚠️ Proceso {i} terminó inesperadamente")
                        
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupción recibida")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.cleanup()

if __name__ == "__main__":
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("main.py") or not os.path.exists("app.py"):
        print("❌ Error: Ejecuta este script desde el directorio raíz del proyecto")
        sys.exit(1)
        
    # Verificar dependencias
    try:
        import requests
    except ImportError:
        print("📦 Instalando requests...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    manager = ServiceManager()
    manager.run() 